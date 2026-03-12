"""
Sensitivity Analysis Engine
============================
Computes parameter sensitivity, trade-off curves, and feasibility boundaries.
"""

import numpy as np
from engine.buoyancy_calculator import compute_buoyancy


def compute_tornado(base_params, variation_pct=20.0):
    """
    Tornado chart data: vary each parameter +/- variation_pct and measure
    effect on mass_available_kg.
    Returns list of dicts sorted by impact magnitude, and the base mass.
    """
    param_defs = [
        ("Outer Radius", "outer_radius_m"),
        ("Shell Thickness", "thickness_m"),
        ("Material Density", "material_density_kg_m3"),
        ("Internal Pressure", "internal_pressure_Pa"),
        ("Atmospheric Pressure", "atmospheric_pressure_Pa"),
    ]
    base_result = compute_buoyancy(**base_params)
    base_mass = base_result.mass_available_kg
    results = []

    for label, key in param_defs:
        base_val = base_params[key]
        low_val = base_val * (1 - variation_pct / 100.0)
        high_val = base_val * (1 + variation_pct / 100.0)
        p_low = {**base_params, key: low_val}
        p_high = {**base_params, key: high_val}
        if key == "thickness_m":
            p_low[key] = max(p_low[key], 0.00001)
            p_high[key] = min(p_high[key], base_params["outer_radius_m"] * 0.5)
        if key == "internal_pressure_Pa":
            p_high[key] = min(p_high[key], base_params["atmospheric_pressure_Pa"] - 100)
        try:
            mass_low = compute_buoyancy(**p_low).mass_available_kg
        except (ValueError, ZeroDivisionError):
            mass_low = base_mass
        try:
            mass_high = compute_buoyancy(**p_high).mass_available_kg
        except (ValueError, ZeroDivisionError):
            mass_high = base_mass
        results.append({
            "parameter": label, "base_value": base_val,
            "mass_at_low": mass_low, "mass_at_high": mass_high,
            "delta_low": mass_low - base_mass, "delta_high": mass_high - base_mass,
            "total_swing": abs(mass_high - mass_low),
        })
    results.sort(key=lambda x: x["total_swing"], reverse=True)
    return results, base_mass


def compute_tradeoff_grid(material_density, internal_pressure_Pa,
                           atmospheric_pressure_Pa,
                           r_min=1.0, r_max=20.0, r_steps=40,
                           t_min=0.0001, t_max=0.005, t_steps=40):
    """2D grid of mass_available for radius vs thickness."""
    radii = np.linspace(r_min, r_max, r_steps)
    thicknesses = np.linspace(t_min, t_max, t_steps)
    mass_grid = np.zeros((len(thicknesses), len(radii)))
    for i, t in enumerate(thicknesses):
        for j, r in enumerate(radii):
            try:
                result = compute_buoyancy(r, t, material_density,
                                           internal_pressure_Pa, atmospheric_pressure_Pa)
                mass_grid[i, j] = result.mass_available_kg
            except (ValueError, ZeroDivisionError):
                mass_grid[i, j] = float('nan')
    return radii, thicknesses, mass_grid


def compute_feasibility_boundary(material_density, internal_pressure_Pa,
                                  atmospheric_pressure_Pa,
                                  r_min=1.0, r_max=20.0, r_steps=100):
    """For each radius, find max thickness with positive buoyancy."""
    radii = np.linspace(r_min, r_max, r_steps)
    max_thicknesses = []
    for r in radii:
        max_t = 0.0
        for t_1000x in range(1, 200):
            t = t_1000x / 1000.0
            if t >= r:
                break
            try:
                result = compute_buoyancy(r, t, material_density,
                                           internal_pressure_Pa, atmospheric_pressure_Pa)
                if result.buoyancy_state == "Positive Buoyancy":
                    max_t = t
                else:
                    break
            except (ValueError, ZeroDivisionError):
                break
        max_thicknesses.append(max_t)
    return radii, np.array(max_thicknesses)