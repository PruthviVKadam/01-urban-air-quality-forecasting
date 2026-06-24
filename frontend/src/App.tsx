import { useEffect, useState, useMemo } from "react";
import { api, type Station, type ForecastResponse } from "./api/client";
import { useAppState } from "./hooks/useAppState";
import { ConnectionStatus } from "./components/ConnectionStatus";
import { Map } from "./components/Map";
import { HorizonScrubber } from "./components/HorizonScrubber";
import { PollutantToggle } from "./components/PollutantToggle";
import { ForecastPanel } from "./components/ForecastPanel";

export function App() {
  const {
    selectedPollutant,
    setSelectedPollutant,
    horizonHour,
    setHorizonHour,
    selectedStationId,
    setSelectedStationId,
    isPlaying,
    togglePlay,
  } = useAppState();

  const [stations, setStations] = useState<Station[]>([]);
  const [forecasts, setForecasts] = useState<Record<string, ForecastResponse | null>>({});

  // Initial fetch of stations
  useEffect(() => {
    const controller = new AbortController();
    api.stations(controller.signal)
      .then((data) => {
        setStations(data);
      })
      .catch((err) => {
        if (err.name !== "ApiError" || err.message !== "Request timed out.") {
          console.error("Failed to fetch stations:", err);
        }
      });
    return () => controller.abort();
  }, []);

  // Fetch forecasts when pollutant or stations change
  useEffect(() => {
    if (stations.length === 0) return;

    const controller = new AbortController();
    
    // Set all to null initially to show loading skeleton in panels if open
    setForecasts((prev) => {
      const next = { ...prev };
      stations.forEach(s => { next[s.id] = null; });
      return next;
    });

    const fetchAll = async () => {
      const promises = stations.map(async (station) => {
        try {
          const res = await api.forecast(
            { stationId: station.id, pollutant: selectedPollutant, horizon: 24 },
            controller.signal
          );
          return { id: station.id, data: res };
        } catch (e) {
          console.warn(`Forecast fetch failed for ${station.id}`, e);
          return { id: station.id, data: null };
        }
      });

      const results = await Promise.all(promises);
      if (controller.signal.aborted) return;
      
      const newForecasts: Record<string, ForecastResponse | null> = {};
      results.forEach((r) => {
        newForecasts[r.id] = r.data;
      });
      setForecasts(newForecasts);
    };

    fetchAll();
    return () => controller.abort();
  }, [stations, selectedPollutant]);

  const selectedStation = useMemo(() => {
    return stations.find((s) => s.id === selectedStationId) || null;
  }, [stations, selectedStationId]);

  return (
    <div className="relative w-full h-screen overflow-hidden bg-night-950 font-sans text-mist-200">
      <Map
        stations={stations}
        forecasts={forecasts}
        horizonHour={horizonHour}
        selectedStationId={selectedStationId}
        onSelectStation={setSelectedStationId}
      />

      {/* Top Header Layer */}
      <header className="absolute top-0 inset-x-0 z-10 flex items-center justify-between p-4 sm:p-6 pointer-events-none">
        <div className="flex items-center gap-3 pointer-events-auto bg-night-950/40 backdrop-blur-md rounded-full pr-4 p-2 border border-night-700/50">
          <span
            className="block h-8 w-8 rounded-full bg-gradient-to-br from-clean-300 via-clean-500 to-night-700 shadow-inner"
            aria-hidden="true"
          />
          <div className="leading-none flex flex-col justify-center">
            <h1 className="font-display text-lg font-bold tracking-tight text-mist-100">
              Atmosphere
            </h1>
          </div>
        </div>
        <div className="pointer-events-auto">
          <ConnectionStatus />
        </div>
      </header>

      {/* Main Controls - Bottom Center */}
      <div className="absolute bottom-8 inset-x-0 z-10 flex flex-col items-center gap-4 pointer-events-none">
        <div className="pointer-events-auto w-full max-w-md px-4">
          <HorizonScrubber
            horizonHour={horizonHour}
            setHorizonHour={setHorizonHour}
            isPlaying={isPlaying}
            togglePlay={togglePlay}
          />
        </div>
        <div className="pointer-events-auto">
          <PollutantToggle
            selected={selectedPollutant}
            onSelect={setSelectedPollutant}
          />
        </div>
      </div>

      {/* Forecast Panel (Slides in when station is selected) */}
      {selectedStation && (
        <ForecastPanel
          station={selectedStation}
          forecast={forecasts[selectedStation.id] || null}
          horizonHour={horizonHour}
          onClose={() => setSelectedStationId(null)}
        />
      )}
    </div>
  );
}
