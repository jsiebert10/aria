"""Emerging crime detection module.

Detects crime types with significant frequency variation
compared to the previous period.
"""

from __future__ import annotations

import pandas as pd
import plotly.graph_objects as go
from dash import Dash, Input, Output, dcc, html

from aria.data.store import DataStore
from aria.modules.base import BaseModule
from aria.theme import Theme


class EmergingModule(BaseModule):
    """Identifies phenomena with >=20% variation vs. the prior period."""

    module_id = "emergentes"
    display_name = "Detección emergentes"

    def __init__(self, store: DataStore, theme: Theme) -> None:
        super().__init__(store, theme)

    def get_layout(self) -> html.Div:
        return html.Div([
            html.Div(className="mod-header", children=[
                html.Div([
                    html.Div("Detección de delitos emergentes", className="mod-title"),
                    html.Div(
                        "Variación de frecuencia respecto al período anterior",
                        className="mod-sub",
                    ),
                ]),
                html.Div(className="mod-actions", children=[
                    dcc.Dropdown(
                        id="emg-per", clearable=False, className="dropdown",
                        style={"width": "180px", "display": "inline-block"},
                    ),
                ]),
            ]),
            html.Div(id="emg-alertas", className="alertas-row"),
            html.Div(className="mod-body", children=[
                html.Div(className="mod-col-left", children=[
                    html.Div("Variación por fenómeno", className="chart-title"),
                    dcc.Graph(
                        id="emg-barras", config={"displayModeBar": False},
                        style={"height": "320px"},
                    ),
                ]),
                html.Div(className="mod-col-right", children=[
                    html.Div("Tendencia mensual completa", className="chart-title"),
                    dcc.Graph(
                        id="emg-lineas", config={"displayModeBar": False},
                        style={"height": "320px"},
                    ),
                ]),
            ]),
            html.Div(id="emg-tabla-wrap", className="tabla-section"),
        ], className="modulo-wrap")

    def register_callbacks(self, app: Dash) -> None:
        store = self._store
        theme = self._theme

        @app.callback(
            Output("emg-per", "options"),
            Output("emg-per", "value"),
            Input("store", "data"),
        )
        def init_period(_: object) -> tuple:
            opts = [{"label": p, "value": p} for p in store.periods]
            val = store.periods[-1] if store.periods else None
            return opts, val

        @app.callback(
            Output("emg-alertas", "children"),
            Output("emg-barras", "figure"),
            Output("emg-lineas", "figure"),
            Output("emg-tabla-wrap", "children"),
            Input("emg-per", "value"),
        )
        def update(period: str | None) -> tuple:
            empty = theme.empty_figure()

            if not period or store.is_empty:
                return [], empty, empty, ""

            df_var = self._compute_variation(period)
            if df_var.empty:
                return (
                    [html.Div(
                        "Selecciona al menos dos períodos para comparar.",
                        className="alerta",
                    )],
                    empty, empty, "",
                )

            alerts = self._build_alerts(df_var, theme)
            bar_fig = self._build_bar_chart(df_var, theme)
            line_fig = self._build_line_chart(df_var, period, store, theme)
            table = self._build_table(df_var, period, store, theme)

            return alerts, bar_fig, line_fig, table

    # -- Private helpers -----------------------------------------------------

    def _compute_variation(self, current_period: str) -> pd.DataFrame:
        """Compute frequency variation vs. the previous period."""
        store = self._store
        if store.is_empty:
            return pd.DataFrame()

        idx = store.periods.index(current_period)
        if idx == 0:
            return pd.DataFrame()
        prev_period = store.periods[idx - 1]

        df_curr = store.filter_by(period=current_period)
        df_prev = store.filter_by(period=prev_period)

        cnt_curr = df_curr["fenomeno"].value_counts().reset_index()
        cnt_prev = df_prev["fenomeno"].value_counts().reset_index()
        cnt_curr.columns = ["fenomeno", "n_actual"]
        cnt_prev.columns = ["fenomeno", "n_anterior"]

        merged = cnt_curr.merge(cnt_prev, on="fenomeno", how="outer").fillna(0)
        merged["variacion_pct"] = (
            (merged["n_actual"] - merged["n_anterior"])
            / merged["n_anterior"].replace(0, 1)
            * 100
        ).round(1)
        merged["variacion_abs"] = (
            merged["n_actual"] - merged["n_anterior"]
        ).astype(int)
        return merged.sort_values("variacion_pct", ascending=False)

    @staticmethod
    def _build_alerts(df: pd.DataFrame, theme: Theme) -> list:
        alerts: list = []
        for _, row in df.iterrows():
            if abs(row["variacion_pct"]) >= 20:
                color = theme.danger if row["variacion_pct"] > 0 else theme.success
                sign = "+" if row["variacion_pct"] > 0 else ""
                label = "alza" if row["variacion_pct"] > 0 else "baja"
                alerts.append(html.Div(className="alerta-chip", children=[
                    html.Span(row["fenomeno"], className="alerta-fen"),
                    html.Span(
                        f"{sign}{row['variacion_pct']}%",
                        style={
                            "color": color, "fontWeight": "500",
                            "marginLeft": "6px", "fontSize": "12px",
                        },
                    ),
                    html.Span(
                        f" en {label}",
                        style={"color": theme.text2, "fontSize": "11px"},
                    ),
                ]))

        if not alerts:
            alerts = [html.Div(
                "Sin variaciones significativas (≥20%) en el período.",
                style={"fontSize": "12px", "color": theme.text2, "padding": "8px 0"},
            )]
        return alerts

    @staticmethod
    def _build_bar_chart(df: pd.DataFrame, theme: Theme) -> go.Figure:
        colors = [
            theme.danger if v > 0 else theme.success
            for v in df["variacion_pct"]
        ]
        fig = go.Figure()
        fig.add_trace(go.Bar(
            x=df["variacion_pct"], y=df["fenomeno"],
            orientation="h",
            marker_color=colors, marker_line_width=0,
            customdata=df[["n_anterior", "n_actual", "variacion_abs"]].values,
            hovertemplate=(
                "<b>%{y}</b><br>"
                "Anterior: %{customdata[0]:.0f}<br>"
                "Actual: %{customdata[1]:.0f}<br>"
                "Variación: %{x:.1f}% (%{customdata[2]:+.0f})<extra></extra>"
            ),
        ))
        fig.add_vline(x=0, line_color=theme.border, line_width=1)
        fig.update_layout(
            **theme.plot_base({"l": 150, "r": 16, "t": 10, "b": 36}),
            bargap=0.3, showlegend=False,
        )
        fig.update_yaxes(tickfont={"size": 10})
        return fig

    @staticmethod
    def _build_line_chart(
        df_var: pd.DataFrame,
        period: str,
        store: DataStore,
        theme: Theme,
    ) -> go.Figure:
        fig = go.Figure()
        series = (
            store.df
            .groupby(["periodo_orden", "periodo_label", "fenomeno"])
            .size().reset_index(name="n")
            .sort_values("periodo_orden")
        )
        top_phenomena = df_var.head(5)["fenomeno"].tolist()
        line_colors = [
            theme.danger, theme.warning, theme.info,
            theme.success, "#7c5cfc",
        ]
        for i, phen in enumerate(top_phenomena):
            s = series[series["fenomeno"] == phen]
            is_current = s["periodo_label"] == period
            c = line_colors[i % len(line_colors)]
            fig.add_trace(go.Scatter(
                x=s["periodo_label"], y=s["n"],
                mode="lines+markers", name=phen,
                line={"color": c, "width": 2},
                marker={
                    "size": [10 if a else 5 for a in is_current],
                    "color": c,
                    "line": {"color": "white", "width": 1.5},
                },
                hovertemplate=f"<b>{phen}</b><br>%{{x}}: %{{y}}<extra></extra>",
            ))
        fig.update_layout(
            **theme.plot_base(), showlegend=True,
            legend={
                "orientation": "h", "x": 0.5, "xanchor": "center", "y": -0.22,
                "font": {"size": 10, "color": theme.text2},
                "bgcolor": "rgba(0,0,0,0)",
            },
        )
        return fig

    @staticmethod
    def _build_table(
        df: pd.DataFrame,
        period: str,
        store: DataStore,
        theme: Theme,
    ) -> html.Div:
        idx = store.periods.index(period)
        prev_period = store.periods[idx - 1] if idx > 0 else "—"

        rows = [html.Tr([
            html.Th(c, className="th-cell") for c in
            ["Fenómeno", "Período anterior", "Período actual",
             "Variación %", "Variación abs.", "Alerta"]
        ])]
        for _, row in df.iterrows():
            v = row["variacion_pct"]
            col = (
                theme.danger if v >= 20
                else theme.success if v <= -20
                else theme.text2
            )
            label = (
                "Alza significativa" if v >= 20
                else "Baja significativa" if v <= -20
                else "Normal"
            )
            rows.append(html.Tr([
                html.Td(row["fenomeno"], className="td-per"),
                html.Td(str(int(row["n_anterior"])), className="td-num"),
                html.Td(str(int(row["n_actual"])), className="td-num"),
                html.Td(
                    f"{'+'if v > 0 else''}{v}%", className="td-num",
                    style={"color": col, "fontWeight": "500"},
                ),
                html.Td(
                    f"{'+'if row['variacion_abs'] > 0 else''}{row['variacion_abs']}",
                    className="td-num",
                ),
                html.Td(html.Span(label, style={
                    "background": f"{col}22", "color": col,
                    "padding": "2px 7px", "borderRadius": "4px",
                    "fontSize": "10px", "fontWeight": "500",
                })),
            ], className="tr-base"))

        return html.Div([
            html.Div(
                f"Comparativa: {prev_period} → {period}",
                className="chart-title", style={"marginTop": "12px"},
            ),
            html.Div(
                html.Table(rows, className="comp-table"),
                className="tabla-wrap",
            ),
        ])
