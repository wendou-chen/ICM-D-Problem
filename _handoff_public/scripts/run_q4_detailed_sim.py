import numpy as np
import pandas as pd
import os
import time
import sys
from collections import defaultdict
from typing import Dict, Any, List, Tuple
from tqdm import tqdm

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from configs.constants import Rocket, Elevator, Problem, PRESET_MODERATE, ReliabilityPreset
from configs.env_constants import EnvConfig
from src.q4.env_ledger import EnvLedger

# --- Constants for Phase 2 ---
POPULATION = 100_000
WATER_PER_CAPITA_TON = 0.175  # 175 L/person/day
DAILY_DEMAND_TON = POPULATION * WATER_PER_CAPITA_TON # 17,500 tons/day
SAFE_STOCK_DAYS = 30
SAFE_INVENTORY_TON = DAILY_DEMAND_TON * SAFE_STOCK_DAYS
PHASE_2B_DAYS = 365

class Q4PhasedSimulation:
    def __init__(self,
                 preset: ReliabilityPreset = PRESET_MODERATE,
                 env_config: EnvConfig = EnvConfig()):
        self.preset = preset
        self.env_config = env_config

        # Load constants
        self.target_build_mass_ton = Problem.TOTAL_MASS_TONS
        self.elev_daily_cap_ton = (Elevator.CAPACITY_PER_HARBOUR_TPY * Elevator.NUM_HARBOURS) / 365.0
        self.rocket_payload_ton = (Rocket.PAYLOAD_RANGE_TON[0] + Rocket.PAYLOAD_RANGE_TON[1]) / 2.0

        # State Variables
        self.ledger = None
        self.t_global = 0 # Global day counter
        self.inventory_water_ton = 0.0

        # Infrastructure State (Persistent across phases)
        self.elevator_down_days = 0
        self.pad_down_days = None # Will init in setup

    def setup(self, K_pads: int, r_rate: float, chi_green: float, elev_scale: float, seed: int):
        if seed is not None:
            np.random.seed(seed)

        # Config Override
        current_env_cfg = EnvConfig(
            chi_green=chi_green,
            # Inherit others explicit to avoid missing fields if EnvConfig changes
            e_CO2_per_attempt_ton=self.env_config.e_CO2_per_attempt_ton,
            e_BC_per_attempt_ton=self.env_config.e_BC_per_attempt_ton,
            tau_bc_years=self.env_config.tau_bc_years,
            epsilon_E_kwh_per_ton=self.env_config.epsilon_E_kwh_per_ton,
            g_grid_kgco2_per_kwh=self.env_config.g_grid_kgco2_per_kwh,
            m_tether_total_ton=self.env_config.m_tether_total_ton,
            e_graphene_MJ_per_kg=self.env_config.e_graphene_MJ_per_kg,
            g_mfg_kgco2_per_MJ=self.env_config.g_mfg_kgco2_per_MJ,
            N_safe_year=self.env_config.N_safe_year,
            N_max_year=self.env_config.N_max_year
        )

        self.ledger = EnvLedger(current_env_cfg)
        self.t_global = 0
        self.inventory_water_ton = 0.0

        self.K_pads = K_pads
        self.r_rate = r_rate
        self.elev_scale = elev_scale

        # Init Infrastructure
        self.lam, self.mu = self.preset.lambda_mu
        self.elevator_down_days = 0
        self.pad_down_days = np.zeros(K_pads, dtype=int)

    def _simulate_daily_capacity(self) -> Tuple[float, int, int]:
        """
        Simulate infrastructure for one day.
        Returns:
            m_E_cap: Available elevator capacity (tons)
            n_attempts: Total rocket attempts made
            n_success_launches: Successful rocket launches
        """
        # 1. Elevator
        m_E_cap = 0.0
        if self.elevator_down_days > 0:
            self.elevator_down_days -= 1
        else:
            if np.random.random() < (1.0 - np.exp(-self.lam)):
                self.elevator_down_days = int(np.ceil(np.random.exponential(scale=self.preset.MTTR_E_DAYS)))
            else:
                m_E_cap = self.elev_daily_cap_ton * self.elev_scale

        # 2. Rockets
        attempts_today = 0
        success_launches = 0

        r_int = int(self.r_rate)
        r_frac = self.r_rate - r_int

        for k in range(self.K_pads):
            if self.pad_down_days[k] > 0:
                self.pad_down_days[k] -= 1
                continue

            if np.random.random() > self.preset.A_B:
                continue

            n_att = r_int + (1 if np.random.random() < r_frac else 0)

            for _ in range(n_att):
                attempts_today += 1
                if np.random.random() < self.preset.P_R:
                    self.pad_down_days[k] = self.preset.TAU_RESET_DAYS
                    break
                else:
                    success_launches += 1

        return m_E_cap, attempts_today, success_launches

    def run_phase1_construction(self, max_years=500):
        """
        Phase 1: Build Infrastructure (1e8 tons).
        Max Effort: Ship everything possible.
        """
        mass_delivered = 0.0
        max_days = max_years * 365
        t_start = self.t_global

        while mass_delivered < self.target_build_mass_ton and (self.t_global - t_start) < max_days:
            m_E_cap, n_attempts, n_success = self._simulate_daily_capacity()

            # All capacity used for construction
            m_R = n_success * self.rocket_payload_ton
            m_total = m_E_cap + m_R

            mass_delivered += m_total

            # Log Environment
            self.ledger.step_day(self.t_global, float(n_attempts), m_E_cap)
            self.t_global += 1

        duration = (self.t_global - t_start) / 365.0
        completed = mass_delivered >= self.target_build_mass_ton

        # Snapshot state
        metrics = self.ledger.finalize()

        return {
            'duration_build_years': duration,
            'build_completed': completed,
            'E_build_ton': metrics['E_CO2_ton'],
            'mass_build_final': mass_delivered
        }

    def run_phase2a_startup(self, max_days=365*5):
        """
        Phase 2a: Accumulate Water Inventory to Safe Level.
        Max Effort: Ship water until inventory >= SAFE_INVENTORY.
        """
        t_start = self.t_global
        completed = False

        while self.inventory_water_ton < SAFE_INVENTORY_TON and (self.t_global - t_start) < max_days:
            m_E_cap, n_attempts, n_success = self._simulate_daily_capacity()

            m_R = n_success * self.rocket_payload_ton
            m_supply = m_E_cap + m_R

            self.inventory_water_ton += m_supply

            self.ledger.step_day(self.t_global, float(n_attempts), m_E_cap)
            self.t_global += 1

            if self.inventory_water_ton >= SAFE_INVENTORY_TON:
                completed = True
                break

        return {
            'duration_startup_days': self.t_global - t_start,
            'startup_completed': completed
        }

    def run_phase2b_operation(self):
        """
        Phase 2b: 1 Year Steady State Operation.
        Order-up-to Logic: Ship strictly what is needed (Demand + Safety Buffer Gap).
        """
        t_start = self.t_global
        stockout_days = 0
        total_demand_met = 0.0
        total_demand = 0.0

        # Snapshot start of OP emissions to calculate delta
        metrics_start = self.ledger.finalize()
        E_start = metrics_start['E_CO2_ton']

        for _ in range(PHASE_2B_DAYS):
            # 1. Calculate Needs
            # Target = SAFE_INVENTORY_TON
            # Gap = Target - Current + Daily_Demand
            gap = SAFE_INVENTORY_TON - self.inventory_water_ton + DAILY_DEMAND_TON
            gap = max(0, gap) # Can't ship negative

            # 2. Determine Capacity
            m_E_cap, n_attempts, n_success = self._simulate_daily_capacity()
            m_R_cap_avail = n_success * self.rocket_payload_ton # Potential rocket capacity

            # 3. Allocate Capacity (Order-up-to)
            # Fill with Elevator first
            m_E_ship = min(gap, m_E_cap)
            gap -= m_E_ship

            # Fill remaining with Rocket
            m_R_ship = min(gap, m_R_cap_avail)

            # Actual shipped
            m_supply = m_E_ship + m_R_ship

            # Note: For environmental ledger, we log attempts and elevator usage.
            # Even if rockets flew empty (which we avoid by not launching),
            # here we assume attempts are determined by r_rate.
            # Refinement: In strict order-up-to, we wouldn't launch if not needed.
            # But "attempts" are scheduled. Let's assume we use the attempts generated.
            # To be precise: If gap is 0, we shouldn't launch.
            # Simplified: We log all attempts generated by the infrastructure simulation
            # as "Scheduled Flights", assuming a fixed schedule.
            # OR: We could scale down attempts? Let's stick to "Scheduled" for robustness.
            # Correction: If we strictly follow demand, we reduce launches.
            # But m_E is "use it or lose it". Rockets are discrete.
            # Let's count all attempts generated by r_rate as "Operational Cost"
            # to maintain readiness, or assume they carry other cargo?
            # Q4 focus is water. Let's assume we log all generated attempts to be conservative on pollution.

            self.ledger.step_day(self.t_global, float(n_attempts), m_E_ship) # Log actual E usage

            # 4. Update Inventory
            self.inventory_water_ton += m_supply

            # 5. Consume Demand
            if self.inventory_water_ton >= DAILY_DEMAND_TON:
                self.inventory_water_ton -= DAILY_DEMAND_TON
                total_demand_met += DAILY_DEMAND_TON
            else:
                total_demand_met += self.inventory_water_ton
                self.inventory_water_ton = 0
                stockout_days += 1

            total_demand += DAILY_DEMAND_TON
            self.t_global += 1

        metrics_end = self.ledger.finalize()
        E_op = metrics_end['E_CO2_ton'] - E_start

        return {
            'E_op_ton': E_op,
            'stockout_days': stockout_days,
            'service_level': total_demand_met / total_demand if total_demand > 0 else 1.0
        }

def run_simulation_batch():
    print("Starting Q4 Phased Simulation Sweep...")
    out_dir = "outputs/q4_detailed"
    os.makedirs(out_dir, exist_ok=True)

    # Configs
    K_values = [1, 5, 10]
    r_values = [1.0, 3.0]
    chi_values = np.arange(0.0, 1.005, 0.005)
    elev_scale_values = [0.0, 0.4, 1.0]
    N_MC = 3

    all_results = []

    total_iters = len(K_values) * len(r_values) * len(chi_values) * len(elev_scale_values) * N_MC

    with tqdm(total=total_iters) as pbar:
        for K in K_values:
            for r in r_values:
                for chi in chi_values:
                    for es in elev_scale_values:
                        for i in range(N_MC):
                            seed = int(time.time()) + i * 999
                            sim = Q4PhasedSimulation()
                            sim.setup(K, r, chi, es, seed)

                            # Phase 1
                            res_p1 = sim.run_phase1_construction(max_years=500)

                            # Phase 2 (Only if P1 succeeded or reasonable time)
                            res_p2a = {'duration_startup_days': 0, 'startup_completed': False}
                            res_p2b = {'E_op_ton': 0, 'stockout_days': 365, 'service_level': 0}

                            if res_p1['build_completed'] and res_p1['duration_build_years'] < 200:
                                res_p2a = sim.run_phase2a_startup()
                                if res_p2a['startup_completed']:
                                    res_p2b = sim.run_phase2b_operation()

                            # Aggregate
                            combined = {
                                'K': K, 'r': r, 'chi': chi, 'elev_scale': es,
                                'iter': i,
                                'completed': res_p1['build_completed'],
                                'unreasonable_duration': res_p1['duration_build_years'] > 200,
                                'duration_years': res_p1['duration_build_years'],
                                'total_mass': res_p1['mass_build_final'], # Construction mass
                                'E_CO2_ton': sim.ledger.finalize()['E_CO2_ton'], # Cumulative Total
                                'S_max_ton': sim.ledger.S_bc_max,
                                'E_build_ton': res_p1['E_build_ton'],
                                'E_op_ton': res_p2b['E_op_ton'],
                                'service_level': res_p2b['service_level']
                            }
                            # Add alpha actual from ledger
                            metrics = sim.ledger.finalize()
                            combined['alpha_actual'] = 0
                            if metrics['attempts_total'] > 0 or metrics['mass_elev_ton'] > 0:
                                 # Approximation of share
                                 m_R_est = metrics['attempts_total'] * sim.rocket_payload_ton
                                 combined['alpha_actual'] = metrics['mass_elev_ton'] / (metrics['mass_elev_ton'] + m_R_est + 1e-6)

                            # EDI Proxy
                            combined['EDI_proxy'] = (
                                (combined['E_CO2_ton'] / 1e8) +
                                (combined['S_max_ton'] / 1e4) +
                                (metrics['E_O3_penalty'] / 1000.0)
                            ) / 3.0

                            all_results.append(combined)
                            pbar.update(1)

    df = pd.DataFrame(all_results)
    df.to_csv(os.path.join(out_dir, "mc_results.csv"), index=False)
    print("Saved Monte Carlo results to mc_results.csv")

    # --- TRACE GENERATION FOR SELECTED SCENARIOS ---
    print("Generating High-Resolution Traces for Representative Scenarios...")
    trace_configs = [
        # Label, K, r, chi, elev_scale
        ("Rocket-Heavy", 10, 3.0, 0.0, 0.0),
        ("Mixed", 5, 2.0, 0.5, 0.4),
        ("Elevator-Heavy", 1, 1.0, 1.0, 1.0)
    ]

    trace_records = []

    for label, K, r, chi, es in trace_configs:
        sim = Q4PhasedSimulation()
        sim.setup(K, r, chi, es, seed=42) # Fixed seed for reproducibility

        # We need to capture daily state. We'll monkey-patch or modify the runner loop?
        # Cleaner: Rerun manually here with logging.
        # Reuse existing methods but we need access to ledger history.
        # Actually, ledger keeps history_S_bc! We just need to map it to days.

        # Phase 1
        res_p1 = sim.run_phase1_construction(max_years=200)

        # Capture Phase 1 History
        # ledger.history_S_bc is a list of S_bc values per day
        # We need to reconstruct the timeline

        # Phase 2
        if res_p1['build_completed']:
            sim.run_phase2a_startup()
            sim.run_phase2b_operation()

        # Extract History
        history = sim.ledger.history_S_bc
        # Create records
        for day, s_bc in enumerate(history):
            # Determine Phase roughly (post-hoc)
            phase = "Construction"
            if day > res_p1['duration_build_years'] * 365:
                phase = "Operation"

            trace_records.append({
                'Scenario': label,
                'Day': day,
                'Year': day / 365.0,
                'S_bc_ton': s_bc,
                'Phase': phase
            })

    df_traces = pd.DataFrame(trace_records)
    df_traces.to_csv(os.path.join(out_dir, "traces.csv"), index=False)
    print(f"Saved traces to {os.path.join(out_dir, 'traces.csv')}")

    print("Done.")

if __name__ == "__main__":
    run_simulation_batch()
