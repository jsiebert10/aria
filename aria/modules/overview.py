"""Executive overview module — Panorama operacional.

KPIs, time series, Pareto, donut, recent events table, and
per-phenomenon summary for the current vs. previous period.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import numpy as np
import pandas as pd
import plotly.graph_objects as go
from dash import Dash, Input, Output, dcc, html
from dash.exceptions import PreventUpdate

from aria.analysis.spatial import SpatialAnalyzer
from aria.data.store import DataStore
from aria.modules.base import BaseModule
from aria.theme import Theme


@dataclass
class NavItem:
    """Module navigation entry for the overview card grid."""

    id: str
    label: str
    group: str
    color: str
    badge: str | None


class OverviewModule(BaseModule):
    """Executive summary dashboard — first screen the user sees."""

    module_id = "resumen"
    display_name = "Panorama"

    def __init__(
        self,
        store: DataStore,
        theme: Theme,
        analyzer: SpatialAnalyzer,
        nav_modules: list[NavItem] | None = None,
    ) -> None:
        super().__init__(store, theme)
        self._analyzer = analyzer
        self._nav_modules = nav_modules or []

    def get_layout(self) -> html.Div:
        s = self._store
        t = self._theme

        if s.is_empty or not s.periods:
            return html.Div("Sin datos.", style={"padding": "2rem", "color": t.text3})

        latest = s.periods[-1]
        previous = s.periods[-2] if len(s.periods) > 1 else None
        df_latest = s.filter_by(period=latest)
        df_prev = s.filter_by(period=previous) if previous else pd.DataFrame()
        total = len(df_latest)
        total_prev = len(df_prev)
        var_total = round((total - total_prev) / max(total_prev, 1) * 100, 1) if total_prev else 0

        rows, alerts_up, alerts_dn = self._compute_phenomenon_rows(latest, previous)
        rows_sorted = sorted(rows, key=lambda x: x["n"], reverse=True)

        # Synthetic hourly distribution
        _ph = [0.012, 0.008, 0.006, 0.004, 0.003, 0.003, 0.008, 0.018, 0.030, 0.040,
               0.048, 0.052, 0.055, 0.058, 0.055, 0.052, 0.050, 0.060, 0.070, 0.072,
               0.068, 0.060, 0.045, 0.025]
        ph = [p / sum(_ph) for p in _ph]
        np.random.seed(42)
        hourly = np.random.choice(24, size=total, p=ph)
        hc = pd.Series(hourly).value_counts().sort_index()
        peak_hour = int(hc.idxmax())

        n_alerts = len(alerts_up) + len(alerts_dn)

        # -- Figures --
        fig_series = self._build_series_chart(t)
        fig_pareto = self._build_pareto_chart(df_latest, t)
        fig_mix = self._build_mix_chart(df_latest, t)
        recent_rows = self._build_recent_table(t)

        return html.Div(className="modulo-wrap", children=[
            html.Div(className="mod-header", children=[
                html.Div([
                    html.Div("01 / Vista ejecutiva", className="mod-eyebrow"),
                    html.Div("Panorama operacional", className="mod-title"),
                    html.Div(f"Región Metropolitana · {latest} vs {previous or '—'}",
                             className="mod-sub"),
                ]),
                html.Div(className="mod-actions", children=[
                    *[html.Span(f"↑ {fen}  +{v}%", style={
                        "fontFamily": t.font_mono, "fontSize": "10px",
                        "padding": "4px 10px", "background": f"{t.danger}18",
                        "border": f"1px solid {t.danger}44", "color": t.danger,
                    }) for fen, v in alerts_up[:3]],
                    *[html.Span(f"↓ {fen}  {v}%", style={
                        "fontFamily": t.font_mono, "fontSize": "10px",
                        "padding": "4px 10px", "background": f"{t.success}18",
                        "border": f"1px solid {t.success}44", "color": t.success,
                    }) for fen, v in alerts_dn[:2]],
                    html.Button("Producto analítico →", id="btn-go-report", n_clicks=0,
                        style={
                            "fontFamily": t.font_mono, "fontSize": "10px",
                            "padding": "5px 12px", "background": t.amber,
                            "border": f"1px solid {t.amber}", "color": "#0a0e14",
                            "cursor": "pointer", "fontWeight": "600", "marginLeft": "4px",
                        }),
                ]),
            ]),
            html.Div(className="mod-body", children=[
                html.Div(className="grid grid-4", children=[
                    self._kpi(f"{total:,}", "Hechos · período actual",
                              f"{'+'if var_total > 0 else''}{var_total}% vs {previous}",
                              t.danger if var_total > 5 else t.success if var_total < -5 else t.warning),
                    self._kpi(
                        str(max((r["n"] for r in rows), default=0)),
                        max(rows, key=lambda x: x["n"], default={"fen": "—"})["fen"],
                        "Fenómeno más frecuente", t.info,
                    ),
                    self._kpi(f"{peak_hour:02d}:00h", "Hora pico · aorístico",
                              "franja vespertina-nocturna", t.warning),
                    self._kpi(str(n_alerts), "Fenómenos en alerta",
                              "variación ≥15% vs período anterior",
                              t.danger if n_alerts > 0 else t.success),
                ]),
                html.Div(className="grid grid-2", children=[
                    html.Div(className="panel", children=[
                        html.Div(className="panel-title", children=[
                            "Serie diaria por tipología",
                            html.Span(f"últimos {s.period_count} períodos", className="tag"),
                        ]),
                        dcc.Graph(figure=fig_series, config={"displayModeBar": False},
                                  style={"height": "180px"}),
                    ]),
                    html.Div(className="panel", children=[
                        html.Div(className="panel-title", children=[
                            "Concentración por comuna",
                            html.Span("ley 80/20 · Weisburd", className="tag accent"),
                        ]),
                        dcc.Graph(figure=fig_pareto, config={"displayModeBar": False},
                                  style={"height": "180px"}),
                    ]),
                ]),
                html.Div(className="grid grid-sidebar", children=[
                    html.Div(className="panel", children=[
                        html.Div(className="panel-title", children=["Mix delictual"]),
                        dcc.Graph(figure=fig_mix, config={"displayModeBar": False},
                                  style={"height": "220px"}),
                    ]),
                    html.Div(className="panel", children=[
                        html.Div(className="panel-title", children=["Últimos hechos relevantes"]),
                        html.Div(style={"maxHeight": "240px", "overflowY": "auto"}, children=[
                            html.Table(style={
                                "width": "100%", "borderCollapse": "collapse", "fontSize": "11px",
                            }, children=[
                                html.Thead(html.Tr([
                                    html.Th(col, style={
                                        "padding": "6px 8px", "fontFamily": t.font_mono,
                                        "fontSize": "9px", "color": t.text3,
                                        "textTransform": "uppercase", "letterSpacing": ".8px",
                                        "borderBottom": f"1px solid {t.border}", "textAlign": "left",
                                    }) for col in ["Fecha", "Tipo", "Comuna", "RUC", "Estado"]
                                ])),
                                html.Tbody(recent_rows),
                            ]),
                        ]),
                    ]),
                ]),
                self._phenomenon_summary_table(rows_sorted, t),
                self._module_cards_panel(t),
            ]),
        ])

    def register_callbacks(self, app: Dash) -> None:
        @app.callback(
            Output("active-module", "data", allow_duplicate=True),
            Input("btn-go-report", "n_clicks"),
            prevent_initial_call=True,
        )
        def go_to_reports(n):
            if not n:
                raise PreventUpdate
            return "reportes"

    # -- Data computation ----------------------------------------------------

    def _compute_phenomenon_rows(
        self, latest: str, previous: str | None,
    ) -> tuple[list[dict], list[tuple], list[tuple]]:
        s = self._store
        analyzer = self._analyzer
        rows: list[dict] = []
        alerts_up: list[tuple] = []
        alerts_dn: list[tuple] = []

        for fen in s.phenomena:
            df_f = s.filter_by(phenomenon=fen)
            n = len(df_f[df_f["periodo_label"] == latest])
            na = len(df_f[df_f["periodo_label"] == previous]) if previous else 0
            v = round((n - na) / max(na, 1) * 100, 1) if na else 0
            ca = analyzer.mean_center(df_f[df_f["periodo_label"] == latest])
            cp = analyzer.mean_center(df_f[df_f["periodo_label"] == previous]) if previous else None
            d = analyzer.displacement(cp, ca)
            rows.append({
                "fen": fen, "n": n, "v": v,
                "km": round(d.distance_km, 2) if d else None,
                "dir": d.direction if d else "—",
            })
            if v >= 15:
                alerts_up.append((fen, v))
            if v <= -15:
                alerts_dn.append((fen, v))

        return rows, alerts_up, alerts_dn

    # -- Figure builders -----------------------------------------------------

    def _build_series_chart(self, t: Theme) -> go.Figure:
        s = self._store
        fig = go.Figure()
        for idx, fen in enumerate(s.phenomena[:6]):
            serie_f = (
                s.filter_by(phenomenon=fen)
                .groupby(["periodo_orden", "periodo_label"]).size()
                .reset_index(name="n").sort_values("periodo_orden")
            )
            c = t.series_colors[idx % len(t.series_colors)]
            fig.add_trace(go.Scatter(
                x=serie_f["periodo_label"], y=serie_f["n"],
                mode="lines+markers", name=fen,
                line={"color": c, "width": 1.5}, marker={"size": 4},
                hovertemplate=f"{fen}: %{{y}}<extra></extra>",
            ))
        fig.update_layout(
            **t.plot_base({"l": 36, "r": 8, "t": 8, "b": 28}),
            showlegend=True,
            legend={"orientation": "h", "x": 0, "y": 1.15,
                    "font": {"size": 8, "color": t.text3}, "bgcolor": "rgba(0,0,0,0)"},
        )
        return fig

    def _build_pareto_chart(self, df: pd.DataFrame, t: Theme) -> go.Figure:
        top20 = df["comuna"].value_counts().head(20)
        coms = top20.index.tolist()
        vals = top20.values.tolist()
        cumul = np.cumsum(vals) / sum(vals) * 100

        fig = go.Figure()
        fig.add_trace(go.Bar(
            x=coms, y=vals, marker_color=t.amber, marker_line_width=0,
            name="Eventos", yaxis="y", hovertemplate="%{x}: %{y}<extra></extra>",
        ))
        fig.add_trace(go.Scatter(
            x=coms, y=cumul, mode="lines+markers",
            line={"color": t.danger, "width": 2}, marker={"size": 5, "color": t.danger},
            name="Acum. %", yaxis="y2", hovertemplate="%{x}: %{y:.1f}%<extra></extra>",
        ))
        fig.update_layout(
            **t.plot_base({"l": 36, "r": 40, "t": 8, "b": 60}, no_axes=True),
            legend={"orientation": "h", "x": 0, "y": 1.12,
                    "font": {"size": 9, "color": t.text3}, "bgcolor": "rgba(0,0,0,0)"},
            xaxis={"gridcolor": t.border, "showline": False, "zeroline": False,
                   "tickangle": -35, "tickfont": {"size": 8}},
            yaxis={"gridcolor": t.border, "showline": False, "zeroline": False},
            yaxis2={"overlaying": "y", "side": "right", "range": [0, 110],
                    "tickformat": ".0f", "ticksuffix": "%",
                    "gridcolor": "rgba(0,0,0,0)", "showline": False, "zeroline": False,
                    "tickfont": {"size": 8, "color": t.danger}},
        )
        return fig

    def _build_mix_chart(self, df: pd.DataFrame, t: Theme) -> go.Figure:
        mix_cnt = df["fenomeno"].value_counts()
        fig = go.Figure()
        fig.add_trace(go.Pie(
            labels=mix_cnt.index.tolist(), values=mix_cnt.values.tolist(),
            hole=0.55, marker_colors=list(t.series_colors[:len(mix_cnt)]),
            textinfo="none",
            hovertemplate="%{label}: %{value} (%{percent})<extra></extra>",
        ))
        fig.update_layout(
            paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
            margin={"l": 0, "r": 0, "t": 8, "b": 8}, showlegend=True,
            font={"color": t.text2, "size": 9, "family": t.font_sans},
            legend={"orientation": "v", "x": 1.0, "y": 0.5,
                    "font": {"size": 9, "color": t.text2}, "bgcolor": "rgba(0,0,0,0)"},
        )
        return fig

    def _build_recent_table(self, t: Theme) -> list:
        s = self._store
        statuses = ["En investigación", "Formalizada", "Archivada provisional",
                    "Con imputado conocido", "En indagación"]
        col_map = {
            f: t.series_colors[i % len(t.series_colors)]
            for i, f in enumerate(s.phenomena)
        }
        np.random.seed(99)
        recent: list[dict[str, Any]] = []
        for _ in range(8):
            period = np.random.choice(s.periods)
            df_m = s.filter_by(period=period)
            if len(df_m) == 0:
                continue
            row = df_m.sample(1).iloc[0]
            hour = f"{np.random.randint(0, 24):02d}:{np.random.randint(0, 60):02d}"
            day = f"{np.random.randint(1, 28):02d}-{period.split()[1][:3]}-2025"
            ruc = f"{np.random.randint(int(1e9), int(9e9))}-{np.random.randint(0, 9)}"
            recent.append({
                "fecha": f"{day} {hour}", "tipo": row["fenomeno"],
                "comuna": row["comuna"], "ruc": ruc,
                "estado": np.random.choice(statuses),
            })

        return [html.Tr(style={"borderBottom": f"1px solid {t.border}22"}, children=[
            html.Td(r["fecha"], style={
                "padding": "6px 8px", "fontFamily": t.font_mono,
                "fontSize": "10px", "color": t.text3,
            }),
            html.Td(html.Span(r["tipo"], style={
                "fontSize": "9px", "padding": "2px 6px", "fontWeight": "500",
                "background": f"{col_map.get(r['tipo'], t.amber)}22",
                "color": col_map.get(r["tipo"], t.amber),
            }), style={"padding": "6px 8px"}),
            html.Td(r["comuna"], style={"padding": "6px 8px", "fontSize": "11px", "color": t.text}),
            html.Td(r["ruc"], style={
                "padding": "6px 8px", "fontFamily": t.font_mono, "fontSize": "10px", "color": t.text3,
            }),
            html.Td(r["estado"], style={"padding": "6px 8px", "fontSize": "11px", "color": t.text2}),
        ]) for r in recent]

    # -- Layout helpers ------------------------------------------------------

    def _kpi(self, value: str, label: str, delta: str, color: str) -> html.Div:
        t = self._theme
        return html.Div(className="kpi", children=[
            html.Div(label, className="kpi-label"),
            html.Div(value, className="kpi-value", style={"color": color}),
            html.Div(delta, className="kpi-delta", style={
                "color": t.danger if "+" in str(delta) and color == t.danger
                         else t.success if color == t.success else t.text3,
            }),
        ])

    def _phenomenon_summary_table(self, rows: list[dict], t: Theme) -> html.Div:
        return html.Div(className="panel", children=[
            html.Div(className="panel-title", children=["Resumen por fenómeno"]),
            html.Table(className="comp-table", children=[
                html.Thead(html.Tr([
                    html.Th(c, className="th-cell") for c in
                    ["Fenómeno", "Hechos", "Variación", "Desplaz.", "Dirección", "Estado"]
                ])),
                html.Tbody([html.Tr(className="tr-base", children=[
                    html.Td(r["fen"], className="td-per"),
                    html.Td(str(r["n"]), className="td-num"),
                    html.Td(html.Span(
                        f"{'+'if r['v'] > 0 else''}{r['v']}%",
                        style={
                            "color": t.danger if r["v"] >= 15 else t.success if r["v"] <= -15 else t.text3,
                            "fontFamily": t.font_mono, "fontSize": "11px",
                        },
                    ), className="td-num"),
                    html.Td(f"{r['km']} km" if r["km"] else "—", className="td-num"),
                    html.Td(r["dir"], className="td-cen"),
                    html.Td(html.Span(
                        "↑ ALZA" if r["v"] >= 15 else "↓ BAJA" if r["v"] <= -15 else "NORMAL",
                        style={
                            "fontFamily": t.font_mono, "fontSize": "9px",
                            "padding": "2px 6px", "letterSpacing": ".5px",
                            "background": f"{t.danger}18" if r["v"] >= 15
                                          else f"{t.success}18" if r["v"] <= -15
                                          else t.bg3,
                            "color": t.danger if r["v"] >= 15
                                     else t.success if r["v"] <= -15
                                     else t.text3,
                        },
                    ), style={"padding": "8px 12px"}),
                ]) for r in rows]),
            ]),
        ])

    def _module_cards_panel(self, t: Theme) -> html.Div:
        if not self._nav_modules:
            return html.Div()
        return html.Div(className="panel", children=[
            html.Div(className="panel-title", children=["Módulos de la plataforma"]),
            html.Div(className="modules-grid", children=[
                self._mod_card(nav, t) for nav in self._nav_modules
            ]),
        ])

    @staticmethod
    def _mod_card(nav: NavItem, t: Theme) -> html.Div:
        bs = t.badge_style(nav.badge or "pronto")
        active = nav.badge in ("activo", "dev")
        return html.Div(
            id=f"modcard-{nav.id}", n_clicks=0,
            className="module-card" + ("" if active else " module-soon"),
            children=[
                html.Div(className="mod-card-icon",
                         style={"borderColor": nav.color if active else t.border}),
                html.Div(nav.label, className="mod-card-name"),
                html.Span(nav.badge or "—", className="mod-card-tag", style=bs),
            ],
        )
