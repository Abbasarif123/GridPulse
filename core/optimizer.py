import pulp
import pandas as pd
import numpy as np
#energy unit -> kW time-> h currency -> euro
class IndustrialBatteryOptimizer:
    def __init__(
        self,
        capacity_kwh: float = 500.0,
        max_power_kw: float = 250.0,      # max charge discharge rate
        efficiency: float = 0.92,         # round trip efficiency factor
        min_soc_pct: float = 0.10,        #lower SOC limit to prevent discharge degradation (10%)
        max_soc_pct: float = 0.90,        #upper SOC limit to prevent overcharge degradation (90%)
        initial_soc_kwh: float = 250.0,
        degradation_cost_per_kwh: float = 0.02,  # cell wear penalty
        peak_penalty_per_kw: float = 12.0 #demand charge applied to the highest grid draw
    ):
        #physical and operational system boundaries
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
        Solves the MILP for a given time horizon
            param price_curve: electricity spot price in for each timestep
            param factory_load: factory baseline consumption in for each timestep
            param dt_hours: Time resolution per interval (1.0 = hourly)
        """
        T = len(price_curve)
        time_steps = range(T)

        prob = pulp.LpProblem("Industrial_GridPulse_Optimization", pulp.LpMinimize)

        #DECISION VARIABLES
        #power charge rate at step t
        p_charge = pulp.LpVariable.dicts("P_Charge", time_steps, lowBound=0, upBound=self.max_power_kw)
        #power discharge rate at step t
        p_discharge = pulp.LpVariable.dicts("P_Discharge", time_steps, lowBound=0, upBound=self.max_power_kw)
        #net power imported from the external grid at step t
        p_grid = pulp.LpVariable.dicts("P_Grid", time_steps, lowBound=0) 
        soc = pulp.LpVariable.dicts("SOC", range(T + 1), lowBound=self.min_soc, upBound=self.max_soc)
        #battery  energy stored at step boundary t
        
        #binary indicator 0 for discharging mode 1 for charging mode
        is_charging = pulp.LpVariable.dicts("IsCharging", time_steps, cat=pulp.LpBinary)
        
        #max grid power drawn across all time steps
        peak_grid_power = pulp.LpVariable("Peak_Grid_Power", lowBound=0)

        #CONSTRAINTS

        # starting state of charge
        prob += soc[0] == self.initial_soc

        for t in time_steps:
            # state of charge dynamics: SOC(t+1) = SOC(t) + (P_ch * eff - P_dis / eff) * dt
            #this accounts for conversion losses during charging and discharging
            prob += soc[t + 1] == soc[t] + (p_charge[t] * self.eff - p_discharge[t] / self.eff) * dt_hours

            # power balance : Grid + Discharge = Factory Load + Charge  (KIRCHOFFS LAW)
            #total power IN == total power OUT
            prob += p_grid[t] + p_discharge[t] == factory_load[t] + p_charge[t]

            # prevent simultaneous charge and discharge via Big-M constraint
            #if is_charging[t] == 1: p_charge <= Max, p_discharge <= 0 
            #if is_charging[t] == 0: p_charge <= 0, p_discharge <= max 
            prob += p_charge[t] <= self.max_power_kw * is_charging[t]
            prob += p_discharge[t] <= self.max_power_kw * (1 - is_charging[t])

            # peak grid tracking
            #max(p_grid[0], p_grid[1], ..., p_grid[T-1])
            prob += peak_grid_power >= p_grid[t]

        # OBJECTIVE FUNCTION: Minimize (Energy Purchase Cost + Battery Wear + Peak Demand Charges)
        
        energy_cost = pulp.lpSum([p_grid[t] * price_curve[t] * dt_hours for t in time_steps])
        degradation_cost = pulp.lpSum([(p_charge[t] + p_discharge[t]) * self.deg_cost * dt_hours for t in time_steps])

        #capacity or demand tarrif charged against the highest single peak power import
        peak_charge = peak_grid_power * self.peak_penalty

        prob += energy_cost + degradation_cost + peak_charge

        #SOLVE
        #invoke the default CBC MILP solver
        solver = pulp.PULP_CBC_CMD(msg=False)
        prob.solve(solver)

        #POST PROCESSING AND METRICS

        #extract the optimised value into a structured time series
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
        
        #FINANCIAL COMPARISON

        #baseline calculation:faactory operating without battery intervention
        baseline_energy_cost = sum(np.array(factory_load) * np.array(price_curve) * dt_hours)
        baseline_peak_cost = max(factory_load) * self.peak_penalty
        baseline_total = baseline_energy_cost + baseline_peak_cost

        #optimised calculation: actual costs including battery operational expenditure and degredation
        opt_energy_cost = sum(df["p_grid_kw"] * df["price_eur_kwh"] * dt_hours)
        opt_peak_cost = df["p_grid_kw"].max() * self.peak_penalty
        opt_deg_cost = sum((df["p_charge_kw"] + df["p_discharge_kw"]) * self.deg_cost * dt_hours)
        opt_total = opt_energy_cost + opt_peak_cost + opt_deg_cost

        savings_pct = ((baseline_total - opt_total) / baseline_total) * 100

        #summary KPI comparing baseline vs optimised
        metrics = {
            "baseline_total_cost": baseline_total,
            "optimized_total_cost": opt_total,
            "savings_eur": baseline_total - opt_total,
            "savings_pct": savings_pct,
            "baseline_peak_kw": max(factory_load),
            "optimized_peak_kw": df["p_grid_kw"].max(),
        }

        return df, metrics