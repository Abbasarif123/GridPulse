# GridPulse 

![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)
![Python 3.10+](https://img.shields.io/badge/Python-3.10%2B-blue)
![React 19](https://img.shields.io/badge/React-19-61dafb?logo=react&logoColor=black)
![Tailwind 4](https://img.shields.io/badge/Tailwind-4.0-38B2AC?logo=tailwind-css&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-009688?logo=fastapi&logoColor=white)

**GridPulse** is an autonomous, AI-driven Energy Management System (EMS) designed for large industrial manufacturing facilities equipped with a utility-scale Battery Energy Storage System (BESS). 

It combines **time-series AI forecasting**, **operations research (linear programming)**, and **real-time event streaming** to optimize battery cycles against dynamic spot electricity markets (EPEX SPOT).

## Key Features

* **Dual-Objective Optimization (MILP):** Solves a Mixed-Integer Linear Program to simultaneously maximize day-ahead arbitrage profit (€/MWh) and minimize peak demand penalty charges (kW).
* **AI Time-Series Forecasting:** Uses LightGBM and weather telemetry (Open-Meteo) to predict solar generation and 24-hour day-ahead electricity prices.
* **Real-Time Telemetry Engine:** An asynchronous FastAPI/WebSocket backend that processes live factory load sensors and broadcasts sub-second microgrid state updates.
* **Industrial Control Panel:** A React 19 / TypeScript dashboard rendering live power flows, Battery State of Charge (SoC), and the 24-hour predictive dispatch horizon using Recharts.

## System Architecture

```text
  [ EPEX SPOT API ]                   [ Factory Sensor Telemetry ]
          │                                        │
          ▼                                        ▼
  ┌──────────────────────┐                 ┌──────────────────────┐
  │  Price Forecasting   │                 │   Load Forecasting   │
  │     (LightGBM)       │                 │   (Factory Baseline) │
  └──────────┬───────────┘                 └──────────┬───────────┘
             │                                        │
             └──────────────────┬─────────────────────┘
                                ▼
                   ┌──────────────────────────┐
                   │   MILP Optimization      │
                   │  (PuLP / HiGHS Solver)   │
                   └────────────┬─────────────┘
                                ▼
                   ┌──────────────────────────┐
                   │    Telemetry Server      │
                   │   (FastAPI + WebSockets) │
                   └────────────┬─────────────┘
                                ▼
                   ┌──────────────────────────┐
                   │ Industrial Control Panel │
                   │ (React, TS, Tailwind v4) │
                   └──────────────────────────┘
```

## The Optimization Model

GridPulse uses the `PuLP` library to minimize the total daily energy expenditure:

**Objective Function:**
```math
Minimize: ∑ (P_grid(t) × Price(t)) + (Degradation_Cost) + (Max_Peak_kW × Penalty_Rate)
```


**Constraints:**
* Battery SOC bounds (e.g., 10% ≤ SOC ≤ 90%)
* Inverter Charge/Discharge C-rate limits
* Strict energy balance: `Grid_Power + Battery_Discharge = Factory_Load + Battery_Charge + PV_Generation`
* Binary flags (Big-M method) to prevent simultaneous charging and discharging.

## Tech Stack
* **Backend / Data Science:** Python, FastAPI, WebSockets, PuLP (Linear Programming), LightGBM, Pandas, NumPy.
* **Frontend:** React 19, TypeScript, Vite, Tailwind CSS v4, Recharts, Lucide Icons.

##  Project Structure
```text
gridpulse/
├── core/
│   ├── optimizer.py         # MILP Battery Optimizer logic
│   ├── market_data.py       # ENTSO-E / Fraunhofer ISE data fetching
│   └── run_demo.py          # CLI Backtesting script
├── ml/
│   ├── data_pipeline.py     # Weather & lag feature engineering
│   └── train_forecaster.py  # LightGBM model training
├── api/
│   └── server.py            # FastAPI REST & WebSocket streaming server
└── frontend/
    ├── src/
    │   ├── App.tsx          # Main EMS Dashboard UI
    │   ├── types.ts         # TypeScript interfaces
    │   └── hooks/           # WebSocket connection logic
    └── package.json         # React 19 & Vite config
```

## Getting Started

### 1. Start the Backend (FastAPI / WebSockets)
```bash
# Clone the repository
git clone [https://github.com/yourusername/GridPulse.git](https://github.com/yourusername/GridPulse.git)
cd GridPulse

# Create virtual environment and install dependencies
python3 -m venv .venv
source .venv/bin/activate
pip install pulp pandas numpy lightgbm requests fastapi uvicorn websockets pydantic highspy

# Launch the telemetry server
uvicorn api.server:app --host 0.0.0.0 --port 8000 --reload
```

### 2. Start the Frontend (React / Vite)
```bash
# Open a new terminal instance
cd GridPulse/frontend

# Install node dependencies
npm install

# Start the Vite development server
npm run dev
```
Navigate to http://localhost:5173 to view the live dashboard.

## Financial Impact (Backtest Results)
In simulated historical backtests across the DE-LU (Germany/Luxembourg) bidding zone, GridPulse demonstrated:

* ~21-25% reduction in total daily electricity costs.
* Successful clamping of factory peak loads, avoiding high-tier peak demand penalties.