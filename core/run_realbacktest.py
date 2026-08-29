import datetime
import numpy as np
from marketdata import MarketDataFetcher
from optimizer import IndustrialBatteryOptimizer


if __name__ == "__main__":
    # fetch real spot prices for a target 24h day
    fetcher = MarketDataFetcher(bidding_zone="DE-LU")
    
    # query yesterday full 24h auction data
    target_day = datetime.date.today() - datetime.timedelta(days=1)
    df_prices = fetcher.get_day_ahead_prices(
        start_date=target_day.isoformat(),
        end_date=target_day.isoformat()
    )

    # in case of 15 min intervals, resample to hourly for our 24h model
    hourly_prices = df_prices["price_eur_kwh"].resample("1h").mean().values[:24]

    if len(hourly_prices) < 24:
        print("Falling back to first 24 records...")
        hourly_prices = df_prices["price_eur_kwh"].values[:24]

    # realistic manufacturing plant load
    factory_load = [
        140, 130, 120, 120, 130, 190,  # 00:00 - 05:00 Early maintenance shift
        320, 450, 520, 480, 460, 440,  # 06:00 - 11:00 Peak production morning
        380, 510, 470, 400, 350, 310,  # 12:00 - 17:00 Afternoon machining run
        260, 230, 190, 160, 150, 140   # 18:00 - 23:00 Evening shutdown
    ]

    # define and run the Optimizer on actual market data
    optimizer = IndustrialBatteryOptimizer(
        capacity_kwh=600.0,
        max_power_kw=300.0,
        efficiency=0.92,
        peak_penalty_per_kw=10.0
    )

    df_results, metrics = optimizer.optimize(
        price_curve=list(hourly_prices),
        factory_load=factory_load,
        dt_hours=1.0
    )

    print(f"\n=======================================================")
    print(f" REAL MARKET BACKTEST: Bidding Zone DE-LU ({target_day})")
    print(f"=======================================================")
    print(f"Market Spot Min:          €{min(hourly_prices)*1000:.2f} / MWh")
    print(f"Market Spot Max:          €{max(hourly_prices)*1000:.2f} / MWh")
    print(f"Market Spot Spread:       €{(max(hourly_prices)-min(hourly_prices))*1000:.2f} / MWh")
    print(f"-------------------------------------------------------")
    print(f"Baseline Unmanaged Cost:  €{metrics['baseline_total_cost']:.2f}")
    print(f"Optimized GridPulse Cost: €{metrics['optimized_total_cost']:.2f}")
    print(f"Net Daily Savings:        €{metrics['savings_eur']:.2f} ({metrics['savings_pct']:.1f}%)")
    print(f"Peak Demand Reduction:    {metrics['baseline_peak_kw']} kW -> {metrics['optimized_peak_kw']:.1f} kW")
    print(f"=======================================================\n")