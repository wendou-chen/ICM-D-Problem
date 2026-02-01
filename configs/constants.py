from dataclasses import dataclass
from typing import Tuple, Dict

@dataclass(frozen=True)
class Problem:
    START_YEAR: int = 2050
    TOTAL_MASS_TONS: float = 100_000_000.0  # M = 100 million metric tons

@dataclass(frozen=True)
class Elevator:
    NUM_HARBOURS: int = 3
    CAPACITY_PER_HARBOUR_TPY: float = 179_000.0  # tons/year

@dataclass(frozen=True)
class Rocket:
    MAX_SITES: int = 10
    PAYLOAD_RANGE_TON: Tuple[float, float] = (100.0, 150.0)  # tons/launch
    DAILY_RATE_SET: Tuple[int, int] = (1, 2)  # launches/day/site (Q1 scenarios)
    
    # Q2 Update: Risk Analysis Parameters
    R_BASE: int = 1
    R_MAX: int = 5
    GAMMA_SET: Tuple[float, ...] = (1.0, 1.5, 2.0, 2.5, 3.0, 4.0)

@dataclass(frozen=True)
class Cost:
    # --- Rocket Cost Parameters (Learning Curve) ---
    # Traditional Earth->Moon launch cost range in 2050 (USD/launch)
    # Assumes technological maturity relative to 2026
    ROCKET_LAUNCH_COST_2050_RANGE_USD: Tuple[float, float] = (30_000_000.0, 150_000_000.0)

    # Cost decay parameters: 5% drop every 5 years
    ROCKET_COST_DECAY_RATE_PER_5YR: float = 0.05
    ROCKET_COST_DECAY_PERIOD_YR: int = 5

    # Floor: Cost cannot drop below this (Hard limit for propellants/hardware)
    ROCKET_COST_FLOOR_USD: float = 10_000_000.0

    # --- Elevator Cost Parameters ---
    # Operational Expenditure (Electricity + Maintenance) per kg
    ELEVATOR_OPEX_PER_KG_RANGE_USD: Tuple[float, float] = (50.0, 100.0)

    # --- Apex Transfer Cost Parameters ---
    # Apex->Moon launch discount factor (relative to direct Earth->Moon rocket)
    # Why < 1.0? No gravity well fight, strictly vacuum transfer.
    # Why > 0.1? Fixed costs (vehicle amortization, ops) remain.
    BETA_APEX_RANGE: Tuple[float, float] = (0.02, 0.1)

@dataclass(frozen=True)
class ReliabilityPreset:
    name: str
    A_E: float  # Elevator Availability [0, 1]
    MTTR_E_DAYS: float  # Mean Time To Repair for Elevator
    P_R: float  # Probability of Rocket failure per launch
    TAU_RESET_DAYS: int  # Pad reset time after failure
    A_B: float  # Base availability (weather etc)

    @property
    def lambda_mu(self) -> Tuple[float, float]:
        """Returns (lambda, mu) for the elevator availability model."""
        # mu = 1 / MTTR
        # A = mu / (lambda + mu) => A*lambda + A*mu = mu => lambda = mu(1-A)/A
        mu = 1.0 / self.MTTR_E_DAYS if self.MTTR_E_DAYS > 0 else 0.0
        if self.A_E >= 1.0:
            lam = 0.0
        else:
            lam = mu * (1.0 - self.A_E) / self.A_E
        return lam, mu

# Presets
# MILD: High reliability, short repair
PRESET_MILD = ReliabilityPreset(
    name="MILD",
    A_E=0.99,
    MTTR_E_DAYS=2.0,
    P_R=0.01,
    TAU_RESET_DAYS=3,
    A_B=0.98
)

# MODERATE: Average reliability
PRESET_MODERATE = ReliabilityPreset(
    name="MODERATE",
    A_E=0.90,
    MTTR_E_DAYS=7.0,
    P_R=0.05,
    TAU_RESET_DAYS=7,
    A_B=0.95
)

# SEVERE: Frequent issues, long delays
PRESET_SEVERE = ReliabilityPreset(
    name="SEVERE",
    A_E=0.75,
    MTTR_E_DAYS=30.0,
    P_R=0.15,
    TAU_RESET_DAYS=14,
    A_B=0.90
)

RELIABILITY_PRESETS: Dict[str, ReliabilityPreset] = {
    "MILD": PRESET_MILD,
    "MODERATE": PRESET_MODERATE,
    "SEVERE": PRESET_SEVERE
}

# --- Q3 Specific Constants ---

@dataclass(frozen=True)
class WaterDemand:
    POPULATION: int = 100_000
    W_L_PER_PERSON_DAY: float = 175.0  # Baseline
    ETA_RECYCLE_LIST: Tuple[float, ...] = (0.0, 0.7, 0.9, 0.95, 0.98)
    T_OPS_DAYS: int = 365

@dataclass(frozen=True)
class WaterPolicy:
    POLICY_TYPE: str = "order_up_to"  # or "rate_matching"
    L_SAFE_DAYS: int = 30
    B_BUFFER_DAYS: int = 15
    USE_DYNAMIC_SURGE: bool = True

@dataclass(frozen=True)
class WaterCapacityShare:
    PHI_E: float = 1.0  # Fraction of elevator capacity for water
    PHI_R: float = 1.0  # Fraction of rocket capacity for water
    PHI_R_SURGE: float = 1.0
