"""Placeholder module for planned but unimplemented features."""

from __future__ import annotations

from dash import Dash, html

from aria.data.store import DataStore
from aria.modules.base import BaseModule
from aria.theme import Theme

MODULE_CONFIGS: dict[str, dict] = {
    "vehiculos": {
        "nombre": "Análisis de robo de vehículos",
        "sprint": "Sprint 2",
        "estado": "Planificado",
        "color": "#7c5cfc",
        "desc": "Análisis específico de robos con inhibidor, lunetas rotas y accesorios en estacionamientos. Clustering por MO más análisis geoespacial y temporal.",
        "metricas": ["Patrones de MO por zona", "Horarios críticos", "Recomendaciones operativas"],
        "nivel": "Nivel 2 — separación estructural",
        "fuente": "RUC / SIRAM",
    },
    "residual": {
        "nombre": "Consolidado de información residual",
        "sprint": "Sprint 2",
        "estado": "Planificado",
        "color": "#f7b84f",
        "desc": "Sistematización de información dispersa (incivilidades, denuncias municipales, vehículos repetidos) que puede constituir antecedentes relevantes para investigaciones.",
        "metricas": ["Vínculos entre registros", "Líneas investigativas sugeridas", "Red de actores identificados"],
        "nivel": "Nivel 2 — separación estructural",
        "fuente": "RUC / SIRAM / Municipios",
    },
    "trayecto": {
        "nombre": "Delitos de trayecto",
        "sprint": "Sprint 2",
        "estado": "Planificado",
        "color": "#f75fc8",
        "desc": "Identificación de delitos asociados a ejes de transporte público. Análisis de tramos críticos, nodos de riesgo y horarios de mayor ocurrencia.",
        "metricas": ["Tramos críticos por recorrido", "Horarios de riesgo", "Alertas por nodo"],
        "nivel": "Nivel 2 — separación estructural",
        "fuente": "RUC / SIRAM + datos GTFS",
    },
    "mapa_nico": {
        "nombre": "Interconexiones sociodelictuales",
        "sprint": "Sprint 3",
        "estado": "Planificado",
        "color": "#cc4fcc",
        "desc": "Cruce de información delictual con variables socioestructurales del territorio (densidad, equipamiento urbano, variables socioeconómicas). Genera perfiles territoriales enriquecidos.",
        "metricas": ["Perfil sociodelictual por zona", "Zonas de riesgo contextualizado", "Mapa de escalamiento"],
        "nivel": "Nivel 3 — agregación",
        "fuente": "RUC / SIRAM + INE + IDE",
    },
}


class PlaceholderModule(BaseModule):
    """Generic 'coming soon' layout for modules not yet implemented."""

    display_name = "Placeholder"

    def __init__(
        self, store: DataStore, theme: Theme, placeholder_id: str,
    ) -> None:
        super().__init__(store, theme)
        self._placeholder_id = placeholder_id
        self.module_id = placeholder_id
        cfg = MODULE_CONFIGS.get(placeholder_id, {})
        self.display_name = cfg.get("nombre", placeholder_id)

    def get_layout(self) -> html.Div:
        cfg = MODULE_CONFIGS.get(self._placeholder_id)
        if not cfg:
            return html.Div("Módulo no encontrado.", className="modulo-wrap")

        color = cfg["color"]
        status = cfg["estado"]
        badge_bg = "rgba(79,142,247,.15)" if "desarrollo" in status.lower() else "rgba(139,145,176,.1)"
        badge_col = "#4f8ef7" if "desarrollo" in status.lower() else "#8b91b0"

        return html.Div(className="modulo-wrap", children=[
            html.Div(className="mod-header", children=[
                html.Div([
                    html.Div(cfg["nombre"], className="mod-title"),
                    html.Div(cfg["desc"], className="mod-sub",
                             style={"maxWidth": "600px", "lineHeight": "1.5"}),
                ]),
                html.Div(className="mod-actions", children=[
                    html.Span(cfg["sprint"], style={
                        "fontSize": "11px", "padding": "3px 10px",
                        "borderRadius": "20px",
                        "background": "rgba(79,142,247,.1)", "color": "#4f8ef7",
                        "marginRight": "6px",
                    }),
                    html.Span(status, style={
                        "fontSize": "11px", "padding": "3px 10px",
                        "borderRadius": "20px",
                        "background": badge_bg, "color": badge_col,
                    }),
                ]),
            ]),
            html.Div(className="placeholder-body", children=[
                html.Div(className="placeholder-grid", children=[
                    html.Div(className="ph-card", children=[
                        html.Div("Métricas que producirá", className="ph-card-title"),
                        html.Div([
                            html.Div(className="ph-metric-row", children=[
                                html.Div(style={
                                    "width": "8px", "height": "8px", "borderRadius": "50%",
                                    "background": color, "flexShrink": "0", "marginTop": "3px",
                                }),
                                html.Span(met, style={"fontSize": "12px", "color": "#c9d1d9"}),
                            ]) for met in cfg["metricas"]
                        ]),
                    ]),
                    html.Div(className="ph-card", children=[
                        html.Div("Datos y privacidad", className="ph-card-title"),
                        html.Div(className="ph-info-row", children=[
                            html.Span("Fuente", className="ph-info-key"),
                            html.Span(cfg["fuente"], className="ph-info-val"),
                        ]),
                        html.Div(className="ph-info-row", children=[
                            html.Span("Recodificación", className="ph-info-key"),
                            html.Span(cfg["nivel"], className="ph-info-val"),
                        ]),
                        html.Div(className="ph-info-row", children=[
                            html.Span("Supervisión", className="ph-info-key"),
                            html.Span("Humana obligatoria", className="ph-info-val",
                                      style={"color": "#4fcc8e"}),
                        ]),
                    ]),
                    html.Div(className="ph-card", children=[
                        html.Div("Dependencias técnicas", className="ph-card-title"),
                        html.Div([
                            html.Div(dep, style={
                                "fontSize": "11px", "color": "#8b91b0",
                                "padding": "3px 0",
                                "borderBottom": "0.5px solid #2e3250",
                            }) for dep in [
                                "Python + Dash", "pandas + geopandas",
                                "Claude API (datos recodificados)",
                                "GeoJSON comunas Santiago",
                            ]
                        ]),
                    ]),
                ]),
                html.Div(className="ph-dev-zone", children=[
                    html.Div(style={
                        "width": "48px", "height": "48px", "borderRadius": "12px",
                        "margin": "0 auto 16px",
                        "background": f"{color}22", "display": "flex",
                        "alignItems": "center", "justifyContent": "center",
                    }, children=[
                        html.Div(style={
                            "width": "20px", "height": "20px", "borderRadius": "50%",
                            "border": f"2px solid {color}", "borderTopColor": "transparent",
                        }),
                    ]),
                    html.Div(
                        f"Módulo en {status.lower()}",
                        style={
                            "fontSize": "14px", "fontWeight": "500",
                            "color": "#c9d1d9", "marginBottom": "8px",
                        },
                    ),
                    html.Div(
                        "Este módulo estará disponible en una próxima versión. "
                        "El prototipo actual sirve como base de arquitectura para "
                        "que un desarrollador lo implemente con conexión a API.",
                        style={
                            "fontSize": "12px", "color": "#7d8590",
                            "maxWidth": "400px", "lineHeight": "1.6",
                            "textAlign": "center", "margin": "0 auto",
                        },
                    ),
                ]),
            ]),
        ])

    def register_callbacks(self, app: Dash) -> None:
        pass
