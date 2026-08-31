import { useState, useEffect } from "react";
import { useTelemetry } from "./hooks/useTelemetry";
import type { OptimizationResponse } from "./types";
import {
  Zap,
  BatteryCharging,
  TrendingDown,
  Activity,
  Sun,
  Factory,
  ShieldCheck,
  RefreshCw,
} from "lucide-react";
import {
  ResponsiveContainer,
  ComposedChart,
  Line,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  Legend,
  CartesianGrid,
} from "recharts";

export default function App() {
  const { telemetry, isConnected, setOperatingMode } = useTelemetry();
  const [optData, setOptData] = useState<OptimizationResponse | null>(null);
  const [isOptimizing, setIsOptimizing] = useState(false);

  const fetchOptimization = async () => {
    setIsOptimizing(true);
    try {
      const res = await fetch("http://localhost:8000/api/optimize/24h", {
        method: "POST",
      });
      if (!res.ok) throw new Error(`HTTP error! status: ${res.status}`);
      const data: OptimizationResponse = await res.json();
      setOptData(data);
    } catch (err) {
      console.error("Optimization fetch failed:", err);
    } finally {
      setIsOptimizing(false);
    }
  };

  useEffect(() => {
    fetchOptimization();
  }, []);

  return (
    <div className="min-h-screen p-6 max-w-7xl mx-auto space-y-6">
      {/* Header Bar */}
      <header className="flex flex-col md:flex-row items-start md:items-center justify-between pb-4 border-b border-slate-800 gap-4">
        <div>
          <div className="flex items-center gap-2">
            <Zap className="h-7 w-7 text-emerald-400" />
            <h1 className="text-2xl font-bold tracking-tight text-white">
              GridPulse{" "}
              <span className="text-xs px-2 py-0.5 rounded bg-emerald-950 text-emerald-400 border border-emerald-800 font-mono">
                BESS EMS v1.0
              </span>
            </h1>
          </div>
          <p className="text-sm text-slate-400">
            Autonomous Industrial Microgrid Arbitrage & Peak Shaver
          </p>
        </div>

        <div className="flex items-center gap-4">
          <div className="flex items-center gap-2 text-xs font-mono bg-slate-900 px-3 py-1.5 rounded-full border border-slate-800">
            <span
              className={`h-2.5 w-2.5 rounded-full ${
                isConnected ? "bg-emerald-500 animate-pulse" : "bg-rose-500"
              }`}
            />
            {isConnected ? "WEBSOCKET LIVE" : "DISCONNECTED"}
          </div>

          <button
            onClick={fetchOptimization}
            disabled={isOptimizing}
            className="flex items-center gap-1.5 px-3.5 py-1.5 bg-slate-800 hover:bg-slate-700 text-slate-200 text-sm font-medium rounded-lg border border-slate-700 transition"
          >
            <RefreshCw className={`h-4 w-4 ${isOptimizing ? "animate-spin" : ""}`} />
            Re-solve MILP
          </button>
        </div>
      </header>

      {/* Real-time KPI Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        {/* State of Charge */}
        <div className="bg-slate-900 border border-slate-800 p-4 rounded-xl relative overflow-hidden">
          <div className="flex justify-between items-start">
            <span className="text-xs font-medium text-slate-400 uppercase tracking-wider">
              Battery SoC
            </span>
            <BatteryCharging className="h-5 w-5 text-emerald-400" />
          </div>
          <div className="mt-3 flex items-baseline gap-2">
            <span className="text-3xl font-bold font-mono text-white">
              {telemetry ? telemetry.soc_pct.toFixed(1) : "--"}%
            </span>
            <span className="text-xs text-slate-400 font-mono">
              ({telemetry ? telemetry.soc_kwh.toFixed(0) : "--"} /{" "}
              {telemetry?.capacity_kwh ?? 600} kWh)
            </span>
          </div>
          <div className="w-full bg-slate-800 h-1.5 rounded-full mt-3 overflow-hidden">
            <div
              className="bg-emerald-400 h-full transition-all duration-500"
              style={{ width: `${telemetry?.soc_pct || 0}%` }}
            />
          </div>
        </div>

        {/* Spot Price */}
        <div className="bg-slate-900 border border-slate-800 p-4 rounded-xl">
          <div className="flex justify-between items-start">
            <span className="text-xs font-medium text-slate-400 uppercase tracking-wider">
              Live Spot Tariff
            </span>
            <TrendingDown className="h-5 w-5 text-cyan-400" />
          </div>
          <div className="mt-3">
            <span className="text-3xl font-bold font-mono text-white">
              €{telemetry ? telemetry.spot_price_eur_kwh.toFixed(3) : "--"}
            </span>
            <span className="text-xs text-slate-400 font-mono ml-1">/ kWh</span>
          </div>
          <p className="text-xs text-cyan-400/80 mt-2 font-mono">
            EPEX SPOT (DE-LU Zone)
          </p>
        </div>

        {/* Real-time Grid Import */}
        <div className="bg-slate-900 border border-slate-800 p-4 rounded-xl">
          <div className="flex justify-between items-start">
            <span className="text-xs font-medium text-slate-400 uppercase tracking-wider">
              Active Grid Import
            </span>
            <Activity className="h-5 w-5 text-amber-400" />
          </div>
          <div className="mt-3 flex items-baseline gap-2">
            <span className="text-3xl font-bold font-mono text-white">
              {telemetry ? telemetry.grid_power_kw.toFixed(1) : "--"}
            </span>
            <span className="text-xs text-slate-400 font-mono">kW</span>
          </div>
          <div className="text-xs text-slate-400 mt-2 flex gap-3">
            <span>Load: {telemetry ? telemetry.factory_load_kw.toFixed(0) : "--"} kW</span>
            <span>PV: {telemetry ? telemetry.pv_generation_kw.toFixed(0) : "--"} kW</span>
          </div>
        </div>

        {/* Cumulative Daily Savings */}
        <div className="bg-slate-900 border border-slate-800 p-4 rounded-xl">
          <div className="flex justify-between items-start">
            <span className="text-xs font-medium text-slate-400 uppercase tracking-wider">
              Cumulative Savings
            </span>
            <ShieldCheck className="h-5 w-5 text-indigo-400" />
          </div>
          <div className="mt-3">
            <span className="text-3xl font-bold font-mono text-emerald-400">
              €{telemetry ? telemetry.cumulative_savings_eur.toFixed(2) : "--"}
            </span>
          </div>
          <p className="text-xs text-slate-400 mt-2">
            {optData
              ? `Target: +€${optData.metrics.savings_eur.toFixed(0)}/day (${optData.metrics.savings_pct.toFixed(1)}%)`
              : "Calculating..."}
          </p>
        </div>
      </div>

      {/* Operational Flow & Controls */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className="lg:col-span-2 bg-slate-900 border border-slate-800 p-5 rounded-xl">
          <h2 className="text-base font-semibold text-white mb-4 flex items-center gap-2">
            <Activity className="h-4 w-4 text-emerald-400" /> Microgrid Power Balance
          </h2>

          <div className="grid grid-cols-2 sm:grid-cols-4 gap-4 text-center">
            <div className="p-3 bg-slate-950 rounded-lg border border-slate-800/80">
              <Factory className="h-6 w-6 text-slate-400 mx-auto mb-1" />
              <div className="text-xs text-slate-400">Factory Load</div>
              <div className="text-lg font-bold font-mono text-white">
                {telemetry ? telemetry.factory_load_kw.toFixed(0) : "--"} kW
              </div>
            </div>
            <div className="p-3 bg-slate-950 rounded-lg border border-slate-800/80">
              <Sun className="h-6 w-6 text-amber-400 mx-auto mb-1" />
              <div className="text-xs text-slate-400">Solar PV Array</div>
              <div className="text-lg font-bold font-mono text-white">
                {telemetry ? telemetry.pv_generation_kw.toFixed(0) : "--"} kW
              </div>
            </div>
            <div className="p-3 bg-slate-950 rounded-lg border border-slate-800/80">
              <BatteryCharging className="h-6 w-6 text-emerald-400 mx-auto mb-1" />
              <div className="text-xs text-slate-400">Battery Output</div>
              <div className="text-lg font-bold font-mono text-white">
                {telemetry ? `${telemetry.battery_power_kw.toFixed(0)} kW` : "--"}
              </div>
            </div>
            <div className="p-3 bg-slate-950 rounded-lg border border-slate-800/80">
              <Zap className="h-6 w-6 text-cyan-400 mx-auto mb-1" />
              <div className="text-xs text-slate-400">Grid Import</div>
              <div className="text-lg font-bold font-mono text-white">
                {telemetry ? `${telemetry.grid_power_kw.toFixed(0)} kW` : "--"}
              </div>
            </div>
          </div>
        </div>

        {/* EMS Strategy Controller */}
        <div className="bg-slate-900 border border-slate-800 p-5 rounded-xl">
          <h2 className="text-base font-semibold text-white mb-3">Operating Strategy</h2>
          <div className="space-y-2">
            {[
              { id: "AUTONOMOUS_ARBITRAGE", label: "Autonomous Arbitrage (AI + MILP)" },
              { id: "PEAK_SHAVING_ONLY", label: "Peak Shaving Guard Only" },
              { id: "MANUAL", label: "Manual Override" },
            ].map((mode) => (
              <button
                key={mode.id}
                onClick={() => setOperatingMode(mode.id)}
                className={`w-full text-left px-3.5 py-2.5 rounded-lg text-sm font-medium transition border ${
                  telemetry?.mode === mode.id
                    ? "bg-emerald-950/80 border-emerald-600 text-emerald-200"
                    : "bg-slate-950 border-slate-800 text-slate-400 hover:text-slate-200"
                }`}
              >
                {mode.label}
              </button>
            ))}
          </div>
        </div>
      </div>

      {/* 24-Hour Predictive MILP Horizon Chart */}
      <div className="bg-slate-900 border border-slate-800 p-5 rounded-xl">
        <div className="flex flex-col sm:flex-row justify-between sm:items-center mb-6 gap-2">
          <div>
            <h2 className="text-base font-semibold text-white">
              24-Hour Predictive Dispatch Horizon
            </h2>
            <p className="text-xs text-slate-400">
              Co-optimized Spot Tariff vs. Battery Charge & Peak Shave Schedule
            </p>
          </div>
          {optData && (
            <div className="flex gap-4 text-xs font-mono">
              <span className="text-slate-400">
                Peak Clamped:{" "}
                <strong className="text-amber-400">
                  {optData.metrics.baseline_peak_kw} kW →{" "}
                  {optData.metrics.optimized_peak_kw.toFixed(1)} kW
                </strong>
              </span>
              <span className="text-slate-400">
                Daily Savings:{" "}
                <strong className="text-emerald-400">
                  €{optData.metrics.savings_eur.toFixed(2)}
                </strong>
              </span>
            </div>
          )}
        </div>

        <div className="h-80 w-full min-h-[320px]">
          {optData ? (
            <ResponsiveContainer width="100%" height="100%" minWidth={100} minHeight={300}>
              <ComposedChart data={optData.schedule}>
                <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" />
                <XAxis
                  dataKey="hour"
                  stroke="#64748b"
                  tickFormatter={(h: number) => `${h}:00`}
                />
                <YAxis
                  yAxisId="power"
                  stroke="#64748b"
                  label={{
                    value: "Power (kW)",
                    angle: -90,
                    position: "insideLeft",
                    fill: "#64748b",
                  }}
                />
                <YAxis
                  yAxisId="price"
                  orientation="right"
                  stroke="#06b6d4"
                  label={{
                    value: "Price (€/kWh)",
                    angle: 90,
                    position: "insideRight",
                    fill: "#06b6d4",
                  }}
                />
                <Tooltip
                  contentStyle={{
                    backgroundColor: "#0f172a",
                    borderColor: "#334155",
                    borderRadius: "0.5rem",
                  }}
                  labelFormatter={(h) => `Hour ${h}:00`}
                />
                <Legend />
                <Bar
                  yAxisId="power"
                  dataKey="p_charge_kw"
                  fill="#10b981"
                  name="Charge (kW)"
                  stackId="b"
                />
                <Bar
                  yAxisId="power"
                  dataKey="p_discharge_kw"
                  fill="#f59e0b"
                  name="Discharge (kW)"
                  stackId="b"
                />
                <Line
                  yAxisId="power"
                  type="monotone"
                  dataKey="p_grid_kw"
                  stroke="#94a3b8"
                  strokeWidth={2}
                  dot={false}
                  name="Grid Import (kW)"
                />
                <Line
                  yAxisId="price"
                  type="monotone"
                  dataKey="price_eur_kwh"
                  stroke="#06b6d4"
                  strokeWidth={2}
                  strokeDasharray="4 4"
                  dot={false}
                  name="Spot Price (€/kWh)"
                />
              </ComposedChart>
            </ResponsiveContainer>
          ) : (
            <div className="flex items-center justify-center h-full text-slate-500 font-mono text-sm">
              Loading 24-Hour Optimization Horizon...
            </div>
          )}
        </div>
      </div>
    </div>
  );
}