"""ARIA v2 — Criminal Intelligence Platform — Entry Point."""

import logging
import os
import sys

from dash import Dash, Input, Output, ctx, dcc, html
from dash.exceptions import PreventUpdate

sys.path.insert(0, os.path.dirname(__file__))

from aria.config import AppConfig
from aria.theme import Theme
from aria.data.loader import DataLoader
from aria.data.store import DataStore
from aria.analysis.spatial import SpatialAnalyzer
from aria.analysis.advanced import AdvancedAnalyzer
from aria.services.claude_api import ClaudeApiClient
from aria.modules.overview import OverviewModule, NavItem
from aria.modules.mobility import MobilityModule
from aria.modules.emerging import EmergingModule
from aria.modules.advanced_analysis import AdvancedAnalysisModule
from aria.modules.case_grouper import CaseGrouperModule
from aria.modules.policy_brief import PolicyBriefModule
from aria.modules.placeholder import PlaceholderModule, MODULE_CONFIGS

logging.basicConfig(level=logging.INFO, format="[aria] %(levelname)s: %(message)s")

# ── Bootstrap ──────────────────────────────────────────────────────────────────
config = AppConfig()
theme = Theme()
loader = DataLoader(config)
df = loader.load_all()
store = DataStore.create(df, config.geojson_path)

analyzer = SpatialAnalyzer(config)
advanced = AdvancedAnalyzer()
claude = ClaudeApiClient()

# ── Navigation definition ──────────────────────────────────────────────────────
NAV_MODULES = [
    NavItem("resumen",    "Panorama",             "inicio",   theme.amber,   None),
    NavItem("movilidad",  "Movilidad delictual",  "analisis", theme.success, "activo"),
    NavItem("emergentes", "Detección emergentes", "analisis", theme.warning, "activo"),
    NavItem("avanzado",   "Análisis avanzado",    "analisis", theme.info,    "activo"),
    NavItem("agrupador",  "Agrupador de casos",   "aria",     theme.info,    "activo"),
    NavItem("policy",     "Policy Brief · IA",    "aria",     theme.amber,   "activo"),
    NavItem("vehiculos",  "Robo de vehículos",    "aria",     "#7c5cfc",     "pronto"),
    NavItem("residual",   "Info. residual",       "aria",     theme.warning, "pronto"),
    NavItem("trayecto",   "Delitos de trayecto",  "aria",     "#f75fc8",     "pronto"),
    NavItem("mapa_nico",  "Mapa sociodelictual",  "aria",     "#cc4fcc",     "pronto"),
]
NAV_IDS = [n.id for n in NAV_MODULES]

# ── Module registry ────────────────────────────────────────────────────────────
modules = {
    "resumen":    OverviewModule(store, theme, analyzer, NAV_MODULES),
    "movilidad":  MobilityModule(store, theme, analyzer, config),
    "emergentes": EmergingModule(store, theme),
    "avanzado":   AdvancedAnalysisModule(store, theme, advanced),
    "agrupador":  CaseGrouperModule(store, theme, claude),
    "policy":     PolicyBriefModule(store, theme, claude),
}
for pid in MODULE_CONFIGS:
    modules[pid] = PlaceholderModule(store, theme, pid)

# ── Dash app ───────────────────────────────────────────────────────────────────
app = Dash(
    __name__,
    title="ARIA · Inteligencia Criminal",
    suppress_callback_exceptions=True,
)


def _nav_item(nav: NavItem, is_active: bool) -> html.Div:
    bs = theme.badge_style(nav.badge or "pronto")
    return html.Div(
        id=f"nav-{nav.id}", n_clicks=0,
        className="nav-item" + (" nav-active" if is_active else ""),
        children=[
            html.Div(className="nav-icon",
                     style={"borderColor": nav.color if is_active else theme.border}),
            html.Span(nav.label, className="nav-text"),
            html.Span(nav.badge, className="nav-badge", style=bs) if nav.badge else None,
        ],
    )


def _sidebar() -> html.Div:
    items: list = []
    current_group = None
    group_labels = {
        "inicio": "Inicio", "analisis": "Análisis",
        "productos": "Productos", "aria": "ARIA avanzado", "sistema": "Sistema",
    }
    for nav in NAV_MODULES:
        if nav.group != current_group:
            if current_group:
                items.append(html.Div(className="sidebar-divider"))
            items.append(html.Div(
                group_labels.get(nav.group, nav.group), className="sidebar-label",
            ))
            current_group = nav.group
        items.append(_nav_item(nav, nav.id == "resumen"))
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
                html.Span(f"{store.record_count:,} registros · {store.period_count} períodos"),
            ]),
            html.Span("|", style={"color": theme.border, "margin": "0 6px"}),
            html.Span("Región Metropolitana", className="topbar-meta"),
        ]),
    ]),
    html.Div(className="shell-body", children=[
        _sidebar(),
        html.Div(id="page-content", className="page-content"),
    ]),
    html.Div(className="bottombar", children=[
        html.Span("datos 100% locales · ningún registro sale de esta máquina",
                   className="bottom-text"),
        html.Span("Ley 19.628 · uso institucional interno", className="bottom-text"),
    ]),
    dcc.Store(id="store"),
    dcc.Store(id="active-module", data="resumen"),
])

# ── Navigation callbacks ──────────────────────────────────────────────────────


@app.callback(
    Output("active-module", "data"),
    [Input(f"nav-{mid}", "n_clicks") for mid in NAV_IDS],
    prevent_initial_call=True,
)
def change_module(*_):
    t = ctx.triggered_id
    if not t:
        raise PreventUpdate
    return t.replace("nav-", "")


@app.callback(
    *[Output(f"nav-{mid}", "className") for mid in NAV_IDS],
    Input("active-module", "data"),
)
def update_nav_classes(active):
    return [
        "nav-item nav-active" if mid == active else "nav-item"
        for mid in NAV_IDS
    ]


@app.callback(
    Output("page-content", "children"),
    Input("active-module", "data"),
)
def render_page(module_id):
    module = modules.get(module_id)
    if module:
        return module.get_layout()
    return html.Div("Módulo no disponible.", style={"padding": "2rem", "color": theme.text3})


@app.callback(
    Output("active-module", "data", allow_duplicate=True),
    [Input(f"modcard-{mid}", "n_clicks") for mid in NAV_IDS],
    prevent_initial_call=True,
)
def click_card(*_):
    t = ctx.triggered_id
    if not t:
        raise PreventUpdate
    mid = t.replace("modcard-", "")
    nav = next((n for n in NAV_MODULES if n.id == mid), None)
    if nav and nav.badge == "pronto":
        raise PreventUpdate
    return mid


# ── Register all module callbacks ──────────────────────────────────────────────
for mod in modules.values():
    mod.register_callbacks(app)

# ── Entry point ────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    print("\n" + "─" * 60)
    print("  ARIA v2.0 · Plataforma de Inteligencia Criminal")
    print(f"  {store.record_count:,} registros · {store.period_count} períodos · {store.comuna_count} comunas")
    print("─" * 60 + "\n  http://localhost:8050\n")
    app.run(debug=False, host="127.0.0.1", port=8050)
