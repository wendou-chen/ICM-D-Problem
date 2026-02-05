from collections import defaultdict
from configs.env_constants import EnvConfig

class EnvLedger:
    def __init__(self, cfg: EnvConfig):
        self.cfg = cfg
        self.attempts_total = 0.0
        self.attempts_by_year = defaultdict(float)
        self.attempts_by_site = defaultdict(float)
        self.mass_elevator_total_ton = 0.0
        self.S_bc = 0.0
        self.S_bc_max = 0.0
        self.E_BC = 0.0

        # Tracking history for plotting if needed
        self.history_S_bc = []

    def step_day(self, t: int, n_attempts: float, m_elev_day_ton: float, site_attempts: dict = None):
        """
        Update environmental state for a single day.

        Args:
            t: Day index (0 to T-1)
            n_attempts: Number of rocket launch attempts today
            m_elev_day_ton: Mass shipped via elevator today
            site_attempts: Dict mapping site_id to attempts (optional)
        """
        y = t // 365

        # 1. Update Rocket Counters
        self.attempts_total += n_attempts
        self.attempts_by_year[y] += n_attempts

        if site_attempts:
            for j, v in site_attempts.items():
                self.attempts_by_site[j] += v
        else:
            # Default to a generic site 'site_0' if not specified
            self.attempts_by_site['site_0'] += n_attempts

        # 2. Update Elevator Counters
        self.mass_elevator_total_ton += m_elev_day_ton

        # 3. Update Stratospheric Black Carbon (Leaky Bucket)
        # u_t = Attempts * Emission_per_Attempt
        u_t = n_attempts * self.cfg.e_BC_per_attempt_ton

        # Accumulate total emitted BC (optional metric)
        self.E_BC += u_t

        # Stock Update: S_{t+1} = (1 - delta) * S_t + u_t
        # delta = 1 / (tau * 365)
        # Note: Time step is 1 day. Tau is in years.
        if self.cfg.tau_bc_years > 0:
            delta = 1.0 / (self.cfg.tau_bc_years * 365.0)
        else:
            delta = 1.0 # Immediate decay if tau=0

        self.S_bc = (1.0 - delta) * self.S_bc + u_t

        # Track Max Stock
        if self.S_bc > self.S_bc_max:
            self.S_bc_max = self.S_bc

        self.history_S_bc.append(self.S_bc)

    def snapshot(self):
        """
        Return a copy of the current state for passing between phases.
        """
        import copy
        return copy.deepcopy(self)

    def finalize(self):
        """
        Calculate final aggregated metrics.
        """
        # 1. CO2 Emissions
        # Rockets
        E_CO2_rocket_ton = self.attempts_total * self.cfg.e_CO2_per_attempt_ton

        # Elevator (Electricity)
        # Energy (kWh) = Mass (ton) * Efficiency (kWh/ton)
        energy_elev_kwh = self.mass_elevator_total_ton * self.cfg.epsilon_E_kwh_per_ton

        # Emissions = Energy * GridIntensity * (1 - GreenRatio)
        # Grid Intensity is kg/kWh -> divide by 1000 for tons
        E_CO2_elev_ton = (energy_elev_kwh
                          * self.cfg.g_grid_kgco2_per_kwh
                          * (1.0 - self.cfg.chi_green)
                          / 1000.0)

        E_CO2_total_ton = E_CO2_rocket_ton + E_CO2_elev_ton

        # 2. Ozone Risk (Soft Constraint Penalty)
        # Sum of excess launches over safe limit per year
        E_O3_penalty = sum(max(0.0, v - self.cfg.N_safe_year) for v in self.attempts_by_year.values())

        # Feasibility check (Hard Limit)
        feasible_o3 = all(v <= self.cfg.N_max_year for v in self.attempts_by_year.values())

        # 3. LCA (Construction Carbon Debt)
        # Mass * Energy * Intensity
        # MJ = ton * 1000 * MJ/kg
        E_LCA_build_ton = (self.cfg.m_tether_total_ton * 1000.0
                           * self.cfg.e_graphene_MJ_per_kg
                           * self.cfg.g_mfg_kgco2_per_MJ
                           / 1000.0)

        # 4. Local Impact (Weighted Sum)
        E_loc = 0.0
        if self.cfg.w_site:
            E_loc = sum(self.cfg.w_site.get(j, 1.0) * v for j, v in self.attempts_by_site.items())
        else:
            # If no weights, just sum attempts (proxy)
            E_loc = self.attempts_total

        # 5. Composite Metric (EDI - Environmental Damage Index)
        # Normalize and weigh?
        # For now, return raw components. The sweeper script can compute EDI.

        return {
            "E_CO2_ton": E_CO2_total_ton,
            "E_CO2_rocket_ton": E_CO2_rocket_ton,
            "E_CO2_elev_ton": E_CO2_elev_ton,
            "E_BC_cumulative_ton": self.E_BC,
            "S_max_ton": self.S_bc_max, # Peak Black Carbon Stock
            "E_O3_penalty": E_O3_penalty,
            "feasible_o3": feasible_o3,
            "E_LCA_ton": E_LCA_build_ton,
            "E_loc": E_loc,
            "attempts_total": self.attempts_total,
            "mass_elev_ton": self.mass_elevator_total_ton
        }
