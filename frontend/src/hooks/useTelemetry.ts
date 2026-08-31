import { useEffect, useState, useRef } from "react";
import type { TelemetryState } from "../types";

export function useTelemetry(wsUrl: string = "ws://localhost:8000/ws/telemetry") {
  const [telemetry, setTelemetry] = useState<TelemetryState | null>(null);
  const [isConnected, setIsConnected] = useState(false);
  const wsRef = useRef<WebSocket | null>(null);

  useEffect(() => {
    const ws = new WebSocket(wsUrl);
    wsRef.current = ws;

    ws.onopen = () => setIsConnected(true);
    ws.onclose = () => setIsConnected(false);
    ws.onerror = () => setIsConnected(false);

    ws.onmessage = (event) => {
      try {
        const message = JSON.parse(event.data);
        if (message.type === "TELEMETRY_UPDATE" || message.type === "INITIAL_STATE") {
          setTelemetry(message.data);
        }
      } catch (err) {
        console.error("Failed to parse telemetry:", err);
      }
    };

    return () => {
      ws.close();
    };
  }, [wsUrl]);

  const setOperatingMode = (mode: string) => {
    if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify({ action: "SET_MODE", mode }));
    }
  };

  return { telemetry, isConnected, setOperatingMode };
}