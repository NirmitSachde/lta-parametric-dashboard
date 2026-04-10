"""
Parametric Design Dashboard - Multi-Page Application
=====================================================
LTA Vehicle with Rotational Spherical Lifting Structure

Pages:
    1. Dashboard   - Interactive gauges and sliders
    2. Materials   - Aerospace material comparison
    3. Sensitivity - Tornado chart, trade-off contours
    4. Power Model - Onboard power consumption model

Author: Nirmit Sachde, Northeastern University
Mentor: David W. Clark, P.E.
"""

import os
import dash
from dash import dcc, html, Input, Output, State, callback, ALL, ctx
import plotly.graph_objects as go
import numpy as np

from engine.buoyancy_calculator import (
    compute_buoyancy, BuoyancyResult, STANDARD_ATM_PRESSURE,
    convert_value, convert_input_to_si, UNIT_CONVERSIONS,
)
from engine.materials_db import (
    MATERIALS, MATERIAL_LOOKUP, MATERIAL_CATEGORIES, evaluate_material,
)
from engine.sensitivity import (
    compute_tornado, compute_tradeoff_grid, compute_feasibility_boundary,
)
from visualization.gauges import (
    build_lift_force_gauge, build_weight_force_gauge, build_net_force_gauge,
    build_brs_gauge, build_mass_available_gauge, build_buoyancy_state_indicator,
    STATE_COLORS, C_TEXT, C_TEXT_DIM, C_GREEN, C_AMBER, C_RED, C_CYAN, FONT_FAMILY,
    TRANSPARENT,
)
from pages import materials as materials_page
from pages import sensitivity as sensitivity_page
from pages.power_page import layout as power_layout
from pages.power_page import register_callbacks as register_power_callbacks
from visualization.sphere_animation import build_3d_scene

import dash_bootstrap_components as dbc

dbc_css = "https://cdn.jsdelivr.net/gh/AnnMarieW/dash-bootstrap-templates@V1.0.2/dbc.min.css"

app = dash.Dash(
    __name__,
    title="LTA Parametric Design Dashboard",
    update_title="Computing...",
    suppress_callback_exceptions=True,
    external_stylesheets=[dbc.themes.DARKLY, dbc_css],
    meta_tags=[{"name": "viewport", "content": "width=device-width, initial-scale=1.0"}],
)
register_power_callbacks(app)
server = app.server

# ── Constants ─────────────────────────────────────────────────────────────
PAGE_BG        = "#0B0F14"
CARD_BG        = "#111820"
CARD_BORDER    = "#1E2A38"
SECTION_BORDER = "#1A2535"
NAV_BG         = "#0E1319"

SLIDER_CONFIGS = [
    {"id": "slider-outer-radius", "label": "Outer Radius", "quantity_type": "length",
     "si_unit": "m", "imp_unit": "ft",
     "si":  {"min": 1.0,     "max": 20.0,     "step": 0.1,    "default": 5.1},
     "imp": {"min": 3.3,     "max": 65.6,     "step": 0.3,    "default": 16.7},
     "tooltip": "Outer radius of the hollow sphere", "fmt": ".1f", "tooltip_transform": "fmtRadius"},
    {"id": "slider-thickness", "label": "Shell Thickness", "quantity_type": "length",
     "si_unit": "m", "imp_unit": "ft",
     "si":  {"min": 0.0001,  "max": 0.01,     "step": 0.0001, "default": 0.0005},
     "imp": {"min": 0.0003,  "max": 0.0328,   "step": 0.0003, "default": 0.0016},
     "tooltip": "Wall thickness of sphere material", "fmt": ".4f", "tooltip_transform": "fmtThickness"},
    {"id": "slider-density", "label": "Material Density", "quantity_type": "density",
     "si_unit": "kg/m\u00b3", "imp_unit": "lb/ft\u00b3",
     "si":  {"min": 100.0,   "max": 8000.0,   "step": 50.0,   "default": 1100.0},
     "imp": {"min": 6.2,     "max": 499.4,    "step": 3.1,    "default": 68.7},
     "tooltip": "Density of sphere shell material", "fmt": ".0f", "tooltip_transform": "fmtDensity"},
    {"id": "slider-internal-pressure", "label": "Internal Pressure", "quantity_type": "pressure",
     "si_unit": "Pa", "imp_unit": "psi",
     "si":  {"min": 100.0,   "max": 100000.0, "step": 100.0,  "default": 5066.25},
     "imp": {"min": 0.015,   "max": 14.5,     "step": 0.015,  "default": 0.735},
     "tooltip": "Reduced pressure inside the rotating sphere", "fmt": ".1f", "tooltip_transform": "fmtPressure"},
    {"id": "slider-atm-pressure", "label": "Atm. Pressure", "quantity_type": "pressure",
     "si_unit": "Pa", "imp_unit": "psi",
     "si":  {"min": 80000.0, "max": 110000.0, "step": 100.0,  "default": 101325.0},
     "imp": {"min": 11.6,    "max": 15.95,    "step": 0.015,  "default": 14.696},
     "tooltip": "External atmospheric pressure", "fmt": ".1f", "tooltip_transform": "fmtPressure"},
]
SLIDER_LOOKUP = {c["id"]: c for c in SLIDER_CONFIGS}

PAGE_LOADER_LABELS = {
    "dashboard":   "Loading Dashboard...",
    "materials":   "Loading Materials...",
    "sensitivity": "Loading Sensitivity Analysis...",
    "power":       "Loading Power Model...",
}

_OVERLAY_SHOW = {
    "position": "fixed", "top": "0", "left": "0",
    "width": "100vw", "height": "100vh",
    "backgroundColor": "rgba(11,15,20,0.92)",
    "display": "flex", "alignItems": "center",
    "justifyContent": "center", "flexDirection": "column",
    "zIndex": "99998", "opacity": "1", "transition": "opacity 0.4s ease",
}


# ── dcc.Loading wrapper — the only graph loader we need ───────────────────
# Dash handles show/hide automatically. No JS, no CSS classes needed.

def loading_graph(graph_id, height=210, modebar=False, extra_graph_style=None):
    """Wrap a dcc.Graph in dcc.Loading with a circular spinner."""
    return dcc.Loading(
        type="circle",
        color="#5BA4B5",
        children=dcc.Graph(
            id=graph_id,
            figure=_empty_dark_fig(height),
            config={
                "displayModeBar": modebar,
                "modeBarButtonsToRemove": ["toImage", "sendDataToCloud"],
                "displaylogo": False,
            },
            style=extra_graph_style or {},
        ),
    )


# ── Reusable layout helpers ───────────────────────────────────────────────

def section_header(text):
    return html.H3(text, style={
        "fontSize": "13px", "color": "#7EC8DB", "letterSpacing": "2px",
        "margin": "0 0 10px 0", "paddingBottom": "6px",
        "borderBottom": f"1px solid {SECTION_BORDER}",
        "fontFamily": FONT_FAMILY, "fontWeight": "700", "textTransform": "uppercase",
    })


def make_slider_row(config):
    sid = config["id"]
    dv  = {
        "--Dash-Fill-Inverse-Strong": "#141D26", "--Dash-Text-Primary": "#E2E8F0",
        "--Dash-Text-Strong": "#FFFFFF",         "--Dash-Text-Weak": "rgba(255,255,255,0.4)",
        "--Dash-Stroke-Strong": "rgba(255,255,255,0.25)",
        "--Dash-Stroke-Weak": "rgba(255,255,255,0.12)",
        "--Dash-Fill-Interactive-Strong": "#5BA4B5",
        "--Dash-Fill-Weak": "rgba(255,255,255,0.06)",
        "--Dash-Fill-Primary-Hover": "rgba(255,255,255,0.10)",
        "--Dash-Shading-Strong": "rgba(0,0,0,0.6)",
    }
    return html.Div(style={
        "backgroundColor": CARD_BG, "border": f"1px solid {CARD_BORDER}",
        "borderRadius": "6px", "padding": "10px 14px", "marginBottom": "8px", **dv,
    }, children=[
        html.Div(style={"display": "flex", "justifyContent": "space-between",
                         "alignItems": "center", "marginBottom": "6px"}, children=[
            html.Div(style={"display": "flex", "alignItems": "baseline", "gap": "8px"}, children=[
                html.Span(config["label"], style={
                    "color": "#E2E8F0", "fontSize": "13px", "fontFamily": FONT_FAMILY,
                    "fontWeight": "700", "textTransform": "uppercase", "letterSpacing": "0.5px",
                }, title=config["tooltip"]),
                html.Span(id=f"{sid}-unit", style={
                    "color": "#7EC8DB", "fontSize": "12px", "fontFamily": FONT_FAMILY,
                    "fontWeight": "600", "backgroundColor": "#1A2535",
                    "padding": "1px 6px", "borderRadius": "3px", "border": "1px solid #263040",
                }),
            ]),
            dcc.Input(
                id=f"{sid}-input", type="number",
                value=config["si"]["default"], min=config["si"]["min"],
                max=config["si"]["max"],       step=config["si"]["step"],
                debounce=True,
                style={
                    "backgroundColor": "#0B0F14", "border": "1px solid #1E2A38",
                    "borderRadius": "4px", "padding": "4px 10px", "width": "120px",
                    "textAlign": "right", "color": "#FFFFFF", "fontSize": "13px",
                    "fontFamily": FONT_FAMILY, "fontWeight": "700", "outline": "none",
                },
            ),
        ]),
        dcc.Slider(id=sid, min=config["si"]["min"], max=config["si"]["max"],
                   step=config["si"]["step"], value=config["si"]["default"],
                   marks=None, tooltip={"placement": "bottom", "always_visible": False},
                   updatemode="mouseup"),
    ])


def readout_row(label, value, color="#FFFFFF"):
    return html.Div(style={
        "display": "flex", "justifyContent": "space-between",
        "alignItems": "center", "padding": "5px 0",
        "borderBottom": f"1px solid {CARD_BORDER}",
    }, children=[
        html.Span(label, style={"color": "#A0AEC0", "fontSize": "11px",
                   "fontFamily": FONT_FAMILY, "fontWeight": "600",
                   "textTransform": "uppercase", "letterSpacing": "0.3px"}),
        html.Span(value, style={"color": color, "fontSize": "13px",
                   "fontFamily": FONT_FAMILY, "fontWeight": "700"}),
    ])


def _empty_dark_fig(h=210):
    fig = go.Figure()
    fig.update_layout(
        paper_bgcolor=TRANSPARENT, plot_bgcolor=TRANSPARENT,
        height=h, margin=dict(l=0, r=0, t=0, b=0),
        xaxis=dict(visible=False), yaxis=dict(visible=False),
    )
    return fig


def gauge_card(graph_id):
    return html.Div(style={
        "flex": "1 1 140px", "minWidth": "140px",
        "backgroundColor": CARD_BG, "border": f"1px solid {CARD_BORDER}",
        "borderRadius": "6px", "padding": "8px",
    }, children=[
        loading_graph(graph_id, height=210),
    ])


# ── Dashboard layout ──────────────────────────────────────────────────────

def dashboard_layout():
    dv = {
        "--Dash-Fill-Inverse-Strong": "#141D26", "--Dash-Text-Primary": "#E2E8F0",
        "--Dash-Text-Strong": "#FFFFFF",         "--Dash-Text-Weak": "rgba(255,255,255,0.4)",
        "--Dash-Stroke-Strong": "rgba(255,255,255,0.25)",
        "--Dash-Stroke-Weak": "rgba(255,255,255,0.12)",
        "--Dash-Fill-Interactive-Strong": "#5BA4B5",
        "--Dash-Fill-Weak": "rgba(255,255,255,0.06)",
        "--Dash-Fill-Primary-Hover": "rgba(255,255,255,0.10)",
        "--Dash-Shading-Strong": "rgba(0,0,0,0.6)",
    }
    return html.Div([
        html.Div(style={"display": "flex", "justifyContent": "flex-end",
                         "alignItems": "center", "gap": "10px",
                         "marginBottom": "14px", "flexWrap": "wrap"}, children=[
            html.Span("UNIT SYSTEM", style={"color": "#A0AEC0", "fontSize": "11px",
                       "fontFamily": FONT_FAMILY, "fontWeight": "600", "letterSpacing": "1px"}),
            html.Div(style={"width": "240px", "minWidth": "200px", **dv}, children=[
                dcc.Dropdown(id="unit-system-toggle", options=[
                    {"label": "SI  (m, kg, N, Pa)",          "value": "SI"},
                    {"label": "Imperial  (ft, lb, lbf, psi)","value": "Imperial"},
                ], value="SI", clearable=False, searchable=False),
            ]),
        ]),

        html.Div(style={"display": "flex", "gap": "16px", "flexWrap": "wrap"}, children=[
            # LEFT
            html.Div(style={"flex": "1 1 320px", "minWidth": "0"}, children=[
                section_header("Input Parameters"),
                *[make_slider_row(c) for c in SLIDER_CONFIGS],
                html.Div(style={"marginTop": "14px"}),
                section_header("Computed Values"),
                html.Div(id="computed-values-panel", style={
                    "backgroundColor": CARD_BG, "border": f"1px solid {CARD_BORDER}",
                    "borderRadius": "6px", "padding": "12px 14px",
                }),
            ]),
            # RIGHT
            html.Div(style={"flex": "2 1 400px", "minWidth": "0"}, children=[
                section_header("Instrument Panel"),
                html.Div(style={"display": "flex", "gap": "10px",
                                 "marginBottom": "10px", "flexWrap": "wrap"}, children=[
                    gauge_card("gauge-lift"),
                    gauge_card("gauge-weight"),
                    gauge_card("gauge-net"),
                ]),
                html.Div(style={"display": "flex", "gap": "10px", "flexWrap": "wrap"}, children=[
                    gauge_card("gauge-brs"),
                    gauge_card("gauge-mass-available"),
                    gauge_card("gauge-buoyancy-state"),
                ]),
                html.Div(style={"marginTop": "12px"}, children=[
                    html.Div(style={"display": "flex", "justifyContent": "space-between",
                                     "alignItems": "center", "marginBottom": "8px"}, children=[
                        section_header("3D ConOps Visualization"),
                        html.Div(style={"display": "flex", "gap": "8px",
                                         "alignItems": "center", **dv}, children=[
                            html.Span("MESH:", style={"color": C_TEXT_DIM, "fontSize": "10px",
                                       "fontFamily": FONT_FAMILY, "fontWeight": "600"}),
                            dcc.Dropdown(
                                id="mesh-quality-toggle",
                                options=[
                                    {"label": "Full Detail (slower)", "value": "full"},
                                    {"label": "Performance (faster)", "value": "light"},
                                ],
                                value="full",
                                clearable=False, searchable=False,
                                style={"width": "180px", "fontSize": "11px"},
                            ),
                        ]),
                    ]),
                    html.Div(style={
                        "backgroundColor": CARD_BG, "border": f"1px solid {CARD_BORDER}",
                        "borderRadius": "6px", "padding": "8px",
                    }, children=[
                        loading_graph("conops-3d-view", height=400, modebar=True),
                    ]),
                    html.P(
                        "VCA Body Shell with magnetic induction landing plate. "
                        "Shell position responds to buoyancy state. Design gap: 0.40m. "
                        "Click legend items to toggle Landing Plate and Magnetic Coil.",
                        style={"color": C_TEXT_DIM, "fontSize": "10px",
                               "fontFamily": FONT_FAMILY, "marginTop": "6px",
                               "textAlign": "center"},
                    ),
                ]),
            ]),
        ]),
    ])


# ── Navbar ────────────────────────────────────────────────────────────────

def make_nav_btn(label, page_id):
    return html.Button(label, id={"type": "nav-btn", "page": page_id}, n_clicks=0, style={
        "backgroundColor": "transparent", "color": C_TEXT_DIM,
        "border": "none", "padding": "10px 18px", "cursor": "pointer",
        "fontSize": "12px", "fontFamily": FONT_FAMILY, "fontWeight": "600",
        "letterSpacing": "1.5px", "textTransform": "uppercase",
        "borderBottom": "2px solid transparent", "transition": "all 0.2s",
    })


# ── Main layout ───────────────────────────────────────────────────────────

app.layout = html.Div(style={
    "backgroundColor": PAGE_BG, "color": C_TEXT,
    "fontFamily": FONT_FAMILY, "minHeight": "100vh", "padding": "0",
}, className="dbc", children=[

    dcc.Store(id="shared-density-store", data=None),
    dcc.Store(id="current-page-store",   data="dashboard"),

    html.Div(style={
        "backgroundColor": NAV_BG, "borderBottom": f"1px solid {SECTION_BORDER}",
        "padding": "12px 16px 0 16px",
    }, children=[
        html.H1("PARAMETRIC DESIGN DASHBOARD", style={
            "fontSize": "16px", "fontWeight": "600", "letterSpacing": "4px",
            "margin": "0 0 4px 0", "color": C_TEXT, "fontFamily": FONT_FAMILY,
        }),
        html.P("LTA Vehicle  \u00b7  Rotational Spherical Lifting Structure", style={
            "fontSize": "10px", "color": C_TEXT_DIM, "margin": "0 0 10px 0",
            "letterSpacing": "1.5px",
        }),
        html.Div(style={"display": "flex", "gap": "4px", "flexWrap": "wrap"}, children=[
            make_nav_btn("Dashboard",   "dashboard"),
            make_nav_btn("Materials",   "materials"),
            make_nav_btn("Sensitivity", "sensitivity"),
            make_nav_btn("Power Model", "power"),
        ]),
    ]),

    # Page-level overlay (only for navigation transitions)
    html.Div(id="app-loader-overlay", style=_OVERLAY_SHOW, children=[
        html.Div(style={
            "width": "40px", "height": "40px", "border": "3px solid #1E2A38",
            "borderTop": "3px solid #5BA4B5", "borderRadius": "50%",
            "animation": "spin 0.8s linear infinite", "marginBottom": "16px",
        }),
        html.Span(id="loader-label", children="Loading Dashboard...", style={
            "color": "#5BA4B5", "fontSize": "13px", "fontFamily": FONT_FAMILY,
            "letterSpacing": "2px", "fontWeight": "600",
        }),
    ]),

    html.Div(id="page-content", style={"padding": "16px"}),

    html.Div(style={
        "textAlign": "center", "padding": "12px 0", "marginTop": "16px",
        "borderTop": f"1px solid {SECTION_BORDER}", "color": "#4A5568",
        "fontSize": "10px", "fontFamily": FONT_FAMILY,
    }, children=[
        html.Span("Nirmit Sachde  \u00b7  Northeastern University  \u00b7  Mentor: David W. Clark, P.E."),
    ]),
])


# ── Navigation ────────────────────────────────────────────────────────────

PAGE_IDS = ["dashboard", "materials", "sensitivity", "power"]

def _nav_styles(active_page):
    out = []
    for pid in PAGE_IDS:
        if pid == active_page:
            out.append({
                "backgroundColor": "#1A2535", "color": "#7EC8DB",
                "border": "none", "padding": "10px 18px", "cursor": "pointer",
                "fontSize": "12px", "fontFamily": FONT_FAMILY, "fontWeight": "700",
                "letterSpacing": "1.5px", "textTransform": "uppercase",
                "borderBottom": "2px solid #5BA4B5", "borderRadius": "4px 4px 0 0",
                "transition": "all 0.2s",
            })
        else:
            out.append({
                "backgroundColor": "transparent", "color": C_TEXT_DIM,
                "border": "none", "padding": "10px 18px", "cursor": "pointer",
                "fontSize": "12px", "fontFamily": FONT_FAMILY, "fontWeight": "600",
                "letterSpacing": "1.5px", "textTransform": "uppercase",
                "borderBottom": "2px solid transparent", "transition": "all 0.2s",
            })
    return out


@callback(
    Output("page-content",                   "children"),
    Output("current-page-store",             "data"),
    Output({"type": "nav-btn", "page": ALL}, "style"),
    Output("loader-label",                   "children"),
    Input({"type": "nav-btn", "page": ALL},  "n_clicks"),
    State("current-page-store",              "data"),
    prevent_initial_call=False,
)
def navigate(n_clicks_list, current_page):
    triggered = ctx.triggered_id
    page  = triggered["page"] if (triggered and isinstance(triggered, dict)) else (current_page or "dashboard")
    label = PAGE_LOADER_LABELS.get(page, "Loading...")
    if page == "materials":
        return materials_page.layout(), page, _nav_styles(page), label
    elif page == "sensitivity":
        return sensitivity_page.layout(), page, _nav_styles(page), label
    elif page == "power":
        return power_layout, page, _nav_styles(page), label
    else:
        return dashboard_layout(), page, _nav_styles(page), label


# ── Dashboard callbacks ───────────────────────────────────────────────────

for cfg in SLIDER_CONFIGS:
    @callback(
        Output(cfg["id"], "value", allow_duplicate=True),
        Input(f"{cfg['id']}-input", "value"),
        prevent_initial_call=True,
    )
    def _input_to_slider(v, _c=cfg):
        return dash.no_update if v is None else max(_c["si"]["min"], min(_c["si"]["max"], v))

    @callback(Output(f"{cfg['id']}-input", "value"), Input(cfg["id"], "value"))
    def _slider_to_input(v):
        return dash.no_update if v is None else v

for cfg in SLIDER_CONFIGS:
    @callback(Output(f"{cfg['id']}-unit", "children"), Input("unit-system-toggle", "value"))
    def _su(us, si_u=cfg["si_unit"], imp_u=cfg["imp_unit"]):
        return imp_u if us == "Imperial" else si_u

for cfg in SLIDER_CONFIGS:
    @callback(
        Output(cfg["id"], "value"),        Output(cfg["id"], "min"),
        Output(cfg["id"], "max"),          Output(cfg["id"], "step"),
        Output(f"{cfg['id']}-input", "value", allow_duplicate=True),
        Output(f"{cfg['id']}-input", "min"),
        Output(f"{cfg['id']}-input", "max"),
        Output(f"{cfg['id']}-input", "step"),
        Input("unit-system-toggle", "value"), Input(cfg["id"], "value"),
        prevent_initial_call=True,
    )
    def _sr(us, cur, _c=cfg):
        sk  = "imp" if us == "Imperial" else "si"
        mn, mx, st = _c[sk]["min"], _c[sk]["max"], _c[sk]["step"]
        if ctx.triggered_id == "unit-system-toggle":
            f   = UNIT_CONVERSIONS[_c["quantity_type"]]["Imperial"]["factor"]
            val = max(mn, min(mx, cur * f if us == "Imperial" else cur / f))
        else:
            val = cur
        return val, mn, mx, st, val, mn, mx, st


@callback(
    Output("gauge-lift",            "figure"),
    Output("gauge-weight",          "figure"),
    Output("gauge-net",             "figure"),
    Output("gauge-brs",             "figure"),
    Output("gauge-mass-available",  "figure"),
    Output("gauge-buoyancy-state",  "figure"),
    Output("computed-values-panel", "children"),
    Output("conops-3d-view",        "figure"),
    Input("slider-outer-radius",     "value"),
    Input("slider-thickness",        "value"),
    Input("slider-density",          "value"),
    Input("slider-internal-pressure","value"),
    Input("slider-atm-pressure",     "value"),
    Input("unit-system-toggle",      "value"),
    Input("mesh-quality-toggle",     "value"),
)
def update_dashboard(R, t, rho, p_in, p_atm, us, mesh):
    us = us or "SI"
    if us == "Imperial":
        R    = convert_input_to_si(R,    "length",   "Imperial")
        t    = convert_input_to_si(t,    "length",   "Imperial")
        rho  = convert_input_to_si(rho,  "density",  "Imperial")
        p_in = convert_input_to_si(p_in, "pressure", "Imperial")
        p_atm= convert_input_to_si(p_atm,"pressure", "Imperial")
    if p_in >= p_atm: p_in = p_atm - 100.0
    if t    >= R:     t    = R * 0.01

    try:
        res = compute_buoyancy(R, t, rho, p_in, p_atm)
    except (ValueError, ZeroDivisionError) as e:
        emp = _empty_dark_fig()
        return emp,emp,emp,emp,emp,emp, html.Div(f"Error: {e}", style={"color":C_RED,"fontSize":"11px"}), emp

    lv, fu = convert_value(res.lift_force_N,      "force", us)
    wv, _  = convert_value(res.weight_force_N,    "force", us)
    nv, _  = convert_value(res.net_force_N,       "force", us)
    mv, mu = convert_value(res.mass_available_kg, "mass",  us)

    fmax = max(abs(lv), abs(wv), 10.0) * 1.5
    bmax = max(res.balanced_rotational_speed_rpm, 500.0) * 1.5
    mmax = max(abs(mv), 10.0) * 1.5

    gl = build_lift_force_gauge(lv, fmax)
    gw = build_weight_force_gauge(wv, fmax)
    gn = build_net_force_gauge(nv, fmax)
    gb = build_brs_gauge(res.balanced_rotational_speed_rpm, bmax)
    gm = build_mass_available_gauge(mv, mmax)
    gs = build_buoyancy_state_indicator(res.buoyancy_state)
    for fig, suf in [(gl,f" {fu}"),(gw,f" {fu}"),(gn,f" {fu}"),(gm,f" {mu}")]:
        fig.data[0].number.suffix = suf

    sc = STATE_COLORS.get(res.buoyancy_state, C_TEXT)
    ri,  lu  = convert_value(res.geometry.inner_radius_m,         "length", us)
    ra,  au  = convert_value(res.geometry.surface_area_m2,        "area",   us)
    rv,  vu  = convert_value(res.geometry.interior_void_volume_m3, "volume", us)
    rsv, _   = convert_value(res.geometry.shell_volume_m3,         "volume", us)
    rm,  mmu = convert_value(res.sphere_mass_kg,                   "mass",   us)
    rd,  _   = convert_value(res.displaced_air_mass_kg,            "mass",   us)
    rav, _   = convert_value(res.mass_available_kg,                "mass",   us)

    panel = html.Div([
        readout_row("Inner Radius",       f"{ri:.4f} {lu}"),
        readout_row("Surface Area",       f"{ra:.2f} {au}"),
        readout_row("Interior Volume",    f"{rv:.2f} {vu}"),
        readout_row("Shell Volume",       f"{rsv:.6f} {vu}"),
        readout_row("Sphere Mass",        f"{rm:.3f} {mmu}"),
        readout_row("Displaced Air Mass", f"{rd:.3f} {mmu}"),
        readout_row("Mass Available",     f"{rav:.3f} {mmu}", color=sc),
        readout_row("BRS (rad/s)",        f"{res.balanced_rotational_speed_rad_s:.2f}"),
        readout_row("BRS (RPM)",          f"{res.balanced_rotational_speed_rpm:.0f}"),
        html.Div(style={"display":"flex","justifyContent":"space-between","padding":"8px 0 2px 0"},
                 children=[
            html.Span("BUOYANCY", style={"color":"#A0AEC0","fontSize":"11px",
                       "fontFamily":FONT_FAMILY,"fontWeight":"600"}),
            html.Span(res.buoyancy_state.upper(), style={"color":sc,"fontSize":"13px",
                       "fontWeight":"700","fontFamily":FONT_FAMILY,"letterSpacing":"1px"}),
        ]),
    ])

    fig3d = build_3d_scene(res.buoyancy_state, res.net_force_N, quality=mesh or "full")
    return gl, gw, gn, gb, gm, gs, panel, fig3d


# ── Materials callbacks ───────────────────────────────────────────────────

CH_TEAL   = "#3D8B8B"
CH_CORAL  = "#8B5A5A"
CH_SAND   = "#8B7D5A"
CH_BLUE   = "#4A7A9B"
CH_PURPLE = "#7A6A9B"


@callback(
    Output("materials-table-container",  "children"),
    Output("material-feasibility-chart", "figure"),
    Input("material-category-filter",    "value"),
    Input("material-chart-selector",     "value"),
)
def update_materials_page(category, chart_type):
    r, t, p_int, p_atm = 5.1, 0.0005, 5066.25, 101325.0
    mats  = MATERIALS if category == "all" else [m for m in MATERIALS if m.category == category]
    evals = [evaluate_material(m, r, t, p_int, p_atm) for m in mats]

    header = html.Thead(html.Tr([
        html.Th(h, style={"padding":"10px 6px","color":"#7EC8DB","fontSize":"10px",
                 "fontWeight":"700","textTransform":"uppercase","letterSpacing":"0.5px",
                 "borderBottom":f"2px solid {CARD_BORDER}","textAlign":a,"fontFamily":FONT_FAMILY})
        for h,a in [("Material","left"),("Type","left"),("Density","right"),
                    ("Avail Mass","right"),("BRS RPM","right"),("Stress MPa","right"),
                    ("Safety","right"),("Status","center"),("","center")]
    ]))
    rows  = [materials_page.make_material_row(e["material"], e) for e in evals]
    table = html.Table([header, html.Tbody(rows)],
                       style={"width":"100%","borderCollapse":"collapse","fontFamily":FONT_FAMILY})

    fig    = go.Figure()
    names  = [e["material"].name     for e in evals]
    masses = [e["mass_available_kg"] for e in evals]

    if chart_type == "bubble":
        densities = [e["material"].density_kg_m3 for e in evals]
        sfs       = [min(e["safety_factor"], 50)  for e in evals]
        feasible  = [e["feasible_overall"]         for e in evals]
        colors    = [CH_TEAL if f else CH_CORAL    for f in feasible]
        fig.add_trace(go.Scatter(
            x=densities, y=masses, mode="markers+text",
            marker=dict(size=[max(s*2,8) for s in sfs], color=colors, opacity=0.7,
                        line=dict(width=1, color="rgba(255,255,255,0.2)")),
            text=names, textposition="top center",
            textfont=dict(size=8, color=C_TEXT_DIM),
            hovertemplate="<b>%{text}</b><br>Density: %{x:.0f} kg/m\u00b3<br>Available Mass: %{y:.1f} kg<extra></extra>",
        ))
        fig.add_hline(y=0, line_dash="dot", line_color=CH_SAND, line_width=1,
                      annotation_text="Buoyancy threshold",
                      annotation_font=dict(size=9, color=CH_SAND))
        fig.update_layout(
            xaxis=dict(title="Material Density (kg/m\u00b3)", gridcolor="#1A2535"),
            yaxis=dict(title="Available Mass (kg)", gridcolor="#1A2535"), height=420)
    elif chart_type == "radar":
        fe = [e for e in evals if e["feasible_overall"]] or evals[:5]
        rc = [CH_TEAL, CH_BLUE, CH_PURPLE, CH_SAND, "#6B8B8B", "#8B6B8B"]
        cats = ["Available Mass","Safety Factor","Low Density","Low BRS","Low Stress"]
        for i, e in enumerate(fe[:6]):
            vals = [
                max(0,min(100,(e["mass_available_kg"]/500)*100)),
                max(0,min(100,(min(e["safety_factor"],20)/20)*100)),
                max(0,min(100,(1-e["material"].density_kg_m3/8000)*100)),
                max(0,min(100,(1-min(e["brs_rpm"],5000)/5000)*100)),
                max(0,min(100,(1-min(e["total_stress_MPa"],500)/500)*100)),
            ]
            fig.add_trace(go.Scatterpolar(
                r=vals+[vals[0]], theta=cats+[cats[0]], fill="toself",
                fillcolor=f"rgba{tuple(list(int(rc[i][j:j+2],16) for j in (1,3,5))+[0.1])}",
                line=dict(color=rc[i], width=2), name=e["material"].name,
            ))
        fig.update_layout(
            polar=dict(bgcolor="#0B0F14",
                       radialaxis=dict(visible=True,range=[0,100],gridcolor="#1A2535",
                                       tickfont=dict(size=8,color=C_TEXT_DIM)),
                       angularaxis=dict(gridcolor="#1A2535",tickfont=dict(size=10,color=C_TEXT))),
            height=450, legend=dict(font=dict(size=10,color=C_TEXT_DIM)))
    else:
        colors = [CH_TEAL if m > 0 else CH_CORAL for m in masses]
        fig.add_trace(go.Bar(x=names, y=masses, marker_color=colors,
            text=[f"{m:.0f}" for m in masses], textposition="outside",
            textfont={"size":10,"color":C_TEXT_DIM}, marker=dict(line=dict(width=0))))
        fig.add_hline(y=0, line_dash="dot", line_color=CH_SAND, line_width=1)
        fig.update_layout(
            xaxis={"tickangle":-45,"gridcolor":"#1A2535","tickfont":{"size":9}},
            yaxis={"title":"Available Mass (kg)","gridcolor":"#1A2535"}, height=400)

    fig.update_layout(
        paper_bgcolor=TRANSPARENT, plot_bgcolor=TRANSPARENT,
        font={"color":C_TEXT,"family":FONT_FAMILY,"size":11},
        margin=dict(l=60,r=20,t=20,b=100), showlegend=(chart_type=="radar"))
    return table, fig


# ── Sensitivity callbacks ─────────────────────────────────────────────────

@callback(
    Output("tornado-chart",        "figure"),
    Output("tradeoff-contour",     "figure"),
    Output("feasibility-boundary", "figure"),
    Input("current-page-store",           "data"),
    Input("sensitivity-variation-pct",    "value"),
    Input("sensitivity-material-density", "value"),
)
def update_sensitivity_page(current_page, variation_pct, mat_density):
    if current_page != "sensitivity":
        emp = go.Figure()
        emp.update_layout(paper_bgcolor=TRANSPARENT, plot_bgcolor=TRANSPARENT, height=100)
        return emp, emp, emp

    var_pct = variation_pct or 20
    density = mat_density or 1100.0
    base = {"outer_radius_m":5.1,"thickness_m":0.0005,
            "material_density_kg_m3":density,
            "internal_pressure_Pa":5066.25,"atmospheric_pressure_Pa":101325.0}

    td, _ = compute_tornado(base, variation_pct=var_pct)
    params = [d["parameter"] for d in td]
    dl     = [d["delta_low"]  for d in td]
    dh     = [d["delta_high"] for d in td]
    ft = go.Figure()
    ft.add_trace(go.Bar(y=params, x=dl, orientation="h", name=f"-{var_pct}%",
        marker_color=CH_CORAL, text=[f"{d:.1f}" for d in dl],
        textposition="outside", textfont={"size":10,"color":C_TEXT_DIM}))
    ft.add_trace(go.Bar(y=params, x=dh, orientation="h", name=f"+{var_pct}%",
        marker_color=CH_TEAL, text=[f"{d:.1f}" for d in dh],
        textposition="outside", textfont={"size":10,"color":C_TEXT_DIM}))
    ft.update_layout(
        barmode="overlay", paper_bgcolor=TRANSPARENT, plot_bgcolor=TRANSPARENT,
        font={"color":C_TEXT,"family":FONT_FAMILY,"size":11},
        xaxis={"title":f"Change in Available Mass (kg) @ \u00b1{var_pct}%",
               "gridcolor":"#1A2535","zeroline":True,"zerolinecolor":"#4A5568"},
        yaxis={"gridcolor":"#1A2535"},
        margin=dict(l=150,r=80,t=20,b=40), height=300,
        legend={"font":{"size":10},"orientation":"h","y":-0.15})

    radii, thicknesses, mass_grid = compute_tradeoff_grid(density,5066.25,101325.0,r_steps=50,t_steps=50)
    fc = go.Figure(go.Contour(
        x=radii, y=thicknesses*1000, z=mass_grid,
        colorscale=[[0,CH_CORAL],[0.35,CH_SAND],[0.5,"#3A4A5A"],[0.75,CH_BLUE],[1,CH_TEAL]],
        contours_showlabels=True, contours=dict(labelfont=dict(size=9,color=C_TEXT)),
        colorbar=dict(title=dict(text="Mass (kg)",font=dict(size=10,color=C_TEXT_DIM)),
                      tickfont=dict(size=9,color=C_TEXT_DIM))))
    fc.update_layout(
        paper_bgcolor=TRANSPARENT, plot_bgcolor=TRANSPARENT,
        font={"color":C_TEXT,"family":FONT_FAMILY,"size":11},
        xaxis={"title":"Outer Radius (m)","gridcolor":"#1A2535"},
        yaxis={"title":"Thickness (mm)","gridcolor":"#1A2535"},
        margin=dict(l=60,r=20,t=20,b=50), height=400)

    radii_b, max_t = compute_feasibility_boundary(density,5066.25,101325.0)
    fb = go.Figure()
    fb.add_trace(go.Scatter(x=radii_b, y=max_t*1000, mode="lines", fill="tozeroy",
        line={"color":CH_TEAL,"width":2}, fillcolor="rgba(61,139,139,0.12)", name="Feasible Region"))
    fb.add_trace(go.Scatter(x=radii_b, y=max_t*1000*1.5, mode="lines",
        line={"color":CH_CORAL,"width":1,"dash":"dot"},
        fill="tonexty", fillcolor="rgba(139,90,90,0.08)", name="Infeasible Region"))
    fb.update_layout(
        paper_bgcolor=TRANSPARENT, plot_bgcolor=TRANSPARENT,
        font={"color":C_TEXT,"family":FONT_FAMILY,"size":11},
        xaxis={"title":"Outer Radius (m)","gridcolor":"#1A2535"},
        yaxis={"title":"Max Thickness (mm)","gridcolor":"#1A2535"},
        margin=dict(l=60,r=20,t=20,b=50), height=380,
        showlegend=True, legend={"font":{"size":10}})
    fb.add_annotation(x=10, y=max_t[len(max_t)//2]*1000*0.4,
        text="POSITIVE<br>BUOYANCY", showarrow=False,
        font={"size":12,"color":CH_TEAL}, opacity=0.5)
    return ft, fc, fb


# ── Material USE button ───────────────────────────────────────────────────

@callback(
    Output("shared-density-store",           "data"),
    Output("page-content",                   "children", allow_duplicate=True),
    Output("current-page-store",             "data",     allow_duplicate=True),
    Output({"type":"nav-btn","page":ALL},    "style",    allow_duplicate=True),
    Input({"type":"use-material-btn","index":ALL}, "n_clicks"),
    prevent_initial_call=True,
)
def on_use_material(clicks):
    if not ctx.triggered_id or not any(n for n in clicks if n):
        return dash.no_update, dash.no_update, dash.no_update, [dash.no_update]*len(PAGE_IDS)
    mat = MATERIAL_LOOKUP.get(ctx.triggered_id["index"])
    if mat:
        return mat.density_kg_m3, dashboard_layout(), "dashboard", _nav_styles("dashboard")
    return dash.no_update, dash.no_update, dash.no_update, [dash.no_update]*len(PAGE_IDS)


@callback(
    Output("slider-density", "value", allow_duplicate=True),
    Input("shared-density-store", "data"),
    Input("unit-system-toggle",   "value"),
    prevent_initial_call=True,
)
def apply_shared_density(density_si, us):
    if density_si is None:
        return dash.no_update
    if (us or "SI") == "Imperial":
        val, _ = convert_value(density_si, "density", "Imperial")
        return val
    return density_si


# ── Page-level overlay (navigation transitions only) ──────────────────────

app.clientside_callback(
    """
    function(pageChildren) {
        var overlay = document.getElementById('app-loader-overlay');
        if (!overlay) return window.dash_clientside.no_update;
        overlay.style.display = 'flex';
        overlay.style.opacity = '1';
        requestAnimationFrame(function() {
            requestAnimationFrame(function() {
                setTimeout(function() {
                    overlay.style.opacity = '0';
                    setTimeout(function() { overlay.style.display = 'none'; }, 400);
                }, 300);
            });
        });
        return window.dash_clientside.no_update;
    }
    """,
    Output("app-loader-overlay", "style"),
    Input("page-content", "children"),
    prevent_initial_call=False,
)


# ── Run ───────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 7860))
    debug = os.environ.get("RENDER") is None
    app.run(debug=debug, host="0.0.0.0", port=port)