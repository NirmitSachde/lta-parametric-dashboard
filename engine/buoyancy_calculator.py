"""
Buoyancy Calculator Engine
==========================
Parametric Design Dashboard for LTA Vehicle with Rotational Spherical Lifting Structure

All physics computations for the dashboard. Replicates and improves upon
the Excel parametric model ("7 Design Parametric Dashboard.xlsx") with
full floating-point precision using math.pi and exact fractions.

Reference:
    - Excel: "7 Design Parametric Dashboard.xlsx" (David W. Clark, P.E.)
    - Paper: Fomin et al., "Developing a Parametric Design Tool for
             Lighter Than Air Vehicles", UVA / Northrop Grumman TASC (2005)

Physical Constants:
    - Standard atmospheric pressure: 101325 Pa (ISA sea level)
    - Air density at sea level: 1.225 kg/m³ (ISA standard)

Author: Nirmit Sachde, Northeastern University
Mentor: David W. Clark, P.E.
"""

import math
from dataclasses import dataclass
from typing import Literal

# ---------------------------------------------------------------------------
# Physical Constants (ISA Standard Atmosphere, Sea Level)
# ---------------------------------------------------------------------------
RHO_AIR_SEA_LEVEL: float = 1.225          # kg/m³, dry air at 15°C, 101325 Pa
STANDARD_ATM_PRESSURE: float = 101325.0   # Pa
RAD_S_TO_RPM: float = 60.0 / (2.0 * math.pi)  # ≈ 9.5493 (exact conversion)


# ---------------------------------------------------------------------------
# Data Classes
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class SphereGeometry:
    """Geometric properties of the hollow rotating sphere."""
    outer_radius_m: float
    inner_radius_m: float
    thickness_m: float
    surface_area_m2: float
    interior_void_volume_m3: float
    total_volume_m3: float
    shell_volume_m3: float


@dataclass(frozen=True)
class BuoyancyResult:
    """Complete buoyancy computation result."""

    # --- Geometry ---
    geometry: SphereGeometry

    # --- Mass properties ---
    sphere_mass_kg: float
    displaced_air_mass_kg: float
    mass_available_kg: float

    # --- Forces (derived from mass, for gauge display) ---
    weight_force_N: float          # sphere_mass * g
    lift_force_N: float            # displaced_air_mass * g
    net_force_N: float             # lift - weight (positive = ascends)

    # --- Buoyancy state ---
    buoyancy_state: Literal["Positive Buoyancy", "Neutral Buoyancy", "Negative Buoyancy"]

    # --- Rotational dynamics ---
    balanced_rotational_speed_rad_s: float
    balanced_rotational_speed_rpm: float

    # --- Input echo (for traceability) ---
    material_density_kg_m3: float
    internal_pressure_Pa: float
    atmospheric_pressure_Pa: float


# ---------------------------------------------------------------------------
# Core Computation Functions
# ---------------------------------------------------------------------------

def compute_sphere_geometry(
    outer_radius_m: float,
    thickness_m: float,
) -> SphereGeometry:
    """
    Compute all geometric properties of the hollow sphere.

    Excel formulas replicated with full precision:
        Inner Radius       = R_outer - thickness          [C4 = A4 - B4]
        Surface Area       = 4 * pi * R_outer^2           [D4 = 4*3.14*A4^2]
        Interior Volume    = (4/3) * pi * R_inner^3       [E4 = 1.33*3.14*C4^3]
        Total Volume       = (4/3) * pi * R_outer^3       [F4 = 1.33*3.14*A4^3]
        Shell Volume       = V_total - V_interior         [G4 = F4 - E4]

    Note: Excel uses pi approx 3.14 and 4/3 approx 1.33. We use math.pi and 4/3 exactly.
    """
    inner_radius_m = outer_radius_m - thickness_m

    surface_area_m2 = 4.0 * math.pi * outer_radius_m ** 2

    interior_void_volume_m3 = (4.0 / 3.0) * math.pi * inner_radius_m ** 3

    total_volume_m3 = (4.0 / 3.0) * math.pi * outer_radius_m ** 3

    shell_volume_m3 = total_volume_m3 - interior_void_volume_m3

    return SphereGeometry(
        outer_radius_m=outer_radius_m,
        inner_radius_m=inner_radius_m,
        thickness_m=thickness_m,
        surface_area_m2=surface_area_m2,
        interior_void_volume_m3=interior_void_volume_m3,
        total_volume_m3=total_volume_m3,
        shell_volume_m3=shell_volume_m3,
    )


def compute_buoyancy(
    outer_radius_m: float,
    thickness_m: float,
    material_density_kg_m3: float,
    internal_pressure_Pa: float,
    atmospheric_pressure_Pa: float = STANDARD_ATM_PRESSURE,
    air_density_kg_m3: float = RHO_AIR_SEA_LEVEL,
    gravity_m_s2: float = 9.80665,
) -> BuoyancyResult:
    """
    Full parametric buoyancy computation for a hollow rotating sphere.

    This function replicates all Excel computations with exact constants
    and additionally computes force values (N) for gauge display.

    Parameters
    ----------
    outer_radius_m : float
        Outer radius of the sphere [m]. Excel cell A4.
    thickness_m : float
        Wall thickness of the sphere shell [m]. Excel cell B4.
    material_density_kg_m3 : float
        Density of the sphere shell material [kg/m³]. Excel cell H4.
    internal_pressure_Pa : float
        Internal pressure inside the rotating sphere [Pa]. Excel cell B11.
        This is the reduced pressure created by centripetal rotation.
    atmospheric_pressure_Pa : float, optional
        External atmospheric pressure [Pa]. Excel cell A11.
        Default: 101325 Pa (ISA sea level).
    air_density_kg_m3 : float, optional
        Ambient air density [kg/m³]. Default: 1.225 (ISA sea level).
    gravity_m_s2 : float, optional
        Gravitational acceleration [m/s²]. Default: 9.80665 (standard).

    Returns
    -------
    BuoyancyResult
        Complete computation result with all derived parameters.

    Physics
    -------
    The concept: A hollow sphere spins fast enough to create a partial
    vacuum inside (internal_pressure < atmospheric_pressure). The reduced
    internal air mass means the sphere displaces more air than it
    (sphere + internal air) weighs, generating net buoyancy.

    Displaced air mass formula:
        m_displaced = rho_air * V_inner * (1 - P_internal / P_atm)
        [Excel D8 = 1.225 * E4 * (1 - B11/A11)]

    This represents the mass of air that *would* occupy the interior
    at atmospheric pressure, minus the mass of air that *actually*
    remains at the reduced internal pressure.

    Balanced Rotational Speed (BRS):
        omega = sqrt((P_atm - P_internal) / (rho_material * thickness * R_inner))
        [Excel D11 = SQRT((A11-B11)/(H4*B4*C4))]

    This is the angular velocity at which centripetal stress in the thin
    shell exactly balances the pressure differential across the wall.
    """
    # --- Input validation ---
    if outer_radius_m <= 0:
        raise ValueError(f"outer_radius_m must be positive, got {outer_radius_m}")
    if thickness_m <= 0:
        raise ValueError(f"thickness_m must be positive, got {thickness_m}")
    if thickness_m >= outer_radius_m:
        raise ValueError(
            f"thickness_m ({thickness_m}) must be less than outer_radius_m ({outer_radius_m})"
        )
    if material_density_kg_m3 <= 0:
        raise ValueError(f"material_density must be positive, got {material_density_kg_m3}")
    if internal_pressure_Pa < 0:
        raise ValueError(f"internal_pressure must be non-negative, got {internal_pressure_Pa}")
    if atmospheric_pressure_Pa <= 0:
        raise ValueError(f"atmospheric_pressure must be positive, got {atmospheric_pressure_Pa}")
    if internal_pressure_Pa >= atmospheric_pressure_Pa:
        raise ValueError(
            f"internal_pressure ({internal_pressure_Pa} Pa) must be less than "
            f"atmospheric_pressure ({atmospheric_pressure_Pa} Pa) for vacuum buoyancy"
        )

    # --- Geometry ---
    geometry = compute_sphere_geometry(outer_radius_m, thickness_m)

    # --- Mass of sphere shell material ---
    # Excel: A8 = H4 * G4
    sphere_mass_kg = material_density_kg_m3 * geometry.shell_volume_m3

    # --- Mass of displaced air (buoyancy driver) ---
    # Excel: D8 = 1.225 * E4 * (1 - B11/A11)
    # This is the effective displaced air mass accounting for the partial vacuum.
    pressure_ratio = internal_pressure_Pa / atmospheric_pressure_Pa
    displaced_air_mass_kg = (
        air_density_kg_m3
        * geometry.interior_void_volume_m3
        * (1.0 - pressure_ratio)
    )

    # --- Mass available for components ---
    # Excel: F8 = D8 - A8
    mass_available_kg = displaced_air_mass_kg - sphere_mass_kg

    # --- Forces (for gauge display) ---
    weight_force_N = sphere_mass_kg * gravity_m_s2
    lift_force_N = displaced_air_mass_kg * gravity_m_s2
    net_force_N = lift_force_N - weight_force_N

    # --- Buoyancy state determination ---
    # Excel: C8 = IF(A8 > D8, "Negative", IF(A8 < D8, "Positive", "Neutral"))
    # Using a small tolerance for floating-point neutral comparison
    MASS_TOLERANCE_KG = 1e-6
    if sphere_mass_kg > displaced_air_mass_kg + MASS_TOLERANCE_KG:
        buoyancy_state = "Negative Buoyancy"
    elif sphere_mass_kg < displaced_air_mass_kg - MASS_TOLERANCE_KG:
        buoyancy_state = "Positive Buoyancy"
    else:
        buoyancy_state = "Neutral Buoyancy"

    # --- Balanced Rotational Speed ---
    # Excel: D11 = SQRT((A11 - B11) / (H4 * B4 * C4))
    # Denominator: material_density * thickness * inner_radius
    brs_denominator = material_density_kg_m3 * thickness_m * geometry.inner_radius_m
    pressure_differential = atmospheric_pressure_Pa - internal_pressure_Pa

    balanced_rotational_speed_rad_s = math.sqrt(pressure_differential / brs_denominator)

    # Excel: F11 = 9.549 * D11 (approximate conversion)
    # We use the exact conversion: RPM = omega * 60 / (2*pi)
    balanced_rotational_speed_rpm = balanced_rotational_speed_rad_s * RAD_S_TO_RPM

    return BuoyancyResult(
        geometry=geometry,
        sphere_mass_kg=sphere_mass_kg,
        displaced_air_mass_kg=displaced_air_mass_kg,
        mass_available_kg=mass_available_kg,
        weight_force_N=weight_force_N,
        lift_force_N=lift_force_N,
        net_force_N=net_force_N,
        buoyancy_state=buoyancy_state,
        balanced_rotational_speed_rad_s=balanced_rotational_speed_rad_s,
        balanced_rotational_speed_rpm=balanced_rotational_speed_rpm,
        material_density_kg_m3=material_density_kg_m3,
        internal_pressure_Pa=internal_pressure_Pa,
        atmospheric_pressure_Pa=atmospheric_pressure_Pa,
    )


# ---------------------------------------------------------------------------
# Validation against Excel baseline
# ---------------------------------------------------------------------------

def validate_against_excel() -> None:
    """
    Validate Python engine output against known Excel values.

    Excel inputs:
        A4  (Outer Radius)       = 5.1
        B4  (Thickness)          = 0.0005
        H4  (Material Density)   = 1100
        A11 (Patm)               = 101325
        B11 (Internal Pressure)  = 5066.25

    Excel outputs (computed with pi approx 3.14, 4/3 approx 1.33):
        C4  (Inner Radius)       = 5.0995
        D4  (Surface Area)       = 326.6856
        E4  (Interior Volume)    = 553.8142
        F4  (Total Volume)       = 553.9771
        G4  (Shell Volume)       = 0.1629
        A8  (Sphere Mass)        = 179.2103
        C8  (Buoyancy State)     = "Positive Buoyancy"
        D8  (Displaced Air Mass) = 644.5013
        F8  (Mass Available)     = 465.2909
        D11 (BRS rad/s)          = 185.2571
        F11 (BRS rpm)            = 1769.0205
    """
    result = compute_buoyancy(
        outer_radius_m=5.1,
        thickness_m=0.0005,
        material_density_kg_m3=1100.0,
        internal_pressure_Pa=5066.25,
        atmospheric_pressure_Pa=101325.0,
    )

    # Excel values (computed with approximate constants)
    excel = {
        "inner_radius":       5.0995,
        "surface_area":       326.68559999999997,
        "interior_volume":    553.814187730443,
        "total_volume":       553.9771062,
        "shell_volume":       0.16291846955698475,
        "sphere_mass":        179.21031651268322,
        "buoyancy_state":     "Positive Buoyancy",
        "displaced_air_mass": 644.501260971303,
        "mass_available":     465.29094445861983,
        "brs_rad_s":          185.25714465634516,
        "brs_rpm":            1769.0204743234399,
    }

    # Python values (computed with exact constants)
    python = {
        "inner_radius":       result.geometry.inner_radius_m,
        "surface_area":       result.geometry.surface_area_m2,
        "interior_volume":    result.geometry.interior_void_volume_m3,
        "total_volume":       result.geometry.total_volume_m3,
        "shell_volume":       result.geometry.shell_volume_m3,
        "sphere_mass":        result.sphere_mass_kg,
        "buoyancy_state":     result.buoyancy_state,
        "displaced_air_mass": result.displaced_air_mass_kg,
        "mass_available":     result.mass_available_kg,
        "brs_rad_s":          result.balanced_rotational_speed_rad_s,
        "brs_rpm":            result.balanced_rotational_speed_rpm,
    }

    print("=" * 80)
    print("VALIDATION: Python Engine vs Excel Baseline")
    print("=" * 80)
    print(f"{'Parameter':<25} {'Excel':>18} {'Python':>18} {'Delta':>10} {'Status':>8}")
    print("-" * 80)

    all_pass = True
    for key in excel:
        e_val = excel[key]
        p_val = python[key]

        if isinstance(e_val, str):
            status = "PASS" if e_val == p_val else "FAIL"
            if status == "FAIL":
                all_pass = False
            print(f"{key:<25} {e_val:>18} {p_val:>18} {'---':>10} {status:>8}")
        else:
            # Percent difference (relative to Excel value)
            pct_diff = abs(p_val - e_val) / abs(e_val) * 100.0 if e_val != 0 else 0.0
            # Accept up to 1% difference (due to Excel's pi approx 3.14 vs math.pi)
            status = "PASS" if pct_diff < 1.0 else "FAIL"
            if status == "FAIL":
                all_pass = False
            print(f"{key:<25} {e_val:>18.6f} {p_val:>18.6f} {pct_diff:>8.4f}% {status:>8}")

    print("-" * 80)
    print(f"Overall: {'ALL TESTS PASSED' if all_pass else 'SOME TESTS FAILED'}")
    print()
    print("Note: Small differences are expected. Excel uses pi~3.14 and 4/3~1.33.")
    print("Python uses math.pi (3.14159265...) and exact 4/3 (1.33333...).")
    print("Python values are MORE accurate than Excel.")
    print("=" * 80)


# ---------------------------------------------------------------------------
# Unit Conversion System (SI ↔ US Customary / Imperial)
# ---------------------------------------------------------------------------
# Aerospace industry standard: tools must support both SI and Imperial.
# All internal computation is done in SI. Display conversion happens at the UI layer.

# Conversion factors: multiply SI value by factor to get Imperial value
UNIT_CONVERSIONS = {
    "length": {
        "SI": {"unit": "m", "factor": 1.0},
        "Imperial": {"unit": "ft", "factor": 3.28084},
    },
    "area": {
        "SI": {"unit": "m²", "factor": 1.0},
        "Imperial": {"unit": "ft²", "factor": 10.7639},
    },
    "volume": {
        "SI": {"unit": "m³", "factor": 1.0},
        "Imperial": {"unit": "ft³", "factor": 35.3147},
    },
    "mass": {
        "SI": {"unit": "kg", "factor": 1.0},
        "Imperial": {"unit": "lb", "factor": 2.20462},
    },
    "force": {
        "SI": {"unit": "N", "factor": 1.0},
        "Imperial": {"unit": "lbf", "factor": 0.224809},
    },
    "pressure": {
        "SI": {"unit": "Pa", "factor": 1.0},
        "Imperial": {"unit": "psi", "factor": 0.000145038},
    },
    "density": {
        "SI": {"unit": "kg/m³", "factor": 1.0},
        "Imperial": {"unit": "lb/ft³", "factor": 0.062428},
    },
    "rotational_speed": {
        "SI": {"unit": "RPM", "factor": 1.0},
        "Imperial": {"unit": "RPM", "factor": 1.0},  # Same in both systems
    },
    "angular_velocity": {
        "SI": {"unit": "rad/s", "factor": 1.0},
        "Imperial": {"unit": "rad/s", "factor": 1.0},  # Same in both systems
    },
}


def convert_value(value: float, quantity_type: str, to_system: str) -> tuple[float, str]:
    """
    Convert a value from SI to the target unit system.

    Parameters
    ----------
    value : float
        Value in SI units.
    quantity_type : str
        One of: 'length', 'area', 'volume', 'mass', 'force', 'pressure',
                'density', 'rotational_speed', 'angular_velocity'.
    to_system : str
        'SI' or 'Imperial'.

    Returns
    -------
    tuple[float, str]
        Converted value and unit label.
    """
    conv = UNIT_CONVERSIONS[quantity_type][to_system]
    return value * conv["factor"], conv["unit"]


def convert_input_to_si(value: float, quantity_type: str, from_system: str) -> float:
    """
    Convert an input value from the given system to SI for computation.

    Parameters
    ----------
    value : float
        Value in the source unit system.
    quantity_type : str
        Quantity type key from UNIT_CONVERSIONS.
    from_system : str
        'SI' or 'Imperial'.

    Returns
    -------
    float
        Value in SI units.
    """
    factor = UNIT_CONVERSIONS[quantity_type][from_system]["factor"]
    return value / factor


# ---------------------------------------------------------------------------
# Module entry point (run validation when executed directly)
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    validate_against_excel()