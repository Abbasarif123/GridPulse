import asyncio
import json
import random
from contextlib import asynccontextmanager
from typing import List

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

import sys
sys.path.append("..")
from core.optimizer import IndustrialBatteryOptimizer


#WEBSOCKET CONNECTION MANAGER
class ConnectionManager:
    """t
        tracks active client WebSocket connections and broadcasts telemetry frames to all connected frontends concurrently
    """
    def __init__(self):
        #in memory registry of active client websocket connections
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket): #accept the incoming handshake and registers the socket connection
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket): #removes the socket from registry
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)

    async def broadcast(self, message: dict): #broadcasts a JSON serializable message to all active clients
        for connection in list(self.active_connections):
            try:
                await connection.send_json(message)
            except Exception:
                self.disconnect(connection) #handle dropped or unresponsive socket gracefully


manager = ConnectionManager() #global instance managing connected dashboard clients

#in memory microgrid state store
class MicrogridState: 
    """holds the live physical and economic state of the on-site microgrid"""
    def __init__(self):
        #battery physical parameters
        self.capacity_kwh = 600.0
        self.max_power_kw = 300.0
        self.current_soc_kwh = 380.0
        self.current_soc_pct = (380.0 / 600.0) * 100
        #real time power balance variables
        self.factory_load_kw = 280.0 #gross factory power consumption
        self.pv_generation_kw = 120.0 #on site solar pv generation
        self.battery_power_kw = 0.0  # + = discharge, - = charge (storage flow)
        self.grid_power_kw = 160.0  #net grid import power
        #financial and operational metadata
        self.spot_price_eur_kwh = 0.18
        self.mode = "AUTONOMOUS_ARBITRAGE"  # Operating strategies: "AUTONOMOUS_ARBITRAGE" or 'PEAK_SHAVING_ONLY', 'MANUAL'
        self.cumulative_savings_eur = 342.50
        self.sim_hour = 14

    def to_dict(self):
        """serializes current state values into a clean dictionary with rounded floats"""
        return {
            "capacity_kwh": self.capacity_kwh,
            "max_power_kw": self.max_power_kw,
            "soc_kwh": round(self.current_soc_kwh, 2),
            "soc_pct": round(self.current_soc_pct, 1),
            "factory_load_kw": round(self.factory_load_kw, 1),
            "pv_generation_kw": round(self.pv_generation_kw, 1),
            "battery_power_kw": round(self.battery_power_kw, 1),
            "grid_power_kw": round(self.grid_power_kw, 1),
            "spot_price_eur_kwh": round(self.spot_price_eur_kwh, 4),
            "mode": self.mode,
            "cumulative_savings_eur": round(self.cumulative_savings_eur, 2),
            "sim_hour": self.sim_hour,
        }

#microgrid state shared across HTTP requests and websocket streams
state = MicrogridState()


#BACKGROUND TELEMETRY SIMULATION LOOP
async def telemetry_simulation_loop():
    """Simulates 1-second ticks representing real-time microgrid dynamics,heuristic battery dispatch and real time metrics to connected clients"""
    while True:
        #non blocking tick pause
        await asyncio.sleep(1.0)

        #injecting stochastic variations to simulate real sensor noise        
        state.factory_load_kw = max(100.0, state.factory_load_kw + random.uniform(-15.0, 15.0))
        state.pv_generation_kw = max(0.0, state.pv_generation_kw + random.uniform(-5.0, 5.0))
        
        # net load that is served after deducting solar generation
        net_factory_need = state.factory_load_kw - state.pv_generation_kw
        
        # real time heuristic dispatch logic
        if state.mode == "AUTONOMOUS_ARBITRAGE":
            if state.spot_price_eur_kwh > 0.25 and state.current_soc_pct > 15:
                # discharge during price peaks to offset expensive grid import
                state.battery_power_kw = min(state.max_power_kw, net_factory_need * 0.7)
            elif state.spot_price_eur_kwh < 0.08 and state.current_soc_pct < 90:
                # charging during dip in price
                state.battery_power_kw = -min(state.max_power_kw, 150.0)
            else:
                state.battery_power_kw = 0.0 #otherwise idle
        
        #updating the SOC dynamics over the 1 second interval
        delta_kwh = (-state.battery_power_kw * (1.0 / 3600.0)) #1 second
        state.current_soc_kwh = max(60.0, min(state.capacity_kwh * 0.95, state.current_soc_kwh + delta_kwh))#enfore buffer limits 10 to 90%
        state.current_soc_pct = (state.current_soc_kwh / state.capacity_kwh) * 100
        
        #grid power balances everything: Grid = Factory - PV - Battery
        state.grid_power_kw = max(0.0, net_factory_need - state.battery_power_kw)
        
        #compute financial savings per second tick
        baseline_cost_tick = (net_factory_need * (1.0 / 3600.0)) * state.spot_price_eur_kwh
        actual_cost_tick = (state.grid_power_kw * (1.0 / 3600.0)) * state.spot_price_eur_kwh
        state.cumulative_savings_eur += max(0.0, baseline_cost_tick - actual_cost_tick)

        #broadcast live frame to all connected WebSockets
        await manager.broadcast({
            "type": "TELEMETRY_UPDATE",
            "data": state.to_dict()
        })

#FASTAPI APPLICATION LIFESPAN AND INITIALISATION
@asynccontextmanager
async def lifespan(app: FastAPI):
    #create the non blocking background telemetry simulation task
    task = asyncio.create_task(telemetry_simulation_loop())
    yield
    #shutdown
    task.cancel()


#fast api application
app = FastAPI(title="GridPulse Telemetry Engine", lifespan=lifespan)
#enable cross origin resource sharing for local frontend dashboard
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


#REST API ENDPOINTS
@app.get("/api/state")
async def get_state():
    return state.to_dict()


class ControlRequest(BaseModel):
    mode: str
    target_capacity_kwh: float | None = None
    manual_battery_kw: float | None = None


@app.post("/api/control")
async def update_control(req: ControlRequest):
    state.mode = req.mode
    if req.target_capacity_kwh:
        state.capacity_kwh = req.target_capacity_kwh
    if req.manual_battery_kw is not None and req.mode == "MANUAL":
        state.battery_power_kw = req.manual_battery_kw
    return {"status": "success", "updated_state": state.to_dict()}


@app.post("/api/optimize/24h")
async def run_24h_optimization():
    """Runs full MILP schedule and returns the 24-hour plan."""
    #test 24 hour day ahead spot price profile
    spot_prices = [
        0.08, 0.06, 0.05, 0.04, 0.05, 0.09,
        0.18, 0.32, 0.38, 0.28, 0.22, 0.20,
        0.16, 0.14, 0.12, 0.15, 0.22, 0.35,
        0.42, 0.39, 0.29, 0.20, 0.14, 0.10
    ]
    #test 24 hour day factory load profile profile
    factory_load = [
        120, 110, 110, 110, 120, 180,
        300, 420, 480, 400, 380, 390,
        350, 490, 450, 380, 320, 280,
        220, 200, 160, 140, 130, 120
    ]

    #instantiate the optimiser using current live battery specs
    optimizer = IndustrialBatteryOptimizer(
        capacity_kwh=state.capacity_kwh,
        max_power_kw=state.max_power_kw
    )
    #solve the MILP model
    df, metrics = optimizer.optimize(spot_prices, factory_load)
    
    return {
        "metrics": metrics,
        "schedule": df.to_dict(orient="records")
    }

#websocket endpoint
@app.websocket("/ws/telemetry")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    # immediately emit current state snapshot upon initial handshake
    await websocket.send_json({"type": "INITIAL_STATE", "data": state.to_dict()})
    try:
        while True:
            # listen asynchronously for incoming JSON control messages from the client
            data = await websocket.receive_text()
            payload = json.loads(data)
            if payload.get("action") == "SET_MODE":
                state.mode = payload.get("mode", state.mode)
    except WebSocketDisconnect:
        #deregister upon close or network drop
        manager.disconnect(websocket)