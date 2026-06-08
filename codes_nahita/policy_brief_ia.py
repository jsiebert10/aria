# =============================================================================
# pages/policy_brief_ia.py — Módulo: Generador de Policy Brief con IA
# Integra la lógica original de policy_brief.py bajo la estética ARIA/SIRAC.
# Usa Claude API. Los relatos de respaldo deben estar recodificados (Nivel 2).
# =============================================================================

import os
from datetime import date
from dash import dcc, html, Input, Output, State
from dash.exceptions import PreventUpdate

BG1="#10161e"; BG2="#161d27"; BG3="#1c2530"
BORDE="#26303d"; TEXT="#e8e6d9"; T2="#a8adb5"; T3="#6b727d"
AMBER="#d4a84b"; AMB2="#b38a2e"
DANGER="#c74d3f"; WARN="#d49b3f"; OK="#7a9e6c"; INFO="#5a8fa8"

TA_STYLE = {
    "width":"100%","background":BG3,"border":f"1px solid {BORDE}",
    "color":TEXT,"padding":"10px 12px","fontSize":"12px","lineHeight":"1.6",
    "fontFamily":"IBM Plex Sans,sans-serif","outline":"none","resize":"vertical",
}

INPUT_STYLE = {
    "width":"100%","background":BG3,"border":f"1px solid {BORDE}",
    "color":TEXT,"padding":"7px 10px","fontSize":"12px",
    "fontFamily":"IBM Plex Sans,sans-serif","outline":"none","marginTop":"4px",
}

LABEL_STYLE = {
    "fontFamily":"IBM Plex Mono,monospace","fontSize":"9px","color":T3,
    "textTransform":"uppercase","letterSpacing":"1px",
    "display":"block","marginBottom":"4px","marginTop":"12px",
}

AVISO = html.Div(style={
    "background":f"{AMBER}0d","border":f"1px solid {AMB2}44",
    "borderLeft":f"3px solid {AMBER}","padding":"10px 14px","marginBottom":"14px",
    "fontSize":"11px","lineHeight":"1.6","color":T2,
    "fontFamily":"IBM Plex Mono,monospace",
}, children=[
    html.Span("⚠ Protocolo de privacidad · Nivel 2  ", style={"color":AMBER,"fontWeight":"600"}),
    "Elimina cualquier identificador directo de los relatos de respaldo antes de pegar. "
    "La descripción del fenómeno no debe incluir RUT, nombres, ni direcciones exactas.",
])

URGENCIA_OPTS = [
    {"label":"Monitoreo","value":"Monitoreo"},
    {"label":"Alerta","value":"Alerta"},
    {"label":"Acción inmediata","value":"Acción inmediata"},
]

NIVEL_OPTS = [
    {"label":"Emergente","value":"Emergente"},
    {"label":"En desarrollo","value":"En desarrollo"},
    {"label":"Consolidado","value":"Consolidado"},
]


def get_layout():
    hoy = date.today().strftime("%d/%m/%Y")
    return html.Div(className="modulo-wrap", children=[
        html.Div(className="mod-header", children=[
            html.Div([
                html.Div("Productos · IA", className="mod-eyebrow"),
                html.Div("Generador de Policy Brief", className="mod-title"),
                html.Div("Produce minutas ejecutivas con respaldo criminológico · IALEIA",
                         className="mod-sub"),
            ]),
            html.Div(className="mod-actions", children=[
                html.Span("Claude API · supervisión humana antes de distribuir",
                          style={"fontFamily":"IBM Plex Mono,monospace","fontSize":"9px","color":T3}),
            ]),
        ]),
        html.Div(className="mod-body", children=[

            AVISO,

            html.Div(className="grid grid-sidebar", children=[

                # Panel izquierdo — configuración
                html.Div(className="panel", children=[

                    html.Div("Configuración del brief", className="panel-title"),

                    html.Label("Nivel de urgencia", style=LABEL_STYLE),
                    dcc.Dropdown(id="pb-urgencia", className="dropdown",
                        options=URGENCIA_OPTS, value="Alerta", clearable=False),

                    html.Label("Solidez del fenómeno", style=LABEL_STYLE),
                    dcc.Dropdown(id="pb-nivel", className="dropdown",
                        options=NIVEL_OPTS, value="En desarrollo", clearable=False),

                    html.Label("Elaborado por", style=LABEL_STYLE),
                    dcc.Input(id="pb-autor", type="text", value="Equipo AMSZO",
                              style=INPUT_STYLE),

                    html.Div(style={"height":"1px","background":BORDE,"margin":"16px 0"}),

                    html.Label("Descripción del fenómeno *", style=LABEL_STYLE),
                    dcc.Textarea(id="pb-fenomeno",
                        placeholder="Describe el fenómeno delictual que estás observando. "
                                    "Incluye: tipo de delito, zona general, frecuencia, "
                                    "características del MO, tendencia observada...",
                        style={**TA_STYLE, "minHeight":"160px"}),

                    html.Label("Relato de respaldo 1 (opcional · recodificado)",
                               style=LABEL_STYLE),
                    dcc.Textarea(id="pb-relato1",
                        placeholder="Relato depurado sin identificadores...",
                        style={**TA_STYLE, "minHeight":"100px"}),

                    html.Label("Relato de respaldo 2 (opcional · recodificado)",
                               style=LABEL_STYLE),
                    dcc.Textarea(id="pb-relato2",
                        placeholder="Relato depurado sin identificadores...",
                        style={**TA_STYLE, "minHeight":"100px"}),

                    html.Div(style={"marginTop":"14px","display":"flex","gap":"8px"}, children=[
                        html.Button("Generar Policy Brief →", id="btn-pb-gen", n_clicks=0,
                            style={"fontFamily":"IBM Plex Mono,monospace","fontSize":"11px",
                                   "padding":"8px 18px","background":AMBER,
                                   "border":f"1px solid {AMBER}","color":"#0a0e14",
                                   "cursor":"pointer","fontWeight":"600","letterSpacing":".5px"}),
                        html.Button("Limpiar", id="btn-pb-limpiar", n_clicks=0,
                            style={"fontFamily":"IBM Plex Mono,monospace","fontSize":"11px",
                                   "padding":"8px 14px","background":"transparent",
                                   "border":f"1px solid {BORDE}","color":T2,"cursor":"pointer"}),
                    ]),

                    html.Div(id="pb-status",
                             style={"fontFamily":"IBM Plex Mono,monospace","fontSize":"10px",
                                    "color":T3,"marginTop":"8px"}),
                ]),

                # Panel derecho — preview resultado
                html.Div(style={"display":"flex","flexDirection":"column","gap":"10px"}, children=[
                    html.Div(id="pb-resultado", children=[
                        html.Div(className="panel", style={"minHeight":"400px"}, children=[
                            html.Div(["Vista previa del brief",
                                      html.Span("revisión humana obligatoria",className="tag")],
                                     className="panel-title"),
                            html.Div(
                                "Configura el fenómeno y presiona «Generar Policy Brief →»",
                                style={"color":T3,"fontFamily":"IBM Plex Mono,monospace",
                                       "fontSize":"11px","padding":"40px 0","textAlign":"center"}),
                        ]),
                    ]),
                    html.Div(id="pb-dl-row", style={"display":"none"}, children=[
                        html.Div(style={"display":"flex","gap":"8px"}, children=[
                            html.Button("↓ Descargar como texto", id="btn-pb-dl", n_clicks=0,
                                style={"fontFamily":"IBM Plex Mono,monospace","fontSize":"10px",
                                       "padding":"6px 14px","background":"transparent",
                                       "border":f"1px solid {BORDE}","color":T2,"cursor":"pointer"}),
                            html.Button("Agregar al reporte IALEIA →", id="btn-pb-ialeia", n_clicks=0,
                                style={"fontFamily":"IBM Plex Mono,monospace","fontSize":"10px",
                                       "padding":"6px 14px","background":f"{AMBER}18",
                                       "border":f"1px solid {AMB2}","color":AMBER,"cursor":"pointer"}),
                        ]),
                        dcc.Download(id="dl-pb-txt"),
                    ]),
                ]),
            ]),
        ]),
    ])


def _llamar_claude(fenomeno, urgencia, nivel, autor, relato1="", relato2=""):
    try:
        from dotenv import load_dotenv
        load_dotenv(os.path.join(os.path.dirname(os.path.dirname(__file__)), ".env"))
        api_key = os.getenv("ANTHROPIC_API_KEY","")
        if not api_key or api_key == "tu_api_key_aqui":
            return "⚠ API key no configurada. Edita el archivo .env y agrega tu ANTHROPIC_API_KEY."

        import anthropic
        client = anthropic.Anthropic(api_key=api_key)

        hoy = date.today().strftime("%d/%m/%Y")
        respaldo = ""
        if relato1 and relato1.strip():
            respaldo += f"\nRelato de respaldo 1:\n{relato1}"
        if relato2 and relato2.strip():
            respaldo += f"\nRelato de respaldo 2:\n{relato2}"

        prompt = f"""Eres un analista criminal experto con formación en criminología y políticas públicas de seguridad.
Redacta un policy brief ejecutivo pero con respaldo técnico-criminológico, dirigido a jefaturas de Fiscalía, Directores de Seguridad Municipal y autoridades.
Usa lenguaje directo y accesible, pero con asidero teórico. Responde EXACTAMENTE en este formato usando markdown:

---

# POLICY BRIEF — ALERTA DE FENÓMENO DELICTUAL

**Fecha:** {hoy}
**Elaborado por:** {autor}
**Nivel de urgencia:** {urgencia}

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
**Solidez del fenómeno:** {nivel}
**Fuente:** Análisis de relatos / Registros institucionales

---

Fenómeno descrito por el analista:
{fenomeno}
{respaldo}"""

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
        Output("pb-resultado",  "children"),
        Output("pb-dl-row",     "style"),
        Output("pb-status",     "children"),
        Output("pb-fenomeno",   "value"),
        Output("pb-relato1",    "value"),
        Output("pb-relato2",    "value"),
        Input("btn-pb-gen",     "n_clicks"),
        Input("btn-pb-limpiar", "n_clicks"),
        State("pb-fenomeno",    "value"),
        State("pb-urgencia",    "value"),
        State("pb-nivel",       "value"),
        State("pb-autor",       "value"),
        State("pb-relato1",     "value"),
        State("pb-relato2",     "value"),
        prevent_initial_call=True,
    )
    def generar(n_gen, n_limp, fenomeno, urgencia, nivel, autor, r1, r2):
        from dash import ctx
        triggered = ctx.triggered_id

        placeholder = html.Div(className="panel", style={"minHeight":"400px"}, children=[
            html.Div(["Vista previa del brief",
                      html.Span("revisión humana obligatoria",className="tag")],
                     className="panel-title"),
            html.Div("Configura el fenómeno y presiona «Generar Policy Brief →»",
                     style={"color":T3,"fontFamily":"IBM Plex Mono,monospace",
                            "fontSize":"11px","padding":"40px 0","textAlign":"center"}),
        ])

        if triggered == "btn-pb-limpiar":
            return placeholder, {"display":"none"}, "", "", "", ""

        if triggered != "btn-pb-gen":
            raise PreventUpdate

        if not fenomeno or not fenomeno.strip():
            return (placeholder, {"display":"none"},
                    "⚠ Describe el fenómeno antes de generar.", fenomeno, r1, r2)

        resultado_texto = _llamar_claude(fenomeno, urgencia, nivel, autor, r1 or "", r2 or "")

        # Renderizar markdown como HTML básico en Dash
        resultado_html = html.Div(className="panel", children=[
            html.Div(["Vista previa del brief",
                      html.Span("revisión humana obligatoria",className="tag")],
                     className="panel-title"),
            # Preformatted para preservar markdown
            html.Pre(resultado_texto, style={
                "fontSize":"12px","lineHeight":"1.7","color":T2,
                "whiteSpace":"pre-wrap","fontFamily":"IBM Plex Sans,sans-serif",
                "margin":"0",
            }),
        ])

        return (resultado_html, {"display":"block"},
                "✓ Brief generado · revisar antes de distribuir", fenomeno, r1, r2)

    @app.callback(
        Output("dl-pb-txt","data"),
        Input("btn-pb-dl","n_clicks"),
        State("pb-resultado","children"),
        prevent_initial_call=True,
    )
    def descargar(n, children):
        if not n: raise PreventUpdate
        # Extraer texto del Pre
        try:
            texto = children["props"]["children"][1]["props"]["children"]
        except Exception:
            texto = "No hay contenido para descargar."
        return dcc.send_string(str(texto), "policy_brief.txt")

    @app.callback(
        Output("active-module","data", allow_duplicate=True),
        Input("btn-pb-ialeia","n_clicks"),
        prevent_initial_call=True,
    )
    def ir_ialeia(n):
        if not n: raise PreventUpdate
        return "reportes"
