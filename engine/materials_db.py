"""
Aerospace Materials Database
=============================
Real material properties for LTA vehicle shell feasibility analysis.
All values sourced from standard aerospace material references.
"""

from dataclasses import dataclass
from typing import Optional
from engine.buoyancy_calculator import compute_buoyancy
import math


@dataclass(frozen=True)
class Material:
    name: str
    category: str
    density_kg_m3: float
    yield_strength_MPa: float
    description: str
    color: str


MATERIALS = [
    Material("Aluminum 6061-T6", "Metal", 2700.0, 276.0,
             "General aerospace structures", "#7EC8DB"),
    Material("Aluminum 7075-T6", "Metal", 2810.0, 503.0,
             "High-strength aerospace alloy", "#5BA4B5"),
    Material("Titanium Ti-6Al-4V", "Metal", 4430.0, 880.0,
             "Aerospace-grade titanium", "#A78BFA"),
    Material("Steel AISI 4130", "Metal", 7850.0, 460.0,
             "Chromoly steel, engine mounts", "#C75050"),
    Material("Magnesium AZ31B", "Metal", 1770.0, 200.0,
             "Lightweight aerospace alloy", "#4CAF7D"),
    Material("Inconel 718", "Metal", 8190.0, 1034.0,
             "Nickel superalloy", "#D4A847"),
    Material("Carbon Fiber (CFRP)", "Composite", 1600.0, 600.0,
             "Primary aerospace composite", "#E2E8F0"),
    Material("Kevlar 49 (AFRP)", "Composite", 1440.0, 525.0,
             "Aramid fiber, impact resistant", "#D4A847"),
    Material("Fiberglass (GFRP)", "Composite", 2100.0, 340.0,
             "Glass fiber reinforced polymer", "#4CAF7D"),
    Material("Carbon Nanotube Sheet", "Exotic", 1300.0, 1000.0,
             "Theoretical advanced material", "#FF9F7F"),
    Material("Mylar (PET Film)", "Polymer", 1390.0, 55.0,
             "Polyester film, balloon envelopes", "#7EC8DB"),
    Material("Kapton (Polyimide)", "Polymer", 1420.0, 69.0,
             "High-temperature polymer film", "#D4A847"),
    Material("UHMWPE (Dyneema)", "Polymer", 970.0, 39.0,
             "Ultra-high MW polyethylene", "#4CAF7D"),
    Material("Graphene Sheet", "Exotic", 2267.0, 130000.0,
             "Theoretical single-layer carbon", "#A78BFA"),
    Material("Beryllium", "Exotic", 1850.0, 240.0,
             "Lightweight metal, aerospace optics", "#C75050"),
]

MATERIAL_LOOKUP = {m.name: m for m in MATERIALS}
MATERIAL_CATEGORIES = sorted(set(m.category for m in MATERIALS))


def evaluate_material(material, outer_radius_m, thickness_m,
                      internal_pressure_Pa, atmospheric_pressure_Pa=101325.0):
    """Evaluate feasibility of a material for given sphere parameters."""
    try:
        result = compute_buoyancy(
            outer_radius_m=outer_radius_m,
            thickness_m=thickness_m,
            material_density_kg_m3=material.density_kg_m3,
            internal_pressure_Pa=internal_pressure_Pa,
            atmospheric_pressure_Pa=atmospheric_pressure_Pa,
        )
        delta_p = atmospheric_pressure_Pa - internal_pressure_Pa
        r = result.geometry.inner_radius_m
        t = thickness_m
        pressure_stress_MPa = (delta_p * r) / (2.0 * t) / 1e6
        omega = result.balanced_rotational_speed_rad_s
        rotational_stress_MPa = material.density_kg_m3 * (omega ** 2) * (r ** 2) / 1e6
        total_stress_MPa = pressure_stress_MPa + rotational_stress_MPa
        safety_factor = material.yield_strength_MPa / total_stress_MPa if total_stress_MPa > 0 else float('inf')

        return {
            "material": material,
            "result": result,
            "feasible_buoyancy": result.buoyancy_state == "Positive Buoyancy",
            "feasible_structural": safety_factor >= 1.5,
            "feasible_overall": (result.buoyancy_state == "Positive Buoyancy") and (safety_factor >= 1.5),
            "mass_available_kg": result.mass_available_kg,
            "brs_rpm": result.balanced_rotational_speed_rpm,
            "pressure_stress_MPa": pressure_stress_MPa,
            "rotational_stress_MPa": rotational_stress_MPa,
            "total_stress_MPa": total_stress_MPa,
            "safety_factor": safety_factor,
        }
    except (ValueError, ZeroDivisionError):
        return {
            "material": material, "result": None,
            "feasible_buoyancy": False, "feasible_structural": False,
            "feasible_overall": False, "mass_available_kg": 0.0,
            "brs_rpm": 0.0, "pressure_stress_MPa": 0.0,
            "rotational_stress_MPa": 0.0, "total_stress_MPa": 0.0,
            "safety_factor": 0.0,
        }


def find_min_feasible_radius(material, thickness_m=0.0005,
                              internal_pressure_Pa=5066.25,
                              atmospheric_pressure_Pa=101325.0):
    """Find minimum radius for positive buoyancy. Returns None if not feasible."""
    for r_10x in range(5, 500):  # 0.5 to 50.0 in 0.1 steps
        r = r_10x / 10.0
        try:
            result = compute_buoyancy(r, thickness_m, material.density_kg_m3,
                                       internal_pressure_Pa, atmospheric_pressure_Pa)
            if result.buoyancy_state == "Positive Buoyancy":
                return r
        except (ValueError, ZeroDivisionError):
            pass
    return None
