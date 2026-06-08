# =============================================================================
# pages/placeholder.py — Pantalla genérica para módulos en desarrollo
# =============================================================================

from dash import html

MODULOS = {
    "agrupador": {
        "nombre":  "Agrupador de casos",
        "sprint":  "Sprint 1",
        "estado":  "En desarrollo",
        "color":   "#4f8ef7",
        "desc":    "Identificación automática de casos similares por modus operandi, zona horaria y tipo de víctima. La IA propone grupos y el analista valida cada agrupación.",
        "metricas":["Porcentaje de similitud entre casos","Etiqueta descriptiva por grupo","Focos investigativos sugeridos"],
        "nivel":   "Nivel 2 — separación estructural",
        "fuente":  "RUC / SIRAM",
    },
    "vehiculos": {
        "nombre":  "Análisis de robo de vehículos",
        "sprint":  "Sprint 2",
        "estado":  "Planificado",
        "color":   "#7c5cfc",
        "desc":    "Análisis específico de robos con inhibidor, lunetas rotas y accesorios en estacionamientos. Clustering por MO más análisis geoespacial y temporal.",
        "metricas":["Patrones de MO por zona","Horarios críticos","Recomendaciones operativas"],
        "nivel":   "Nivel 2 — separación estructural",
        "fuente":  "RUC / SIRAM",
    },
    "residual": {
        "nombre":  "Consolidado de información residual",
        "sprint":  "Sprint 2",
        "estado":  "Planificado",
        "color":   "#f7b84f",
        "desc":    "Sistematización de información dispersa (incivilidades, denuncias municipales, vehículos repetidos) que puede constituir antecedentes relevantes para investigaciones.",
        "metricas":["Vínculos entre registros","Líneas investigativas sugeridas","Red de actores identificados"],
        "nivel":   "Nivel 2 — separación estructural",
        "fuente":  "RUC / SIRAM / Municipios",
    },
    "trayecto": {
        "nombre":  "Delitos de trayecto",
        "sprint":  "Sprint 2",
        "estado":  "Planificado",
        "color":   "#f75fc8",
        "desc":    "Identificación de delitos asociados a ejes de transporte público. Análisis de tramos críticos, nodos de riesgo y horarios de mayor ocurrencia.",
        "metricas":["Tramos críticos por recorrido","Horarios de riesgo","Alertas por nodo"],
        "nivel":   "Nivel 2 — separación estructural",
        "fuente":  "RUC / SIRAM + datos GTFS",
    },
    "redes": {
        "nombre":  "Redes criminales",
        "sprint":  "Sprint 3",
        "estado":  "Planificado",
        "color":   "#5cf7e8",
        "desc":    "Análisis de vínculos entre casos, personas y organizaciones mediante redes sociales (SNA). Identificación de actores clave, centralidad y estructura de grupos delictuales.",
        "metricas":["Índice de centralidad por actor","Comunidades detectadas","Vínculos entre casos"],
        "nivel":   "Nivel 1 — seudonimización",
        "fuente":  "RUC / SIRAM",
    },
    "temporal": {
        "nombre":  "Análisis temporal",
        "sprint":  "Sprint 3",
        "estado":  "Planificado",
        "color":   "#4fcc8e",
        "desc":    "Series de tiempo de frecuencia delictual con detección de estacionalidad, cambios de patrón y proyecciones descriptivas. Sin predicción — solo descripción del comportamiento histórico.",
        "metricas":["Estacionalidad semanal/mensual","Puntos de cambio detectados","Comparativa interanual"],
        "nivel":   "Nivel 3 — agregación",
        "fuente":  "RUC / SIRAM",
    },
    "receptacion": {
        "nombre":  "Zonas de receptación",
        "sprint":  "Sprint 3",
        "estado":  "Planificado",
        "color":   "#f7975f",
        "desc":    "Identificación de territorios donde se concentran mercados ilegales de vehículos y especies. Análisis de redes de receptación a partir de registros de recuperación.",
        "metricas":["Índice de concentración por zona","Tipo de especies predominante","Red de receptación hipotética"],
        "nivel":   "Nivel 3 — agregación",
        "fuente":  "RUC / SIRAM",
    },
    "policy": {
        "nombre":  "Policy brief automatizado",
        "sprint":  "Sprint 1",
        "estado":  "En desarrollo",
        "color":   "#4f8ef7",
        "desc":    "Generación automática de minutas ejecutivas a partir de datos agregados del período. Claude redacta el documento base, el analista revisa y aprueba antes de distribuir.",
        "metricas":["Resumen ejecutivo del período","Tendencias identificadas","3 recomendaciones automáticas"],
        "nivel":   "Nivel 3 — agregación",
        "fuente":  "Outputs de otros módulos",
    },
    "mapa_nico": {
        "nombre":  "Interconexiones sociodelictuales",
        "sprint":  "Sprint 3",
        "estado":  "Planificado",
        "color":   "#cc4fcc",
        "desc":    "Cruce de información delictual con variables socioestructurales del territorio (densidad, equipamiento urbano, variables socioeconómicas). Genera perfiles territoriales enriquecidos.",
        "metricas":["Perfil sociоdelictual por zona","Zonas de riesgo contextualizado","Mapa de escalamiento"],
        "nivel":   "Nivel 3 — agregación",
        "fuente":  "RUC / SIRAM + INE + IDE",
    },
}


def get_layout(modulo_id):
    m = MODULOS.get(modulo_id, {})
    if not m:
        return html.Div("Módulo no encontrado.", className="modulo-wrap")

    color  = m["color"]
    estado = m["estado"]
    badge_bg  = "rgba(79,142,247,.15)"  if "desarrollo" in estado.lower() else "rgba(139,145,176,.1)"
    badge_col = "#4f8ef7"               if "desarrollo" in estado.lower() else "#8b91b0"

    return html.Div(className="modulo-wrap", children=[

        html.Div(className="mod-header", children=[
            html.Div([
                html.Div(m["nombre"], className="mod-title"),
                html.Div(m["desc"],   className="mod-sub",
                         style={"maxWidth":"600px","lineHeight":"1.5"}),
            ]),
            html.Div(className="mod-actions", children=[
                html.Span(m["sprint"], style={
                    "fontSize":"11px","padding":"3px 10px","borderRadius":"20px",
                    "background":"rgba(79,142,247,.1)","color":"#4f8ef7","marginRight":"6px",
                }),
                html.Span(estado, style={
                    "fontSize":"11px","padding":"3px 10px","borderRadius":"20px",
                    "background":badge_bg,"color":badge_col,
                }),
            ]),
        ]),

        html.Div(className="placeholder-body", children=[

            html.Div(className="placeholder-grid", children=[

                # Card: qué producirá
                html.Div(className="ph-card", children=[
                    html.Div("Métricas que producirá", className="ph-card-title"),
                    html.Div([
                        html.Div(className="ph-metric-row", children=[
                            html.Div(style={
                                "width":"8px","height":"8px","borderRadius":"50%",
                                "background":color,"flexShrink":"0","marginTop":"3px",
                            }),
                            html.Span(met, style={"fontSize":"12px","color":"#c9d1d9"}),
                        ]) for met in m["metricas"]
                    ]),
                ]),

                # Card: datos y privacidad
                html.Div(className="ph-card", children=[
                    html.Div("Datos y privacidad", className="ph-card-title"),
                    html.Div(className="ph-info-row", children=[
                        html.Span("Fuente", className="ph-info-key"),
                        html.Span(m["fuente"], className="ph-info-val"),
                    ]),
                    html.Div(className="ph-info-row", children=[
                        html.Span("Recodificación", className="ph-info-key"),
                        html.Span(m["nivel"], className="ph-info-val"),
                    ]),
                    html.Div(className="ph-info-row", children=[
                        html.Span("Supervisión", className="ph-info-key"),
                        html.Span("Humana obligatoria", className="ph-info-val",
                                  style={"color":"#4fcc8e"}),
                    ]),
                ]),

                # Card: dependencias
                html.Div(className="ph-card", children=[
                    html.Div("Dependencias técnicas", className="ph-card-title"),
                    html.Div([
                        html.Div(d, style={"fontSize":"11px","color":"#8b91b0",
                                           "padding":"3px 0","borderBottom":"0.5px solid #2e3250"})
                        for d in ["Python + Dash","pandas + geopandas","Claude API (datos recodificados)",
                                  "GeoJSON comunas Santiago"]
                    ]),
                ]),
            ]),

            # Zona de desarrollo
            html.Div(className="ph-dev-zone", children=[
                html.Div(style={
                    "width":"48px","height":"48px","borderRadius":"12px","margin":"0 auto 16px",
                    "background":f"{color}22","display":"flex","alignItems":"center",
                    "justifyContent":"center",
                }, children=[
                    html.Div(style={
                        "width":"20px","height":"20px","borderRadius":"50%",
                        "border":f"2px solid {color}","borderTopColor":"transparent",
                    })
                ]),
                html.Div(f"Módulo en {estado.lower()}",
                         style={"fontSize":"14px","fontWeight":"500","color":"#c9d1d9",
                                "marginBottom":"8px"}),
                html.Div("Este módulo estará disponible en una próxima versión. "
                         "El prototipo actual sirve como base de arquitectura para "
                         "que un desarrollador lo implemente con conexión a API.",
                         style={"fontSize":"12px","color":"#7d8590","maxWidth":"400px",
                                "lineHeight":"1.6","textAlign":"center","margin":"0 auto"}),
            ]),
        ]),
    ])
