import pulp
import pandas as pd
import numpy as np

class IndustrialBatteryOptimizer:
    def __init__(
        self,
        capacity_kwh: float = 500.0,
        max_power_kw: float = 250.0,      # max charge discharge rate
        efficiency: float = 0.92,         # round trip efficiency factor
        min_soc_pct: float = 0.10,        #lower SOC limit to prevent discharge degradation
        max_soc_pct: float = 0.90,        #upper SOC limit to prevent overcharge degradation
        initial_soc_kwh: float = 250.0,
        degradation_cost_per_kwh: float = 0.02,  # cell wear penalty (~2ct/kWh throughput)
        peak_penalty_per_kw: float = 12.0 # Monthly/daily peak demand fee weighting
    ):
        self.capacity_kwh = capacity_kwh
        self.max_power_kw = max_power_kw
        self.eff = efficiency
        self.min_soc = capacity_kwh * min_soc_pct
        self.max_soc = capacity_kwh * max_soc_pct
        self.initial_soc = initial_soc_kwh
        self.deg_cost = degradation_cost_per_kwh
        self.peak_penalty = peak_penalty_per_kw

    def optimize(self, price_curve: list[float], factory_load: list[float], dt_hours: float = 1.0) -> pd.DataFrame:
        """
        Solves the MILP for a given time horizon.
        :param price_curve: Electricity spot price in €/kWh for each timestep.
        :param factory_load: Factory baseline consumption in kW for each timestep.
        :param dt_hours: Time resolution per interval (1.0 = hourly, 0.25 = 15-min).
        """
        T = len(price_curve)
        time_steps = range(T)

        prob = pulp.LpProblem("Industrial_GridPulse_Optimization", pulp.LpMinimize)

        # Decision Variables
        p_charge = pulp.LpVariable.dicts("P_Charge", time_steps, lowBound=0, upBound=self.max_power_kw)
        p_discharge = pulp.LpVariable.dicts("P_Discharge", time_steps, lowBound=0, upBound=self.max_power_kw)
        p_grid = pulp.LpVariable.dicts("P_Grid", time_steps, lowBound=0) # Power imported from grid
        soc = pulp.LpVariable.dicts("SOC", range(T + 1), lowBound=self.min_soc, upBound=self.max_soc)
        
        # Binary flags to strictly prevent simultaneous charge & discharge
        is_charging = pulp.LpVariable.dicts("IsCharging", time_steps, cat=pulp.LpBinary)
        
        # Peak power variable across the horizon
        peak_grid_power = pulp.LpVariable("Peak_Grid_Power", lowBound=0)

        # Initial SOC boundary
        prob += soc[0] == self.initial_soc

        for t in time_steps:
            # 1. State of Charge Dynamics: SOC(t+1) = SOC(t) + (P_ch * eff - P_dis / eff) * dt
            prob += soc[t + 1] == soc[t] + (p_charge[t] * self.eff - p_discharge[t] / self.eff) * dt_hours

            # 2. Power Balance: Grid + Discharge = Factory Load + Charge
            prob += p_grid[t] + p_discharge[t] == factory_load[t] + p_charge[t]

            # 3. Prevent simultaneous charge/discharge via Big-M constraint
            prob += p_charge[t] <= self.max_power_kw * is_charging[t]
            prob += p_discharge[t] <= self.max_power_kw * (1 - is_charging[t])

            # 4. Peak grid tracking
            prob += peak_grid_power >= p_grid[t]

        # Objective Function: Minimize (Energy Purchase Cost + Battery Wear + Peak Demand Charges)
        energy_cost = pulp.lpSum([p_grid[t] * price_curve[t] * dt_hours for t in time_steps])
        degradation_cost = pulp.lpSum([(p_charge[t] + p_discharge[t]) * self.deg_cost * dt_hours for t in time_steps])
        peak_charge = peak_grid_power * self.peak_penalty

        prob += energy_cost + degradation_cost + peak_charge

        # Solve using HiGHS or CBC
        solver = pulp.PULP_CBC_CMD(msg=False)
        prob.solve(solver)

        # Parse Results into a Clean DataFrame
        results = []
        for t in time_steps:
            results.append({
                "hour": t,
                "price_eur_kwh": price_curve[t],
                "factory_load_kw": factory_load[t],
                "p_grid_kw": pulp.value(p_grid[t]),
                "p_charge_kw": pulp.value(p_charge[t]),
                "p_discharge_kw": pulp.value(p_discharge[t]),
                "soc_kwh": pulp.value(soc[t + 1]),
                "soc_pct": (pulp.value(soc[t + 1]) / self.capacity_kwh) * 100,
            })

        df = pd.DataFrame(results)
        
        # Financial Comparison
        baseline_energy_cost = sum(np.array(factory_load) * np.array(price_curve) * dt_hours)
        baseline_peak_cost = max(factory_load) * self.peak_penalty
        baseline_total = baseline_energy_cost + baseline_peak_cost

        opt_energy_cost = sum(df["p_grid_kw"] * df["price_eur_kwh"] * dt_hours)
        opt_peak_cost = df["p_grid_kw"].max() * self.peak_penalty
        opt_deg_cost = sum((df["p_charge_kw"] + df["p_discharge_kw"]) * self.deg_cost * dt_hours)
        opt_total = opt_energy_cost + opt_peak_cost + opt_deg_cost

        savings_pct = ((baseline_total - opt_total) / baseline_total) * 100

        metrics = {
            "baseline_total_cost": baseline_total,
            "optimized_total_cost": opt_total,
            "savings_eur": baseline_total - opt_total,
            "savings_pct": savings_pct,
            "baseline_peak_kw": max(factory_load),
            "optimized_peak_kw": df["p_grid_kw"].max(),
        }

        return df, metrics