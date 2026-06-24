import { useMemo } from "react";
import {
  Area,
  AreaChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
  ReferenceLine,
} from "recharts";
import { CheckCircle2, ShieldAlert } from "lucide-react";
import { cn } from "../lib/utils";
import type { ForecastResponse, Station } from "../api/client";

interface ForecastPanelProps {
  station: Station;
  forecast: ForecastResponse | null;
  horizonHour: number;
  onClose: () => void;
}

export function ForecastPanel({ station, forecast, horizonHour, onClose }: ForecastPanelProps) {
  const chartData = useMemo(() => {
    if (!forecast) return [];
    
    // We can prepend the "latest" value at T=0
    const t0 = new Date(station.latest[0]?.observed_at || new Date()).getTime();
    const data = [
      {
        ts: t0,
        label: "Now",
        value: station.latest[0]?.value || 0,
        baseline: station.latest[0]?.value || 0,
        lower: station.latest[0]?.value || 0,
        upper: station.latest[0]?.value || 0,
      },
    ];

    forecast.points.forEach((pt) => {
      const ts = new Date(pt.ts).getTime();
      const hour = new Date(pt.ts).getHours();
      data.push({
        ts,
        label: `${hour}:00`,
        value: pt.value,
        baseline: pt.baseline,
        lower: pt.lower,
        upper: pt.upper,
      });
    });

    return data;
  }, [station, forecast]);

  if (!forecast) {
    return (
      <div className="absolute top-4 right-4 w-80 rounded-card border border-night-600 bg-night-800/90 p-6 backdrop-blur-xl shadow-2xl flex flex-col justify-center items-center h-64 z-20">
        <div className="skeleton w-3/4 h-6 rounded-md mb-4" />
        <div className="skeleton w-full h-32 rounded-md" />
      </div>
    );
  }

  // Calculate the X position of the horizon line
  const currentHorizonPoint = chartData[horizonHour];

  return (
    <div className="absolute top-4 right-4 w-96 max-h-[calc(100vh-2rem)] overflow-y-auto rounded-card border border-night-600 bg-night-800/90 p-5 backdrop-blur-xl shadow-2xl z-20 transition-all duration-300">
      <div className="flex justify-between items-start mb-4">
        <div>
          <h2 className="font-display text-xl font-bold text-mist-100">{station.name}</h2>
          <p className="text-xs text-mist-400">{station.city}, {station.country}</p>
        </div>
        <button onClick={onClose} className="text-mist-400 hover:text-mist-200" aria-label="Close panel">
          &times;
        </button>
      </div>

      <div className="mb-6 flex gap-2 flex-wrap">
        {/* HL1 Freshness Badge */}
        <div className={cn(
          "inline-flex items-center gap-1.5 rounded-full px-2.5 py-1 text-xs font-medium border",
          forecast.stale 
            ? "bg-amber-900/30 text-amber-400 border-amber-800/50" 
            : "bg-clean-900/20 text-clean-400 border-clean-800/40"
        )}>
          {forecast.stale ? <ShieldAlert size={14} /> : <CheckCircle2 size={14} />}
          {forecast.stale ? "Stale Data" : "Live"}
        </div>
        
        {/* HL2 Model vs Baseline Badge */}
        <div className={cn(
          "inline-flex items-center gap-1.5 rounded-full px-2.5 py-1 text-xs font-medium border",
          forecast.beats_baseline 
            ? "bg-clean-900/20 text-clean-400 border-clean-800/40" 
            : "bg-night-700/50 text-mist-400 border-night-600"
        )}>
          {forecast.beats_baseline ? "Beats Baseline" : `Fallback: ${forecast.baseline_label}`}
        </div>
      </div>

      <div className="h-48 w-full -ml-4">
        <ResponsiveContainer width="100%" height="100%">
          <AreaChart data={chartData} margin={{ top: 5, right: 0, left: 0, bottom: 0 }}>
            <defs>
              <linearGradient id="colorValue" x1="0" y1="0" x2="0" y2="1">
                <stop offset="5%" stopColor="var(--color-clean-400)" stopOpacity={0.3}/>
                <stop offset="95%" stopColor="var(--color-clean-400)" stopOpacity={0}/>
              </linearGradient>
            </defs>
            <XAxis dataKey="label" stroke="var(--color-night-600)" tick={{ fill: "var(--color-mist-500)", fontSize: 10 }} tickLine={false} axisLine={false} />
            <YAxis stroke="var(--color-night-600)" tick={{ fill: "var(--color-mist-500)", fontSize: 10 }} tickLine={false} axisLine={false} width={40} />
            <Tooltip 
              contentStyle={{ backgroundColor: "var(--color-night-800)", borderColor: "var(--color-night-600)", borderRadius: "8px" }}
              itemStyle={{ color: "var(--color-mist-200)" }}
              labelStyle={{ color: "var(--color-mist-400)", marginBottom: "4px" }}
            />
            {/* Confidence Interval Area */}
            <Area type="monotone" dataKey="upper" stroke="none" fill="var(--color-night-600)" fillOpacity={0.2} />
            <Area type="monotone" dataKey="lower" stroke="none" fill="var(--color-night-800)" fillOpacity={1} />
            
            {/* Baseline Line */}
            <Area type="step" dataKey="baseline" stroke="var(--color-mist-500)" strokeDasharray="3 3" fill="none" />
            
            {/* Predicted Value */}
            <Area type="monotone" dataKey="value" stroke="var(--color-clean-400)" strokeWidth={2} fillOpacity={1} fill="url(#colorValue)" />
            
            {currentHorizonPoint && (
              <ReferenceLine x={currentHorizonPoint.label} stroke="var(--color-mist-300)" strokeDasharray="3 3" />
            )}
          </AreaChart>
        </ResponsiveContainer>
      </div>
      
      <div className="mt-4 text-[10px] text-mist-500 leading-tight">
        {forecast.disclaimer}
      </div>
    </div>
  );
}
