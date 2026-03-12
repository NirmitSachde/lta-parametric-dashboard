"""
VCA Body Shell 3D Visualization
================================
Renders the VCA body shell STL file provided by David Clark, with
magnetic induction landing plate per his specifications.

Animation: vertical Z-axis movement based on buoyancy state.

Landing system per David Clark's specifications:
    - Magnetic induction landing plate (no physical contact)
    - Design gap: 0.40m between bottom of shell and top of plate
    - Plate diameter: 130% of body shell diameter
    - ConOps visualization: hover, ascend, descend

The STL is pre-processed into a JSON mesh file (data/vca_shell_mesh.json)
to avoid parsing binary STL at runtime.
"""

import json
import os
import numpy as np
import plotly.graph_objects as go
from visualization.gauges import (
    C_TEXT, C_TEXT_DIM, C_GREEN, C_AMBER, C_RED, C_CYAN, FONT_FAMILY, TRANSPARENT,
)

# ---------------------------------------------------------------------------
# Shell geometry constants (from STL analysis)
# ---------------------------------------------------------------------------
SHELL_DIAMETER = 350.65       # CAD units (mm in model)
SHELL_HEIGHT = 90.12
SHELL_BOTTOM_Z = -10.0
SHELL_TOP_Z = 80.12

# Landing plate specs (David Clark)
PLATE_DIAMETER = SHELL_DIAMETER * 1.30   # 130% of shell diameter
PLATE_THICKNESS = 3.0                     # Visual thickness
DESIGN_GAP = 0.40 * 350.65 / 9.0         # Scale 0.40m to CAD units (approx)
PLATE_Z = SHELL_BOTTOM_Z - DESIGN_GAP    # Plate sits below shell at design gap

# Animation Z offsets based on buoyancy state
Z_OFFSET_POSITIVE = 60.0     # Rise above neutral
Z_OFFSET_NEUTRAL = 0.0       # Hover at design gap
Z_OFFSET_NEGATIVE = -15.0    # Descend (but maintain gap from plate)


# ---------------------------------------------------------------------------
# Mesh loading
# ---------------------------------------------------------------------------

_mesh_cache = None

def load_shell_mesh():
    """Load the pre-processed VCA shell mesh from JSON."""
    global _mesh_cache
    if _mesh_cache is not None:
        return _mesh_cache

    paths = [
        os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "vca_shell_mesh.json"),
        os.path.join("data", "vca_shell_mesh.json"),
        "vca_shell_mesh.json",
    ]

    for path in paths:
        if os.path.exists(path):
            with open(path, "r") as f:
                _mesh_cache = json.load(f)
            return _mesh_cache

    return None


# ---------------------------------------------------------------------------
# Landing plate mesh generation
# ---------------------------------------------------------------------------

def create_landing_plate(z_position, diameter, resolution=60):
    """Create a flat circular disk (landing plate) as Mesh3d data."""
    radius = diameter / 2.0
    angles = np.linspace(0, 2 * np.pi, resolution, endpoint=False)

    cx, cy = 0.0, 0.0
    x_vals = [cx] + [cx + radius * np.cos(a) for a in angles]
    y_vals = [cy] + [cy + radius * np.sin(a) for a in angles]
    z_vals = [z_position] * (resolution + 1)

    i_vals, j_vals, k_vals = [], [], []
    for idx in range(resolution):
        i_vals.append(0)
        j_vals.append(idx + 1)
        k_vals.append((idx + 1) % resolution + 1)

    return {
        "x": x_vals, "y": y_vals, "z": z_vals,
        "i": i_vals, "j": j_vals, "k": k_vals,
    }


# ---------------------------------------------------------------------------
# Magnetic field ring (visual indicator)
# ---------------------------------------------------------------------------

def create_magnetic_ring(z_position, inner_r, outer_r, resolution=60):
    """Create a ring (annulus) representing the magnetic induction coil."""
    angles = np.linspace(0, 2 * np.pi, resolution, endpoint=False)

    x_vals, y_vals, z_vals = [], [], []
    i_vals, j_vals, k_vals = [], [], []

    for a in angles:
        x_vals.append(inner_r * np.cos(a))
        y_vals.append(inner_r * np.sin(a))
        z_vals.append(z_position)
    for a in angles:
        x_vals.append(outer_r * np.cos(a))
        y_vals.append(outer_r * np.sin(a))
        z_vals.append(z_position)

    n = resolution
    for idx in range(n):
        next_idx = (idx + 1) % n
        i_vals.extend([idx, idx, n + idx])
        j_vals.extend([next_idx, n + idx, n + next_idx])
        k_vals.extend([n + idx, n + next_idx, next_idx])

    return {
        "x": x_vals, "y": y_vals, "z": z_vals,
        "i": i_vals, "j": j_vals, "k": k_vals,
    }


# ---------------------------------------------------------------------------
# Main figure builder
# ---------------------------------------------------------------------------

def build_3d_scene(buoyancy_state, net_force_N=0.0):
    """
    Build the complete 3D ConOps visualization.

    Parameters
    ----------
    buoyancy_state : str
        "Positive Buoyancy", "Neutral Buoyancy", or "Negative Buoyancy"
    net_force_N : float
        Net vertical force for proportional animation offset.

    Returns
    -------
    go.Figure
        Plotly 3D figure with VCA shell STL, plate, and magnetic ring.
    """
    mesh = load_shell_mesh()

    # Determine Z offset based on buoyancy state
    if buoyancy_state == "Positive Buoyancy":
        max_offset = Z_OFFSET_POSITIVE
        z_offset = min(max_offset, max(10.0, abs(net_force_N) / 100.0))
    elif buoyancy_state == "Negative Buoyancy":
        z_offset = Z_OFFSET_NEGATIVE
    else:
        z_offset = Z_OFFSET_NEUTRAL

    # State color for the shell
    state_colors = {
        "Positive Buoyancy": C_GREEN,
        "Neutral Buoyancy": C_AMBER,
        "Negative Buoyancy": C_RED,
    }
    shell_color = state_colors.get(buoyancy_state, C_TEXT_DIM)

    fig = go.Figure()

    # --- VCA Body Shell (from David Clark's STL) ---
    if mesh:
        z_shifted = [z + z_offset for z in mesh["z"]]
        fig.add_trace(go.Mesh3d(
            x=mesh["x"], y=mesh["y"], z=z_shifted,
            i=mesh["i"], j=mesh["j"], k=mesh["k"],
            color=shell_color,
            opacity=0.85,
            flatshading=True,
            lighting=dict(
                ambient=0.4, diffuse=0.6, specular=0.3,
                roughness=0.5, fresnel=0.2,
            ),
            lightposition=dict(x=200, y=200, z=300),
            name="VCA Body Shell",
            showlegend=True,
            hoverinfo="name",
        ))
    else:
        # Fallback: simple sphere if mesh not available
        u = np.linspace(0, 2*np.pi, 30)
        v = np.linspace(0, np.pi, 20)
        r = SHELL_DIAMETER / 2
        x = r * np.outer(np.cos(u), np.sin(v)).flatten()
        y = r * np.outer(np.sin(u), np.sin(v)).flatten()
        z = (r * np.outer(np.ones(np.size(u)), np.cos(v)).flatten()
             + SHELL_TOP_Z/2 + z_offset)
        fig.add_trace(go.Scatter3d(
            x=x, y=y, z=z, mode="markers",
            marker=dict(size=1, color=shell_color, opacity=0.5),
            name="VCA Shell (simplified)",
        ))

    # --- Landing Plate (hidden by default, toggle via legend) ---
    plate = create_landing_plate(PLATE_Z, PLATE_DIAMETER)
    fig.add_trace(go.Mesh3d(
        x=plate["x"], y=plate["y"], z=plate["z"],
        i=plate["i"], j=plate["j"], k=plate["k"],
        color="#2A3A4E",
        opacity=0.9,
        flatshading=True,
        name="Landing Plate",
        showlegend=True,
        hoverinfo="name",
        visible="legendonly",
    ))

    # --- Magnetic Induction Ring (hidden by default, toggle via legend) ---
    ring = create_magnetic_ring(
        PLATE_Z + 0.5,
        inner_r=SHELL_DIAMETER * 0.35,
        outer_r=SHELL_DIAMETER * 0.45,
    )
    ring_color = "#5BA4B5" if buoyancy_state != "Negative Buoyancy" else "#4A5568"
    fig.add_trace(go.Mesh3d(
        x=ring["x"], y=ring["y"], z=ring["z"],
        i=ring["i"], j=ring["j"], k=ring["k"],
        color=ring_color,
        opacity=0.7,
        flatshading=True,
        name="Magnetic Coil",
        showlegend=True,
        hoverinfo="name",
        visible="legendonly",
    ))

    # --- Layout ---
    scene_range = PLATE_DIAMETER * 0.7
    z_min = PLATE_Z - 20
    z_max = SHELL_TOP_Z + Z_OFFSET_POSITIVE + 40

    fig.update_layout(
        paper_bgcolor=TRANSPARENT,
        plot_bgcolor=TRANSPARENT,
        uirevision="constant",
        font=dict(color=C_TEXT, family=FONT_FAMILY, size=10),
        scene=dict(
            xaxis=dict(
                visible=False,
                range=[-scene_range, scene_range],
                showbackground=False,
            ),
            yaxis=dict(
                visible=False,
                range=[-scene_range, scene_range],
                showbackground=False,
            ),
            zaxis=dict(
                visible=True,
                range=[z_min, z_max],
                showgrid=True,
                gridcolor="#1A2535",
                showbackground=False,
                title=dict(text="Altitude", font=dict(size=10, color=C_TEXT_DIM)),
                tickfont=dict(size=8, color=C_TEXT_DIM),
            ),
            bgcolor="#0B0F14",
            camera=dict(
                eye=dict(x=1.5, y=1.5, z=0.8),
                up=dict(x=0, y=0, z=1),
            ),
            aspectmode="data",
        ),
        margin=dict(l=0, r=0, t=30, b=0),
        height=450,
        showlegend=True,
        legend=dict(
            font=dict(size=10, color=C_TEXT_DIM),
            bgcolor="rgba(0,0,0,0)",
            x=0.01, y=0.99,
        ),
        annotations=[
            dict(
                text=f"<b>{buoyancy_state.upper()}</b>",
                x=0.5, y=0.97, xref="paper", yref="paper",
                showarrow=False,
                font=dict(size=14, color=shell_color, family=FONT_FAMILY),
            ),
        ],
    )

    return fig