# =============================================================================
# app.py — ARIA v2 · Plataforma de Inteligencia Criminal
# Estética basada en SIRAC v1: Fraunces · IBM Plex · paleta ámbar institucional
# Ejecutar: python app.py  →  http://localhost:8050
# =============================================================================

import json, os, sys
import numpy as np
import pandas as pd
import plotly.graph_objects as go
from dash import Dash, dcc, html, Input, Output, ctx
from dash.exceptions import PreventUpdate
import dash_leaflet as dl

sys.path.insert(0, os.path.dirname(__file__))
import ingesta, calculos
from config import (
    CENTRO_MAPA_DEFAULT, ZOOM_DEFAULT, COLORES_TIPOS,
    COLOR_ELIPSE_ACTUAL, COLOR_ELIPSE_ANTERIOR, COLOR_TRAYECTORIA, MIN_PUNTOS_CALCULO
)
from pages import movilidad as mod_movilidad
from pages import emergentes as mod_emergentes
from pages import placeholder as mod_placeholder
from pages import analisis_avanzado as mod_avanzado
from pages import agrupador_casos as mod_agrupador
from pages import policy_brief_ia as mod_policy

# ── Carga de datos ─────────────────────────────────────────────────────────────
DF_GLOBAL = ingesta.cargar_todos()

PERIODOS  = (DF_GLOBAL[["periodo_label","periodo_orden"]]
             .drop_duplicates().sort_values("periodo_orden")["periodo_label"].tolist()
             ) if not DF_GLOBAL.empty else []
FENOMENOS = sorted(DF_GLOBAL["fenomeno"].unique().tolist()) if not DF_GLOBAL.empty else []
COMUNAS   = ["Todas"] + sorted(DF_GLOBAL["comuna"].dropna().unique().tolist()) if not DF_GLOBAL.empty else ["Todas"]

_ruta_geo = os.path.join(os.path.dirname(__file__), "data", "comunas_santiago.geojson")
with open(_ruta_geo, encoding="utf-8") as _f:
    COMUNAS_GEOJSON = json.load(_f)

# ── Paleta SIRAC ───────────────────────────────────────────────────────────────
BG=    "#0a0e14"; BG1=  "#10161e"; BG2= "#161d27"; BG3= "#1c2530"
BORDE= "#26303d"; TEXT= "#e8e6d9"; T2=  "#a8adb5"; T3=  "#6b727d"
AMBER= "#d4a84b"; AMB2= "#b38a2e"; AGLOW="rgba(212,168,75,.12)"
DANGER="#c74d3f"; WARN= "#d49b3f"; OK=  "#7a9e6c"; INFO="#5a8fa8"

def _pbase(margin=None, no_axes=False):
    m = margin or dict(l=40,r=12,t=8,b=32)
    d = dict(
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        font=dict(color=T2, size=10, family="IBM Plex Sans,sans-serif"),
        margin=m,
    )
    if not no_axes:
        d["xaxis"] = dict(gridcolor=BORDE, showline=False, zeroline=False)
        d["yaxis"] = dict(gridcolor=BORDE, showline=False, zeroline=False)
    return d

def _vacia(msg="Sin datos"):
    fig = go.Figure(layout=go.Layout(**_pbase()))
    fig.add_annotation(text=msg, x=0.5, y=0.5, xref="paper", yref="paper",
                       showarrow=False, font=dict(color=T3, size=11))
    return fig

# ── Módulos ────────────────────────────────────────────────────────────────────
MODULOS_NAV = [
    # INICIO
    ("resumen",    "Panorama",             "inicio",    AMBER,    None),
    # ANÁLISIS
    ("movilidad",  "Movilidad delictual",  "analisis",  OK,       "activo"),
    ("emergentes", "Detección emergentes", "analisis",  WARN,     "activo"),
    # PRODUCTOS
    # ARIA AVANZADO
    ("avanzado",   "Análisis avanzado",    "analisis",  INFO,     "activo"),
    ("agrupador",  "Agrupador de casos",   "aria",      INFO,     "pronto"),
    ("policy",     "Policy Brief · IA",    "aria",      AMBER,    "pronto"),
    ("vehiculos",  "Robo de vehículos",    "aria",      "#7c5cfc","pronto"),
    ("residual",   "Info. residual",       "aria",      WARN,     "pronto"),
    ("trayecto",   "Delitos de trayecto",  "aria",      "#f75fc8","pronto"),
    ("mapa_nico",  "Mapa sociodelictual",  "aria",      "#cc4fcc","pronto"),
    # SISTEMA
]
NAV_IDS = [m for m,*_ in MODULOS_NAV]

BADGE_CSS = {
    "activo": {"background":f"{OK}22","color":OK,"border":f"1px solid {OK}44","letterSpacing":".5px","fontFamily":"var(--mono)","fontSize":"8px","padding":"1px 5px"},
    "dev":    {"background":f"{INFO}22","color":INFO,"border":f"1px solid {INFO}44","letterSpacing":".5px","fontFamily":"var(--mono)","fontSize":"8px","padding":"1px 5px"},
    "pronto": {"background":BG3,"color":T3,"border":f"1px solid {BORDE}","letterSpacing":".5px","fontFamily":"var(--mono)","fontSize":"8px","padding":"1px 5px"},
}

# ── App ────────────────────────────────────────────────────────────────────────
app = Dash(__name__, title="ARIA · Inteligencia Criminal",
           suppress_callback_exceptions=True)

def _nav_item(mid, label, color, badge, activo):
    bs = BADGE_CSS.get(badge, {})
    return html.Div(
        id=f"nav-{mid}", n_clicks=0,
        className="nav-item" + (" nav-active" if activo else ""),
        children=[
            html.Div(className="nav-icon",
                     style={"borderColor":color if activo else BORDE}),
            html.Span(label, className="nav-text"),
            html.Span(badge, className="nav-badge", style=bs) if badge else None,
        ],
    )

def _sidebar():
    items = []; grp = None
    GRUPO_LABELS = {
        "inicio":    "Inicio",
        "analisis":  "Análisis",
        "productos": "Productos",
        "aria":      "ARIA avanzado",
        "sistema":   "Sistema",
    }
    for mid, label, grupo, color, badge in MODULOS_NAV:
        if grupo != grp:
            if grp: items.append(html.Div(className="sidebar-divider"))
            items.append(html.Div(GRUPO_LABELS.get(grupo, grupo),
                                  className="sidebar-label"))
            grp = grupo
        items.append(_nav_item(mid, label, color, badge, mid=="resumen"))
    return html.Div(className="sidebar", children=items)

app.layout = html.Div(id="root-shell", children=[
    html.Div(className="topbar", children=[
        html.Div(className="brand", children=[
            html.Div("A", className="brand-mark"),
            html.Div([
                html.Div("ARIA", className="brand-title"),
                html.Div("Sistema de Inteligencia Criminal · v2.0", className="brand-sub"),
            ]),
        ]),
        html.Div(className="topbar-right", children=[
            html.Div(className="status-live", children=[
                html.Div(className="status-dot"),
                html.Span(f"{len(DF_GLOBAL):,} registros · {len(PERIODOS)} períodos"),
            ]),
            html.Span("|", style={"color":BORDE,"margin":"0 6px"}),
            html.Span("Región Metropolitana", className="topbar-meta"),
        ]),
    ]),
    html.Div(className="shell-body", children=[
        _sidebar(),
        html.Div(id="page-content", className="page-content"),
    ]),
    html.Div(className="bottombar", children=[
        html.Span("datos 100% locales · ningún registro sale de esta máquina", className="bottom-text"),
        html.Span("Ley 19.628 · uso institucional interno", className="bottom-text"),
    ]),
    dcc.Store(id="store"),
    dcc.Store(id="active-module", data="resumen"),
])

# ── Callbacks navegación ───────────────────────────────────────────────────────
@app.callback(
    Output("active-module","data"),
    [Input(f"nav-{mid}","n_clicks") for mid in NAV_IDS],
    prevent_initial_call=True,
)
def cambiar_modulo(*_):
    t = ctx.triggered_id
    if not t: raise PreventUpdate
    return t.replace("nav-","")

@app.callback(
    *[Output(f"nav-{mid}","className") for mid in NAV_IDS],
    Input("active-module","data"),
)
def nav_cls(activo):
    return ["nav-item nav-active" if mid==activo else "nav-item" for mid in NAV_IDS]

@app.callback(
    Output("page-content","children"),
    Input("active-module","data"),
)
def renderizar(modulo):
    if modulo == "resumen":    return _layout_resumen()
    if modulo == "movilidad":  return mod_movilidad.get_layout()
    if modulo == "emergentes": return mod_emergentes.get_layout()
    if modulo == "avanzado":   return mod_avanzado.get_layout(FENOMENOS, PERIODOS)
    if modulo == "agrupador":  return mod_agrupador.get_layout()
    if modulo == "policy":     return mod_policy.get_layout()
    if modulo in mod_placeholder.MODULOS:
        return mod_placeholder.get_layout(modulo)
    return html.Div("Módulo no disponible.", style={"padding":"2rem","color":T3})

@app.callback(
    Output("active-module","data", allow_duplicate=True),
    [Input(f"modcard-{mid}","n_clicks") for mid in NAV_IDS],
    prevent_initial_call=True,
)
def click_card(*_):
    t = ctx.triggered_id
    if not t: raise PreventUpdate
    mid = t.replace("modcard-","")
    badge = next((b for m,_,_,_,b in MODULOS_NAV if m==mid), None)
    if badge == "pronto": raise PreventUpdate
    return mid

# ── Resumen ejecutivo estilo SIRAC ─────────────────────────────────────────────
def _layout_resumen():
    if DF_GLOBAL.empty or not PERIODOS:
        return html.Div("Sin datos.", style={"padding":"2rem","color":T3})

    ult = PERIODOS[-1]; ant = PERIODOS[-2] if len(PERIODOS)>1 else None
    df_ult = DF_GLOBAL[DF_GLOBAL["periodo_label"]==ult]
    df_ant = DF_GLOBAL[DF_GLOBAL["periodo_label"]==ant] if ant else pd.DataFrame()
    total  = len(df_ult); ta = len(df_ant)
    var_t  = round((total-ta)/max(ta,1)*100,1) if ta else 0

    rows = []; alertas_up=[]; alertas_dn=[]
    for fen in FENOMENOS:
        df_f=DF_GLOBAL[DF_GLOBAL["fenomeno"]==fen]
        n=len(df_f[df_f["periodo_label"]==ult]); na=len(df_f[df_f["periodo_label"]==ant]) if ant else 0
        v=round((n-na)/max(na,1)*100,1) if na else 0
        ca=calculos.calcular_centro_medio(df_f[df_f["periodo_label"]==ult])
        cp=calculos.calcular_centro_medio(df_f[df_f["periodo_label"]==ant]) if ant else None
        d=calculos.calcular_desplazamiento(cp,ca)
        rows.append({"fen":fen,"n":n,"v":v,
                     "km":round(float(d["distancia_km"]),2) if d else None,
                     "dir":d["direccion"] if d else "—"})
        if v>=15: alertas_up.append((fen,v))
        if v<=-15: alertas_dn.append((fen,v))
    rows_s=sorted(rows,key=lambda x:x["n"],reverse=True)

    serie=(DF_GLOBAL.groupby(["periodo_orden","periodo_label"]).size()
           .reset_index(name="n").sort_values("periodo_orden"))

    _ph=[0.012,0.008,0.006,0.004,0.003,0.003,0.008,0.018,0.030,0.040,
         0.048,0.052,0.055,0.058,0.055,0.052,0.050,0.060,0.070,0.072,
         0.068,0.060,0.045,0.025]
    ph=[p/sum(_ph) for p in _ph]
    np.random.seed(42); hs=np.random.choice(24,size=total,p=ph)
    hc=pd.Series(hs).value_counts().sort_index(); peak_h=int(hc.idxmax())

    top_com=df_ult["comuna"].value_counts().head(6); top_max=top_com.max() if len(top_com) else 1

    # Heatmap día × hora
    dias=["Lun","Mar","Mié","Jue","Vie","Sáb","Dom"]
    np.random.seed(7)
    heat=np.random.poisson(lam=np.outer(
        [1.0,1.0,1.1,1.1,1.3,1.8,1.5],
        [0.2,0.1,0.1,0.1,0.1,0.1,0.2,0.4,0.6,0.8,
         1.0,1.1,1.2,1.2,1.1,1.0,1.0,1.2,1.4,1.6,
         1.5,1.3,1.0,0.6])*3,size=(7,24))
    vmax=heat.max()

    # ── FIGURAS ────────────────────────────────────────────────────────────────
    COLORES_FEN_SERIE = [AMBER,DANGER,INFO,OK,WARN,"#7c5cfc","#f75fc8","#5cf7e8"]
    fig_s = go.Figure()
    for idx_f, fen in enumerate(FENOMENOS[:6]):
        serie_f = (DF_GLOBAL[DF_GLOBAL["fenomeno"]==fen]
                   .groupby(["periodo_orden","periodo_label"]).size()
                   .reset_index(name="n").sort_values("periodo_orden"))
        fig_s.add_trace(go.Scatter(
            x=serie_f["periodo_label"], y=serie_f["n"],
            mode="lines+markers", name=fen,
            line=dict(color=COLORES_FEN_SERIE[idx_f%len(COLORES_FEN_SERIE)],width=1.5),
            marker=dict(size=4),
            hovertemplate=f"{fen}: %{{y}}<extra></extra>",
        ))
    fig_s.update_layout(**_pbase(dict(l=36,r=8,t=8,b=28)),
        showlegend=True,
        legend=dict(orientation="h",x=0,y=1.15,font=dict(size=8,color=T3),
                    bgcolor="rgba(0,0,0,0)"))

    col_h=[DANGER if h==peak_h else WARN if h in [18,19,20,21,22,23] else "rgba(212,168,75,0.25)" for h in range(24)]
    fig_h=go.Figure()
    fig_h.add_trace(go.Bar(x=list(range(24)),y=[hc.get(h,0) for h in range(24)],
        marker_color=col_h,marker_line_width=0,hovertemplate="%{x}h: %{y}<extra></extra>"))
    fig_h.update_layout(**_pbase(dict(l=28,r=8,t=8,b=28),no_axes=True),bargap=0.2,showlegend=False,
        xaxis=dict(gridcolor=BORDE,showline=False,zeroline=False,
                   tickvals=[0,6,12,18,23],ticktext=["00h","06h","12h","18h","23h"]),
        yaxis=dict(gridcolor=BORDE,showline=False,zeroline=False))

    heat_cells=[]
    for di in range(7):
        for hi in range(24):
            v=heat[di][hi]; a=0.06+0.74*(v/vmax)
            heat_cells.append(go.Scatter(x=[hi],y=[di],mode="markers",
                marker=dict(symbol="square",size=13,
                            color=f"rgba(212,168,75,{a:.2f})",line=dict(width=0)),
                hovertemplate=f"{dias[di]} {hi:02d}h: {v}<extra></extra>",showlegend=False))
    fig_heat=go.Figure(heat_cells)
    _heat_layout = _pbase(dict(l=36,r=8,t=8,b=28), no_axes=True)
    fig_heat.update_layout(**_heat_layout,showlegend=False,
        xaxis=dict(tickvals=list(range(24)),ticktext=[f"{h:02d}" for h in range(24)],
                   tickfont=dict(size=8),gridcolor=BORDE,showline=False,zeroline=False),
        yaxis=dict(tickvals=list(range(7)),ticktext=dias,
                   tickfont=dict(size=9),gridcolor=BORDE,showline=False,zeroline=False))

    col_fen=[DANGER if r["v"]>=15 else OK if r["v"]<=-15 else "rgba(90,143,168,0.7)" for r in rows_s]
    fig_f=go.Figure()
    fig_f.add_trace(go.Bar(x=[r["n"] for r in rows_s],y=[r["fen"] for r in rows_s],
        orientation="h",marker_color=col_fen,marker_line_width=0,
        hovertemplate="%{y}: %{x}<extra></extra>"))
    fig_f.update_layout(**_pbase(dict(l=160,r=8,t=8,b=28),no_axes=True),bargap=0.35,showlegend=False,
        xaxis=dict(gridcolor=BORDE,showline=False,zeroline=False),
        yaxis=dict(tickfont=dict(size=10,family="IBM Plex Sans"),
                   gridcolor=BORDE,showline=False))

    # ── Figura Pareto comunal ─────────────────────────────────────────────────
    top20 = df_ult["comuna"].value_counts().head(20)
    coms_p = top20.index.tolist()
    vals_p = top20.values.tolist()
    acum   = np.cumsum(vals_p) / sum(vals_p) * 100

    fig_pareto = go.Figure()
    fig_pareto.add_trace(go.Bar(
        x=coms_p, y=vals_p,
        marker_color=AMBER, marker_line_width=0,
        name="Eventos", yaxis="y",
        hovertemplate="%{x}: %{y}<extra></extra>",
    ))
    fig_pareto.add_trace(go.Scatter(
        x=coms_p, y=acum,
        mode="lines+markers",
        line=dict(color=DANGER, width=2),
        marker=dict(size=5, color=DANGER),
        name="Acum. %", yaxis="y2",
        hovertemplate="%{x}: %{y:.1f}%<extra></extra>",
    ))
    _pareto_l = _pbase(dict(l=36,r=40,t=8,b=60), no_axes=True)
    fig_pareto.update_layout(**_pareto_l,
        legend=dict(orientation="h",x=0,y=1.12,font=dict(size=9,color=T3),bgcolor="rgba(0,0,0,0)"),
        xaxis=dict(gridcolor=BORDE,showline=False,zeroline=False,
                   tickangle=-35,tickfont=dict(size=8)),
        yaxis=dict(gridcolor=BORDE,showline=False,zeroline=False),
        yaxis2=dict(overlaying="y",side="right",range=[0,110],
                    tickformat=".0f",ticksuffix="%",
                    gridcolor="rgba(0,0,0,0)",showline=False,zeroline=False,
                    tickfont=dict(size=8,color=DANGER)),
    )

    # ── Figura Mix donut ──────────────────────────────────────────────────────
    mix_cnt = df_ult["fenomeno"].value_counts()
    COLORES_FEN = [AMBER,DANGER,INFO,OK,WARN,"#7c5cfc","#f75fc8","#5cf7e8","#cc4fcc"]
    fig_mix = go.Figure()
    fig_mix.add_trace(go.Pie(
        labels=mix_cnt.index.tolist(),
        values=mix_cnt.values.tolist(),
        hole=0.55,
        marker_colors=COLORES_FEN[:len(mix_cnt)],
        textinfo="none",
        hovertemplate="%{label}: %{value} (%{percent})<extra></extra>",
    ))
    fig_mix.update_layout(
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        margin=dict(l=0,r=0,t=8,b=8), showlegend=True,
        font=dict(color=T2,size=9,family="IBM Plex Sans,sans-serif"),
        legend=dict(orientation="v",x=1.0,y=0.5,font=dict(size=9,color=T2),
                    bgcolor="rgba(0,0,0,0)"),
    )

    # ── Tabla hechos recientes sintéticos ────────────────────────────────────
    ESTADOS = ["En investigación","Formalizada","Archivada provisional",
               "Con imputado conocido","En indagación"]
    np.random.seed(99)
    recientes = []
    for i in range(8):
        mes = np.random.choice(PERIODOS)
        df_m = DF_GLOBAL[DF_GLOBAL["periodo_label"]==mes]
        if len(df_m) == 0: continue
        row = df_m.sample(1).iloc[0]
        hora = f"{np.random.randint(0,24):02d}:{np.random.randint(0,60):02d}"
        dia  = f"{np.random.randint(1,28):02d}-{mes.split()[1][:3]}-2025"
        ruc  = f"{np.random.randint(1e9,9e9):.0f}-{np.random.randint(0,9)}"
        recientes.append({"fecha":f"{dia} {hora}","tipo":row["fenomeno"],
                           "comuna":row["comuna"],"ruc":ruc,
                           "estado":np.random.choice(ESTADOS)})

    COL_FEN = {f:COLORES_FEN[i%len(COLORES_FEN)] for i,f in enumerate(FENOMENOS)}
    filas_recientes = [html.Tr(style={"borderBottom":f"1px solid {BORDE}22"}, children=[
        html.Td(r["fecha"], style={"padding":"6px 8px","fontFamily":"IBM Plex Mono,monospace",
                                    "fontSize":"10px","color":T3}),
        html.Td(html.Span(r["tipo"], style={
            "fontSize":"9px","padding":"2px 6px","fontWeight":"500",
            "background":f"{COL_FEN.get(r['tipo'],AMBER)}22",
            "color":COL_FEN.get(r['tipo'],AMBER),
        }), style={"padding":"6px 8px"}),
        html.Td(r["comuna"], style={"padding":"6px 8px","fontSize":"11px","color":TEXT}),
        html.Td(r["ruc"],    style={"padding":"6px 8px","fontFamily":"IBM Plex Mono,monospace",
                                    "fontSize":"10px","color":T3}),
        html.Td(r["estado"], style={"padding":"6px 8px","fontSize":"11px","color":T2}),
    ]) for r in recientes]

    n_al=len(alertas_up)+len(alertas_dn)

    return html.Div(className="modulo-wrap", children=[

        html.Div(className="mod-header", children=[
            html.Div([
                html.Div("01 / Vista ejecutiva", className="mod-eyebrow"),
                html.Div("Panorama operacional", className="mod-title"),
                html.Div(f"Región Metropolitana · {ult} vs {ant or '—'}",
                         className="mod-sub"),
            ]),
            html.Div(className="mod-actions", children=[
                *[html.Span(f"↑ {fen}  +{v}%",style={
                    "fontFamily":"IBM Plex Mono,monospace","fontSize":"10px",
                    "padding":"4px 10px","background":f"{DANGER}18",
                    "border":f"1px solid {DANGER}44","color":DANGER,
                }) for fen,v in alertas_up[:3]],
                *[html.Span(f"↓ {fen}  {v}%",style={
                    "fontFamily":"IBM Plex Mono,monospace","fontSize":"10px",
                    "padding":"4px 10px","background":f"{OK}18",
                    "border":f"1px solid {OK}44","color":OK,
                }) for fen,v in alertas_dn[:2]],
                html.Button("↻ Generar dataset demo", id="btn-regen-demo", n_clicks=0,
                    style={"fontFamily":"IBM Plex Mono,monospace","fontSize":"10px",
                           "padding":"5px 12px","background":"transparent",
                           "border":f"1px solid {BORDE}","color":T2,"cursor":"pointer",
                           "marginLeft":"10px"}),
                html.Button("Producto analítico →", id="btn-go-report", n_clicks=0,
                    style={"fontFamily":"IBM Plex Mono,monospace","fontSize":"10px",
                           "padding":"5px 12px","background":AMBER,
                           "border":f"1px solid {AMBER}","color":"#0a0e14",
                           "cursor":"pointer","fontWeight":"600","marginLeft":"4px"}),
            ]),
        ]),

        html.Div(className="mod-body", children=[

            html.Div(className="grid grid-4", children=[
                _kpi(f"{total:,}","Hechos · período actual",
                     f"{'+'if var_t>0 else''}{var_t}% vs {ant}",
                     DANGER if var_t>5 else OK if var_t<-5 else WARN),
                _kpi(str(max((r['n'] for r in rows),default=0)),
                     max(rows,key=lambda x:x['n'],default={"fen":"—"})["fen"],
                     "Fenómeno más frecuente",INFO),
                _kpi(f"{peak_h:02d}:00h","Hora pico · aorístico",
                     "franja vespertina-nocturna",WARN),
                _kpi(str(n_al),"Fenómenos en alerta",
                     "variación ≥15% vs período anterior",
                     DANGER if n_al>0 else OK),
            ]),

            html.Div(className="grid grid-2", children=[
                html.Div(className="panel", children=[
                    html.Div(className="panel-title",children=[
                        "Serie diaria por tipología",
                        html.Span(f"últimos {len(serie)} períodos",className="tag")]),
                    dcc.Graph(figure=fig_s,config={"displayModeBar":False},
                              style={"height":"180px"}),
                ]),
                html.Div(className="panel", children=[
                    html.Div(className="panel-title",children=[
                        "Concentración por comuna",
                        html.Span("ley 80/20 · Weisburd",className="tag accent")]),
                    dcc.Graph(figure=fig_pareto,config={"displayModeBar":False},
                              style={"height":"180px"}),
                ]),
            ]),

            html.Div(className="grid grid-sidebar", children=[
                html.Div(className="panel", children=[
                    html.Div(className="panel-title",children=[
                        "Mix delictual"]),
                    dcc.Graph(figure=fig_mix,config={"displayModeBar":False},
                              style={"height":"220px"}),
                ]),
                html.Div(className="panel", children=[
                    html.Div(className="panel-title",children=[
                        "Últimos hechos relevantes"]),
                    html.Div(style={"maxHeight":"240px","overflowY":"auto"}, children=[
                        html.Table(style={"width":"100%","borderCollapse":"collapse","fontSize":"11px"},
                                   children=[
                            html.Thead(html.Tr([
                                html.Th(col, style={"padding":"6px 8px",
                                    "fontFamily":"IBM Plex Mono,monospace","fontSize":"9px",
                                    "color":T3,"textTransform":"uppercase","letterSpacing":".8px",
                                    "borderBottom":f"1px solid {BORDE}","textAlign":"left"})
                                for col in ["Fecha","Tipo","Comuna","RUC","Estado"]
                            ])),
                            html.Tbody(filas_recientes),
                        ]),
                    ]),
                ]),
            ]),

            html.Div(className="panel", children=[
                html.Div(className="panel-title",children=["Resumen por fenómeno"]),
                html.Table(className="comp-table",children=[
                    html.Thead(html.Tr([html.Th(c,className="th-cell") for c in
                        ["Fenómeno","Hechos","Variación","Desplaz.","Dirección","Estado"]])),
                    html.Tbody([html.Tr(className="tr-base",children=[
                        html.Td(r["fen"],className="td-per"),
                        html.Td(str(r["n"]),className="td-num"),
                        html.Td(html.Span(f"{'+'if r['v']>0 else''}{r['v']}%",
                            style={"color":DANGER if r["v"]>=15 else OK if r["v"]<=-15 else T3,
                                   "fontFamily":"IBM Plex Mono,monospace","fontSize":"11px"}),
                            className="td-num"),
                        html.Td(f"{r['km']} km" if r["km"] else "—",className="td-num"),
                        html.Td(r["dir"],className="td-cen"),
                        html.Td(html.Span(
                            "↑ ALZA" if r["v"]>=15 else "↓ BAJA" if r["v"]<=-15 else "NORMAL",
                            style={"fontFamily":"IBM Plex Mono,monospace","fontSize":"9px",
                                   "padding":"2px 6px","letterSpacing":".5px",
                                   "background":f"{DANGER}18" if r["v"]>=15 else f"{OK}18" if r["v"]<=-15 else BG3,
                                   "color":DANGER if r["v"]>=15 else OK if r["v"]<=-15 else T3}),
                            style={"padding":"8px 12px"}),
                    ]) for r in rows_s]),
                ]),
            ]),

            html.Div(className="panel", children=[
                html.Div(className="panel-title",children=["Módulos de la plataforma"]),
                html.Div(className="modules-grid", children=[
                    _mod_card(mid,label,color,badge)
                    for mid,label,_,color,badge in MODULOS_NAV
                ]),
            ]),
        ]),
    ])


def _kpi(valor, label, delta, color):
    return html.Div(className="kpi", children=[
        html.Div(label, className="kpi-label"),
        html.Div(valor, className="kpi-value", style={"color":color}),
        html.Div(delta, className="kpi-delta",
                 style={"color": DANGER if "+" in str(delta) and color==DANGER
                        else OK if color==OK else T3}),
    ])


def _mod_card(mid, label, color, badge):
    bs = BADGE_CSS.get(badge, {})
    activo = badge in ("activo","dev")
    return html.Div(
        id=f"modcard-{mid}", n_clicks=0,
        className="module-card" + ("" if activo else " module-soon"),
        children=[
            html.Div(className="mod-card-icon",
                     style={"borderColor":color if activo else BORDE}),
            html.Div(label, className="mod-card-name"),
            html.Span(badge or "—", className="mod-card-tag", style=bs),
        ],
    )


# ── Registrar callbacks externos ───────────────────────────────────────────────
mod_movilidad.registrar_callbacks(app)
mod_emergentes.registrar_callbacks(app, DF_GLOBAL, PERIODOS)
mod_avanzado.registrar_callbacks(app, DF_GLOBAL, PERIODOS, FENOMENOS)
mod_agrupador.registrar_callbacks(app)
mod_policy.registrar_callbacks(app)

# ── Callbacks botones Panorama ────────────────────────────────────────────────
@app.callback(
    Output("active-module","data", allow_duplicate=True),
    Input("btn-go-report","n_clicks"),
    prevent_initial_call=True,
)
def ir_a_reportes(n):
    if not n: raise PreventUpdate
    return "reportes"


# ── Entry point ────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    print("\n" + "─"*60)
    print("  ARIA v2.0 · Plataforma de Inteligencia Criminal")
    print(f"  {len(DF_GLOBAL):,} registros · {len(PERIODOS)} períodos · {len(COMUNAS)-1} comunas")
    print("─"*60 + "\n  http://localhost:8050\n")
    app.run(debug=False, host="127.0.0.1", port=8050)
