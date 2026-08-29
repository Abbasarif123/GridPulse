import numpy as np
import matplotlib.pyplot as plt
from optimizer import IndustrialBatteryOptimizer

if __name__ == "__main__":
    # 24 hour spot price curve, cheap initially, gets expensive and then goes back down and then rises at peak times
    hours = np.arange(24)
    spot_prices = [
        0.08, 0.06, 0.05, 0.04, 0.05, 0.09, # 00:00 - 05:00 Night valley
        0.18, 0.32, 0.38, 0.28, 0.22, 0.20, # 06:00 - 11:00 Morning peak
        0.16, 0.14, 0.12, 0.15, 0.22, 0.35, # 12:00 - 17:00 Afternoon dip
        0.42, 0.39, 0.29, 0.20, 0.14, 0.10  # 18:00 - 23:00 Evening peak
    ]

    # industrial load, base load with heavy machinery spikes at 19 and 14
    factory_load = [
        120, 110, 110, 110, 120, 180,
        300, 420, 480, 400, 380, 390,
        350, 490, 450, 380, 320, 280,
        220, 200, 160, 140, 130, 120
    ]

    optimizer = IndustrialBatteryOptimizer(
        capacity_kwh=600.0,
        max_power_kw=300.0,
        peak_penalty_per_kw=10.0
    )

    df, metrics = optimizer.optimize(spot_prices, factory_load)

    print("\n--- OPTIMIZATION RESULTS ---")
    print(f"Baseline Unmanaged Cost:  €{metrics['baseline_total_cost']:.2f}")
    print(f"Optimized GridPulse Cost: €{metrics['optimized_total_cost']:.2f}")
    print(f"Daily Net Savings:        €{metrics['savings_eur']:.2f} ({metrics['savings_pct']:.1f}%)")
    print(f"Peak Grid Demand Clamped: {metrics['baseline_peak_kw']} kW -> {metrics['optimized_peak_kw']:.1f} kW")
    print("----------------------------\n")