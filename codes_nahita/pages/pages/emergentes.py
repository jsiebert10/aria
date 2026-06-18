# =============================================================================
# pages/emergentes.py — Módulo de Detección de Delitos Emergentes
# Detecta modalidades con variación significativa respecto al período anterior.
# =============================================================================

import pandas as pd
import plotly.graph_objects as go
from dash import dcc, html, Input, Output, callback
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

# ── Colores ───────────────────────────────────────────────────────────────────
BG    = "#1a1d27"
SURF  = "#22263a"
BORDE = "#2e3250"
TEXT  = "#e8eaf0"
TEXT2 = "#8b91b0"
VERDE = "#4fcc8e"
ROJO  = "#f75f5f"
AMBAR = "#f7b84f"
AZUL  = "#4f8ef7"

def _layout_base(m=None):
    mg = m or dict(l=44,r=16,t=16,b=36)
    return dict(
        paper_bgcolor=BG, plot_bgcolor=BG,
        font=dict(color=TEXT, size=11, family="DM Sans,sans-serif"),
        margin=mg,
        xaxis=dict(gridcolor=BORDE, showline=False, zeroline=False),
        yaxis=dict(gridcolor=BORDE, showline=False, zeroline=False),
    )

def _generar_datos_emergentes(df_global, fenomeno, periodo_actual, periodos):
    """Calcula variación de frecuencia vs período anterior."""
    if df_global is None or df_global.empty:
        return pd.DataFrame()
    idx = periodos.index(periodo_actual)
    if idx == 0:
        return pd.DataFrame()
    per_ant = periodos[idx - 1]

    df_act = df_global[df_global["periodo_label"] == periodo_actual]
    df_ant = df_global[df_global["periodo_label"] == per_ant]

    # Contar por fenómeno
    cnt_act = df_act["fenomeno"].value_counts().reset_index()
    cnt_ant = df_ant["fenomeno"].value_counts().reset_index()
    cnt_act.columns = ["fenomeno","n_actual"]
    cnt_ant.columns = ["fenomeno","n_anterior"]

    merged = cnt_act.merge(cnt_ant, on="fenomeno", how="outer").fillna(0)
    merged["variacion_pct"] = ((merged["n_actual"] - merged["n_anterior"])
                               / merged["n_anterior"].replace(0,1) * 100).round(1)
    merged["variacion_abs"] = (merged["n_actual"] - merged["n_anterior"]).astype(int)
    merged = merged.sort_values("variacion_pct", ascending=False)
    return merged


def get_layout():
    return html.Div([
        html.Div(className="mod-header", children=[
            html.Div([
                html.Div("Detección de delitos emergentes", className="mod-title"),
                html.Div("Variación de frecuencia respecto al período anterior",
                         className="mod-sub"),
            ]),
            html.Div(className="mod-actions", children=[
                dcc.Dropdown(id="emg-per", clearable=False, className="dropdown",
                             style={"width":"180px","display":"inline-block"}),
            ]),
        ]),

        html.Div(id="emg-alertas", className="alertas-row"),

        html.Div(className="mod-body", children=[
            html.Div(className="mod-col-left", children=[
                html.Div("Variación por fenómeno", className="chart-title"),
                dcc.Graph(id="emg-barras", config={"displayModeBar":False},
                          style={"height":"320px"}),
            ]),
            html.Div(className="mod-col-right", children=[
                html.Div("Tendencia mensual completa", className="chart-title"),
                dcc.Graph(id="emg-lineas", config={"displayModeBar":False},
                          style={"height":"320px"}),
            ]),
        ]),

        html.Div(id="emg-tabla-wrap", className="tabla-section"),
    ], className="modulo-wrap")


def registrar_callbacks(app, df_global, periodos):

    @app.callback(
        Output("emg-per","options"),
        Output("emg-per","value"),
        Input("store","data"),
    )
    def init_periodo(_):
        opts = [{"label":p,"value":p} for p in periodos]
        val  = periodos[-1] if periodos else None
        return opts, val

    @app.callback(
        Output("emg-alertas","children"),
        Output("emg-barras","figure"),
        Output("emg-lineas","figure"),
        Output("emg-tabla-wrap","children"),
        Input("emg-per","value"),
    )
    def actualizar(periodo):
        vacia = go.Figure(layout=go.Layout(**_layout_base()))
        vacia.add_annotation(text="Sin datos",x=0.5,y=0.5,xref="paper",yref="paper",
                             showarrow=False,font=dict(color=TEXT2))

        if not periodo or df_global is None or df_global.empty:
            return [], vacia, vacia, ""

        df = _generar_datos_emergentes(df_global, None, periodo, periodos)
        if df.empty:
            return [html.Div("Selecciona al menos dos períodos para comparar.",
                    className="alerta")], vacia, vacia, ""

        # ── Alertas ───────────────────────────────────────────────────────────
        alertas = []
        for _, row in df.iterrows():
            if abs(row["variacion_pct"]) >= 20:
                color = ROJO if row["variacion_pct"] > 0 else VERDE
                signo = "+" if row["variacion_pct"] > 0 else ""
                etiq  = "alza" if row["variacion_pct"] > 0 else "baja"
                alertas.append(html.Div(className="alerta-chip", children=[
                    html.Span(row["fenomeno"], className="alerta-fen"),
                    html.Span(f"{signo}{row['variacion_pct']}%",
                              style={"color":color,"fontWeight":"500","marginLeft":"6px",
                                     "fontSize":"12px"}),
                    html.Span(f" en {etiq}", style={"color":TEXT2,"fontSize":"11px"}),
                ]))

        if not alertas:
            alertas = [html.Div("Sin variaciones significativas (≥20%) en el período.",
                                style={"fontSize":"12px","color":TEXT2,"padding":"8px 0"})]

        # ── Barras de variación ───────────────────────────────────────────────
        colores = [ROJO if v > 0 else VERDE for v in df["variacion_pct"]]
        fig_b = go.Figure()
        fig_b.add_trace(go.Bar(
            x=df["variacion_pct"], y=df["fenomeno"],
            orientation="h",
            marker_color=colores, marker_line_width=0,
            customdata=df[["n_anterior","n_actual","variacion_abs"]].values,
            hovertemplate=(
                "<b>%{y}</b><br>"
                "Anterior: %{customdata[0]:.0f}<br>"
                "Actual: %{customdata[1]:.0f}<br>"
                "Variación: %{x:.1f}% (%{customdata[2]:+.0f})<extra></extra>"
            ),
        ))
        fig_b.add_vline(x=0, line_color=BORDE, line_width=1)
        fig_b.update_layout(
            **_layout_base(dict(l=150,r=16,t=10,b=36)),
            bargap=0.3, showlegend=False,
        )
        fig_b.update_yaxes(tickfont=dict(size=10))

        # ── Líneas de tendencia por fenómeno ─────────────────────────────────
        fig_l = go.Figure()
        serie = (
            df_global.groupby(["periodo_orden","periodo_label","fenomeno"])
            .size().reset_index(name="n").sort_values("periodo_orden")
        )
        top_fen = df.head(5)["fenomeno"].tolist()
        colores_l = [ROJO,AMBAR,AZUL,VERDE,"#7c5cfc"]
        for i, fen in enumerate(top_fen):
            s = serie[serie["fenomeno"]==fen]
            es_act = s["periodo_label"] == periodo
            fig_l.add_trace(go.Scatter(
                x=s["periodo_label"], y=s["n"],
                mode="lines+markers",
                name=fen,
                line=dict(color=colores_l[i%len(colores_l)], width=2),
                marker=dict(
                    size=[10 if a else 5 for a in es_act],
                    color=colores_l[i%len(colores_l)],
                    line=dict(color="white",width=1.5),
                ),
                hovertemplate=f"<b>{fen}</b><br>%{{x}}: %{{y}}<extra></extra>",
            ))
        fig_l.update_layout(**_layout_base(), showlegend=True,
            legend=dict(orientation="h",x=0.5,xanchor="center",y=-0.22,
                        font=dict(size=10,color=TEXT2),bgcolor="rgba(0,0,0,0)"))

        # ── Tabla resumen ─────────────────────────────────────────────────────
        idx_per = periodos.index(periodo)
        per_ant = periodos[idx_per-1] if idx_per>0 else "—"

        filas = [html.Tr([
            html.Th(c, className="th-cell") for c in
            ["Fenómeno","Período anterior","Período actual","Variación %","Variación abs.","Alerta"]
        ])]
        for _, row in df.iterrows():
            v = row["variacion_pct"]
            col = ROJO if v>=20 else VERDE if v<=-20 else TEXT2
            etiq = "Alza significativa" if v>=20 else "Baja significativa" if v<=-20 else "Normal"
            filas.append(html.Tr([
                html.Td(row["fenomeno"],   className="td-per"),
                html.Td(str(int(row["n_anterior"])), className="td-num"),
                html.Td(str(int(row["n_actual"])),   className="td-num"),
                html.Td(f"{'+'if v>0 else''}{v}%",  className="td-num",
                        style={"color":col,"fontWeight":"500"}),
                html.Td(f"{'+'if row['variacion_abs']>0 else''}{row['variacion_abs']}",
                        className="td-num"),
                html.Td(html.Span(etiq,style={"background":f"{col}22","color":col,
                                              "padding":"2px 7px","borderRadius":"4px",
                                              "fontSize":"10px","fontWeight":"500"})),
            ], className="tr-base"))

        tabla = html.Div([
            html.Div(f"Comparativa: {per_ant} → {periodo}", className="chart-title",
                     style={"marginTop":"12px"}),
            html.Div(html.Table(filas, className="comp-table"), className="tabla-wrap"),
        ])

        return alertas, fig_b, fig_l, tabla
