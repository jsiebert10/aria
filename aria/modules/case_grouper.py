"""Case grouper module — Claude API analysis of crime narratives."""

from __future__ import annotations

from dash import Dash, Input, Output, State, ctx, dcc, html
from dash.exceptions import PreventUpdate

from aria.data.store import DataStore
from aria.modules.base import BaseModule
from aria.services.claude_api import ClaudeApiClient
from aria.theme import Theme

_CASE_ANALYSIS_PROMPT = """Eres un analista criminal experto. Analiza estos {n} relatos y responde EXACTAMENTE en este formato usando markdown. Sé conciso.

## Resumen por caso
Para cada caso, solo:
- **Tipo de delito:**
- **Lugar y hora:**
- **MO resumido en una línea:**
- **Vehículos/especies clave:**

## Coincidencias principales
(tabla markdown con las variables que coinciden entre casos)

## Similitud
(un porcentaje por cada par de casos, en formato: Caso X vs Caso Y: XX%)

## Clasificación
**Nivel:** Sin relación / Alerta / Foco investigativo
**Criterio:** (una línea explicando por qué)

## Recomendación
(máximo dos líneas)

Relatos:
{narratives}"""


class CaseGrouperModule(BaseModule):
    """Compares up to 4 crime narratives using Claude API."""

    module_id = "agrupador"
    display_name = "Agrupador de casos"

    def __init__(
        self, store: DataStore, theme: Theme, claude: ClaudeApiClient,
    ) -> None:
        super().__init__(store, theme)
        self._claude = claude

    def get_layout(self) -> html.Div:
        t = self._theme
        label_style = {
            "fontFamily": t.font_mono, "fontSize": "9px", "color": t.text3,
            "textTransform": "uppercase", "letterSpacing": "1px",
            "display": "block", "marginBottom": "5px",
        }
        ta_style = {
            "width": "100%", "background": t.bg3,
            "border": f"1px solid {t.border}", "color": t.text,
            "padding": "10px 12px", "fontSize": "12px", "lineHeight": "1.6",
            "fontFamily": t.font_sans, "outline": "none", "resize": "vertical",
            "minHeight": "140px",
        }

        cases = []
        for i in range(1, 5):
            opt = " (opcional)" if i > 2 else ""
            cases.append(html.Div([
                html.Label(f"Relato · Caso {i}{opt}", style=label_style),
                dcc.Textarea(
                    id=f"ag-caso{i}",
                    placeholder=f"Pega el relato {i} recodificado...",
                    style=ta_style,
                ),
            ]))

        return html.Div(className="modulo-wrap", children=[
            html.Div(className="mod-header", children=[
                html.Div([
                    html.Div("Análisis · IA", className="mod-eyebrow"),
                    html.Div("Agrupador de casos", className="mod-title"),
                    html.Div(
                        "Detecta similitudes entre relatos y recomienda foco investigativo",
                        className="mod-sub",
                    ),
                ]),
                html.Div(className="mod-actions", children=[
                    html.Span(
                        "Claude API · Nivel 2 · supervisión humana obligatoria",
                        style={"fontFamily": t.font_mono, "fontSize": "9px", "color": t.text3},
                    ),
                ]),
            ]),
            html.Div(className="mod-body", children=[
                self._privacy_notice(),
                html.Div(className="grid grid-2", children=cases),
                html.Div(style={
                    "display": "flex", "alignItems": "center",
                    "gap": "12px", "margin": "4px 0",
                }, children=[
                    html.Button("Analizar casos →", id="btn-ag-analizar", n_clicks=0,
                        style={
                            "fontFamily": t.font_mono, "fontSize": "11px",
                            "padding": "8px 20px", "background": t.amber,
                            "border": f"1px solid {t.amber}", "color": "#0a0e14",
                            "cursor": "pointer", "fontWeight": "600",
                            "letterSpacing": ".5px",
                        }),
                    html.Button("Limpiar", id="btn-ag-limpiar", n_clicks=0,
                        style={
                            "fontFamily": t.font_mono, "fontSize": "11px",
                            "padding": "8px 16px", "background": "transparent",
                            "border": f"1px solid {t.border}", "color": t.text2,
                            "cursor": "pointer",
                        }),
                    html.Div(id="ag-status", style={
                        "fontFamily": t.font_mono, "fontSize": "10px", "color": t.text3,
                    }),
                ]),
                html.Div(id="ag-resultado", style={"display": "none"}, children=[
                    html.Div(className="panel", children=[
                        html.Div([
                            "Resultado del análisis",
                            html.Span(
                                "supervisión humana requerida antes de cualquier acción",
                                className="tag",
                            ),
                        ], className="panel-title"),
                        html.Div(id="ag-output", style={
                            "fontSize": "12px", "lineHeight": "1.8", "color": t.text2,
                            "whiteSpace": "pre-wrap", "fontFamily": t.font_sans,
                        }),
                        html.Div(style={
                            "marginTop": "12px", "paddingTop": "10px",
                            "borderTop": f"1px solid {t.border}",
                            "display": "flex", "justifyContent": "space-between",
                            "alignItems": "center",
                        }, children=[
                            html.Div(
                                "Este resultado es una sugerencia analítica. "
                                "El analista decide si existe mérito investigativo.",
                                style={
                                    "fontFamily": t.font_mono,
                                    "fontSize": "9px", "color": t.text3,
                                },
                            ),
                            html.Button("↓ Descargar resultado", id="btn-ag-dl", n_clicks=0,
                                style={
                                    "fontFamily": t.font_mono, "fontSize": "10px",
                                    "padding": "5px 12px", "background": "transparent",
                                    "border": f"1px solid {t.border}", "color": t.text2,
                                    "cursor": "pointer",
                                }),
                        ]),
                        dcc.Download(id="dl-ag-txt"),
                    ]),
                ]),
            ]),
        ])

    def register_callbacks(self, app: Dash) -> None:
        claude = self._claude

        @app.callback(
            Output("ag-output", "children"),
            Output("ag-resultado", "style"),
            Output("ag-status", "children"),
            Output("ag-caso1", "value"),
            Output("ag-caso2", "value"),
            Output("ag-caso3", "value"),
            Output("ag-caso4", "value"),
            Input("btn-ag-analizar", "n_clicks"),
            Input("btn-ag-limpiar", "n_clicks"),
            State("ag-caso1", "value"),
            State("ag-caso2", "value"),
            State("ag-caso3", "value"),
            State("ag-caso4", "value"),
            prevent_initial_call=True,
        )
        def analyze(n_analyze: int, n_clear: int, c1, c2, c3, c4):
            triggered = ctx.triggered_id

            if triggered == "btn-ag-limpiar":
                return "", {"display": "none"}, "", "", "", "", ""
            if triggered != "btn-ag-analizar":
                raise PreventUpdate

            narratives = {}
            for i, text in enumerate([c1, c2, c3, c4], 1):
                if text and text.strip():
                    narratives[f"Caso {i}"] = text.strip()

            if len(narratives) < 2:
                return (
                    "", {"display": "none"},
                    "⚠ Ingresa al menos dos relatos para comparar.",
                    c1, c2, c3, c4,
                )

            narratives_text = "\n\n".join(
                f"**{k}:**\n{v}" for k, v in narratives.items()
            )
            prompt = _CASE_ANALYSIS_PROMPT.format(
                n=len(narratives), narratives=narratives_text,
            )
            result = claude.send_prompt(prompt)

            return (
                result, {"display": "block"},
                f"✓ Análisis completado · {len(narratives)} casos",
                c1, c2, c3, c4,
            )

        @app.callback(
            Output("dl-ag-txt", "data"),
            Input("btn-ag-dl", "n_clicks"),
            State("ag-output", "children"),
            prevent_initial_call=True,
        )
        def download(n: int, text: str):
            if not n or not text:
                raise PreventUpdate
            return dcc.send_string(str(text), "agrupador_resultado.txt")

    def _privacy_notice(self) -> html.Div:
        t = self._theme
        return html.Div(style={
            "background": f"{t.amber}0d",
            "border": f"1px solid {t.amber2}44",
            "borderLeft": f"3px solid {t.amber}",
            "padding": "10px 14px", "marginBottom": "14px",
            "fontSize": "11px", "lineHeight": "1.6", "color": t.text2,
            "fontFamily": t.font_mono,
        }, children=[
            html.Span(
                "⚠ Protocolo de privacidad · Nivel 2  ",
                style={"color": t.amber, "fontWeight": "600"},
            ),
            "Antes de pegar un relato, elimina: nombres, RUT, direcciones exactas, "
            "teléfonos y cualquier dato que identifique directamente a personas. "
            "Los textos se envían a Claude API externa. "
            "Si el relato contiene menores de edad, no lo incluyas.",
        ])
