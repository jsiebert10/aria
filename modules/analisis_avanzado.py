# =============================================================================
# pages/analisis_avanzado.py — ARIA v3
# Módulo de análisis espacial avanzado:
#   · Near Repeat Analysis (victimización repetida en espacio-tiempo)
#   · Nearest Neighbor Index (clustering estadístico)
#   · Network KDE (densidad sobre red vial aproximada)
# Referencias: Ratcliffe (2002), Johnson et al. (2007), Clark & Evans (1954)
# =============================================================================

import numpy as np
import pandas as pd
import plotly.graph_objects as go
from scipy.spatial import cKDTree
from scipy.stats import norm
from dash import dcc, html, Input, Output, State
from dash.exceptions import PreventUpdate

BG1 = "#10161e"; BG2 = "#161d27"; BG3 = "#1c2530"
BORDE = "#26303d"; TEXT = "#e8e6d9"; T2 = "#a8adb5"; T3 = "#6b727d"
AMBER = "#d4a84b"; AMB2 = "#b38a2e"; AGLOW = "rgba(212,168,75,.12)"
DANGER = "#c74d3f"; WARN = "#d49b3f"; OK = "#7a9e6c"; INFO = "#5a8fa8"

DD_STYLE = {"background": BG3, "border": f"1px solid {BORDE}", "color": TEXT,
            "padding": "5px 8px", "fontSize": "12px", "fontFamily": "IBM Plex Sans,sans-serif",
            "outline": "none", "width": "100%", "marginTop": "4px"}

LABEL_STYLE = {"fontFamily": "IBM Plex Mono,monospace", "fontSize": "9px", "color": T3,
               "textTransform": "uppercase", "letterSpacing": "1px",
               "display": "block", "marginBottom": "4px", "marginTop": "10px"}


def _pbase(m=None, no_axes=False):
    d = dict(paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
             font=dict(color=T2, size=10, family="IBM Plex Sans,sans-serif"),
             margin=m or dict(l=40, r=12, t=8, b=32))
    if not no_axes:
        d["xaxis"] = dict(gridcolor=BORDE, showline=False, zeroline=False)
        d["yaxis"] = dict(gridcolor=BORDE, showline=False, zeroline=False)
    return d


def _deg2m(lat, lon, lat0=-33.45, lon0=-70.65):
    """Convierte coordenadas a metros aproximados centrados en Santiago."""
    dlat = (lat - lat0) * 111320
    dlon = (lon - lon0) * 111320 * np.cos(np.radians(lat0))
    return np.column_stack([dlat, dlon])


# ── NEAR REPEAT ANALYSIS ──────────────────────────────────────────────────────
def calcular_near_repeat(df_global, fenomeno, periodos, radio_m=500):
    """
    Near Repeat Analysis: mide si hechos del período actual tienen
    antecedentes espacialmente cercanos en el período anterior.
    Ref: Johnson et al. (2007) — Near Repeat Victimization.
    """
    resultados = []
    radios = [200, 400, 600, 800, 1000]

    df_f = df_global[df_global["fenomeno"] == fenomeno]

    for i in range(1, len(periodos)):
        per_act = periodos[i]
        per_ant = periodos[i - 1]
        df_act = df_f[df_f["periodo_label"] == per_act]
        df_ant = df_f[df_f["periodo_label"] == per_ant]

        if len(df_act) < 5 or len(df_ant) < 5:
            continue

        pts_act = _deg2m(df_act["latitud"].values, df_act["longitud"].values)
        pts_ant = _deg2m(df_ant["latitud"].values, df_ant["longitud"].values)
        tree = cKDTree(pts_ant)

        for r in radios:
            near = tree.query_ball_point(pts_act, r=r)
            n_near = sum(1 for n in near if len(n) > 0)
            pct = round(n_near / len(pts_act) * 100, 1)
            resultados.append({
                "periodo": per_act,
                "radio_m": r,
                "n_total": len(pts_act),
                "n_near_repeat": n_near,
                "pct_near_repeat": pct,
            })

    return pd.DataFrame(resultados)


# ── NEAREST NEIGHBOR INDEX ────────────────────────────────────────────────────
def calcular_nni(df_global, fenomeno, periodo):
    """
    Nearest Neighbor Index (Clark & Evans, 1954).
    R < 1: clustering · R = 1: aleatorio · R > 1: disperso
    z-score indica significancia estadística.
    """
    df_f = df_global[(df_global["fenomeno"] == fenomeno) &
                     (df_global["periodo_label"] == periodo)]
    if len(df_f) < 10:
        return None

    pts = _deg2m(df_f["latitud"].values, df_f["longitud"].values)
    n = len(pts)
    tree = cKDTree(pts)
    dists, _ = tree.query(pts, k=2)
    nn_dists = dists[:, 1]  # distancia al vecino más cercano (k=2 porque k=1 es el mismo punto)

    d_obs = np.mean(nn_dists)

    # Área del bounding box como aproximación del área de estudio
    x_range = pts[:, 0].max() - pts[:, 0].min()
    y_range = pts[:, 1].max() - pts[:, 1].min()
    area = x_range * y_range
    if area == 0:
        return None

    d_exp = 0.5 * np.sqrt(area / n)
    R = d_obs / d_exp

    # Z-score
    se = 0.26136 / np.sqrt(n * n / area)
    z = (d_obs - d_exp) / se if se > 0 else 0
    p = 2 * (1 - norm.cdf(abs(z)))

    interpretacion = "Clustering significativo" if R < 0.7 else \
                     "Clustering moderado" if R < 0.9 else \
                     "Distribución aleatoria" if R < 1.1 else "Distribución dispersa"

    return {
        "R": round(float(R), 3),
        "d_obs_m": round(float(d_obs), 1),
        "d_exp_m": round(float(d_exp), 1),
        "z_score": round(float(z), 2),
        "p_valor": round(float(p), 4),
        "n": n,
        "interpretacion": interpretacion,
        "significativo": bool(p < 0.05),
    }


# ── NETWORK KDE APROXIMADO ────────────────────────────────────────────────────
def calcular_network_kde(df_global, fenomeno, periodo, bandwidth=300):
    """
    Network KDE aproximado: KDE calculado con distancia Manhattan
    (proxy de distancia de red vial en cuadrícula urbana).
    Más realista que KDE euclidiano para entornos urbanos.
    Ref: Xie & Yan (2008) — Kernel density estimation of traffic accidents.
    """
    df_f = df_global[(df_global["fenomeno"] == fenomeno) &
                     (df_global["periodo_label"] == periodo)]
    if len(df_f) < 5:
        return None, None, None

    pts = _deg2m(df_f["latitud"].values, df_f["longitud"].values)

    # Grid de evaluación
    n_grid = 40
    x_min, x_max = pts[:, 0].min() - bandwidth, pts[:, 0].max() + bandwidth
    y_min, y_max = pts[:, 1].min() - bandwidth, pts[:, 1].max() + bandwidth

    xi = np.linspace(x_min, x_max, n_grid)
    yi = np.linspace(y_min, y_max, n_grid)
    Xi, Yi = np.meshgrid(xi, yi)
    grid_pts = np.column_stack([Xi.ravel(), Yi.ravel()])

    # KDE con distancia Manhattan (L1) como proxy de red vial
    Z = np.zeros(len(grid_pts))
    for pt in pts:
        manhattan_dist = np.abs(grid_pts[:, 0] - pt[0]) + np.abs(grid_pts[:, 1] - pt[1])
        mask = manhattan_dist <= bandwidth
        Z[mask] += (1 - manhattan_dist[mask] / bandwidth) ** 2  # kernel cuártico

    Z = Z.reshape(n_grid, n_grid)

    # Convertir grid de vuelta a coordenadas geográficas
    lat0, lon0 = -33.45, -70.65
    xi_geo = xi / 111320 + lat0
    yi_geo = yi / (111320 * np.cos(np.radians(lat0))) + lon0

    return Z, xi_geo, yi_geo


# ── LAYOUT ────────────────────────────────────────────────────────────────────
def get_layout(fenomenos, periodos):
    return html.Div(className="modulo-wrap", children=[

        html.Div(className="mod-header", children=[
            html.Div([
                html.Div("03 / Análisis espacial avanzado", className="mod-eyebrow"),
                html.Div("Near Repeat · Nearest Neighbor · Network KDE", className="mod-title"),
                html.Div("Métodos de segunda generación en análisis criminal geoespacial",
                         className="mod-sub"),
            ]),
            html.Div(className="mod-actions", children=[
                html.Span("Clark & Evans 1954 · Johnson et al. 2007 · Xie & Yan 2008",
                          style={"fontFamily": "IBM Plex Mono,monospace",
                                 "fontSize": "9px", "color": T3}),
            ]),
        ]),

        html.Div(className="mod-body", children=[

            # Filtros
            html.Div(style={"display": "grid", "gridTemplateColumns": "1fr 1fr",
                            "gap": "12px", "marginBottom": "8px"}, children=[
                html.Div([
                    html.Label("Fenómeno", style=LABEL_STYLE),
                    dcc.Dropdown(id="adv-fen", className="dropdown",
                                 options=[{"label": f, "value": f} for f in fenomenos],
                                 value=fenomenos[0] if fenomenos else None,
                                 clearable=False),
                ]),
                html.Div([
                    html.Label("Período", style=LABEL_STYLE),
                    dcc.Dropdown(id="adv-per", className="dropdown",
                                 options=[{"label": p, "value": p} for p in periodos],
                                 value=periodos[-1] if periodos else None,
                                 clearable=False),
                ]),
            ]),

            # ── NEAR REPEAT ──────────────────────────────────────────────────
            html.Div(className="panel", children=[
                html.Div(["Near Repeat Analysis",
                          html.Span("Johnson et al. 2007", className="tag accent")],
                         className="panel-title"),

                html.Div(id="adv-nr-kpis", style={
                    "display": "grid", "gridTemplateColumns": "repeat(4,1fr)",
                    "gap": "8px", "marginBottom": "10px",
                }),

                html.Div(className="grid grid-2", children=[
                    dcc.Graph(id="adv-nr-radios", config={"displayModeBar": False},
                              style={"height": "200px"}),
                    dcc.Graph(id="adv-nr-serie", config={"displayModeBar": False},
                              style={"height": "200px"}),
                ]),

                html.Div(style={
                    "background": BG3, "border": f"1px solid {BORDE}",
                    "borderLeft": f"3px solid {AMBER}",
                    "padding": "10px 14px", "marginTop": "8px",
                    "fontSize": "11px", "lineHeight": "1.7", "color": T2,
                    "fontFamily": "IBM Plex Mono,monospace",
                }, children=[
                    html.Span("¿Qué mide? ", style={"color": AMBER, "fontWeight": "600"}),
                    "Si un hecho delictual genera un área de riesgo elevado en los días siguientes. "
                    "Un % alto indica que los hechos no son independientes — el victimizador "
                    "regresa o recomienda la zona. Permite alertas tempranas de victimización repetida.",
                ]),
            ]),

            # ── NEAREST NEIGHBOR ─────────────────────────────────────────────
            html.Div(className="panel", children=[
                html.Div(["Nearest Neighbor Index",
                          html.Span("Clark & Evans 1954", className="tag")],
                         className="panel-title"),

                html.Div(id="adv-nni-resultado"),

                html.Div(className="grid grid-2", children=[
                    dcc.Graph(id="adv-nni-gauge", config={"displayModeBar": False},
                              style={"height": "180px"}),
                    dcc.Graph(id="adv-nni-hist", config={"displayModeBar": False},
                              style={"height": "180px"}),
                ]),

                html.Div(style={
                    "background": BG3, "border": f"1px solid {BORDE}",
                    "borderLeft": f"3px solid {INFO}",
                    "padding": "10px 14px", "marginTop": "8px",
                    "fontSize": "11px", "lineHeight": "1.7", "color": T2,
                    "fontFamily": "IBM Plex Mono,monospace",
                }, children=[
                    html.Span("¿Qué mide? ", style={"color": INFO, "fontWeight": "600"}),
                    "R < 1 indica clustering (hechos más agrupados que el azar). "
                    "R = 1 distribución aleatoria. R > 1 distribución dispersa. "
                    "El z-score indica si el resultado es estadísticamente significativo.",
                ]),
            ]),

            # ── NETWORK KDE ──────────────────────────────────────────────────
            html.Div(className="panel", children=[
                html.Div(["Network KDE — densidad sobre red vial",
                          html.Span("Xie & Yan 2008", className="tag accent")],
                         className="panel-title"),

                dcc.Graph(id="adv-nkde", config={"displayModeBar": False},
                          style={"height": "320px"}),

                html.Div(style={
                    "background": BG3, "border": f"1px solid {BORDE}",
                    "borderLeft": f"3px solid {OK}",
                    "padding": "10px 14px", "marginTop": "8px",
                    "fontSize": "11px", "lineHeight": "1.7", "color": T2,
                    "fontFamily": "IBM Plex Mono,monospace",
                }, children=[
                    html.Span("¿Qué mejora vs KDE estándar? ", style={"color": OK, "fontWeight": "600"}),
                    "El KDE euclidiano calcula distancias en línea recta, ignorando que los "
                    "desplazamientos ocurren por calles. El Network KDE usa distancia Manhattan "
                    "como proxy de la red vial urbana — más preciso en contexto urbano de cuadrícula.",
                ]),
            ]),
        ]),
    ])


# ── CALLBACKS ────────────────────────────────────────────────────────────────
def registrar_callbacks(app, df_global, periodos, fenomenos):

    @app.callback(
        Output("adv-nr-kpis",   "children"),
        Output("adv-nr-radios", "figure"),
        Output("adv-nr-serie",  "figure"),
        Output("adv-nni-resultado", "children"),
        Output("adv-nni-gauge", "figure"),
        Output("adv-nni-hist",  "figure"),
        Output("adv-nkde",      "figure"),
        Input("adv-fen", "value"),
        Input("adv-per", "value"),
    )
    def actualizar(fenomeno, periodo):
        import traceback
        try:
            return _actualizar_inner(fenomeno, periodo, df_global, periodos)
        except Exception as e:
            traceback.print_exc()
            vacia = go.Figure(layout=go.Layout(**_pbase()))
            vacia.add_annotation(text=f"Error: {str(e)[:60]}", x=0.5, y=0.5,
                                 xref="paper", yref="paper", showarrow=False,
                                 font=dict(color=DANGER))
            return [], vacia, vacia, html.Div(str(e), style={"color":DANGER}), vacia, vacia, vacia

def _actualizar_inner(fenomeno, periodo, df_global, periodos):
        vacia = go.Figure(layout=go.Layout(**_pbase()))
        vacia.add_annotation(text="Sin datos", x=0.5, y=0.5,
                             xref="paper", yref="paper",
                             showarrow=False, font=dict(color=T3))

        if not fenomeno or not periodo or df_global.empty:
            return [], vacia, vacia, html.Div(""), vacia, vacia, vacia

        # ── NEAR REPEAT ──────────────────────────────────────────────────────
        df_nr = calcular_near_repeat(df_global, fenomeno, periodos)
        df_nr_per = df_nr[df_nr["periodo"] == periodo] if not df_nr.empty else pd.DataFrame()

        if not df_nr_per.empty:
            # KPIs
            r500 = df_nr_per[df_nr_per["radio_m"].astype(int) == 500]
            # usar radio más cercano disponible si 500 no está
            if len(r500) == 0:
                r500 = df_nr_per.iloc[[df_nr_per["radio_m"].sub(500).abs().argmin()]]
            pct_500 = float(r500["pct_near_repeat"].values[0])
            n_total = int(r500["n_total"].values[0])
            n_near  = int(r500["n_near_repeat"].values[0])
            col_pct = DANGER if pct_500 > 50 else WARN if pct_500 > 30 else OK

            kpis = [
                _kpi_mini(f"{pct_500}%", "Near Repeat (500m)", col_pct),
                _kpi_mini(str(n_near), "Hechos con antecedente", AMBER),
                _kpi_mini(str(n_total), "Total hechos período", T2),
                _kpi_mini("500 m", "Radio de análisis", INFO),
            ]

            # Gráfico por radio
            fig_r = go.Figure()
            fig_r.add_trace(go.Bar(
                x=[str(r) + "m" for r in df_nr_per["radio_m"]],
                y=df_nr_per["pct_near_repeat"],
                marker_color=[DANGER if v > 50 else WARN if v > 30 else OK
                              for v in df_nr_per["pct_near_repeat"]],
                marker_line_width=0,
                hovertemplate="Radio %{x}: %{y}%<extra></extra>",
            ))
            fig_r.update_layout(**_pbase(dict(l=36, r=8, t=8, b=28)),
                                showlegend=False)
            fig_r.update_xaxes(title_text="Radio de búsqueda", title_font=dict(size=10))
            fig_r.update_yaxes(title_text="% Near Repeat", title_font=dict(size=10))

            # Serie temporal Near Repeat a 500m
            df_nr_500 = df_nr[df_nr["radio_m"].astype(int) == 500].sort_values("periodo")
            fig_s = go.Figure()
            fig_s.add_trace(go.Scatter(
                x=df_nr_500["periodo"], y=df_nr_500["pct_near_repeat"],
                mode="lines+markers",
                line=dict(color=AMBER, width=2),
                marker=dict(size=[9 if p == periodo else 5 for p in df_nr_500["periodo"]],
                            color=[AMBER if p == periodo else AMB2
                                   for p in df_nr_500["periodo"]]),
                hovertemplate="%{x}: %{y}%<extra></extra>",
            ))
            fig_s.add_hline(y=50, line_color=DANGER, line_dash="dash",
                            line_width=1, annotation_text="Umbral 50%",
                            annotation_font=dict(size=9, color=DANGER))
            fig_s.update_layout(**_pbase(dict(l=36, r=8, t=8, b=28)),
                                showlegend=False)
        else:
            kpis = []
            fig_r = vacia
            fig_s = vacia

        # ── NEAREST NEIGHBOR ─────────────────────────────────────────────────
        nni = calcular_nni(df_global, fenomeno, periodo)

        if nni:
            col_R = DANGER if nni["R"] < 0.7 else WARN if nni["R"] < 0.9 else \
                    OK if nni["R"] > 1.1 else T2
            sig_text = "Estadísticamente significativo (p<0.05)" \
                       if bool(nni["significativo"]) else "No significativo"

            nni_info = html.Div(style={
                "display": "grid", "gridTemplateColumns": "repeat(4,1fr)",
                "gap": "8px", "marginBottom": "10px",
            }, children=[
                _kpi_mini(str(nni["R"]), "Índice R (NNI)", col_R),
                _kpi_mini(f"{nni['d_obs_m']}m", "Distancia media obs.", T2),
                _kpi_mini(f"{nni['d_exp_m']}m", "Distancia media esp.", T2),
                _kpi_mini(f"p={nni['p_valor']}", sig_text,
                          OK if bool(nni["significativo"]) else T3),
            ])

            # Gauge del índice R
            fig_g = go.Figure(go.Indicator(
                mode="gauge+number",
                value=nni["R"],
                title=dict(text=nni["interpretacion"],
                           font=dict(size=11, color=T2)),
                gauge=dict(
                    axis=dict(range=[0, 2],
                              tickvals=[0, 0.5, 1.0, 1.5, 2.0],
                              ticktext=["0", "Agrup.", "Aleatorio", "Disperso", "2"],
                              tickfont=dict(size=9, color=T3)),
                    bar=dict(color=col_R, thickness=0.3),
                    bgcolor=BG3,
                    borderwidth=1, bordercolor=BORDE,
                    steps=[
                        dict(range=[0, 0.9],  color="rgba(199,77,63,0.2)"),
                        dict(range=[0.9, 1.1], color="rgba(122,158,108,0.13)"),
                        dict(range=[1.1, 2.0], color="rgba(90,143,168,0.13)"),
                    ],
                    threshold=dict(line=dict(color=T3, width=2),
                                   thickness=0.75, value=1.0),
                ),
                number=dict(font=dict(size=28, color=col_R, family="IBM Plex Mono")),
            ))
            _gl = _pbase(dict(l=20, r=20, t=40, b=20), no_axes=True)
            fig_g.update_layout(**_gl)

            # Histograma de distancias al vecino más cercano
            df_f = df_global[(df_global["fenomeno"] == fenomeno) &
                             (df_global["periodo_label"] == periodo)]
            pts = _deg2m(df_f["latitud"].values, df_f["longitud"].values)
            tree_h = __import__("scipy.spatial", fromlist=["cKDTree"]).cKDTree(pts)
            dists_h, _ = tree_h.query(pts, k=2)
            nn_dists_h = dists_h[:, 1]

            fig_h = go.Figure()
            fig_h.add_trace(go.Histogram(
                x=nn_dists_h.tolist(), nbinsx=30,
                marker_color=AMBER, marker_line_width=0, opacity=0.8,
                hovertemplate="Distancia %{x:.0f}m: %{y} hechos<extra></extra>",
            ))
            fig_h.add_vline(x=nni["d_obs_m"], line_color=AMBER,
                            line_dash="solid", line_width=2,
                            annotation_text=f"Media: {nni['d_obs_m']}m",
                            annotation_font=dict(size=9, color=AMBER))
            fig_h.add_vline(x=nni["d_exp_m"], line_color=T3,
                            line_dash="dash", line_width=1,
                            annotation_text=f"Esperado: {nni['d_exp_m']}m",
                            annotation_font=dict(size=9, color=T3))
            fig_h.update_layout(**_pbase(dict(l=36, r=8, t=8, b=28)),
                                showlegend=False)
            fig_h.update_xaxes(title_text="Distancia al vecino más cercano (m)",
                               title_font=dict(size=9))
        else:
            nni_info = html.Div("Insuficientes datos para calcular NNI.",
                                style={"color": T3, "fontSize": "12px"})
            fig_g = vacia
            fig_h = vacia

        # ── NETWORK KDE ──────────────────────────────────────────────────────
        Z, xi_geo, yi_geo = calcular_network_kde(df_global, fenomeno, periodo)

        if Z is not None:
            df_f_plot = df_global[(df_global["fenomeno"] == fenomeno) &
                                  (df_global["periodo_label"] == periodo)]
            fig_nkde = go.Figure()

            # Heatmap
            fig_nkde.add_trace(go.Heatmap(
                x=yi_geo, y=xi_geo, z=Z,
                colorscale=[[0, "rgba(0,0,0,0)"],
                            [0.2, f"rgba(212,168,75,0.1)"],
                            [0.5, f"rgba(212,168,75,0.5)"],
                            [0.8, f"rgba(199,77,63,0.7)"],
                            [1.0, f"rgba(199,77,63,0.95)"]],
                showscale=True,
                colorbar=dict(
                    title=dict(text="Densidad", font=dict(size=10, color=T2)),
                    tickfont=dict(size=9, color=T2),
                    bgcolor=BG1, bordercolor=BORDE, len=0.8,
                ),
                hovertemplate="Lat: %{y:.4f}<br>Lon: %{x:.4f}<br>Densidad: %{z:.2f}<extra></extra>",
            ))

            # Puntos encima
            fig_nkde.add_trace(go.Scatter(
                x=df_f_plot["longitud"], y=df_f_plot["latitud"],
                mode="markers",
                marker=dict(size=4, color=TEXT, opacity=0.6,
                            line=dict(color=BG1, width=0.5)),
                name="Hechos",
                hovertemplate="Lat: %{y:.4f}<br>Lon: %{x:.4f}<extra></extra>",
            ))

            _nkde_l = _pbase(dict(l=40, r=60, t=8, b=40), no_axes=True)
            fig_nkde.update_layout(
                **_nkde_l, showlegend=False,
                xaxis=dict(title="Longitud", gridcolor=BORDE,
                           showline=False, zeroline=False, tickfont=dict(size=8)),
                yaxis=dict(title="Latitud", gridcolor=BORDE,
                           showline=False, zeroline=False, tickfont=dict(size=8)),
            )
        else:
            fig_nkde = vacia

        return kpis, fig_r, fig_s, nni_info, fig_g, fig_h, fig_nkde


def _kpi_mini(valor, label, color):
    return html.Div(style={
        "background": BG1, "border": f"1px solid {BORDE}",
        "borderLeft": f"3px solid {color}", "padding": "10px 12px",
    }, children=[
        html.Div(valor, style={"fontFamily": "IBM Plex Mono,monospace",
                               "fontSize": "20px", "fontWeight": "500",
                               "color": color, "lineHeight": "1"}),
        html.Div(label, style={"fontSize": "10px", "color": T3, "marginTop": "4px"}),
    ])
