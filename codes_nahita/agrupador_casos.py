# =============================================================================
# pages/agrupador_casos.py — Módulo: Agrupador de casos
# Integra la lógica original de agrupador.py bajo la estética ARIA/SIRAC.
# Usa Claude API con datos recodificados (Nivel 2: sin identificadores directos).
# =============================================================================

import os
from dash import dcc, html, Input, Output, State
from dash.exceptions import PreventUpdate

BG1="#10161e"; BG2="#161d27"; BG3="#1c2530"
BORDE="#26303d"; TEXT="#e8e6d9"; T2="#a8adb5"; T3="#6b727d"
AMBER="#d4a84b"; AMB2="#b38a2e"; AGLOW="rgba(212,168,75,.12)"
DANGER="#c74d3f"; WARN="#d49b3f"; OK="#7a9e6c"; INFO="#5a8fa8"

TA_STYLE = {
    "width":"100%","background":BG3,"border":f"1px solid {BORDE}",
    "color":TEXT,"padding":"10px 12px","fontSize":"12px","lineHeight":"1.6",
    "fontFamily":"IBM Plex Sans,sans-serif","outline":"none","resize":"vertical",
    "minHeight":"140px",
}

AVISO_RECODIFICACION = html.Div(style={
    "background":f"{AMBER}0d","border":f"1px solid {AMB2}44",
    "borderLeft":f"3px solid {AMBER}","padding":"10px 14px","marginBottom":"14px",
    "fontSize":"11px","lineHeight":"1.6","color":T2,
    "fontFamily":"IBM Plex Mono,monospace",
}, children=[
    html.Span("⚠ Protocolo de privacidad · Nivel 2  ", style={"color":AMBER,"fontWeight":"600"}),
    "Antes de pegar un relato, elimina: nombres, RUT, direcciones exactas, teléfonos y cualquier "
    "dato que identifique directamente a personas. Los textos se envían a Claude API externa. "
    "Si el relato contiene menores de edad, no lo incluyas.",
])


def get_layout():
    return html.Div(className="modulo-wrap", children=[
        html.Div(className="mod-header", children=[
            html.Div([
                html.Div("Análisis · IA", className="mod-eyebrow"),
                html.Div("Agrupador de casos", className="mod-title"),
                html.Div("Detecta similitudes entre relatos y recomienda foco investigativo",
                         className="mod-sub"),
            ]),
            html.Div(className="mod-actions", children=[
                html.Span("Claude API · Nivel 2 · supervisión humana obligatoria",
                          style={"fontFamily":"IBM Plex Mono,monospace","fontSize":"9px","color":T3}),
            ]),
        ]),
        html.Div(className="mod-body", children=[

            AVISO_RECODIFICACION,

            # Campos de relatos
            html.Div(className="grid grid-2", children=[
                html.Div([
                    html.Label("Relato · Caso 1",
                               style={"fontFamily":"IBM Plex Mono,monospace","fontSize":"9px",
                                      "color":T3,"textTransform":"uppercase","letterSpacing":"1px",
                                      "display":"block","marginBottom":"5px"}),
                    dcc.Textarea(id="ag-caso1", placeholder="Pega el primer relato recodificado...",
                                 style=TA_STYLE),
                ]),
                html.Div([
                    html.Label("Relato · Caso 2",
                               style={"fontFamily":"IBM Plex Mono,monospace","fontSize":"9px",
                                      "color":T3,"textTransform":"uppercase","letterSpacing":"1px",
                                      "display":"block","marginBottom":"5px"}),
                    dcc.Textarea(id="ag-caso2", placeholder="Pega el segundo relato recodificado...",
                                 style=TA_STYLE),
                ]),
                html.Div([
                    html.Label("Relato · Caso 3 (opcional)",
                               style={"fontFamily":"IBM Plex Mono,monospace","fontSize":"9px",
                                      "color":T3,"textTransform":"uppercase","letterSpacing":"1px",
                                      "display":"block","marginBottom":"5px"}),
                    dcc.Textarea(id="ag-caso3", placeholder="Pega el tercer relato (opcional)...",
                                 style=TA_STYLE),
                ]),
                html.Div([
                    html.Label("Relato · Caso 4 (opcional)",
                               style={"fontFamily":"IBM Plex Mono,monospace","fontSize":"9px",
                                      "color":T3,"textTransform":"uppercase","letterSpacing":"1px",
                                      "display":"block","marginBottom":"5px"}),
                    dcc.Textarea(id="ag-caso4", placeholder="Pega el cuarto relato (opcional)...",
                                 style=TA_STYLE),
                ]),
            ]),

            # Botón analizar
            html.Div(style={"display":"flex","alignItems":"center","gap":"12px","margin":"4px 0"}, children=[
                html.Button("Analizar casos →", id="btn-ag-analizar", n_clicks=0,
                    style={"fontFamily":"IBM Plex Mono,monospace","fontSize":"11px",
                           "padding":"8px 20px","background":AMBER,
                           "border":f"1px solid {AMBER}","color":"#0a0e14",
                           "cursor":"pointer","fontWeight":"600","letterSpacing":".5px"}),
                html.Button("Limpiar", id="btn-ag-limpiar", n_clicks=0,
                    style={"fontFamily":"IBM Plex Mono,monospace","fontSize":"11px",
                           "padding":"8px 16px","background":"transparent",
                           "border":f"1px solid {BORDE}","color":T2,"cursor":"pointer"}),
                html.Div(id="ag-status", style={"fontFamily":"IBM Plex Mono,monospace",
                                                 "fontSize":"10px","color":T3}),
            ]),

            # Resultado
            html.Div(id="ag-resultado", style={"display":"none"}, children=[
                html.Div(className="panel", children=[
                    html.Div(["Resultado del análisis",
                              html.Span("supervisión humana requerida antes de cualquier acción",
                                        className="tag")],
                             className="panel-title"),
                    html.Div(id="ag-output", style={
                        "fontSize":"12px","lineHeight":"1.8","color":T2,
                        "whiteSpace":"pre-wrap","fontFamily":"IBM Plex Sans,sans-serif",
                    }),
                    html.Div(style={"marginTop":"12px","paddingTop":"10px",
                                    "borderTop":f"1px solid {BORDE}",
                                    "display":"flex","justifyContent":"space-between",
                                    "alignItems":"center"}, children=[
                        html.Div("Este resultado es una sugerencia analítica. "
                                 "El analista decide si existe mérito investigativo.",
                                 style={"fontFamily":"IBM Plex Mono,monospace",
                                        "fontSize":"9px","color":T3}),
                        html.Button("↓ Descargar resultado", id="btn-ag-dl", n_clicks=0,
                            style={"fontFamily":"IBM Plex Mono,monospace","fontSize":"10px",
                                   "padding":"5px 12px","background":"transparent",
                                   "border":f"1px solid {BORDE}","color":T2,"cursor":"pointer"}),
                    ]),
                    dcc.Download(id="dl-ag-txt"),
                ]),
            ]),
        ]),
    ])


def _llamar_claude(relatos: dict) -> str:
    """Llama a Claude API con los relatos recodificados."""
    try:
        from dotenv import load_dotenv
        load_dotenv(os.path.join(os.path.dirname(os.path.dirname(__file__)), ".env"))
        api_key = os.getenv("ANTHROPIC_API_KEY","")
        if not api_key or api_key == "tu_api_key_aqui":
            return "⚠ API key no configurada. Edita el archivo .env y agrega tu ANTHROPIC_API_KEY."

        import anthropic
        client = anthropic.Anthropic(api_key=api_key)

        relatos_texto = "\n\n".join([f"**{k}:**\n{v}" for k,v in relatos.items()])

        prompt = f"""Eres un analista criminal experto. Analiza estos {len(relatos)} relatos y responde EXACTAMENTE en este formato usando markdown. Sé conciso.

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
{relatos_texto}"""

        resp = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=2048,
            messages=[{"role":"user","content":prompt}],
        )
        return resp.content[0].text

    except Exception as e:
        return f"Error al conectar con Claude API: {str(e)}"


def registrar_callbacks(app):

    @app.callback(
        Output("ag-output",    "children"),
        Output("ag-resultado", "style"),
        Output("ag-status",    "children"),
        Output("ag-caso1",     "value"),
        Output("ag-caso2",     "value"),
        Output("ag-caso3",     "value"),
        Output("ag-caso4",     "value"),
        Input("btn-ag-analizar","n_clicks"),
        Input("btn-ag-limpiar", "n_clicks"),
        State("ag-caso1","value"),
        State("ag-caso2","value"),
        State("ag-caso3","value"),
        State("ag-caso4","value"),
        prevent_initial_call=True,
    )
    def analizar(n_analizar, n_limpiar, c1, c2, c3, c4):
        from dash import ctx
        triggered = ctx.triggered_id

        if triggered == "btn-ag-limpiar":
            return "", {"display":"none"}, "", "", "", "", ""

        if triggered != "btn-ag-analizar":
            raise PreventUpdate

        relatos = {}
        for i, texto in enumerate([c1,c2,c3,c4], 1):
            if texto and texto.strip():
                relatos[f"Caso {i}"] = texto.strip()

        if len(relatos) < 2:
            return ("", {"display":"none"},
                    "⚠ Ingresa al menos dos relatos para comparar.",
                    c1, c2, c3, c4)

        status = f"Analizando {len(relatos)} casos con Claude API..."
        resultado = _llamar_claude(relatos)

        return (resultado, {"display":"block"}, f"✓ Análisis completado · {len(relatos)} casos",
                c1, c2, c3, c4)

    @app.callback(
        Output("dl-ag-txt","data"),
        Input("btn-ag-dl","n_clicks"),
        State("ag-output","children"),
        prevent_initial_call=True,
    )
    def descargar(n, texto):
        if not n or not texto: raise PreventUpdate
        return dcc.send_string(str(texto), "agrupador_resultado.txt")
