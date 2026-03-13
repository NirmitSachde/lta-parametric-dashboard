"""
power_model.py
Onboard Power Consumption Model for the Rotational Spherical Lifting Structure (VCA)

Physics chain:
    omega       = 2 * pi * rpm / 60                             [rad/s]
    rho_gas     = rho_He_1atm * P_frac                          [kg/m3]
    Re          = rho_gas * omega * R**2 / mu                   [dimensionless]
    Cf          = 0.074 / Re**0.2                               [dimensionless]
    P_gas_drag  = (3 * pi**2 / 8) * rho_gas * Cf * omega**3 * R**5   [W]
    P_bearings  = Tb * omega                                    [W]
    P_total     = P_gas_drag + P_bearings                       [W]

Baseline validation (He at 1% Patm, R=9.2 m, 600 rpm):
    P_gas_drag  ~ 0.52 MW
"""

import math

# ---------------------------------------------------------------------------
# Gas property presets
# ---------------------------------------------------------------------------
GAS_PRESETS = {
    "Helium": {
        "rho_1atm": 0.164,       # kg/m3 at 1 atm
        "mu":       1.96e-5,     # Pa.s dynamic viscosity
    },
    "Air": {
        "rho_1atm": 1.225,
        "mu":       1.81e-5,
    },
    "Hydrogen": {
        "rho_1atm": 0.0838,
        "mu":       8.90e-6,
    },
}

# Bearing torque presets [N.m]
BEARING_PRESETS = {
    "Optimistic":    10.0,
    "Baseline":      50.0,
    "Conservative": 200.0,
}


def compute_power(
    R: float,
    rpm: float,
    P_frac: float,
    rho_1atm: float,
    mu: float,
    Tb: float,
) -> dict:
    """
    Compute onboard power consumption for the rotating sphere.

    Parameters
    ----------
    R        : Sphere outer radius [m]
    rpm      : Rotational speed [rev/min]
    P_frac   : Interior gas pressure as fraction of atmospheric (e.g. 0.01 = 1%)
    rho_1atm : Gas density at 1 atm [kg/m3]
    mu       : Dynamic viscosity of gas [Pa.s]
    Tb       : Bearing drag torque [N.m]

    Returns
    -------
    dict with keys:
        omega        [rad/s]
        V_equator    [m/s]   equatorial surface speed
        rho_gas      [kg/m3]
        Re           [-]
        Cf           [-]
        P_gas_drag   [W]
        P_bearings   [W]
        P_total      [W]
    """
    omega = 2.0 * math.pi * rpm / 60.0
    V_equator = omega * R
    rho_gas = rho_1atm * P_frac
    Re = rho_gas * omega * R**2 / mu
    Cf = 0.074 / Re**0.2
    P_gas_drag = (3.0 * math.pi**2 / 8.0) * rho_gas * Cf * omega**3 * R**5
    P_bearings = Tb * omega
    P_total = P_gas_drag + P_bearings

    return {
        "omega":      omega,
        "V_equator":  V_equator,
        "rho_gas":    rho_gas,
        "Re":         Re,
        "Cf":         Cf,
        "P_gas_drag": P_gas_drag,
        "P_bearings": P_bearings,
        "P_total":    P_total,
    }


# ---------------------------------------------------------------------------
# Baseline validation
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    result = compute_power(
        R=9.2,
        rpm=600.0,
        P_frac=0.01,
        rho_1atm=GAS_PRESETS["Helium"]["rho_1atm"],
        mu=GAS_PRESETS["Helium"]["mu"],
        Tb=BEARING_PRESETS["Baseline"],
    )
    print("=== Baseline Validation: R=9.2 m, 600 rpm, He at 1% Patm, Tb=50 N.m ===")
    print(f"  omega        = {result['omega']:.4f} rad/s")
    print(f"  V_equator    = {result['V_equator']:.2f} m/s")
    print(f"  rho_gas      = {result['rho_gas']:.6f} kg/m3")
    print(f"  Re           = {result['Re']:.4e}")
    print(f"  Cf           = {result['Cf']:.6f}")
    print(f"  P_gas_drag   = {result['P_gas_drag']/1e6:.4f} MW  (target ~0.52 MW)")
    print(f"  P_bearings   = {result['P_bearings']/1e3:.4f} kW")
    print(f"  P_total      = {result['P_total']/1e6:.4f} MW")
