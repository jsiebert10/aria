# =============================================================================
# app.py — Dashboard de Movilidad Delictual — versión completa
# Visualizaciones: Rosa · Línea · Narrativa · Flechas · Tabla
# Ejecutar: python app.py  →  abrir http://localhost:8050
# 100% local. Ningún dato sale de la máquina.
# =============================================================================

import json
import numpy as np
import pandas as pd
import plotly.graph_objects as go
from dash import Dash, dcc, html, Input, Output, ctx
from dash.exceptions import PreventUpdate
import dash_leaflet as dl

import ingesta
import calculos
from config import (
    CENTRO_MAPA_DEFAULT, ZOOM_DEFAULT, COLORES_TIPOS,
    COLOR_ELIPSE_ACTUAL, COLOR_ELIPSE_ANTERIOR,
    COLOR_TRAYECTORIA, MIN_PUNTOS_CALCULO
)

# ── Carga inicial ─────────────────────────────────────────────────────────────
DF_GLOBAL = ingesta.cargar_todos()

if DF_GLOBAL.empty:
    print("\n⚠  Sin datos. Ejecuta: python generar_sinteticos.py\n")

PERIODOS  = (
    DF_GLOBAL[["periodo_label","periodo_orden"]]
    .drop_duplicates().sort_values("periodo_orden")["periodo_label"].tolist()
) if not DF_GLOBAL.empty else []

FENOMENOS = sorted(DF_GLOBAL["fenomeno"].unique().tolist()) if not DF_GLOBAL.empty else []
COMUNAS   = ["Todas"] + sorted(DF_GLOBAL["comuna"].dropna().unique().tolist()) if not DF_GLOBAL.empty else ["Todas"]

# Cargar GeoJSON de comunas para visualización
import os as _os
_ruta_geo = _os.path.join(_os.path.dirname(_os.path.dirname(__file__)), "data", "comunas_santiago.geojson")
with open(_ruta_geo, encoding="utf-8") as _f:
    COMUNAS_GEOJSON = json.load(_f)

# ── Colores temáticos ─────────────────────────────────────────────────────────
PLOT_BG    = "#1a1d27"
PLOT_PAPER = "#1a1d27"
PLOT_TEXT  = "#e8eaf0"
PLOT_TEXT2 = "#8b91b0"
PLOT_GRID  = "#2e3250"

def _clasif_color(j):
    if j is None:  return "#8b91b0"
    if j >= 0.70:  return "#4fcc8e"
    if j >= 0.30:  return "#f7b84f"
    return "#f75f5f"

def _clasif_bg(j):
    if j is None:  return "rgba(139,145,176,.15)"
    if j >= 0.70:  return "rgba(79,204,142,.15)"
    if j >= 0.30:  return "rgba(247,184,79,.15)"
    return "rgba(247,95,95,.15)"

def _clasif_label(j):
    if j is None:  return "Sin datos"
    if j >= 0.70:  return "Patrón estable"
    if j >= 0.30:  return "Desp. parcial"
    return "Desp. significativo"

def _layout(margin=None):
    m = margin or dict(l=44, r=12, t=16, b=36)
    return dict(
        paper_bgcolor=PLOT_PAPER, plot_bgcolor=PLOT_BG,
        font=dict(color=PLOT_TEXT, size=11, family="DM Sans,sans-serif"),
        margin=m,
        xaxis=dict(gridcolor=PLOT_GRID, showline=False, zeroline=False),
        yaxis=dict(gridcolor=PLOT_GRID, showline=False, zeroline=False),
    )

def _vacia(msg="Sin datos suficientes"):
    fig = go.Figure(layout=go.Layout(**_layout()))
    fig.add_annotation(text=msg, x=0.5, y=0.5, xref="paper", yref="paper",
                       showarrow=False, font=dict(color=PLOT_TEXT2, size=12))
    return fig


# ── Layout ────────────────────────────────────────────────────────────────────
def get_layout():
    return html.Div(id="root-movilidad", children=[

    html.Div(className="header", children=[
        html.Div(className="header-left", children=[
            html.H1("Movilidad Delictual"),
            html.Span("Análisis espacial · Uso institucional interno",
                      className="header-sub"),
        ]),
        html.Div(className="header-right", children=[
            html.Span(f"{len(DF_GLOBAL):,} registros · {len(PERIODOS)} período(s)",
                      className="header-meta"),
        ]),
    ]),

    html.Div(className="body", children=[

        # SIDEBAR
        html.Div(className="sidebar", children=[

            html.Div(className="control-section", children=[
                html.Label("Tipo penal", className="control-label"),
                dcc.Dropdown(id="dd-fen",
                    options=[{"label":f,"value":f} for f in FENOMENOS],
                    value=FENOMENOS[0] if FENOMENOS else None,
                    clearable=False, className="dropdown"),
            ]),

            html.Div(className="control-section", children=[
                html.Label("Período", className="control-label"),
                dcc.Dropdown(id="dd-per",
                    options=[{"label":p,"value":p} for p in PERIODOS],
                    value=PERIODOS[-1] if PERIODOS else None,
                    clearable=False, className="dropdown"),
            ]),

            html.Div(className="control-section", children=[
                html.Label("Filtrar por comuna", className="control-label"),
                dcc.Dropdown(id="dd-comuna",
                    options=[{"label":c,"value":c} for c in COMUNAS],
                    value="Todas",
                    clearable=False, className="dropdown"),
                html.Div(id="info-comuna", className="comuna-info"),
            ]),

            html.Div(className="control-section", children=[
                html.Label("Capas del mapa", className="control-label"),
                dcc.Checklist(id="chk-capas",
                    options=[
                        {"label":" Comunas (coroplético)", "value":"comunas"},
                        {"label":" Puntos",          "value":"puntos"},
                        {"label":" KDE (densidad)",  "value":"kde"},
                        {"label":" Elipse actual",   "value":"elipse_act"},
                        {"label":" Elipse anterior", "value":"elipse_ant"},
                        {"label":" Trayectoria",     "value":"trayectoria"},
                    ],
                    value=["comunas","puntos","elipse_act"],
                    className="checklist",
                    inputClassName="checklist-input",
                    labelClassName="checklist-label",
                ),
            ]),

            html.Div(className="control-section", children=[
                html.Label("Opacidad elipse", className="control-label"),
                dcc.Slider(id="sl-op", min=0.1, max=1.0, step=0.1, value=0.5,
                           marks={0.1:"10%", 0.5:"50%", 1.0:"100%"},
                           className="slider"),
            ]),

            html.Div(id="alerta-n", className="alerta", style={"display":"none"}),

            html.Div(className="metrics-panel", children=[
                html.Div("Métricas del período", className="metric-title"),
                *[html.Div(className="metric-row", children=[
                    html.Span(lbl, className="metric-label"),
                    html.Span(id=mid, className="metric-value"),
                ]) for lbl, mid in [
                    ("Hechos",           "mt-n"),
                    ("Desplazamiento",   "mt-desp"),
                    ("Dirección",        "mt-dir"),
                    ("Solapamiento",     "mt-solap"),
                    ("Clasificación",    "mt-clasif"),
                    ("Variación área",   "mt-area"),
                ]],
            ]),
        ]),

        # MAPA
        html.Div(className="map-panel", children=[
            dl.Map(id="mapa", center=CENTRO_MAPA_DEFAULT, zoom=ZOOM_DEFAULT,
                   style={"width":"100%","height":"100%"}, children=[
                dl.TileLayer(url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png",
                             attribution="© OpenStreetMap", maxZoom=19),
                dl.LayerGroup(id="lyr-comunas"),
                dl.LayerGroup(id="lyr-pts"),
                dl.LayerGroup(id="lyr-kde"),
                dl.LayerGroup(id="lyr-elip-act"),
                dl.LayerGroup(id="lyr-elip-ant"),
                dl.LayerGroup(id="lyr-tray"),
            ]),
        ]),

        # PANEL DERECHO — 5 VISUALIZACIONES
        html.Div(className="chart-panel", children=[

            html.Div(className="viz-tabs", children=[
                html.Button("Rosa",      id="tab-rosa",    className="viz-tab active", n_clicks=0),
                html.Button("Tendencia", id="tab-linea",   className="viz-tab",        n_clicks=0),
                html.Button("Narrativa", id="tab-narr",    className="viz-tab",        n_clicks=0),
                html.Button("Flechas",   id="tab-flechas", className="viz-tab",        n_clicks=0),
                html.Button("Tabla",     id="tab-tabla",   className="viz-tab",        n_clicks=0),
            ]),

            # VIZ 1 — Rosa
            html.Div(id="viz-rosa", children=[
                html.Div("Dirección del desplazamiento", className="chart-title"),
                dcc.Graph(id="fig-rosa", config={"displayModeBar":False},
                          style={"height":"270px"}),
                html.Div("Período actual vs anterior", className="chart-sub"),
            ]),

            # VIZ 2 — Línea + Serie
            html.Div(id="viz-linea", style={"display":"none"}, children=[
                html.Div("Tendencia del desplazamiento (km)", className="chart-title"),
                dcc.Graph(id="fig-linea", config={"displayModeBar":False},
                          style={"height":"195px"}),
                html.Div("Frecuencia mensual", className="chart-title",
                         style={"marginTop":"6px"}),
                dcc.Graph(id="fig-serie", config={"displayModeBar":False},
                          style={"height":"155px"}),
            ]),

            # VIZ 3 — Narrativa
            html.Div(id="viz-narr", style={"display":"none"}, children=[
                html.Div("Síntesis automática", className="chart-title"),
                html.Div(id="narr-cuerpo", className="narr-box"),
                html.Div("Distribución por tipo · período", className="chart-title",
                         style={"marginTop":"10px"}),
                dcc.Graph(id="fig-tipos", config={"displayModeBar":False},
                          style={"height":"195px"}),
            ]),

            # VIZ 4 — Flechas
            html.Div(id="viz-flechas", style={"display":"none"}, children=[
                html.Div("Desplazamiento mensual completo", className="chart-title"),
                dcc.Graph(id="fig-flechas", config={"displayModeBar":False},
                          style={"height":"250px"}),
                html.Div("Verde = estable · Ámbar = parcial · Rojo = significativo",
                         className="chart-sub"),
            ]),

            # VIZ 5 — Tabla
            html.Div(id="viz-tabla", style={"display":"none"}, children=[
                html.Div("Comparativa mensual", className="chart-title"),
                html.Div(id="tabla-cuerpo", className="tabla-wrap"),
                html.Button("Exportar CSV", id="btn-export",
                            className="export-btn", n_clicks=0),
                dcc.Download(id="dl-csv"),
            ]),
        ]),
    ]),

    ])



def registrar_callbacks(app):
    """Registra todos los callbacks de movilidad en la app principal."""


    # ─────────────────────────────────────────────────────────────────────────────
    # CÁLCULOS
    # ─────────────────────────────────────────────────────────────────────────────
    @app.callback(
        Output("store",    "data"),
        Output("alerta-n", "children"),
        Output("alerta-n", "style"),
        Input("dd-fen",    "value"),
        Input("dd-per",    "value"),
        Input("dd-comuna", "value"),
    )
    def calcular(fenomeno, periodo, comuna):
        if not fenomeno or not periodo or DF_GLOBAL.empty:
            raise PreventUpdate

        df_tipo   = DF_GLOBAL[DF_GLOBAL["fenomeno"] == fenomeno]
        if comuna and comuna != "Todas":
            df_tipo = df_tipo[df_tipo["comuna"] == comuna]
        df_act    = df_tipo[df_tipo["periodo_label"] == periodo]
        n_act     = len(df_act)

        idx_p     = PERIODOS.index(periodo)
        per_ant   = PERIODOS[idx_p - 1] if idx_p > 0 else None
        df_ant    = df_tipo[df_tipo["periodo_label"] == per_ant] if per_ant else pd.DataFrame()

        alerta = ("⚠ Datos insuficientes para métricas espaciales "
                  f"(n={n_act} < {MIN_PUNTOS_CALCULO})") if n_act < MIN_PUNTOS_CALCULO else ""
        alerta_style = {"display": "block"} if alerta else {"display": "none"}

        centro_act = calculos.calcular_centro_medio(df_act)  if n_act >= 1        else None
        sde_act    = calculos.calcular_sde(df_act)
        kde_act    = calculos.calcular_kde(df_act)
        centro_ant = calculos.calcular_centro_medio(df_ant)  if len(df_ant) >= 1  else None
        sde_ant    = calculos.calcular_sde(df_ant)
        desp       = calculos.calcular_desplazamiento(centro_ant, centro_act)
        solap      = calculos.calcular_solapamiento(sde_ant, sde_act)
        var_area   = calculos.calcular_variacion_area(sde_act, sde_ant)

        # Trayectoria y serie
        trayectoria = []
        for p in PERIODOS:
            c = calculos.calcular_centro_medio(df_tipo[df_tipo["periodo_label"] == p])
            if c:
                trayectoria.append({"lat": c[0], "lon": c[1], "label": p})

        serie = (
            df_tipo.groupby(["periodo_orden","periodo_label"]).size()
            .reset_index(name="n").sort_values("periodo_orden")
            .to_dict(orient="records")
        )

        # Historial mes a mes
        hist = []
        for i in range(1, len(PERIODOS)):
            pc = PERIODOS[i]; pp = PERIODOS[i-1]
            dc = df_tipo[df_tipo["periodo_label"] == pc]
            dp = df_tipo[df_tipo["periodo_label"] == pp]
            cc = calculos.calcular_centro_medio(dc)
            cp = calculos.calcular_centro_medio(dp)
            d  = calculos.calcular_desplazamiento(cp, cc)
            sc = calculos.calcular_sde(dc)
            sp = calculos.calcular_sde(dp)
            s  = calculos.calcular_solapamiento(sp, sc)
            a  = calculos.calcular_variacion_area(sc, sp)
            hist.append({
                "periodo":  pc,
                "n":        int(len(dc)),
                "desp_km":  float(round(float(d["distancia_km"]),  2)) if d else None,
                "dir":      str(d["direccion"])                         if d else None,
                "az":       float(round(float(d["azimut_grados"]), 1)) if d else None,
                "jaccard":  float(round(float(s), 3))                   if s is not None else None,
                "var_area": float(round(float(a), 1))                   if a is not None else None,
            })

        # Datos mapa
        puntos = df_act[["latitud","longitud"]].to_dict(orient="records")
        elip_act = list(sde_act["poligono"].exterior.coords) if sde_act else None
        elip_ant = list(sde_ant["poligono"].exterior.coords) if sde_ant else None
        kde_pts  = None
        if kde_act:
            lats = kde_act["lats"].ravel(); lons = kde_act["lons"].ravel()
            dens = kde_act["densidad"].ravel(); mask = dens > 0.05
            kde_pts = [[float(la), float(lo), float(d)]
                       for la, lo, d in zip(lats[mask], lons[mask], dens[mask])]

        # Datos comunales para coroplético
        if not DF_GLOBAL.empty:
            df_per_fen = DF_GLOBAL[
                (DF_GLOBAL["fenomeno"] == fenomeno) &
                (DF_GLOBAL["periodo_label"] == periodo)
            ]
            conteo_comunas = df_per_fen["comuna"].value_counts().to_dict()
        else:
            conteo_comunas = {}

        return {
            "n":              n_act,    "periodo":  periodo,   "per_ant":   per_ant,
            "fenomeno":       fenomeno, "color":    COLORES_TIPOS.get(fenomeno, "#4f8ef7"),
            "puntos":         puntos,   "elip_act": elip_act,  "elip_ant":  elip_ant,
            "kde_pts":        kde_pts,  "tray":     trayectoria,
            "desp":           desp,     "solap":    solap,     "clasif":    calculos.clasificar_solapamiento(solap),
            "var_area":       var_area, "serie":    serie,     "hist":      hist,
            "comuna":         comuna or "Todas",
            "conteo_comunas": conteo_comunas,
        }, alerta, alerta_style


    # ─────────────────────────────────────────────────────────────────────────────
    # MÉTRICAS RÁPIDAS
    # ─────────────────────────────────────────────────────────────────────────────
    @app.callback(
        Output("mt-n",     "children"), Output("mt-desp",  "children"),
        Output("mt-dir",   "children"), Output("mt-solap", "children"),
        Output("mt-clasif","children"), Output("mt-area",  "children"),
        Input("store", "data"),
    )
    def metricas(d):
        if not d: return ["—"]*6
        desp = d.get("desp"); s = d.get("solap"); a = d.get("var_area")
        return (
            str(d.get("n", 0)),
            f"{desp['distancia_km']} km"   if desp else "—",
            desp["direccion"]              if desp else "—",
            f"{round(s*100,1)}%"           if s is not None else "—",
            d.get("clasif", "—"),
            (f"+{a}%" if a and a > 0 else f"{a}%") if a is not None else "—",
        )


    # ─────────────────────────────────────────────────────────────────────────────
    # MAPA
    # ─────────────────────────────────────────────────────────────────────────────
    @app.callback(
        Output("lyr-comunas",  "children"),
        Output("lyr-pts",      "children"), Output("lyr-kde",      "children"),
        Output("lyr-elip-act", "children"), Output("lyr-elip-ant", "children"),
        Output("lyr-tray",     "children"),
        Input("store",    "data"),
        Input("chk-capas","value"),
        Input("sl-op",    "value"),
    )
    def mapa(datos, capas, op):
        if not datos: return [], [], [], [], [], []
        color  = datos.get("color", "#4f8ef7")
        act    = set(capas or [])

        # ── Coroplético comunal ───────────────────────────────────────────────────
        comunas_layer = []
        if "comunas" in act and COMUNAS_GEOJSON:
            conteo = datos.get("conteo_comunas", {})
            max_c  = max(conteo.values()) if conteo else 1
            com_sel = datos.get("comuna", "Todas")

            for feat in COMUNAS_GEOJSON["features"]:
                nombre = feat["properties"]["comuna"]
                n      = conteo.get(nombre, 0)
                pct    = n / max_c if max_c > 0 else 0

                # Color: azul claro → azul intenso según intensidad
                if pct == 0:
                    fill = "#1a1d27"; fill_op = 0.15
                elif pct < 0.25:
                    fill = "#B5D4F4"; fill_op = 0.45
                elif pct < 0.50:
                    fill = "#378ADD"; fill_op = 0.50
                elif pct < 0.75:
                    fill = "#185FA5"; fill_op = 0.55
                else:
                    fill = "#042C53"; fill_op = 0.65

                # Resaltar comuna seleccionada
                borde_color = "#f7b84f" if (com_sel != "Todas" and nombre == com_sel) else "#4f8ef7"
                borde_w     = 3         if (com_sel != "Todas" and nombre == com_sel) else 1

                coords = feat["geometry"]["coordinates"]
                # Convertir a formato Leaflet [lat,lon]
                if feat["geometry"]["type"] == "Polygon":
                    positions = [[pt[1], pt[0]] for pt in coords[0]]
                else:
                    positions = [[pt[1], pt[0]] for pt in coords[0][0]]

                comunas_layer.append(dl.Polygon(
                    positions=positions,
                    color=borde_color,
                    weight=borde_w,
                    fillColor=fill,
                    fillOpacity=fill_op,
                    children=dl.Tooltip(
                        f"{nombre}: {n} hechos" + (f" ({round(pct*100)}% del máximo)" if n > 0 else "")
                    ),
                ))

        pts = [dl.CircleMarker(center=[p["latitud"],p["longitud"]], radius=6,
                  color="white", weight=1.5, fillColor=color, fillOpacity=0.85,
                  children=dl.Tooltip(datos["fenomeno"]))
               for p in datos.get("puntos",[])] if "puntos" in act else []

        kde = [dl.CircleMarker(center=[la,lo], radius=max(4,int(d*18)),
                  color="none", fillColor=color, fillOpacity=d*0.35)
               for la,lo,d in (datos.get("kde_pts") or []) if d > 0.3
               ] if "kde" in act else []

        ea = [dl.Polygon(positions=[[c[1],c[0]] for c in datos["elip_act"]],
                  color=COLOR_ELIPSE_ACTUAL, weight=2,
                  fillColor=COLOR_ELIPSE_ACTUAL, fillOpacity=op*0.4,
                  children=dl.Tooltip("Elipse actual"))
              ] if "elipse_act" in act and datos.get("elip_act") else []

        eant = [dl.Polygon(positions=[[c[1],c[0]] for c in datos["elip_ant"]],
                   color=COLOR_ELIPSE_ANTERIOR, weight=2, dashArray="6 4",
                   fillColor=COLOR_ELIPSE_ANTERIOR, fillOpacity=op*0.15,
                   children=dl.Tooltip(f"Elipse — {datos.get('per_ant','anterior')}"))
                ] if "elipse_ant" in act and datos.get("elip_ant") else []

        tray = []
        if "trayectoria" in act:
            t = datos.get("tray",[])
            if len(t) >= 2:
                tray.append(dl.Polyline(
                    positions=[[x["lat"],x["lon"]] for x in t],
                    color=COLOR_TRAYECTORIA, weight=2, dashArray="4 4"))
            for x in t:
                es = x["label"] == datos["periodo"]
                tray.append(dl.CircleMarker(
                    center=[x["lat"],x["lon"]], radius=8 if es else 5,
                    color="white", weight=2, fillColor=COLOR_TRAYECTORIA,
                    fillOpacity=1.0 if es else 0.6,
                    children=dl.Tooltip(x["label"])))

        return comunas_layer, pts, kde, ea, eant, tray


    # ─────────────────────────────────────────────────────────────────────────────
    # TABS
    # ─────────────────────────────────────────────────────────────────────────────
    TABS = ["rosa","linea","narr","flechas","tabla"]

    @app.callback(
        *[Output(f"viz-{t}",   "style")     for t in TABS],
        *[Output(f"tab-{t}",   "className") for t in TABS],
        *[Input(f"tab-{t}",    "n_clicks")  for t in TABS],
    )
    def cambiar_tab(*_):
        triggered = ctx.triggered_id or "tab-rosa"
        activo    = triggered.replace("tab-","")
        vis = [{"display":"block"} if t == activo else {"display":"none"} for t in TABS]
        cls = ["viz-tab active"    if t == activo else "viz-tab"          for t in TABS]
        return (*vis, *cls)


    # ─────────────────────────────────────────────────────────────────────────────
    # VIZ 1 — ROSA
    # ─────────────────────────────────────────────────────────────────────────────
    @app.callback(Output("fig-rosa","figure"), Input("store","data"))
    def fig_rosa(datos):
        if not datos or not datos.get("desp"):
            return _vacia("Sin período anterior para comparar")

        desp = datos["desp"]
        az   = desp["azimut_grados"]
        km   = desp["distancia_km"]
        dir_ = desp["direccion"]
        s    = datos.get("solap")
        col  = _clasif_color(s)
        # Magnitud: siempre entre 0.45 y 0.90 del radio para que sea visible
        mag = 0.45 + 0.45 * min(km / 3.0, 1.0)

        # Plotly polar: 0°=Este CCW. Azimut: 0°=Norte CW → theta = 90-az
        theta = (90 - az) % 360

        fig = go.Figure()

        # Anillos de referencia
        for r in [0.33, 0.66, 1.0]:
            fig.add_trace(go.Scatterpolar(
                r=[r]*361, theta=list(range(361)),
                mode="lines", line=dict(color=PLOT_GRID, width=0.8, dash="dot"),
                showlegend=False, hoverinfo="skip"))

        # Flecha
        fig.add_trace(go.Scatterpolar(
            r=[0, mag], theta=[theta, theta], mode="lines+markers",
            line=dict(color=col, width=5),
            marker=dict(size=[6,16], symbol=["circle","arrow"],
                        angleref="previous", color=col,
                        line=dict(color="white", width=1.5)),
            showlegend=False,
            hovertemplate=f"<b>{km} km · {dir_}</b><extra></extra>"))

        fig.add_annotation(x=0.5, y=0.06, xref="paper", yref="paper",
            text=f"<b>{km} km</b> · {dir_} · {_clasif_label(s)}",
            showarrow=False, font=dict(size=12, color=col))

        fig.update_layout(
            **_layout(margin=dict(l=16, r=16, t=16, b=40)),
            polar=dict(
                bgcolor=PLOT_BG,
                radialaxis=dict(visible=False, range=[0, 1.25]),
                angularaxis=dict(
                    tickmode="array",
                    tickvals=[0, 45, 90, 135, 180, 225, 270, 315],
                    ticktext=["E","NE","N","NW","O","SW","S","SE"],
                    direction="counterclockwise", rotation=0,
                    gridcolor=PLOT_GRID, linecolor=PLOT_GRID,
                    tickfont=dict(color=PLOT_TEXT2, size=11)),
            ),
            showlegend=False,
        )
        return fig


    # ─────────────────────────────────────────────────────────────────────────────
    # VIZ 2 — LÍNEA + SERIE
    # ─────────────────────────────────────────────────────────────────────────────
    @app.callback(
        Output("fig-linea","figure"),
        Output("fig-serie","figure"),
        Input("store","data"),
    )
    def fig_linea_serie(datos):
        if not datos: return _vacia(), _vacia()

        hist      = datos.get("hist", [])
        serie     = datos.get("serie", [])
        per_act   = datos.get("periodo", "")
        color     = datos.get("color", "#4f8ef7")

        # Línea de desplazamiento
        if hist:
            labels = [h["periodo"]  for h in hist]
            desps  = [h["desp_km"] or 0 for h in hist]
            jacs   = [h["jaccard"]  for h in hist]
            colores= [_clasif_color(j) for j in jacs]

            fig_l = go.Figure()
            fig_l.add_trace(go.Scatter(
                x=labels, y=desps, mode="lines",
                line=dict(color=PLOT_GRID, width=1.5),
                showlegend=False, hoverinfo="skip"))
            fig_l.add_trace(go.Scatter(
                x=labels, y=desps, mode="markers",
                marker=dict(size=10, color=colores,
                            line=dict(color="white", width=1.5)),
                showlegend=False,
                hovertemplate="<b>%{x}</b><br>%{y:.2f} km<extra></extra>"))
            if per_act in labels:
                i = labels.index(per_act)
                fig_l.add_trace(go.Scatter(
                    x=[labels[i]], y=[desps[i]], mode="markers",
                    marker=dict(size=15, color=color, symbol="circle",
                                line=dict(color="white", width=2)),
                    showlegend=False,
                    hovertemplate=f"<b>{per_act}</b><br>{desps[i]:.2f} km<extra></extra>"))
            fig_l.update_layout(**_layout(margin=dict(l=40,r=10,t=10,b=36)),
                                yaxis_title="km")
        else:
            fig_l = _vacia("Solo hay un período cargado")

        # Frecuencia mensual
        if serie:
            ls = [s["periodo_label"] for s in serie]
            vs = [s["n"]             for s in serie]
            cs = [color if l == per_act else PLOT_TEXT2 for l in ls]
            fig_s = go.Figure()
            fig_s.add_trace(go.Bar(
                x=ls, y=vs, marker_color=cs, marker_line_width=0,
                hovertemplate="%{x}: %{y}<extra></extra>"))
            fig_s.update_layout(**_layout(margin=dict(l=36,r=10,t=8,b=36)),
                                bargap=0.35, showlegend=False)
        else:
            fig_s = _vacia()

        return fig_l, fig_s


    # ─────────────────────────────────────────────────────────────────────────────
    # VIZ 3 — NARRATIVA + TIPOS
    # ─────────────────────────────────────────────────────────────────────────────
    DIR_ES = {"N":"norte","NE":"noreste","E":"este","SE":"sureste",
              "S":"sur","SW":"suroeste","W":"oeste","NW":"noroeste"}

    @app.callback(
        Output("narr-cuerpo","children"),
        Output("fig-tipos",  "figure"),
        Input("store","data"),
    )
    def fig_narrativa(datos):
        if not datos: return "Sin datos.", _vacia()

        desp    = datos.get("desp")
        s       = datos.get("solap")
        a       = datos.get("var_area")
        n       = datos.get("n", 0)
        per     = datos.get("periodo","")
        per_a   = datos.get("per_ant","")
        fen     = datos.get("fenomeno","")
        color   = datos.get("color","#4f8ef7")

        if desp:
            km   = desp["distancia_km"]
            dir_ = desp["direccion"]
            dir_es = DIR_ES.get(dir_, dir_)
            pct  = round(s*100) if s is not None else None
            if s is None:   txt_s = "sin período anterior para comparar"
            elif s >= 0.70: txt_s = f"el patrón es estable — {pct}% del territorio coincide con {per_a}"
            elif s >= 0.30: txt_s = f"el patrón cambió moderadamente — {pct}% del territorio coincide con {per_a}"
            else:           txt_s = f"hay desplazamiento significativo — solo {pct}% del territorio coincide con {per_a}"

            txt_a = f"El área {'se expandió' if a and a>0 else 'se contrajo'} un {abs(a)}%." if a else ""

            narr = html.Div([
                html.Div(f"{fen} · {per} vs {per_a}", className="narr-period"),
                html.Div([
                    f"El fenómeno se desplazó {km} km hacia el {dir_es}. ",
                    html.Span(txt_s.capitalize()+". ", style={"color":_clasif_color(s)}),
                    txt_a,
                ], className="narr-text"),
                html.Div(className="narr-chips", children=[
                    html.Span(f"{n} hechos",       className="chip chip-blue"),
                    html.Span(f"{km} km · {dir_}", className="chip chip-blue"),
                    html.Span(_clasif_label(s), className="chip",
                              style={"background":_clasif_bg(s),"color":_clasif_color(s)}),
                    html.Span(
                        f"{'+'if a and a>0 else''}{a}% área" if a is not None else "—",
                        className="chip",
                        style={"background":"rgba(79,204,142,.15)" if a and a>0 else "rgba(247,95,95,.15)",
                               "color":"#4fcc8e" if a and a>0 else "#f75f5f"}),
                ]),
            ])
        else:
            narr = html.Div("Sin período anterior para comparar.", className="narr-period")

        # Distribución por tipo
        if not DF_GLOBAL.empty and per:
            df_p   = DF_GLOBAL[DF_GLOBAL["periodo_label"] == per]
            conteo = df_p["fenomeno"].value_counts().reset_index()
            conteo.columns = ["fenomeno","n"]
            cs = [COLORES_TIPOS.get(f,"#8b91b0") for f in conteo["fenomeno"]]
            fig_t = go.Figure()
            fig_t.add_trace(go.Bar(
                x=conteo["n"], y=conteo["fenomeno"], orientation="h",
                marker_color=cs, marker_line_width=0,
                hovertemplate="%{y}: %{x}<extra></extra>"))
            fig_t.update_layout(**_layout(margin=dict(l=140,r=10,t=8,b=28)),
                                bargap=0.3, showlegend=False)
            fig_t.update_yaxes(tickfont=dict(size=10))
        else:
            fig_t = _vacia()

        return narr, fig_t


    # ─────────────────────────────────────────────────────────────────────────────
    # VIZ 4 — FLECHAS
    # ─────────────────────────────────────────────────────────────────────────────
    @app.callback(Output("fig-flechas","figure"), Input("store","data"))
    def fig_flechas(datos):
        if not datos: return _vacia()
        hist    = datos.get("hist",[])
        per_act = datos.get("periodo","")
        if not hist: return _vacia("Solo hay un período cargado")

        fig  = go.Figure()
        maxd = max((h["desp_km"] or 0) for h in hist) or 1

        # Escala fija: flecha más larga = 0.42 unidades (independiente del valor real)
        LARGO_MAX = 0.42

        for i, h in enumerate(hist):
            if h["desp_km"] is None or h["az"] is None: continue
            az  = h["az"]; km = h["desp_km"]
            col = _clasif_color(h["jaccard"])
            es  = h["periodo"] == per_act
            rad = np.radians(az)

            # Magnitud normalizada con mínimo visible garantizado
            mag = LARGO_MAX * (0.35 + 0.65 * (km / maxd))

            dx  = np.sin(rad) * mag
            dy  = np.cos(rad) * mag
            x0,y0 = i - dx * 0.25, -dy * 0.25
            x1,y1 = i + dx * 0.75,  dy * 0.75

            fig.add_trace(go.Scatter(
                x=[x0, x1], y=[y0, y1], mode="lines",
                line=dict(color=col, width=5 if es else 3),
                showlegend=False,
                hovertemplate=f"<b>{h['periodo']}</b><br>{km:.2f} km · {h['dir']}<extra></extra>"))
            fig.add_trace(go.Scatter(
                x=[x1], y=[y1], mode="markers",
                marker=dict(size=14 if es else 10, color=col,
                            symbol="arrow", angle=az,
                            line=dict(color="white", width=1.5)),
                showlegend=False, hoverinfo="skip"))
            fig.add_annotation(x=i, y=-0.68,
                text=h["periodo"].split()[0][:3],
                showarrow=False, font=dict(size=10, color=PLOT_TEXT2))
            fig.add_annotation(x=i, y=0.62,
                text=f"{km:.2f} km",
                showarrow=False, font=dict(size=10, color=col))

        for lbl, clr in [("Estable","#4fcc8e"),("Parcial","#f7b84f"),("Significativo","#f75f5f")]:
            fig.add_trace(go.Scatter(x=[None],y=[None],mode="markers",
                marker=dict(size=8,color=clr,symbol="square"),
                name=lbl, showlegend=True))

        fig.update_layout(
            **_layout(margin=dict(l=20,r=20,t=16,b=52)),
            xaxis=dict(visible=False, range=[-0.8, len(hist)-0.2]),
            yaxis=dict(visible=False, range=[-0.85, 0.85]),
            legend=dict(orientation="h", x=0.5, xanchor="center", y=-0.2,
                        font=dict(size=10, color=PLOT_TEXT2), bgcolor="rgba(0,0,0,0)"),
            showlegend=True,
        )
        return fig


    # ─────────────────────────────────────────────────────────────────────────────
    # VIZ 5 — TABLA
    # ─────────────────────────────────────────────────────────────────────────────
    @app.callback(Output("tabla-cuerpo","children"), Input("store","data"))
    def tabla(datos):
        if not datos:
            return html.Div("Sin datos.", style={"color":PLOT_TEXT2,"fontSize":"12px"})

        hist    = datos.get("hist",[])
        per_act = datos.get("periodo","")

        cols = ["Período","Hechos","Desplaz.","Dirección","Jaccard","Clasificación","Var. área"]
        filas = [html.Tr([html.Th(c, className="th-cell") for c in cols])]

        # Primera fila sin comparación
        if PERIODOS:
            fen = datos.get("fenomeno","")
            n0  = len(DF_GLOBAL[(DF_GLOBAL["periodo_label"]==PERIODOS[0]) &
                                 (DF_GLOBAL["fenomeno"]==fen)]) if not DF_GLOBAL.empty else 0
            filas.append(html.Tr([
                html.Td(PERIODOS[0], className="td-per"),
                html.Td(str(n0),     className="td-num"),
                html.Td("—",         className="td-num"),
                html.Td("—",         className="td-cen"),
                html.Td("—",         className="td-num"),
                html.Td("—"),
                html.Td("—",         className="td-num"),
            ], className="tr-base"))

        for h in hist:
            j = h["jaccard"]; a = h["var_area"]; es = h["periodo"] == per_act
            filas.append(html.Tr([
                html.Td(h["periodo"], className="td-per"+(" td-act" if es else "")),
                html.Td(str(h["n"]),  className="td-num"),
                html.Td(f"{h['desp_km']:.2f} km" if h["desp_km"] else "—", className="td-num"),
                html.Td(h["dir"] or "—",  className="td-cen"),
                html.Td(f"{round(j*100)}%" if j is not None else "—", className="td-num"),
                html.Td(html.Span(_clasif_label(j),
                    style={"background":_clasif_bg(j),"color":_clasif_color(j),
                           "padding":"2px 7px","borderRadius":"4px",
                           "fontSize":"10px","fontWeight":"500"})),
                html.Td(f"{'+'if a and a>0 else''}{a}%" if a is not None else "—",
                    className="td-num",
                    style={"color":"#4fcc8e" if a and a>0 else "#f75f5f" if a and a<0 else PLOT_TEXT2}),
            ], className="tr-act" if es else "tr-base"))

        return html.Table(filas, className="comp-table")


    # ─────────────────────────────────────────────────────────────────────────────
    # EXPORTAR CSV
    # ─────────────────────────────────────────────────────────────────────────────
    @app.callback(
        Output("dl-csv","data"),
        Input("btn-export","n_clicks"),
        Input("store","data"),
        prevent_initial_call=True,
    )
    def exportar(n_clicks, datos):
        if ctx.triggered_id != "btn-export" or not datos: raise PreventUpdate
        hist = datos.get("hist",[])
        if not hist: raise PreventUpdate
        df_e = pd.DataFrame(hist)
        df_e.columns = ["Período","Hechos","Desp_km","Dirección","Azimut","Jaccard","Var_area_%"]
        return dcc.send_data_frame(df_e.to_csv, "desplazamiento_mensual.csv", index=False)




    @app.callback(
        Output("info-comuna", "children"),
        Input("store", "data"),
        Input("dd-comuna", "value"),
    )
    def info_comuna(datos, comuna):
        if not datos or not comuna or comuna == "Todas":
            return ""
        conteo = datos.get("conteo_comunas", {})
        n_com  = conteo.get(comuna, 0)
        n_tot  = datos.get("n", 0)
        pct    = round(100 * n_com / n_tot, 1) if n_tot > 0 else 0
        return html.Div([
            html.Span(f"{n_com} hechos en {comuna}", style={"fontWeight":"500","color":"var(--accent)"}),
            html.Span(f" ({pct}% del total del período)",
                      style={"fontSize":"10px","color":"var(--text2)"}),
        ], style={"marginTop":"4px","fontSize":"11px"})

    # ─────────────────────────────────────────────────────────────────────────────
    # EXPORTAR LAYOUT PARA USO COMO MÓDULO
    # ─────────────────────────────────────────────────────────────────────────────
    def get_layout():
        """Retorna el layout del módulo de movilidad para integración en la app principal."""
        return app.layout

    def registrar_callbacks(app_externo):
        """Re-registra los callbacks en una app Dash externa."""
        pass  # Los callbacks ya están registrados en 'app' de este módulo

