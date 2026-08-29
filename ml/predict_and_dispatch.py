import joblib
import pandas as pd
import numpy as np
import sys
sys.path.append("..")
from core.optimizer import IndustrialBatteryOptimizer

def run_forecasted_dispatch(test_feature_matrix: pd.DataFrame, actual_spot_prices: list[float], factory_load: list[float]):
    #load trained ml artifact
    #deserialise the persisted dictionary containing the trained lightGPM model and the exact expected feature column order
    artifact = joblib.load("price_forecaster_lgb.pkl")
    model = artifact["model"]
    feature_cols = artifact["features"]

    # generate 24hour day ahead price forecasts
    #extract the first 24 hours of feature vectors and predict wholesale prices
    predicted_prices_mwh = model.predict(test_feature_matrix[feature_cols].iloc[:24])
    #megawatt to kilowatt
    predicted_prices_kwh = (predicted_prices_mwh / 1000.0).tolist()

    #SOLVE PREDICTIVE MILP DISPATCH
    #define the optimizer with industrial battery specs
    optimizer = IndustrialBatteryOptimizer(capacity_kwh=600.0, max_power_kw=300.0)
    #solve the MILP using the AI predicted price curve to determine the planned dispatch schedule
    df_planned, _ = optimizer.optimize(
        price_curve=predicted_prices_kwh, #forward looking forecast signal
        factory_load=factory_load, #baseline factory power demand
        dt_hours=1.0 #hourly resolution
    )

    # FINANCIAL EVALUATION AFTER
    actual_prices_kwh = [p / 1000.0 for p in actual_spot_prices[:24]]
    realized_energy_cost = sum(df_planned["p_grid_kw"] * actual_prices_kwh)
    baseline_energy_cost = sum(np.array(factory_load) * actual_prices_kwh)
    net_savings = baseline_energy_cost - realized_energy_cost

    print("\n--- AUTONOMOUS AI DISPATCH RESULT ---")
    print(f"Predicted Arbitrage Savings: €{net_savings:.2f}")
    print("-------------------------------------")