"""Policy brief generator module — Claude API executive brief production."""

from __future__ import annotations

from datetime import date

from dash import Dash, Input, Output, State, ctx, dcc, html
from dash.exceptions import PreventUpdate

from aria.data.store import DataStore
from aria.modules.base import BaseModule
from aria.services.claude_api import ClaudeApiClient
from aria.theme import Theme

_URGENCY_OPTIONS = [
    {"label": "Monitoreo", "value": "Monitoreo"},
    {"label": "Alerta", "value": "Alerta"},
    {"label": "Acción inmediata", "value": "Acción inmediata"},
]

_LEVEL_OPTIONS = [
    {"label": "Emergente", "value": "Emergente"},
    {"label": "En desarrollo", "value": "En desarrollo"},
    {"label": "Consolidado", "value": "Consolidado"},
]

_POLICY_BRIEF_PROMPT = """Eres un analista criminal experto con formación en criminología y políticas públicas de seguridad.
Redacta un policy brief ejecutivo pero con respaldo técnico-criminológico, dirigido a jefaturas de Fiscalía, Directores de Seguridad Municipal y autoridades.
Usa lenguaje directo y accesible, pero con asidero teórico. Responde EXACTAMENTE en este formato usando markdown:

---

# POLICY BRIEF — ALERTA DE FENÓMENO DELICTUAL

**Fecha:** {date}
**Elaborado por:** {author}
**Nivel de urgencia:** {urgency}

---

## Resumen Ejecutivo
(3-4 líneas máximo)

---

## Descripción del Fenómeno
(Máximo 150 palabras)

---

## Marco Criminológico
(Máximo 100 palabras, menciona 1 o 2 teorías relevantes explicadas de forma accesible)

---

## Impacto Potencial
- **Corto plazo:**
- **Mediano plazo:**
- **Riesgo de no actuar:**

---

## Anticipación y Recomendaciones

### Para Fiscalía
(2-3 líneas concretas)

### Para Municipios / Directores de Seguridad
(2-3 líneas concretas)

### Para Unidades Policiales
(2-3 líneas concretas)

---

## Nivel de Evidencia
**Solidez del fenómeno:** {level}
**Fuente:** Análisis de relatos / Registros institucionales

---

Fenómeno descrito por el analista:
{phenomenon}
{supporting}"""


class PolicyBriefModule(BaseModule):
    """Generates IALEIA-standard executive briefs via Claude API."""

    module_id = "policy"
    display_name = "Policy Brief · IA"

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
            "display": "block", "marginBottom": "4px", "marginTop": "12px",
        }
        ta_style = {
            "width": "100%", "background": t.bg3,
            "border": f"1px solid {t.border}", "color": t.text,
            "padding": "10px 12px", "fontSize": "12px", "lineHeight": "1.6",
            "fontFamily": t.font_sans, "outline": "none", "resize": "vertical",
        }
        input_style = {
            "width": "100%", "background": t.bg3,
            "border": f"1px solid {t.border}", "color": t.text,
            "padding": "7px 10px", "fontSize": "12px",
            "fontFamily": t.font_sans, "outline": "none", "marginTop": "4px",
        }

        return html.Div(className="modulo-wrap", children=[
            html.Div(className="mod-header", children=[
                html.Div([
                    html.Div("Productos · IA", className="mod-eyebrow"),
                    html.Div("Generador de Policy Brief", className="mod-title"),
                    html.Div(
                        "Produce minutas ejecutivas con respaldo criminológico · IALEIA",
                        className="mod-sub",
                    ),
                ]),
                html.Div(className="mod-actions", children=[
                    html.Span(
                        "Claude API · supervisión humana antes de distribuir",
                        style={"fontFamily": t.font_mono, "fontSize": "9px", "color": t.text3},
                    ),
                ]),
            ]),
            html.Div(className="mod-body", children=[
                self._privacy_notice(),
                html.Div(className="grid grid-sidebar", children=[
                    html.Div(className="panel", children=[
                        html.Div("Configuración del brief", className="panel-title"),
                        html.Label("Nivel de urgencia", style=label_style),
                        dcc.Dropdown(id="pb-urgencia", className="dropdown",
                            options=_URGENCY_OPTIONS, value="Alerta", clearable=False),
                        html.Label("Solidez del fenómeno", style=label_style),
                        dcc.Dropdown(id="pb-nivel", className="dropdown",
                            options=_LEVEL_OPTIONS, value="En desarrollo", clearable=False),
                        html.Label("Elaborado por", style=label_style),
                        dcc.Input(id="pb-autor", type="text", value="Equipo AMSZO",
                                  style=input_style),
                        html.Div(style={
                            "height": "1px", "background": t.border, "margin": "16px 0",
                        }),
                        html.Label("Descripción del fenómeno *", style=label_style),
                        dcc.Textarea(id="pb-fenomeno",
                            placeholder=(
                                "Describe el fenómeno delictual que estás observando. "
                                "Incluye: tipo de delito, zona general, frecuencia, "
                                "características del MO, tendencia observada..."
                            ),
                            style={**ta_style, "minHeight": "160px"}),
                        html.Label("Relato de respaldo 1 (opcional · recodificado)",
                                   style=label_style),
                        dcc.Textarea(id="pb-relato1",
                            placeholder="Relato depurado sin identificadores...",
                            style={**ta_style, "minHeight": "100px"}),
                        html.Label("Relato de respaldo 2 (opcional · recodificado)",
                                   style=label_style),
                        dcc.Textarea(id="pb-relato2",
                            placeholder="Relato depurado sin identificadores...",
                            style={**ta_style, "minHeight": "100px"}),
                        html.Div(style={"marginTop": "14px", "display": "flex", "gap": "8px"}, children=[
                            html.Button("Generar Policy Brief →", id="btn-pb-gen", n_clicks=0,
                                style={
                                    "fontFamily": t.font_mono, "fontSize": "11px",
                                    "padding": "8px 18px", "background": t.amber,
                                    "border": f"1px solid {t.amber}", "color": "#0a0e14",
                                    "cursor": "pointer", "fontWeight": "600",
                                    "letterSpacing": ".5px",
                                }),
                            html.Button("Limpiar", id="btn-pb-limpiar", n_clicks=0,
                                style={
                                    "fontFamily": t.font_mono, "fontSize": "11px",
                                    "padding": "8px 14px", "background": "transparent",
                                    "border": f"1px solid {t.border}", "color": t.text2,
                                    "cursor": "pointer",
                                }),
                        ]),
                        html.Div(id="pb-status", style={
                            "fontFamily": t.font_mono, "fontSize": "10px",
                            "color": t.text3, "marginTop": "8px",
                        }),
                    ]),
                    html.Div(style={
                        "display": "flex", "flexDirection": "column", "gap": "10px",
                    }, children=[
                        html.Div(id="pb-resultado", children=[
                            self._preview_placeholder(),
                        ]),
                        html.Div(id="pb-dl-row", style={"display": "none"}, children=[
                            html.Div(style={"display": "flex", "gap": "8px"}, children=[
                                html.Button("↓ Descargar como texto", id="btn-pb-dl", n_clicks=0,
                                    style={
                                        "fontFamily": t.font_mono, "fontSize": "10px",
                                        "padding": "6px 14px", "background": "transparent",
                                        "border": f"1px solid {t.border}", "color": t.text2,
                                        "cursor": "pointer",
                                    }),
                                html.Button("Agregar al reporte IALEIA →", id="btn-pb-ialeia", n_clicks=0,
                                    style={
                                        "fontFamily": t.font_mono, "fontSize": "10px",
                                        "padding": "6px 14px", "background": f"{t.amber}18",
                                        "border": f"1px solid {t.amber2}", "color": t.amber,
                                        "cursor": "pointer",
                                    }),
                            ]),
                            dcc.Download(id="dl-pb-txt"),
                        ]),
                    ]),
                ]),
            ]),
        ])

    def register_callbacks(self, app: Dash) -> None:
        claude = self._claude
        theme = self._theme

        @app.callback(
            Output("pb-resultado", "children"),
            Output("pb-dl-row", "style"),
            Output("pb-status", "children"),
            Output("pb-fenomeno", "value"),
            Output("pb-relato1", "value"),
            Output("pb-relato2", "value"),
            Input("btn-pb-gen", "n_clicks"),
            Input("btn-pb-limpiar", "n_clicks"),
            State("pb-fenomeno", "value"),
            State("pb-urgencia", "value"),
            State("pb-nivel", "value"),
            State("pb-autor", "value"),
            State("pb-relato1", "value"),
            State("pb-relato2", "value"),
            prevent_initial_call=True,
        )
        def generate(n_gen, n_clear, phenomenon, urgency, level, author, r1, r2):
            triggered = ctx.triggered_id
            placeholder = self._preview_placeholder()

            if triggered == "btn-pb-limpiar":
                return placeholder, {"display": "none"}, "", "", "", ""
            if triggered != "btn-pb-gen":
                raise PreventUpdate
            if not phenomenon or not phenomenon.strip():
                return (
                    placeholder, {"display": "none"},
                    "⚠ Describe el fenómeno antes de generar.",
                    phenomenon, r1, r2,
                )

            supporting = ""
            if r1 and r1.strip():
                supporting += f"\nRelato de respaldo 1:\n{r1}"
            if r2 and r2.strip():
                supporting += f"\nRelato de respaldo 2:\n{r2}"

            prompt = _POLICY_BRIEF_PROMPT.format(
                date=date.today().strftime("%d/%m/%Y"),
                author=author or "Equipo AMSZO",
                urgency=urgency,
                level=level,
                phenomenon=phenomenon,
                supporting=supporting,
            )
            result_text = claude.send_prompt(prompt)

            result_html = html.Div(className="panel", children=[
                html.Div([
                    "Vista previa del brief",
                    html.Span("revisión humana obligatoria", className="tag"),
                ], className="panel-title"),
                html.Pre(result_text, style={
                    "fontSize": "12px", "lineHeight": "1.7", "color": theme.text2,
                    "whiteSpace": "pre-wrap", "fontFamily": theme.font_sans,
                    "margin": "0",
                }),
            ])

            return (
                result_html, {"display": "block"},
                "✓ Brief generado · revisar antes de distribuir",
                phenomenon, r1, r2,
            )

        @app.callback(
            Output("dl-pb-txt", "data"),
            Input("btn-pb-dl", "n_clicks"),
            State("pb-resultado", "children"),
            prevent_initial_call=True,
        )
        def download(n: int, children):
            if not n:
                raise PreventUpdate
            try:
                text = children["props"]["children"][1]["props"]["children"]
            except Exception:
                text = "No hay contenido para descargar."
            return dcc.send_string(str(text), "policy_brief.txt")

        @app.callback(
            Output("active-module", "data", allow_duplicate=True),
            Input("btn-pb-ialeia", "n_clicks"),
            prevent_initial_call=True,
        )
        def go_to_ialeia(n: int):
            if not n:
                raise PreventUpdate
            return "reportes"

    def _preview_placeholder(self) -> html.Div:
        t = self._theme
        return html.Div(className="panel", style={"minHeight": "400px"}, children=[
            html.Div([
                "Vista previa del brief",
                html.Span("revisión humana obligatoria", className="tag"),
            ], className="panel-title"),
            html.Div(
                "Configura el fenómeno y presiona «Generar Policy Brief →»",
                style={
                    "color": t.text3, "fontFamily": t.font_mono,
                    "fontSize": "11px", "padding": "40px 0", "textAlign": "center",
                },
            ),
        ])

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
            "Elimina cualquier identificador directo de los relatos de respaldo antes de pegar. "
            "La descripción del fenómeno no debe incluir RUT, nombres, ni direcciones exactas.",
        ])
