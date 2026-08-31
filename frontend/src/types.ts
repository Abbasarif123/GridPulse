export interface TelemetryState {
  capacity_kwh: number;
  max_power_kw: number;
  soc_kwh: number;
  soc_pct: number;
  factory_load_kw: number;
  pv_generation_kw: number;
  battery_power_kw: number; // >0 discharging, <0 charging
  grid_power_kw: number;
  spot_price_eur_kwh: number;
  mode: string;
  cumulative_savings_eur: number;
  sim_hour: number;
}

export interface ScheduleStep {
  hour: number;
  price_eur_kwh: number;
  factory_load_kw: number;
  p_grid_kw: number;
  p_charge_kw: number;
  p_discharge_kw: number;
  soc_kwh: number;
  soc_pct: number;
}

export interface OptimizationResponse {
  metrics: {
    baseline_total_cost: number;
    optimized_total_cost: number;
    savings_eur: number;
    savings_pct: number;
    baseline_peak_kw: number;
    optimized_peak_kw: number;
  };
  schedule: ScheduleStep[];
}