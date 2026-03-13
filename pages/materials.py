"""
Materials Comparison Page
=========================
Compare real aerospace materials for LTA sphere feasibility.
"""

from dash import html, dcc
from engine.materials_db import MATERIALS, MATERIAL_CATEGORIES
from visualization.gauges import C_TEXT, C_TEXT_DIM, C_CYAN, FONT_FAMILY

CARD_BG     = "#111820"
CARD_BORDER = "#1E2A38"
CH_TEAL     = "#3D8B8B"
CH_CORAL    = "#8B5A5A"
CH_SAND     = "#8B7D5A"
CH_BLUE     = "#4A7A9B"

DASH_VARS = {
    "--Dash-Fill-Inverse-Strong":    "#141D26",
    "--Dash-Text-Primary":           "#E2E8F0",
    "--Dash-Text-Strong":            "#FFFFFF",
    "--Dash-Stroke-Strong":          "rgba(255,255,255,0.25)",
    "--Dash-Fill-Interactive-Strong":"#5BA4B5",
    "--Dash-Fill-Weak":              "rgba(255,255,255,0.06)",
    "--Dash-Fill-Primary-Hover":     "rgba(255,255,255,0.10)",
    "--Dash-Shading-Strong":         "rgba(0,0,0,0.6)",
}


def make_material_row(mat, eval_data):
    feasible  = eval_data["feasible_overall"]
    buoy_ok   = eval_data["feasible_buoyancy"]
    struct_ok = eval_data["feasible_structural"]
    status_color = CH_TEAL if feasible else (CH_SAND if buoy_ok else CH_CORAL)
    status_text  = "FEASIBLE" if feasible else ("BUOYANCY OK" if buoy_ok else "NOT FEASIBLE")
    sf      = eval_data["safety_factor"]
    sf_text = f"{sf:.1f}x" if sf < 1000 else ">999x"

    return html.Tr(style={"borderBottom": f"1px solid {CARD_BORDER}"}, children=[
        html.Td(mat.name,   style={"padding":"8px 6px","color":C_TEXT,"fontSize":"12px","fontWeight":"600"}),
        html.Td(mat.category, style={"padding":"8px 6px","color":C_TEXT_DIM,"fontSize":"11px"}),
        html.Td(f"{mat.density_kg_m3:.0f}", style={"padding":"8px 6px","color":C_TEXT,"fontSize":"12px","textAlign":"right"}),
        html.Td(f"{eval_data['mass_available_kg']:.1f}", style={"padding":"8px 6px",
            "color":CH_TEAL if eval_data['mass_available_kg']>0 else CH_CORAL,
            "fontSize":"12px","textAlign":"right","fontWeight":"600"}),
        html.Td(f"{eval_data['brs_rpm']:.0f}", style={"padding":"8px 6px","color":CH_BLUE,"fontSize":"12px","textAlign":"right"}),
        html.Td(f"{eval_data['total_stress_MPa']:.1f}", style={"padding":"8px 6px","color":C_TEXT,"fontSize":"12px","textAlign":"right"}),
        html.Td(sf_text, style={"padding":"8px 6px",
            "color":CH_TEAL if struct_ok else CH_CORAL,"fontSize":"12px","textAlign":"right","fontWeight":"600"}),
        html.Td(status_text, style={"padding":"8px 6px","color":status_color,"fontSize":"11px","fontWeight":"700","textAlign":"center"}),
        html.Td(html.Button("USE",
            id={"type":"use-material-btn","index":mat.name}, n_clicks=0,
            style={"backgroundColor":"#1A2535","color":C_CYAN,"border":f"1px solid {C_CYAN}",
                   "borderRadius":"4px","padding":"3px 10px","cursor":"pointer",
                   "fontSize":"10px","fontFamily":FONT_FAMILY,"fontWeight":"600"}),
            style={"padding":"8px 6px","textAlign":"center"}),
    ])


def layout():
    return html.Div([
        html.H2("MATERIAL COMPARISON", style={
            "color":C_TEXT,"fontSize":"16px","fontWeight":"700",
            "letterSpacing":"3px","marginBottom":"6px","fontFamily":FONT_FAMILY,
        }),
        html.P("Feasibility analysis of aerospace materials at current design parameters. "
               "Click USE to load a material's density into the dashboard.",
               style={"color":C_TEXT_DIM,"fontSize":"11px","marginBottom":"16px","fontFamily":FONT_FAMILY}),

        # Controls
        html.Div(style={"display":"flex","gap":"20px","marginBottom":"14px",
                         "flexWrap":"wrap","alignItems":"center"}, children=[
            html.Div(style={"display":"flex","gap":"8px","alignItems":"center"}, children=[
                html.Span("CATEGORY:", style={"color":C_TEXT_DIM,"fontSize":"11px",
                           "fontFamily":FONT_FAMILY,"fontWeight":"600"}),
                html.Div(style={"width":"200px",**DASH_VARS}, children=[
                    dcc.Dropdown(id="material-category-filter",
                        options=[{"label":"All Categories","value":"all"}] +
                                [{"label":c,"value":c} for c in MATERIAL_CATEGORIES],
                        value="all", clearable=False, searchable=False),
                ]),
            ]),
            html.Div(style={"display":"flex","gap":"8px","alignItems":"center"}, children=[
                html.Span("CHART:", style={"color":C_TEXT_DIM,"fontSize":"11px",
                           "fontFamily":FONT_FAMILY,"fontWeight":"600"}),
                html.Div(style={"width":"260px",**DASH_VARS}, children=[
                    dcc.Dropdown(id="material-chart-selector",
                        options=[
                            {"label":"Available Mass Comparison", "value":"mass_bar"},
                            {"label":"Density vs Mass (Bubble)",  "value":"bubble"},
                            {"label":"Multi-Axis Radar Comparison","value":"radar"},
                        ],
                        value="mass_bar", clearable=False, searchable=False),
                ]),
            ]),
        ]),

        # Table
        html.Div(id="materials-table-container", style={
            "backgroundColor":CARD_BG,"border":f"1px solid {CARD_BORDER}",
            "borderRadius":"6px","padding":"0","overflowX":"auto",
        }),

        # Chart wrapped in dcc.Loading
        html.Div(style={"marginTop":"20px"}, children=[
            dcc.Loading(type="circle", color="#5BA4B5", children=[
                dcc.Graph(id="material-feasibility-chart",
                          config={"displayModeBar": False}),
            ]),
        ]),
    ])