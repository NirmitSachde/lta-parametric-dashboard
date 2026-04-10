"""
power_page.py
Onboard Power Consumption page for the LTA Parametric Dashboard.

Additions over v1:
  1. RPM sweep chart shows all 3 bearing-torque preset curves simultaneously
  2. Export readout panel: formatted text summary of current operating point
  3. Baseline validation badge: live 0.545 MW vs 0.52 MW target with pass/fail indicator
  4. (README.md updated separately)
  5. (tests/test_power_model.py added separately)
"""

import math
import dash
from dash import dcc, html, Input, Output, State
import plotly.graph_objects as go

try:
    from engine.power_model import compute_power, GAS_PRESETS, BEARING_PRESETS
except ImportError:
    import sys, os
    sys.path.insert(0, os.path.dirname(__file__))
    from power_model import compute_power, GAS_PRESETS, BEARING_PRESETS

# ---------------------------------------------------------------------------
# Colors (consistent with project)
# ---------------------------------------------------------------------------
CH_TEAL   = "#3D8B8B"
CH_CORAL  = "#8B5A5A"
CH_SAND   = "#8B7D5A"
BG_DARK   = "#0B0F14"
BG_MID    = "#111820"
BG_CARD   = "#1E2A38"
TEXT_PRI  = "#E2E8F0"
TEXT_SEC  = "#A0AEC0"
ACCENT    = "#00d4ff"
GREEN     = "#4CAF50"
AMBER     = "#FFC107"
RED_CLR   = "#F44336"

# Preset curve colors for the 3-curve RPM sweep
PRESET_COLORS = {
    "Optimistic":    "#4CAF50",
    "Baseline":      "#00d4ff",
    "Conservative":  "#F44336",
}

# Baseline reference from David Clark (13 Mar 2026)
BASELINE_R   = 9.2    # m
BASELINE_RPM = 600.0
BASELINE_TARGET_MW = 0.52

# ---------------------------------------------------------------------------
# Layout helpers
# ---------------------------------------------------------------------------
def _slider_block(label, id_, min_, max_, step, value, marks=None):
    return html.Div([
        html.Label(label, style={"color": TEXT_SEC, "fontSize": "13px", "marginBottom": "4px"}),
        dcc.Slider(
            id=id_, min=min_, max=max_, step=step, value=value,
            marks=marks or {},
            tooltip={"placement": "bottom", "always_visible": True},
            updatemode="drag",
        ),
    ], style={"marginBottom": "20px"})


def _kv_row(label, value_id, unit):
    return html.Div([
        html.Span(label, style={"color": TEXT_SEC, "fontSize": "13px", "flex": "1"}),
        html.Span(id=value_id, style={"color": ACCENT, "fontSize": "14px",
                                       "fontWeight": "600", "marginRight": "4px"}),
        html.Span(unit, style={"color": TEXT_SEC, "fontSize": "12px"}),
    ], style={"display": "flex", "alignItems": "center", "padding": "6px 0",
              "borderBottom": f"1px solid {BG_CARD}"})


# ---------------------------------------------------------------------------
# Page layout
# ---------------------------------------------------------------------------
layout = html.Div([
    # Header
    html.Div([
        html.Div(style={"display": "flex", "alignItems": "center",
                        "justifyContent": "space-between", "flexWrap": "wrap", "gap": "12px"},
        children=[
            html.Div([
                html.H2("Onboard Power Consumption Model",
                        style={"color": ACCENT, "margin": "0", "fontSize": "20px"}),
                html.P("Rotational gas-drag and bearing power for the spherical lifting structure",
                       style={"color": TEXT_SEC, "margin": "4px 0 0 0", "fontSize": "13px"}),
            ]),
            # Baseline validation badge (item 3)
            html.Div(id="pw-baseline-badge", style={"flexShrink": "0"}),
        ]),
    ], style={"padding": "20px 24px 12px", "borderBottom": f"1px solid {BG_CARD}"}),

    # Main body: 3 columns
    html.Div([
        # LEFT: inputs
        html.Div([
            html.H4("Design Inputs", style={"color": TEXT_PRI, "marginBottom": "16px",
                                             "fontSize": "15px"}),

            _slider_block("Sphere Radius R [m]", "pw-radius",
                          min_=1.0, max_=15.0, step=0.1, value=9.2,
                          marks={1: "1", 5: "5", 9.2: "9.2", 12: "12", 15: "15"}),

            _slider_block("Rotational Speed [rpm]", "pw-rpm",
                          min_=10, max_=1500, step=10, value=600,
                          marks={10: "10", 300: "300", 600: "600", 1000: "1000", 1500: "1500"}),

            _slider_block("Interior Gas Pressure [% Patm]", "pw-pfrac",
                          min_=0.1, max_=10.0, step=0.1, value=1.0,
                          marks={0.1: "0.1%", 1: "1%", 5: "5%", 10: "10%"}),

            html.Label("Gas Type", style={"color": TEXT_SEC, "fontSize": "13px"}),
            dcc.Dropdown(
                id="pw-gas",
                options=[{"label": g, "value": g} for g in GAS_PRESETS],
                value="Helium", clearable=False,
                style={"backgroundColor": BG_MID, "color": TEXT_PRI, "marginBottom": "20px"},
            ),

            html.Label("Bearing Torque Preset", style={"color": TEXT_SEC, "fontSize": "13px"}),
            dcc.RadioItems(
                id="pw-tb-preset",
                options=[
                    {"label": "Optimistic  (10 N.m)",    "value": "Optimistic"},
                    {"label": "Baseline    (50 N.m)",     "value": "Baseline"},
                    {"label": "Conservative (200 N.m)",  "value": "Conservative"},
                ],
                value="Baseline",
                labelStyle={"display": "block", "color": TEXT_PRI, "fontSize": "13px",
                            "marginBottom": "6px"},
                style={"marginBottom": "20px"},
            ),

            html.Label("Custom Bearing Torque Tb [N.m]", style={"color": TEXT_SEC, "fontSize": "13px"}),
            dcc.Input(
                id="pw-tb-custom", type="number", min=0, max=5000, step=1, value=50,
                style={"backgroundColor": BG_MID, "color": TEXT_PRI,
                       "border": f"1px solid {BG_CARD}", "borderRadius": "4px",
                       "padding": "6px 10px", "width": "100%",
                       "marginBottom": "8px", "fontSize": "13px"},
            ),
            html.Small("Overrides preset when changed manually",
                       style={"color": TEXT_SEC, "fontSize": "11px"}),

        ], style={"flex": "0 0 300px", "padding": "20px 24px",
                  "borderRight": f"1px solid {BG_CARD}"}),

        # MIDDLE: outputs + gauge + export readout (item 2)
        html.Div([
            html.H4("Computed Outputs", style={"color": TEXT_PRI, "marginBottom": "8px",
                                                "fontSize": "15px"}),
            _kv_row("Angular velocity omega",      "pw-out-omega",  "rad/s"),
            _kv_row("Equatorial surface speed",    "pw-out-Veq",    "m/s"),
            _kv_row("Gas density (interior)",      "pw-out-rho",    "kg/m3"),
            _kv_row("Reynolds number Re",          "pw-out-Re",     ""),
            _kv_row("Friction coefficient Cf",     "pw-out-Cf",     ""),
            _kv_row("Gas-drag power P_drag",       "pw-out-Pdrag",  "kW"),
            _kv_row("Bearing power P_bearings",    "pw-out-Pbear",  "kW"),
            _kv_row("TOTAL onboard power P_total", "pw-out-Ptotal", "MW"),

            dcc.Graph(id="pw-gauge-total", config={"displayModeBar": False},
                      style={"height": "220px", "marginTop": "12px"}),

            # Export readout (item 2)
            html.Div([
                html.Div(style={"display": "flex", "justifyContent": "space-between",
                                 "alignItems": "center", "marginBottom": "6px"}, children=[
                    html.Span("Export Summary", style={"color": TEXT_SEC, "fontSize": "12px",
                                                        "fontWeight": "600", "letterSpacing": "1px",
                                                        "textTransform": "uppercase"}),
                    html.Button("Copy", id="pw-copy-btn", n_clicks=0,
                                style={"backgroundColor": BG_CARD, "color": ACCENT,
                                       "border": f"1px solid {BG_CARD}", "borderRadius": "4px",
                                       "padding": "3px 10px", "fontSize": "11px",
                                       "cursor": "pointer"}),
                ]),
                html.Pre(id="pw-export-text", style={
                    "backgroundColor": "#0B0F14", "color": TEXT_SEC,
                    "border": f"1px solid {BG_CARD}", "borderRadius": "4px",
                    "padding": "10px 12px", "fontSize": "11px", "lineHeight": "1.6",
                    "margin": "0", "whiteSpace": "pre-wrap", "overflowX": "auto",
                    "fontFamily": "monospace",
                }),
                # Clientside copy confirmation
                html.Div(id="pw-copy-confirm",
                         style={"color": GREEN, "fontSize": "11px",
                                "marginTop": "4px", "height": "14px"}),
            ], style={"marginTop": "16px"}),

        ], style={"flex": "1", "padding": "20px 24px",
                  "borderRight": f"1px solid {BG_CARD}", "overflowY": "auto"}),

        # RIGHT: breakdown bar + multi-preset RPM sweep (item 1)
        html.Div([
            html.H4("Power Breakdown", style={"color": TEXT_PRI, "marginBottom": "8px",
                                               "fontSize": "15px"}),
            dcc.Graph(id="pw-bar-breakdown", config={"displayModeBar": False},
                      style={"height": "200px", "marginBottom": "12px"}),

            html.Div(style={"display": "flex", "justifyContent": "space-between",
                             "alignItems": "center", "marginBottom": "8px"}, children=[
                html.H4("RPM Sweep", style={"color": TEXT_PRI, "margin": "0", "fontSize": "15px"}),
                html.Span("All 3 bearing presets shown",
                          style={"color": TEXT_SEC, "fontSize": "11px"}),
            ]),
            dcc.Graph(id="pw-sweep-chart", config={"displayModeBar": False},
                      style={"height": "260px"}),

        ], style={"flex": "1", "padding": "20px 24px"}),

    ], style={"display": "flex", "flexDirection": "row", "flex": "1", "overflow": "hidden"}),

], style={"display": "flex", "flexDirection": "column", "height": "100%",
          "backgroundColor": BG_DARK, "color": TEXT_PRI, "fontFamily": "Arial, sans-serif"})


# ---------------------------------------------------------------------------
# Callbacks
# ---------------------------------------------------------------------------
def register_callbacks(app):

    # Sync preset -> custom Tb input
    @app.callback(
        Output("pw-tb-custom", "value"),
        Input("pw-tb-preset", "value"),
    )
    def sync_tb_from_preset(preset):
        return BEARING_PRESETS[preset]

    # Main computation callback
    @app.callback(
        [
            Output("pw-out-omega",       "children"),
            Output("pw-out-Veq",         "children"),
            Output("pw-out-rho",         "children"),
            Output("pw-out-Re",          "children"),
            Output("pw-out-Cf",          "children"),
            Output("pw-out-Pdrag",       "children"),
            Output("pw-out-Pbear",       "children"),
            Output("pw-out-Ptotal",      "children"),
            Output("pw-gauge-total",     "figure"),
            Output("pw-bar-breakdown",   "figure"),
            Output("pw-sweep-chart",     "figure"),
            Output("pw-export-text",     "children"),   # item 2
            Output("pw-baseline-badge",  "children"),   # item 3
        ],
        [
            Input("pw-radius",    "value"),
            Input("pw-rpm",       "value"),
            Input("pw-pfrac",     "value"),
            Input("pw-gas",       "value"),
            Input("pw-tb-custom", "value"),
        ],
    )
    def update_power(R, rpm, pfrac, gas, Tb):
        R     = float(R    or 9.2)
        rpm   = float(rpm  or 600)
        pfrac = float(pfrac or 1.0) / 100.0
        gas   = gas or "Helium"
        Tb    = float(Tb   or 50)

        props = GAS_PRESETS.get(gas, GAS_PRESETS["Helium"])
        res   = compute_power(R, rpm, pfrac, props["rho_1atm"], props["mu"], Tb)

        omega_str = f"{res['omega']:.3f}"
        Veq_str   = f"{res['V_equator']:.2f}"
        rho_str   = f"{res['rho_gas']:.5f}"
        Re_str    = f"{res['Re']:.3e}"
        Cf_str    = f"{res['Cf']:.5f}"
        Pdrag_str = f"{res['P_gas_drag']/1e3:.2f}"
        Pbear_str = f"{res['P_bearings']/1e3:.2f}"
        Ptot_str  = f"{res['P_total']/1e6:.4f}"

        Ptot_MW  = res["P_total"]    / 1e6
        Pdrag_MW = res["P_gas_drag"] / 1e6
        Pbear_MW = res["P_bearings"] / 1e6

        g_color = GREEN if Ptot_MW < 0.3 else (AMBER if Ptot_MW < 1.0 else RED_CLR)

        # ── Gauge ────────────────────────────────────────────────────────────
        gauge_max = max(2.0, Ptot_MW * 1.5)
        gauge_fig = go.Figure(go.Indicator(
            mode="gauge+number+delta",
            value=Ptot_MW,
            number={"suffix": " MW", "font": {"color": TEXT_PRI, "size": 20}},
            delta={"reference": BASELINE_TARGET_MW, "relative": False,
                   "suffix": " MW vs baseline", "font": {"size": 11}},
            gauge={
                "axis": {"range": [0, gauge_max], "tickcolor": TEXT_SEC,
                         "tickfont": {"color": TEXT_SEC, "size": 10}},
                "bar": {"color": g_color, "thickness": 0.15},
                "bgcolor": BG_MID, "bordercolor": BG_CARD,
                "steps": [
                    {"range": [0,               gauge_max * 0.3], "color": "#1a2e1a"},
                    {"range": [gauge_max * 0.3, gauge_max * 0.6], "color": "#2e2a1a"},
                    {"range": [gauge_max * 0.6, gauge_max],       "color": "#2e1a1a"},
                ],
                "threshold": {"line": {"color": ACCENT, "width": 2},
                              "thickness": 0.75, "value": BASELINE_TARGET_MW},
            },
            title={"text": "Total Onboard Power", "font": {"color": TEXT_SEC, "size": 13}},
        ))
        gauge_fig.update_layout(
            paper_bgcolor=BG_DARK, font_color=TEXT_PRI, height=220,
            margin=dict(l=20, r=20, t=30, b=10),
        )

        # ── Bar breakdown ────────────────────────────────────────────────────
        bar_fig = go.Figure([
            go.Bar(name="Gas Drag", x=["Power Breakdown"], y=[Pdrag_MW],
                   marker_color=CH_TEAL,
                   text=[f"{Pdrag_MW:.3f} MW"], textposition="auto"),
            go.Bar(name="Bearings", x=["Power Breakdown"], y=[Pbear_MW],
                   marker_color=CH_CORAL,
                   text=[f"{Pbear_MW*1e3:.1f} kW"], textposition="auto"),
        ])
        bar_fig.update_layout(
            barmode="stack", paper_bgcolor=BG_DARK, plot_bgcolor=BG_MID,
            font_color=TEXT_PRI, height=200, margin=dict(l=20, r=10, t=10, b=30),
            yaxis_title="MW", legend=dict(orientation="h", y=1.1, font_size=11),
            xaxis=dict(showgrid=False), yaxis=dict(gridcolor=BG_CARD),
        )

        # ── Multi-preset RPM sweep (item 1) ──────────────────────────────────
        rpms = list(range(50, 1501, 25))
        sweep_fig = go.Figure()

        for preset_name, preset_color in PRESET_COLORS.items():
            Tb_p = BEARING_PRESETS[preset_name]
            ptot_sweep = [
                compute_power(R, r_, pfrac, props["rho_1atm"], props["mu"], Tb_p)["P_total"] / 1e6
                for r_ in rpms
            ]
            lw = 2.5 if preset_name == "Baseline" else 1.5
            dash_style = "solid" if preset_name == "Baseline" else "dot"
            sweep_fig.add_trace(go.Scatter(
                x=rpms, y=ptot_sweep,
                name=f"{preset_name} ({int(Tb_p)} N.m)",
                line=dict(color=preset_color, width=lw, dash=dash_style),
            ))

        # Current operating point marker
        sweep_fig.add_trace(go.Scatter(
            x=[rpm], y=[Ptot_MW], mode="markers",
            marker=dict(color=g_color, size=12, symbol="circle",
                        line=dict(color="white", width=1)),
            name="Current point",
        ))
        # Baseline reference line
        sweep_fig.add_hline(
            y=BASELINE_TARGET_MW, line_dash="dash", line_color=ACCENT,
            line_width=1, opacity=0.5,
            annotation_text=f"Baseline target {BASELINE_TARGET_MW} MW",
            annotation_font=dict(size=9, color=ACCENT),
            annotation_position="top right",
        )
        sweep_fig.update_layout(
            paper_bgcolor=BG_DARK, plot_bgcolor=BG_MID, font_color=TEXT_PRI,
            height=260, margin=dict(l=40, r=10, t=10, b=40),
            xaxis=dict(title="RPM", gridcolor=BG_CARD),
            yaxis=dict(title="P_total [MW]", gridcolor=BG_CARD),
            legend=dict(font_size=10, bgcolor="rgba(0,0,0,0)", orientation="h", y=-0.25),
        )

        # ── Export readout (item 2) ──────────────────────────────────────────
        bearing_preset_label = next(
            (k for k, v in BEARING_PRESETS.items() if abs(v - Tb) < 0.5), "Custom"
        )
        export_text = (
            f"LTA Power Model Export\n"
            f"{'='*36}\n"
            f"Inputs:\n"
            f"  Radius R          = {R:.2f} m\n"
            f"  Speed             = {rpm:.0f} rpm\n"
            f"  Gas pressure      = {pfrac*100:.2f} % Patm\n"
            f"  Gas type          = {gas}\n"
            f"  Bearing torque    = {Tb:.1f} N.m ({bearing_preset_label})\n"
            f"\nOutputs:\n"
            f"  omega             = {res['omega']:.4f} rad/s\n"
            f"  V_equator         = {res['V_equator']:.2f} m/s\n"
            f"  rho_gas           = {res['rho_gas']:.6f} kg/m3\n"
            f"  Re                = {res['Re']:.4e}\n"
            f"  Cf                = {res['Cf']:.6f}\n"
            f"  P_gas_drag        = {res['P_gas_drag']/1e6:.4f} MW\n"
            f"  P_bearings        = {res['P_bearings']/1e3:.4f} kW\n"
            f"  P_total           = {res['P_total']/1e6:.4f} MW\n"
        )

        # ── Baseline validation badge (item 3) ──────────────────────────────
        bl_res = compute_power(
            BASELINE_R, BASELINE_RPM, 0.01,
            GAS_PRESETS["Helium"]["rho_1atm"],
            GAS_PRESETS["Helium"]["mu"],
            BEARING_PRESETS["Baseline"],
        )
        bl_MW    = bl_res["P_gas_drag"] / 1e6
        pct_err  = abs(bl_MW - BASELINE_TARGET_MW) / BASELINE_TARGET_MW * 100
        passing  = pct_err <= 10.0
        badge_color  = GREEN if passing else AMBER
        badge_symbol = "PASS" if passing else "CHECK"
        badge = html.Div([
            html.Div([
                html.Span(badge_symbol, style={
                    "fontSize": "10px", "fontWeight": "700", "marginRight": "6px",
                    "color": badge_color, "letterSpacing": "1px",
                }),
                html.Span(f"Baseline: {bl_MW:.3f} MW",
                          style={"color": TEXT_PRI, "fontSize": "12px"}),
                html.Span(f" (target {BASELINE_TARGET_MW} MW, err {pct_err:.1f}%)",
                          style={"color": TEXT_SEC, "fontSize": "11px"}),
            ], style={
                "display": "flex", "alignItems": "center",
                "backgroundColor": BG_MID, "border": f"1px solid {badge_color}",
                "borderRadius": "6px", "padding": "6px 12px",
            }),
        ])

        return (omega_str, Veq_str, rho_str, Re_str, Cf_str,
                Pdrag_str, Pbear_str, Ptot_str,
                gauge_fig, bar_fig, sweep_fig,
                export_text, badge)

    # ── Clientside copy to clipboard (item 2) ───────────────────────────────
    app.clientside_callback(
        """
        function(n_clicks, text) {
            if (!n_clicks || !text) return '';
            navigator.clipboard.writeText(text).catch(function(){});
            return 'Copied to clipboard';
        }
        """,
        Output("pw-copy-confirm", "children"),
        Input("pw-copy-btn", "n_clicks"),
        State("pw-export-text", "children"),
        prevent_initial_call=True,
    )