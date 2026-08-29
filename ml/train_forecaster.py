import joblib
import pandas as pd
import numpy as np
import lightgbm as lgb
from sklearn.metrics import mean_absolute_error, root_mean_squared_error

import sys
sys.path.append("..")
from core.marketdata import MarketDataFetcher
from datapipeline import fetch_historical_weather, build_feature_dataset


def train_model():
    """trains a LightGBM Gradient Boosted Decision Tree (GBDT) regressor
    to forecast day-ahead electricity spot prices
    """    
    print("Fetching training data (prices + weather)...")

    #FETCHING HISTORICAL TRAINING DATA
    fetcher = MarketDataFetcher(bidding_zone="DE-LU")
    
    #6 month window
    df_prices = fetcher.get_day_ahead_prices(start_date="2026-01-01", end_date="2026-07-01")
    df_weather = fetch_historical_weather(start_date="2026-01-01", end_date="2026-07-01")

    #FEATURE MATRIX CONSTRUCTION AND DATA PREPARATION
    print("Constructing lag & weather feature matrices...")
    #merges tables, computes calendar cycles, rolling statistics, and autoregressive lag regressors
    dataset = build_feature_dataset(df_prices, df_weather)

    #defining independent predictor variables explicitly
    features = [
        "hour_sin", "hour_cos", #cyclic diurnal features
        "dayofweek", "is_weekend", "month", #calendar
        "temperature_c", "wind_speed_kmh", "solar_radiation_wm2", #weather generation
        "price_lag_24h", "price_lag_48h", "price_lag_168h", #historical price correlation
        "price_rolling_mean_24h", "price_rolling_std_24h" #baseline level and volatility
    ]
    #dependent target variable to predict
    target = "price_eur_mwh"

    X = dataset[features]
    y = dataset[target]

    #CHRONOLOGICAL TRAINING 

    split_idx = int(len(dataset) * 0.8)
    X_train, X_test = X.iloc[:split_idx], X.iloc[split_idx:]
    y_train, y_test = y.iloc[:split_idx], y.iloc[split_idx:]

    print(f"Training on {len(X_train)} samples, testing on {len(X_test)} samples...")

    #LIGHTGBM MODEL INITIALIZATION AND TRAINING

    model = lgb.LGBMRegressor(
        n_estimators=600, #max decision trees to build
        learning_rate=0.03, #shrinkage factor per tree step
        max_depth=6, #limit tree depth to control model complexity and prevent overfitting
        num_leaves=31, #max leaf nodes per tree
        subsample=0.8, #row subsampling ratio (train on 80%)
        colsample_bytree=0.8, #selects 80 percent of random features
        random_state=42 #fixed seed for reproducablitity
    )
    # monitor validation loss on (X_test, y_test) halt training if validation score doesn't
    # improve for 30 consecutive boosting iterations, preventing overfitting
    model.fit(
        X_train, y_train,
        eval_set=[(X_test, y_test)],
        callbacks=[lgb.early_stopping(stopping_rounds=30, verbose=False)]
    )

    #MODEL EVALUATION AND ERROR METRICS
    preds = model.predict(X_test)
    #MAE gives the average absolute forecast deviation
    mae = mean_absolute_error(y_test, preds)
    #RMSE penalizes larger price spike prediction errors more severely
    rmse = root_mean_squared_error(y_test, preds)

    print("\n--- MODEL EVALUATION ---")
    print(f"Test MAE:  €{mae:.2f} / MWh")
    print(f"Test RMSE: €{rmse:.2f} / MWh")
    print("------------------------\n")

    #FEATURE IMPORTANCE ANALYSIS
    # ranks features by the number of times they were used across tree split points 
    importance = pd.Series(model.feature_importances_, index=features).sort_values(ascending=False)
    print("Top Predictive Features:")
    print(importance.head(5))

    # MODEL ARTIFACT SERIALIZATION
    # persist the trained estimator along with its expected feature column order into a dictionary artifact
    joblib.dump({"model": model, "features": features}, "price_forecaster_lgb.pkl")
    print("\nModel exported to 'ml/price_forecaster_lgb.pkl'.")


if __name__ == "__main__":
    train_model()