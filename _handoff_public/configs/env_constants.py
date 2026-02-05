from dataclasses import dataclass, field
from typing import Dict, Optional

@dataclass
class EnvConfig:
    """
    Environmental parameters for Q4 analysis.
    Values represent a 'Base' scenario unless otherwise specified.
    """
    # --- Rocket Emissions ---
    # CO2 equivalent per launch (tonnes).
    # Reference: Heavy lift rocket (Starship-like) ~2000-3000t propellant, mostly LOX/CH4.
    # Burning CH4 produces CO2.
    # e_CO2 ~ 1000-3000 tons per launch depending on assumption.
    # Let's use 2000.0 as base.
    e_CO2_per_attempt_ton: float = 2000.0

    # Black Carbon (Soot) per launch (tonnes).
    # Clean burning Methane is low soot, Kerosene is high.
    # Assuming Methalox future: 1-10 kg? Or more?
    # Kerosene can be 100s of kg.
    # Prompt implies significant impact, let's assume 1.0 ton for conservative/older tech
    # or accumulated radiative forcing equivalent.
    # Actually, for "Leaky Bucket", we track mass.
    # Let's use 0.1 tons (100kg) per launch as a placeholder for Methalox base.
    e_BC_per_attempt_ton: float = 0.1

    # --- Atmosphere Dynamics (Leaky Bucket) ---
    # Residence time of soot in stratosphere (years).
    tau_bc_years: float = 4.0

    # --- Elevator Emissions ---
    # Electricity consumption per ton lifted (kWh/ton).
    # LEO potential energy ~ 33 MJ/kg ~ 9 kWh/kg ~ 9000 kWh/ton.
    # GEO is higher.
    # Efficiency losses included. Let's say 15,000 kWh/ton.
    epsilon_E_kwh_per_ton: float = 15000.0

    # Grid Carbon Intensity (kg CO2 / kWh).
    # 2050 assumption: Global grid is cleaner but not zero.
    # 0.2 kg/kWh (Global avg today is ~0.45).
    g_grid_kgco2_per_kwh: float = 0.2

    # Decarbonization ratio (chi): 0.0 (dirty grid) to 1.0 (100% renewable dedicated).
    # This is a sweep variable, default 0.0 here (uses grid).
    chi_green: float = 0.0

    # --- Life Cycle Assessment (LCA) ---
    # Elevator Tether Mass (tons).
    # 100,000 km long, tapered. Total mass is huge.
    # Assumption: 6000 tons? 100,000 tons?
    # Let's use 10,000 tons as a placeholder.
    m_tether_total_ton: float = 10000.0

    # Graphene/CNT manufacturing energy (MJ/kg).
    # High energy intensity. Aluminum is ~200 MJ/kg. CNTs might be 1000+.
    e_graphene_MJ_per_kg: float = 1000.0

    # Manufacturing Carbon Intensity (kg CO2 / MJ).
    # Industrial heat/electricity. 0.05 kgCO2/MJ?
    g_mfg_kgco2_per_MJ: float = 0.05

    # --- Ozone / Regulatory ---
    # Safe limit of launches per year (Soft constraint).
    N_safe_year: float = 1000.0

    # Hard limit of launches per year.
    N_max_year: float = 5000.0

    # Local environmental weights for launch sites (Dictionary).
    # Default None (all 1.0).
    w_site: Optional[Dict[str, float]] = None
