"""Mobility analysis module — spatial displacement dashboard.

Visualizations: compass rose, trend line, narrative, arrows, table.
Map layers: choropleth, points, KDE, SDE ellipses, trajectory.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import dash_leaflet as dl
from dash import Dash, Input, Output, ctx, dcc, html
from dash.exceptions import PreventUpdate

from aria.analysis.spatial import SpatialAnalyzer
from aria.data.store import DataStore
from aria.modules.base import BaseModule
from aria.theme import Theme


class MobilityModule(BaseModule):
    """Spatial mobility analysis with map, metrics, and 5 visualization tabs."""

    module_id = "movilidad"
    display_name = "Movilidad delictual"

    def __init__(
        self, store: DataStore, theme: Theme, analyzer: SpatialAnalyzer,
        config: "AppConfig | None" = None,
    ) -> None:
        super().__init__(store, theme)
        self._analyzer = analyzer
        self._config = config

    def get_layout(self) -> html.Div:
        s = self._store
        cfg = self._config

        center = cfg.map.center if cfg else (-33.45, -70.65)
        zoom = cfg.map.zoom if cfg else 11

        return html.Div(id="root-movilidad", children=[
            html.Div(className="header", children=[
                html.Div(className="header-left", children=[
                    html.H1("Movilidad Delictual"),
                    html.Span("Análisis espacial · Uso institucional interno",
                              className="header-sub"),
                ]),
                html.Div(className="header-right", children=[
                    html.Span(
                        f"{s.record_count:,} registros · {s.period_count} período(s)",
                        className="header-meta",
                    ),
                ]),
            ]),
            html.Div(className="body", children=[
                self._sidebar_layout(),
                html.Div(className="map-panel", children=[
                    dl.Map(id="mapa", center=center, zoom=zoom,
                           style={"width": "100%", "height": "100%"}, children=[
                        dl.TileLayer(
                            url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png",
                            attribution="© OpenStreetMap", maxZoom=19,
                        ),
                        dl.LayerGroup(id="lyr-comunas"),
                        dl.LayerGroup(id="lyr-pts"),
                        dl.LayerGroup(id="lyr-kde"),
                        dl.LayerGroup(id="lyr-elip-act"),
                        dl.LayerGroup(id="lyr-elip-ant"),
                        dl.LayerGroup(id="lyr-tray"),
                    ]),
                ]),
                self._chart_panel_layout(),
            ]),
        ])

    def register_callbacks(self, app: Dash) -> None:
        store = self._store
        theme = self._theme
        analyzer = self._analyzer
        config = self._config

        # -- COMPUTE --
        @app.callback(
            Output("store", "data"),
            Output("alerta-n", "children"),
            Output("alerta-n", "style"),
            Input("dd-fen", "value"),
            Input("dd-per", "value"),
            Input("dd-comuna", "value"),
        )
        def compute(phenomenon, period, comuna):
            if not phenomenon or not period or store.is_empty:
                raise PreventUpdate

            min_pts = config.spatial.min_points if config else 5

            df_type = store.filter_by(phenomenon=phenomenon)
            if comuna and comuna != "Todas":
                df_type = df_type[df_type["comuna"] == comuna]
            df_curr = df_type[df_type["periodo_label"] == period]
            n_curr = len(df_curr)

            idx_p = store.periods.index(period)
            prev_period = store.periods[idx_p - 1] if idx_p > 0 else None
            df_prev = (
                df_type[df_type["periodo_label"] == prev_period]
                if prev_period else pd.DataFrame()
            )

            alert = (
                f"⚠ Datos insuficientes para métricas espaciales (n={n_curr} < {min_pts})"
                if n_curr < min_pts else ""
            )
            alert_style = {"display": "block"} if alert else {"display": "none"}

            center_curr = analyzer.mean_center(df_curr) if n_curr >= 1 else None
            sde_curr = analyzer.standard_deviational_ellipse(df_curr)
            kde_curr = analyzer.kernel_density(df_curr)
            center_prev = analyzer.mean_center(df_prev) if len(df_prev) >= 1 else None
            sde_prev = analyzer.standard_deviational_ellipse(df_prev)
            disp = analyzer.displacement(center_prev, center_curr)
            overlap = analyzer.jaccard_overlap(sde_prev, sde_curr)
            area_var = analyzer.area_variation(sde_curr, sde_prev)

            trajectory = []
            for p in store.periods:
                c = analyzer.mean_center(df_type[df_type["periodo_label"] == p])
                if c:
                    trajectory.append({"lat": c[0], "lon": c[1], "label": p})

            series = (
                df_type.groupby(["periodo_orden", "periodo_label"]).size()
                .reset_index(name="n").sort_values("periodo_orden")
                .to_dict(orient="records")
            )

            hist = []
            for i in range(1, len(store.periods)):
                pc, pp = store.periods[i], store.periods[i - 1]
                dc = df_type[df_type["periodo_label"] == pc]
                dp = df_type[df_type["periodo_label"] == pp]
                cc = analyzer.mean_center(dc)
                cp = analyzer.mean_center(dp)
                d = analyzer.displacement(cp, cc)
                sc = analyzer.standard_deviational_ellipse(dc)
                sp = analyzer.standard_deviational_ellipse(dp)
                s = analyzer.jaccard_overlap(sp, sc)
                a = analyzer.area_variation(sc, sp)
                hist.append({
                    "periodo": pc,
                    "n": int(len(dc)),
                    "desp_km": float(round(d.distance_km, 2)) if d else None,
                    "dir": d.direction if d else None,
                    "az": float(round(d.azimuth_degrees, 1)) if d else None,
                    "jaccard": float(round(s, 3)) if s is not None else None,
                    "var_area": float(round(a, 1)) if a is not None else None,
                })

            points = df_curr[["latitud", "longitud"]].to_dict(orient="records")
            ellipse_curr = (
                list(sde_curr.polygon.exterior.coords) if sde_curr else None
            )
            ellipse_prev = (
                list(sde_prev.polygon.exterior.coords) if sde_prev else None
            )

            kde_pts = None
            if kde_curr:
                lats = kde_curr.lats.ravel()
                lons = kde_curr.lons.ravel()
                dens = kde_curr.density.ravel()
                mask = dens > 0.05
                kde_pts = [
                    [float(la), float(lo), float(d)]
                    for la, lo, d in zip(lats[mask], lons[mask], dens[mask])
                ]

            crime_colors = config.crime_type_colors if config else {}
            df_per_fen = store.filter_by(phenomenon=phenomenon, period=period)
            comuna_counts = df_per_fen["comuna"].value_counts().to_dict()

            disp_dict = (
                {"distancia_km": disp.distance_km, "distancia_m": disp.distance_m,
                 "azimut_grados": disp.azimuth_degrees, "direccion": disp.direction}
                if disp else None
            )

            return {
                "n": n_curr, "periodo": period, "per_ant": prev_period,
                "fenomeno": phenomenon,
                "color": crime_colors.get(phenomenon, "#4f8ef7"),
                "puntos": points, "elip_act": ellipse_curr, "elip_ant": ellipse_prev,
                "kde_pts": kde_pts, "tray": trajectory,
                "desp": disp_dict, "solap": overlap,
                "clasif": analyzer.classify_overlap(overlap),
                "var_area": area_var, "serie": series, "hist": hist,
                "comuna": comuna or "Todas",
                "conteo_comunas": comuna_counts,
            }, alert, alert_style

        # -- METRICS --
        @app.callback(
            Output("mt-n", "children"), Output("mt-desp", "children"),
            Output("mt-dir", "children"), Output("mt-solap", "children"),
            Output("mt-clasif", "children"), Output("mt-area", "children"),
            Input("store", "data"),
        )
        def metrics(d):
            if not d:
                return ["—"] * 6
            desp = d.get("desp")
            s = d.get("solap")
            a = d.get("var_area")
            return (
                str(d.get("n", 0)),
                f"{desp['distancia_km']} km" if desp else "—",
                desp["direccion"] if desp else "—",
                f"{round(s * 100, 1)}%" if s is not None else "—",
                d.get("clasif", "—"),
                (f"+{a}%" if a and a > 0 else f"{a}%") if a is not None else "—",
            )

        # -- MAP --
        @app.callback(
            Output("lyr-comunas", "children"),
            Output("lyr-pts", "children"), Output("lyr-kde", "children"),
            Output("lyr-elip-act", "children"), Output("lyr-elip-ant", "children"),
            Output("lyr-tray", "children"),
            Input("store", "data"),
            Input("chk-capas", "value"),
            Input("sl-op", "value"),
        )
        def render_map(data, layers, opacity):
            if not data:
                return [], [], [], [], [], []
            color = data.get("color", "#4f8ef7")
            active = set(layers or [])

            ellipse_curr_color = config.ellipse_current_color if config else "#4f8ef7"
            ellipse_prev_color = config.ellipse_previous_color if config else "#f75f5f"
            traj_color = config.trajectory_color if config else "#f7b84f"

            comunas_layer = []
            if "comunas" in active and store.comunas_geojson:
                counts = data.get("conteo_comunas", {})
                max_c = max(counts.values()) if counts else 1
                selected = data.get("comuna", "Todas")

                for feat in store.comunas_geojson["features"]:
                    geom_type = feat["geometry"]["type"]
                    if geom_type not in ("Polygon", "MultiPolygon"):
                        continue
                    name = feat["properties"]["comuna"]
                    n = counts.get(name, 0)
                    pct = n / max_c if max_c > 0 else 0

                    if pct == 0:
                        fill, fill_op = "#1a1d27", 0.15
                    elif pct < 0.25:
                        fill, fill_op = "#B5D4F4", 0.45
                    elif pct < 0.50:
                        fill, fill_op = "#378ADD", 0.50
                    elif pct < 0.75:
                        fill, fill_op = "#185FA5", 0.55
                    else:
                        fill, fill_op = "#042C53", 0.65

                    border_c = "#f7b84f" if (selected != "Todas" and name == selected) else "#4f8ef7"
                    border_w = 3 if (selected != "Todas" and name == selected) else 1

                    coords = feat["geometry"]["coordinates"]
                    ring = coords[0][0] if geom_type == "MultiPolygon" else coords[0]
                    positions = [
                        [pt[1], pt[0]] for pt in ring
                        if isinstance(pt, (list, tuple)) and len(pt) >= 2
                    ]
                    comunas_layer.append(dl.Polygon(
                        positions=positions, color=border_c, weight=border_w,
                        fillColor=fill, fillOpacity=fill_op,
                        children=dl.Tooltip(
                            f"{name}: {n} hechos"
                            + (f" ({round(pct * 100)}% del máximo)" if n > 0 else "")
                        ),
                    ))

            pts = (
                [dl.CircleMarker(
                    center=[p["latitud"], p["longitud"]], radius=6,
                    color="white", weight=1.5, fillColor=color, fillOpacity=0.85,
                    children=dl.Tooltip(data["fenomeno"]),
                ) for p in data.get("puntos", [])]
                if "puntos" in active else []
            )

            kde = (
                [dl.CircleMarker(
                    center=[la, lo], radius=max(4, int(d * 18)),
                    color="none", fillColor=color, fillOpacity=d * 0.35,
                ) for la, lo, d in (data.get("kde_pts") or []) if d > 0.3]
                if "kde" in active else []
            )

            ea = (
                [dl.Polygon(
                    positions=[[c[1], c[0]] for c in data["elip_act"]],
                    color=ellipse_curr_color, weight=2,
                    fillColor=ellipse_curr_color, fillOpacity=opacity * 0.4,
                    children=dl.Tooltip("Elipse actual"),
                )]
                if "elipse_act" in active and data.get("elip_act") else []
            )

            eant = (
                [dl.Polygon(
                    positions=[[c[1], c[0]] for c in data["elip_ant"]],
                    color=ellipse_prev_color, weight=2, dashArray="6 4",
                    fillColor=ellipse_prev_color, fillOpacity=opacity * 0.15,
                    children=dl.Tooltip(f"Elipse — {data.get('per_ant', 'anterior')}"),
                )]
                if "elipse_ant" in active and data.get("elip_ant") else []
            )

            tray = []
            if "trayectoria" in active:
                t = data.get("tray", [])
                if len(t) >= 2:
                    tray.append(dl.Polyline(
                        positions=[[x["lat"], x["lon"]] for x in t],
                        color=traj_color, weight=2, dashArray="4 4",
                    ))
                for x in t:
                    is_curr = x["label"] == data["periodo"]
                    tray.append(dl.CircleMarker(
                        center=[x["lat"], x["lon"]],
                        radius=8 if is_curr else 5,
                        color="white", weight=2, fillColor=traj_color,
                        fillOpacity=1.0 if is_curr else 0.6,
                        children=dl.Tooltip(x["label"]),
                    ))

            return comunas_layer, pts, kde, ea, eant, tray

        # -- TABS --
        TABS = ["rosa", "linea", "narr", "flechas", "tabla"]

        @app.callback(
            *[Output(f"viz-{t}", "style") for t in TABS],
            *[Output(f"tab-{t}", "className") for t in TABS],
            *[Input(f"tab-{t}", "n_clicks") for t in TABS],
        )
        def switch_tab(*_):
            triggered = ctx.triggered_id or "tab-rosa"
            active_tab = triggered.replace("tab-", "")
            vis = [
                {"display": "block"} if t == active_tab else {"display": "none"}
                for t in TABS
            ]
            cls = [
                "viz-tab active" if t == active_tab else "viz-tab"
                for t in TABS
            ]
            return (*vis, *cls)

        # -- VIZ 1: COMPASS ROSE --
        @app.callback(Output("fig-rosa", "figure"), Input("store", "data"))
        def fig_rose(data):
            if not data or not data.get("desp"):
                return theme.empty_figure("Sin período anterior para comparar")

            desp = data["desp"]
            az = desp["azimut_grados"]
            km = desp["distancia_km"]
            dir_ = desp["direccion"]
            s = data.get("solap")
            col = theme.classify_color(s)
            mag = 0.45 + 0.45 * min(km / 3.0, 1.0)
            theta = (90 - az) % 360

            fig = go.Figure()
            for r in [0.33, 0.66, 1.0]:
                fig.add_trace(go.Scatterpolar(
                    r=[r] * 361, theta=list(range(361)),
                    mode="lines", line={"color": theme.border, "width": 0.8, "dash": "dot"},
                    showlegend=False, hoverinfo="skip",
                ))
            fig.add_trace(go.Scatterpolar(
                r=[0, mag], theta=[theta, theta], mode="lines+markers",
                line={"color": col, "width": 5},
                marker={
                    "size": [6, 16], "symbol": ["circle", "arrow"],
                    "angleref": "previous", "color": col,
                    "line": {"color": "white", "width": 1.5},
                },
                showlegend=False,
                hovertemplate=f"<b>{km} km · {dir_}</b><extra></extra>",
            ))
            fig.add_annotation(
                x=0.5, y=0.06, xref="paper", yref="paper",
                text=f"<b>{km} km</b> · {dir_} · {theme.classify_label(s)}",
                showarrow=False, font={"size": 12, "color": col},
            )
            fig.update_layout(
                **theme.plot_base({"l": 16, "r": 16, "t": 16, "b": 40}),
                polar={
                    "bgcolor": theme.bg,
                    "radialaxis": {"visible": False, "range": [0, 1.25]},
                    "angularaxis": {
                        "tickmode": "array",
                        "tickvals": [0, 45, 90, 135, 180, 225, 270, 315],
                        "ticktext": ["E", "NE", "N", "NW", "O", "SW", "S", "SE"],
                        "direction": "counterclockwise", "rotation": 0,
                        "gridcolor": theme.border, "linecolor": theme.border,
                        "tickfont": {"color": theme.text2, "size": 11},
                    },
                },
                showlegend=False,
            )
            return fig

        # -- VIZ 2: TREND + SERIES --
        @app.callback(
            Output("fig-linea", "figure"), Output("fig-serie", "figure"),
            Input("store", "data"),
        )
        def fig_trend(data):
            if not data:
                return theme.empty_figure(), theme.empty_figure()

            hist = data.get("hist", [])
            series = data.get("serie", [])
            curr_period = data.get("periodo", "")
            color = data.get("color", "#4f8ef7")

            if hist:
                labels = [h["periodo"] for h in hist]
                desps = [h["desp_km"] or 0 for h in hist]
                jacs = [h["jaccard"] for h in hist]
                colors = [theme.classify_color(j) for j in jacs]

                fig_l = go.Figure()
                fig_l.add_trace(go.Scatter(
                    x=labels, y=desps, mode="lines",
                    line={"color": theme.border, "width": 1.5},
                    showlegend=False, hoverinfo="skip",
                ))
                fig_l.add_trace(go.Scatter(
                    x=labels, y=desps, mode="markers",
                    marker={"size": 10, "color": colors, "line": {"color": "white", "width": 1.5}},
                    showlegend=False,
                    hovertemplate="<b>%{x}</b><br>%{y:.2f} km<extra></extra>",
                ))
                if curr_period in labels:
                    i = labels.index(curr_period)
                    fig_l.add_trace(go.Scatter(
                        x=[labels[i]], y=[desps[i]], mode="markers",
                        marker={"size": 15, "color": color, "symbol": "circle",
                                "line": {"color": "white", "width": 2}},
                        showlegend=False,
                        hovertemplate=f"<b>{curr_period}</b><br>{desps[i]:.2f} km<extra></extra>",
                    ))
                fig_l.update_layout(
                    **theme.plot_base({"l": 40, "r": 10, "t": 10, "b": 36}),
                    yaxis_title="km",
                )
            else:
                fig_l = theme.empty_figure("Solo hay un período cargado")

            if series:
                ls = [s["periodo_label"] for s in series]
                vs = [s["n"] for s in series]
                cs = [color if l == curr_period else theme.text2 for l in ls]
                fig_s = go.Figure()
                fig_s.add_trace(go.Bar(
                    x=ls, y=vs, marker_color=cs, marker_line_width=0,
                    hovertemplate="%{x}: %{y}<extra></extra>",
                ))
                fig_s.update_layout(
                    **theme.plot_base({"l": 36, "r": 10, "t": 8, "b": 36}),
                    bargap=0.35, showlegend=False,
                )
            else:
                fig_s = theme.empty_figure()

            return fig_l, fig_s

        # -- VIZ 3: NARRATIVE --
        DIR_ES = {
            "N": "norte", "NE": "noreste", "E": "este", "SE": "sureste",
            "S": "sur", "SW": "suroeste", "W": "oeste", "NW": "noroeste",
        }

        @app.callback(
            Output("narr-cuerpo", "children"), Output("fig-tipos", "figure"),
            Input("store", "data"),
        )
        def fig_narrative(data):
            if not data:
                return "Sin datos.", theme.empty_figure()

            desp = data.get("desp")
            s = data.get("solap")
            a = data.get("var_area")
            n = data.get("n", 0)
            per = data.get("periodo", "")
            per_a = data.get("per_ant", "")
            fen = data.get("fenomeno", "")
            color = data.get("color", "#4f8ef7")

            if desp:
                km = desp["distancia_km"]
                dir_ = desp["direccion"]
                dir_es = DIR_ES.get(dir_, dir_)
                pct = round(s * 100) if s is not None else None
                if s is None:
                    txt_s = "sin período anterior para comparar"
                elif s >= 0.70:
                    txt_s = f"el patrón es estable — {pct}% del territorio coincide con {per_a}"
                elif s >= 0.30:
                    txt_s = f"el patrón cambió moderadamente — {pct}% del territorio coincide con {per_a}"
                else:
                    txt_s = f"hay desplazamiento significativo — solo {pct}% del territorio coincide con {per_a}"

                txt_a = (
                    f"El área {'se expandió' if a and a > 0 else 'se contrajo'} un {abs(a)}%."
                    if a else ""
                )

                narr = html.Div([
                    html.Div(f"{fen} · {per} vs {per_a}", className="narr-period"),
                    html.Div([
                        f"El fenómeno se desplazó {km} km hacia el {dir_es}. ",
                        html.Span(txt_s.capitalize() + ". ",
                                  style={"color": theme.classify_color(s)}),
                        txt_a,
                    ], className="narr-text"),
                    html.Div(className="narr-chips", children=[
                        html.Span(f"{n} hechos", className="chip chip-blue"),
                        html.Span(f"{km} km · {dir_}", className="chip chip-blue"),
                        html.Span(theme.classify_label(s), className="chip",
                                  style={"background": theme.classify_bg(s),
                                         "color": theme.classify_color(s)}),
                        html.Span(
                            f"{'+'if a and a > 0 else''}{a}% área" if a is not None else "—",
                            className="chip",
                            style={
                                "background": "rgba(79,204,142,.15)" if a and a > 0
                                              else "rgba(247,95,95,.15)",
                                "color": "#4fcc8e" if a and a > 0 else "#f75f5f",
                            },
                        ),
                    ]),
                ])
            else:
                narr = html.Div("Sin período anterior para comparar.", className="narr-period")

            crime_colors = config.crime_type_colors if config else {}
            if not store.is_empty and per:
                df_p = store.filter_by(period=per)
                counts = df_p["fenomeno"].value_counts().reset_index()
                counts.columns = ["fenomeno", "n"]
                cs = [crime_colors.get(f, "#8b91b0") for f in counts["fenomeno"]]
                fig_t = go.Figure()
                fig_t.add_trace(go.Bar(
                    x=counts["n"], y=counts["fenomeno"], orientation="h",
                    marker_color=cs, marker_line_width=0,
                    hovertemplate="%{y}: %{x}<extra></extra>",
                ))
                fig_t.update_layout(
                    **theme.plot_base({"l": 140, "r": 10, "t": 8, "b": 28}),
                    bargap=0.3, showlegend=False,
                )
                fig_t.update_yaxes(tickfont={"size": 10})
            else:
                fig_t = theme.empty_figure()

            return narr, fig_t

        # -- VIZ 4: ARROWS --
        @app.callback(Output("fig-flechas", "figure"), Input("store", "data"))
        def fig_arrows(data):
            if not data:
                return theme.empty_figure()
            hist = data.get("hist", [])
            curr_period = data.get("periodo", "")
            if not hist:
                return theme.empty_figure("Solo hay un período cargado")

            fig = go.Figure()
            maxd = max((h["desp_km"] or 0) for h in hist) or 1
            MAX_LEN = 0.42

            for i, h in enumerate(hist):
                if h["desp_km"] is None or h["az"] is None:
                    continue
                az, km = h["az"], h["desp_km"]
                col = theme.classify_color(h["jaccard"])
                is_curr = h["periodo"] == curr_period
                rad = np.radians(az)
                mag = MAX_LEN * (0.35 + 0.65 * (km / maxd))

                dx = np.sin(rad) * mag
                dy = np.cos(rad) * mag
                x0, y0 = i - dx * 0.25, -dy * 0.25
                x1, y1 = i + dx * 0.75, dy * 0.75

                fig.add_trace(go.Scatter(
                    x=[x0, x1], y=[y0, y1], mode="lines",
                    line={"color": col, "width": 5 if is_curr else 3},
                    showlegend=False,
                    hovertemplate=f"<b>{h['periodo']}</b><br>{km:.2f} km · {h['dir']}<extra></extra>",
                ))
                fig.add_trace(go.Scatter(
                    x=[x1], y=[y1], mode="markers",
                    marker={"size": 14 if is_curr else 10, "color": col,
                            "symbol": "arrow", "angle": az,
                            "line": {"color": "white", "width": 1.5}},
                    showlegend=False, hoverinfo="skip",
                ))
                fig.add_annotation(
                    x=i, y=-0.68, text=h["periodo"].split()[0][:3],
                    showarrow=False, font={"size": 10, "color": theme.text2},
                )
                fig.add_annotation(
                    x=i, y=0.62, text=f"{km:.2f} km",
                    showarrow=False, font={"size": 10, "color": col},
                )

            for lbl, clr in [
                ("Estable", theme.success), ("Parcial", theme.warning),
                ("Significativo", theme.danger),
            ]:
                fig.add_trace(go.Scatter(
                    x=[None], y=[None], mode="markers",
                    marker={"size": 8, "color": clr, "symbol": "square"},
                    name=lbl, showlegend=True,
                ))

            fig.update_layout(
                theme.plot_base({"l": 20, "r": 20, "t": 16, "b": 52}),
                xaxis={"visible": False, "range": [-0.8, len(hist) - 0.2]},
                yaxis={"visible": False, "range": [-0.85, 0.85]},
                legend={
                    "orientation": "h", "x": 0.5, "xanchor": "center", "y": -0.2,
                    "font": {"size": 10, "color": theme.text2},
                    "bgcolor": "rgba(0,0,0,0)",
                },
                showlegend=True,
            )
            return fig

        # -- VIZ 5: TABLE --
        @app.callback(Output("tabla-cuerpo", "children"), Input("store", "data"))
        def table(data):
            if not data:
                return html.Div("Sin datos.", style={"color": theme.text2, "fontSize": "12px"})

            hist = data.get("hist", [])
            curr_period = data.get("periodo", "")

            cols = ["Período", "Hechos", "Desplaz.", "Dirección", "Jaccard", "Clasificación", "Var. área"]
            rows = [html.Tr([html.Th(c, className="th-cell") for c in cols])]

            if store.periods:
                fen = data.get("fenomeno", "")
                n0 = len(store.filter_by(phenomenon=fen, period=store.periods[0]))
                rows.append(html.Tr([
                    html.Td(store.periods[0], className="td-per"),
                    html.Td(str(n0), className="td-num"),
                    html.Td("—", className="td-num"),
                    html.Td("—", className="td-cen"),
                    html.Td("—", className="td-num"),
                    html.Td("—"),
                    html.Td("—", className="td-num"),
                ], className="tr-base"))

            for h in hist:
                j, a = h["jaccard"], h["var_area"]
                is_curr = h["periodo"] == curr_period
                rows.append(html.Tr([
                    html.Td(h["periodo"], className="td-per" + (" td-act" if is_curr else "")),
                    html.Td(str(h["n"]), className="td-num"),
                    html.Td(f"{h['desp_km']:.2f} km" if h["desp_km"] else "—", className="td-num"),
                    html.Td(h["dir"] or "—", className="td-cen"),
                    html.Td(f"{round(j * 100)}%" if j is not None else "—", className="td-num"),
                    html.Td(html.Span(
                        theme.classify_label(j),
                        style={
                            "background": theme.classify_bg(j),
                            "color": theme.classify_color(j),
                            "padding": "2px 7px", "borderRadius": "4px",
                            "fontSize": "10px", "fontWeight": "500",
                        },
                    )),
                    html.Td(
                        f"{'+'if a and a > 0 else''}{a}%" if a is not None else "—",
                        className="td-num",
                        style={
                            "color": theme.success if a and a > 0
                                     else theme.danger if a and a < 0
                                     else theme.text2,
                        },
                    ),
                ], className="tr-act" if is_curr else "tr-base"))

            return html.Table(rows, className="comp-table")

        # -- CSV EXPORT --
        @app.callback(
            Output("dl-csv", "data"),
            Input("btn-export", "n_clicks"),
            Input("store", "data"),
            prevent_initial_call=True,
        )
        def export_csv(n_clicks, data):
            if ctx.triggered_id != "btn-export" or not data:
                raise PreventUpdate
            hist = data.get("hist", [])
            if not hist:
                raise PreventUpdate
            df_e = pd.DataFrame(hist)
            df_e.columns = ["Período", "Hechos", "Desp_km", "Dirección", "Azimut", "Jaccard", "Var_area_%"]
            return dcc.send_data_frame(df_e.to_csv, "desplazamiento_mensual.csv", index=False)

        # -- COMUNA INFO --
        @app.callback(
            Output("info-comuna", "children"),
            Input("store", "data"),
            Input("dd-comuna", "value"),
        )
        def comuna_info(data, comuna):
            if not data or not comuna or comuna == "Todas":
                return ""
            counts = data.get("conteo_comunas", {})
            n_com = counts.get(comuna, 0)
            n_tot = data.get("n", 0)
            pct = round(100 * n_com / n_tot, 1) if n_tot > 0 else 0
            return html.Div([
                html.Span(
                    f"{n_com} hechos en {comuna}",
                    style={"fontWeight": "500", "color": "var(--accent)"},
                ),
                html.Span(
                    f" ({pct}% del total del período)",
                    style={"fontSize": "10px", "color": "var(--text2)"},
                ),
            ], style={"marginTop": "4px", "fontSize": "11px"})

    # -- Layout helpers ------------------------------------------------------

    def _sidebar_layout(self) -> html.Div:
        s = self._store
        return html.Div(className="sidebar", children=[
            html.Div(className="control-section", children=[
                html.Label("Tipo penal", className="control-label"),
                dcc.Dropdown(id="dd-fen",
                    options=[{"label": f, "value": f} for f in s.phenomena],
                    value=s.phenomena[0] if s.phenomena else None,
                    clearable=False, className="dropdown"),
            ]),
            html.Div(className="control-section", children=[
                html.Label("Período", className="control-label"),
                dcc.Dropdown(id="dd-per",
                    options=[{"label": p, "value": p} for p in s.periods],
                    value=s.periods[-1] if s.periods else None,
                    clearable=False, className="dropdown"),
            ]),
            html.Div(className="control-section", children=[
                html.Label("Filtrar por comuna", className="control-label"),
                dcc.Dropdown(id="dd-comuna",
                    options=[{"label": c, "value": c} for c in s.comunas],
                    value="Todas", clearable=False, className="dropdown"),
                html.Div(id="info-comuna", className="comuna-info"),
            ]),
            html.Div(className="control-section", children=[
                html.Label("Capas del mapa", className="control-label"),
                dcc.Checklist(id="chk-capas",
                    options=[
                        {"label": " Comunas (coroplético)", "value": "comunas"},
                        {"label": " Puntos", "value": "puntos"},
                        {"label": " KDE (densidad)", "value": "kde"},
                        {"label": " Elipse actual", "value": "elipse_act"},
                        {"label": " Elipse anterior", "value": "elipse_ant"},
                        {"label": " Trayectoria", "value": "trayectoria"},
                    ],
                    value=["comunas", "puntos", "elipse_act"],
                    className="checklist",
                    inputClassName="checklist-input",
                    labelClassName="checklist-label",
                ),
            ]),
            html.Div(className="control-section", children=[
                html.Label("Opacidad elipse", className="control-label"),
                dcc.Slider(id="sl-op", min=0.1, max=1.0, step=0.1, value=0.5,
                           marks={0.1: "10%", 0.5: "50%", 1.0: "100%"},
                           className="slider"),
            ]),
            html.Div(id="alerta-n", className="alerta", style={"display": "none"}),
            html.Div(className="metrics-panel", children=[
                html.Div("Métricas del período", className="metric-title"),
                *[html.Div(className="metric-row", children=[
                    html.Span(lbl, className="metric-label"),
                    html.Span(id=mid, className="metric-value"),
                ]) for lbl, mid in [
                    ("Hechos", "mt-n"), ("Desplazamiento", "mt-desp"),
                    ("Dirección", "mt-dir"), ("Solapamiento", "mt-solap"),
                    ("Clasificación", "mt-clasif"), ("Variación área", "mt-area"),
                ]],
            ]),
        ])

    def _chart_panel_layout(self) -> html.Div:
        return html.Div(className="chart-panel", children=[
            html.Div(className="viz-tabs", children=[
                html.Button("Rosa", id="tab-rosa", className="viz-tab active", n_clicks=0),
                html.Button("Tendencia", id="tab-linea", className="viz-tab", n_clicks=0),
                html.Button("Narrativa", id="tab-narr", className="viz-tab", n_clicks=0),
                html.Button("Flechas", id="tab-flechas", className="viz-tab", n_clicks=0),
                html.Button("Tabla", id="tab-tabla", className="viz-tab", n_clicks=0),
            ]),
            html.Div(id="viz-rosa", children=[
                html.Div("Dirección del desplazamiento", className="chart-title"),
                dcc.Graph(id="fig-rosa", config={"displayModeBar": False}, style={"height": "270px"}),
                html.Div("Período actual vs anterior", className="chart-sub"),
            ]),
            html.Div(id="viz-linea", style={"display": "none"}, children=[
                html.Div("Tendencia del desplazamiento (km)", className="chart-title"),
                dcc.Graph(id="fig-linea", config={"displayModeBar": False}, style={"height": "195px"}),
                html.Div("Frecuencia mensual", className="chart-title", style={"marginTop": "6px"}),
                dcc.Graph(id="fig-serie", config={"displayModeBar": False}, style={"height": "155px"}),
            ]),
            html.Div(id="viz-narr", style={"display": "none"}, children=[
                html.Div("Síntesis automática", className="chart-title"),
                html.Div(id="narr-cuerpo", className="narr-box"),
                html.Div("Distribución por tipo · período", className="chart-title",
                         style={"marginTop": "10px"}),
                dcc.Graph(id="fig-tipos", config={"displayModeBar": False}, style={"height": "195px"}),
            ]),
            html.Div(id="viz-flechas", style={"display": "none"}, children=[
                html.Div("Desplazamiento mensual completo", className="chart-title"),
                dcc.Graph(id="fig-flechas", config={"displayModeBar": False}, style={"height": "250px"}),
                html.Div("Verde = estable · Ámbar = parcial · Rojo = significativo",
                         className="chart-sub"),
            ]),
            html.Div(id="viz-tabla", style={"display": "none"}, children=[
                html.Div("Comparativa mensual", className="chart-title"),
                html.Div(id="tabla-cuerpo", className="tabla-wrap"),
                html.Button("Exportar CSV", id="btn-export", className="export-btn", n_clicks=0),
                dcc.Download(id="dl-csv"),
            ]),
        ])
