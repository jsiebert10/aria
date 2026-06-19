"""Advanced spatial analysis module — Near Repeat, NNI, Network KDE.

UI layer only. Pure analysis lives in ``aria.analysis.advanced``.
"""

from __future__ import annotations

import traceback

import numpy as np
import pandas as pd
import plotly.graph_objects as go
from dash import Dash, Input, Output, dcc, html
from scipy.spatial import cKDTree

from aria.analysis.advanced import (
    AdvancedAnalyzer,
    NearRepeatResult,
    NniResult,
    NetworkKdeResult,
    _deg_to_meters,
)
from aria.data.store import DataStore
from aria.modules.base import BaseModule
from aria.theme import Theme


class AdvancedAnalysisModule(BaseModule):
    """Near Repeat, Nearest Neighbor Index, and Network KDE visualizations."""

    module_id = "avanzado"
    display_name = "Análisis avanzado"

    def __init__(
        self, store: DataStore, theme: Theme, analyzer: AdvancedAnalyzer,
    ) -> None:
        super().__init__(store, theme)
        self._analyzer = analyzer

    def get_layout(self) -> html.Div:
        t = self._theme
        s = self._store
        label_style = {
            "fontFamily": t.font_mono, "fontSize": "9px", "color": t.text3,
            "textTransform": "uppercase", "letterSpacing": "1px",
            "display": "block", "marginBottom": "4px", "marginTop": "10px",
        }

        return html.Div(className="modulo-wrap", children=[
            html.Div(className="mod-header", children=[
                html.Div([
                    html.Div("03 / Análisis espacial avanzado", className="mod-eyebrow"),
                    html.Div("Near Repeat · Nearest Neighbor · Network KDE", className="mod-title"),
                    html.Div("Métodos de segunda generación en análisis criminal geoespacial",
                             className="mod-sub"),
                ]),
                html.Div(className="mod-actions", children=[
                    html.Span(
                        "Clark & Evans 1954 · Johnson et al. 2007 · Xie & Yan 2008",
                        style={"fontFamily": t.font_mono, "fontSize": "9px", "color": t.text3},
                    ),
                ]),
            ]),
            html.Div(className="mod-body", children=[
                html.Div(style={
                    "display": "grid", "gridTemplateColumns": "1fr 1fr",
                    "gap": "12px", "marginBottom": "8px",
                }, children=[
                    html.Div([
                        html.Label("Fenómeno", style=label_style),
                        dcc.Dropdown(id="adv-fen", className="dropdown",
                            options=[{"label": f, "value": f} for f in s.phenomena],
                            value=s.phenomena[0] if s.phenomena else None,
                            clearable=False),
                    ]),
                    html.Div([
                        html.Label("Período", style=label_style),
                        dcc.Dropdown(id="adv-per", className="dropdown",
                            options=[{"label": p, "value": p} for p in s.periods],
                            value=s.periods[-1] if s.periods else None,
                            clearable=False),
                    ]),
                ]),
                self._near_repeat_panel(),
                self._nni_panel(),
                self._nkde_panel(),
            ]),
        ])

    def register_callbacks(self, app: Dash) -> None:
        store = self._store
        theme = self._theme
        analyzer = self._analyzer

        @app.callback(
            Output("adv-nr-kpis", "children"),
            Output("adv-nr-radios", "figure"),
            Output("adv-nr-serie", "figure"),
            Output("adv-nni-resultado", "children"),
            Output("adv-nni-gauge", "figure"),
            Output("adv-nni-hist", "figure"),
            Output("adv-nkde", "figure"),
            Input("adv-fen", "value"),
            Input("adv-per", "value"),
        )
        def update(phenomenon: str, period: str) -> tuple:
            try:
                return self._update_inner(phenomenon, period)
            except Exception as exc:
                traceback.print_exc()
                empty = theme.empty_figure(f"Error: {str(exc)[:60]}")
                return (
                    [], empty, empty,
                    html.Div(str(exc), style={"color": theme.danger}),
                    empty, empty, empty,
                )

    def _update_inner(self, phenomenon: str, period: str) -> tuple:
        store = self._store
        theme = self._theme
        analyzer = self._analyzer
        empty = theme.empty_figure()

        if not phenomenon or not period or store.is_empty:
            return [], empty, empty, html.Div(""), empty, empty, empty

        # -- Near Repeat --
        nr_results = analyzer.near_repeat(store.df, phenomenon, store.periods)
        nr_df = pd.DataFrame([
            {"periodo": r.period, "radio_m": r.radius_m,
             "n_total": r.total_events, "n_near_repeat": r.near_repeat_count,
             "pct_near_repeat": r.near_repeat_pct}
            for r in nr_results
        ]) if nr_results else pd.DataFrame()

        nr_per = nr_df[nr_df["periodo"] == period] if not nr_df.empty else pd.DataFrame()

        if not nr_per.empty:
            r500 = nr_per[nr_per["radio_m"].astype(int) == 500]
            if len(r500) == 0:
                r500 = nr_per.iloc[[nr_per["radio_m"].sub(500).abs().argmin()]]
            pct_500 = float(r500["pct_near_repeat"].values[0])
            n_total = int(r500["n_total"].values[0])
            n_near = int(r500["n_near_repeat"].values[0])
            col_pct = theme.danger if pct_500 > 50 else theme.warning if pct_500 > 30 else theme.success

            kpis = [
                self._kpi_mini(f"{pct_500}%", "Near Repeat (500m)", col_pct),
                self._kpi_mini(str(n_near), "Hechos con antecedente", theme.amber),
                self._kpi_mini(str(n_total), "Total hechos período", theme.text2),
                self._kpi_mini("500 m", "Radio de análisis", theme.info),
            ]

            fig_r = go.Figure()
            fig_r.add_trace(go.Bar(
                x=[f"{r}m" for r in nr_per["radio_m"]],
                y=nr_per["pct_near_repeat"],
                marker_color=[
                    theme.danger if v > 50 else theme.warning if v > 30 else theme.success
                    for v in nr_per["pct_near_repeat"]
                ],
                marker_line_width=0,
                hovertemplate="Radio %{x}: %{y}%<extra></extra>",
            ))
            fig_r.update_layout(**theme.plot_base({"l": 36, "r": 8, "t": 8, "b": 28}), showlegend=False)
            fig_r.update_xaxes(title_text="Radio de búsqueda", title_font={"size": 10})
            fig_r.update_yaxes(title_text="% Near Repeat", title_font={"size": 10})

            nr_500 = nr_df[nr_df["radio_m"].astype(int) == 500].sort_values("periodo")
            fig_s = go.Figure()
            fig_s.add_trace(go.Scatter(
                x=nr_500["periodo"], y=nr_500["pct_near_repeat"],
                mode="lines+markers",
                line={"color": theme.amber, "width": 2},
                marker={
                    "size": [9 if p == period else 5 for p in nr_500["periodo"]],
                    "color": [theme.amber if p == period else theme.amber2 for p in nr_500["periodo"]],
                },
                hovertemplate="%{x}: %{y}%<extra></extra>",
            ))
            fig_s.add_hline(y=50, line_color=theme.danger, line_dash="dash", line_width=1,
                           annotation_text="Umbral 50%", annotation_font={"size": 9, "color": theme.danger})
            fig_s.update_layout(**theme.plot_base({"l": 36, "r": 8, "t": 8, "b": 28}), showlegend=False)
        else:
            kpis = []
            fig_r = empty
            fig_s = empty

        # -- NNI --
        nni = analyzer.nearest_neighbor_index(store.df, phenomenon, period)

        if nni:
            col_r = (theme.danger if nni.r_index < 0.7
                     else theme.warning if nni.r_index < 0.9
                     else theme.success if nni.r_index > 1.1
                     else theme.text2)
            sig_text = ("Estadísticamente significativo (p<0.05)"
                        if nni.significant else "No significativo")

            nni_info = html.Div(style={
                "display": "grid", "gridTemplateColumns": "repeat(4,1fr)",
                "gap": "8px", "marginBottom": "10px",
            }, children=[
                self._kpi_mini(str(nni.r_index), "Índice R (NNI)", col_r),
                self._kpi_mini(f"{nni.observed_distance_m}m", "Distancia media obs.", theme.text2),
                self._kpi_mini(f"{nni.expected_distance_m}m", "Distancia media esp.", theme.text2),
                self._kpi_mini(f"p={nni.p_value}", sig_text,
                              theme.success if nni.significant else theme.text3),
            ])

            fig_g = go.Figure(go.Indicator(
                mode="gauge+number", value=nni.r_index,
                title={"text": nni.interpretation, "font": {"size": 11, "color": theme.text2}},
                gauge={
                    "axis": {"range": [0, 2], "tickvals": [0, 0.5, 1.0, 1.5, 2.0],
                             "ticktext": ["0", "Agrup.", "Aleatorio", "Disperso", "2"],
                             "tickfont": {"size": 9, "color": theme.text3}},
                    "bar": {"color": col_r, "thickness": 0.3},
                    "bgcolor": theme.bg3, "borderwidth": 1, "bordercolor": theme.border,
                    "steps": [
                        {"range": [0, 0.9], "color": "rgba(199,77,63,0.2)"},
                        {"range": [0.9, 1.1], "color": "rgba(122,158,108,0.13)"},
                        {"range": [1.1, 2.0], "color": "rgba(90,143,168,0.13)"},
                    ],
                    "threshold": {"line": {"color": theme.text3, "width": 2},
                                  "thickness": 0.75, "value": 1.0},
                },
                number={"font": {"size": 28, "color": col_r, "family": theme.font_mono}},
            ))
            fig_g.update_layout(**theme.plot_base({"l": 20, "r": 20, "t": 40, "b": 20}, no_axes=True))

            df_f = store.filter_by(phenomenon=phenomenon, period=period)
            pts = _deg_to_meters(df_f["latitud"].values, df_f["longitud"].values)
            tree = cKDTree(pts)
            dists, _ = tree.query(pts, k=2)
            nn_dists = dists[:, 1]

            fig_h = go.Figure()
            fig_h.add_trace(go.Histogram(
                x=nn_dists.tolist(), nbinsx=30,
                marker_color=theme.amber, marker_line_width=0, opacity=0.8,
                hovertemplate="Distancia %{x:.0f}m: %{y} hechos<extra></extra>",
            ))
            fig_h.add_vline(x=nni.observed_distance_m, line_color=theme.amber,
                           line_dash="solid", line_width=2,
                           annotation_text=f"Media: {nni.observed_distance_m}m",
                           annotation_font={"size": 9, "color": theme.amber})
            fig_h.add_vline(x=nni.expected_distance_m, line_color=theme.text3,
                           line_dash="dash", line_width=1,
                           annotation_text=f"Esperado: {nni.expected_distance_m}m",
                           annotation_font={"size": 9, "color": theme.text3})
            fig_h.update_layout(**theme.plot_base({"l": 36, "r": 8, "t": 8, "b": 28}), showlegend=False)
            fig_h.update_xaxes(title_text="Distancia al vecino más cercano (m)", title_font={"size": 9})
        else:
            nni_info = html.Div("Insuficientes datos para calcular NNI.",
                                style={"color": theme.text3, "fontSize": "12px"})
            fig_g = empty
            fig_h = empty

        # -- Network KDE --
        nkde = analyzer.network_kde(store.df, phenomenon, period)

        if nkde:
            df_plot = store.filter_by(phenomenon=phenomenon, period=period)
            fig_nkde = go.Figure()
            fig_nkde.add_trace(go.Heatmap(
                x=nkde.lon_grid, y=nkde.lat_grid, z=nkde.density,
                colorscale=[
                    [0, "rgba(0,0,0,0)"], [0.2, "rgba(212,168,75,0.1)"],
                    [0.5, "rgba(212,168,75,0.5)"], [0.8, "rgba(199,77,63,0.7)"],
                    [1.0, "rgba(199,77,63,0.95)"],
                ],
                showscale=True,
                colorbar={
                    "title": {"text": "Densidad", "font": {"size": 10, "color": theme.text2}},
                    "tickfont": {"size": 9, "color": theme.text2},
                    "bgcolor": theme.bg1, "bordercolor": theme.border, "len": 0.8,
                },
                hovertemplate="Lat: %{y:.4f}<br>Lon: %{x:.4f}<br>Densidad: %{z:.2f}<extra></extra>",
            ))
            fig_nkde.add_trace(go.Scatter(
                x=df_plot["longitud"], y=df_plot["latitud"],
                mode="markers",
                marker={"size": 4, "color": theme.text, "opacity": 0.6,
                        "line": {"color": theme.bg1, "width": 0.5}},
                name="Hechos",
                hovertemplate="Lat: %{y:.4f}<br>Lon: %{x:.4f}<extra></extra>",
            ))
            fig_nkde.update_layout(
                **theme.plot_base({"l": 40, "r": 60, "t": 8, "b": 40}, no_axes=True),
                showlegend=False,
                xaxis={"title": "Longitud", "gridcolor": theme.border,
                       "showline": False, "zeroline": False, "tickfont": {"size": 8}},
                yaxis={"title": "Latitud", "gridcolor": theme.border,
                       "showline": False, "zeroline": False, "tickfont": {"size": 8}},
            )
        else:
            fig_nkde = empty

        return kpis, fig_r, fig_s, nni_info, fig_g, fig_h, fig_nkde

    # -- Layout helpers ------------------------------------------------------

    def _near_repeat_panel(self) -> html.Div:
        t = self._theme
        return html.Div(className="panel", children=[
            html.Div(["Near Repeat Analysis",
                      html.Span("Johnson et al. 2007", className="tag accent")],
                     className="panel-title"),
            html.Div(id="adv-nr-kpis", style={
                "display": "grid", "gridTemplateColumns": "repeat(4,1fr)",
                "gap": "8px", "marginBottom": "10px",
            }),
            html.Div(className="grid grid-2", children=[
                dcc.Graph(id="adv-nr-radios", config={"displayModeBar": False}, style={"height": "200px"}),
                dcc.Graph(id="adv-nr-serie", config={"displayModeBar": False}, style={"height": "200px"}),
            ]),
            self._info_box(t.amber,
                "¿Qué mide? ",
                "Si un hecho delictual genera un área de riesgo elevado en los días siguientes. "
                "Un % alto indica que los hechos no son independientes — el victimizador "
                "regresa o recomienda la zona. Permite alertas tempranas de victimización repetida."),
        ])

    def _nni_panel(self) -> html.Div:
        t = self._theme
        return html.Div(className="panel", children=[
            html.Div(["Nearest Neighbor Index",
                      html.Span("Clark & Evans 1954", className="tag")],
                     className="panel-title"),
            html.Div(id="adv-nni-resultado"),
            html.Div(className="grid grid-2", children=[
                dcc.Graph(id="adv-nni-gauge", config={"displayModeBar": False}, style={"height": "180px"}),
                dcc.Graph(id="adv-nni-hist", config={"displayModeBar": False}, style={"height": "180px"}),
            ]),
            self._info_box(t.info,
                "¿Qué mide? ",
                "R < 1 indica clustering (hechos más agrupados que el azar). "
                "R = 1 distribución aleatoria. R > 1 distribución dispersa. "
                "El z-score indica si el resultado es estadísticamente significativo."),
        ])

    def _nkde_panel(self) -> html.Div:
        t = self._theme
        return html.Div(className="panel", children=[
            html.Div(["Network KDE — densidad sobre red vial",
                      html.Span("Xie & Yan 2008", className="tag accent")],
                     className="panel-title"),
            dcc.Graph(id="adv-nkde", config={"displayModeBar": False}, style={"height": "320px"}),
            self._info_box(t.success,
                "¿Qué mejora vs KDE estándar? ",
                "El KDE euclidiano calcula distancias en línea recta, ignorando que los "
                "desplazamientos ocurren por calles. El Network KDE usa distancia Manhattan "
                "como proxy de la red vial urbana — más preciso en contexto urbano de cuadrícula."),
        ])

    def _info_box(self, accent_color: str, title: str, body: str) -> html.Div:
        t = self._theme
        return html.Div(style={
            "background": t.bg3, "border": f"1px solid {t.border}",
            "borderLeft": f"3px solid {accent_color}",
            "padding": "10px 14px", "marginTop": "8px",
            "fontSize": "11px", "lineHeight": "1.7", "color": t.text2,
            "fontFamily": t.font_mono,
        }, children=[
            html.Span(title, style={"color": accent_color, "fontWeight": "600"}),
            body,
        ])

    def _kpi_mini(self, value: str, label: str, color: str) -> html.Div:
        t = self._theme
        return html.Div(style={
            "background": t.bg1, "border": f"1px solid {t.border}",
            "borderLeft": f"3px solid {color}", "padding": "10px 12px",
        }, children=[
            html.Div(value, style={
                "fontFamily": t.font_mono, "fontSize": "20px", "fontWeight": "500",
                "color": color, "lineHeight": "1",
            }),
            html.Div(label, style={"fontSize": "10px", "color": t.text3, "marginTop": "4px"}),
        ])
