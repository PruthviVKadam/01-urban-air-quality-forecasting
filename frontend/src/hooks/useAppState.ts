import { useState, useCallback, useEffect } from "react";
import type { Pollutant } from "../api/client";

export function useAppState() {
  const [selectedPollutant, setSelectedPollutant] = useState<Pollutant>("pm25");
  const [horizonHour, setHorizonHour] = useState<number>(0);
  const [selectedStationId, setSelectedStationId] = useState<string | null>(null);
  const [isPlaying, setIsPlaying] = useState<boolean>(false);

  // Auto-play interval
  useEffect(() => {
    if (!isPlaying) return;

    const interval = setInterval(() => {
      setHorizonHour((prev) => {
        if (prev >= 24) {
          setIsPlaying(false);
          return 24;
        }
        return prev + 1;
      });
    }, 150); // Fast, fluid increment

    return () => clearInterval(interval);
  }, [isPlaying]);

  const togglePlay = useCallback(() => {
    setIsPlaying((p) => !p);
    if (horizonHour >= 24) {
      // restart if at end
      setHorizonHour(0);
      setIsPlaying(true);
    }
  }, [horizonHour]);

  return {
    selectedPollutant,
    setSelectedPollutant,
    horizonHour,
    setHorizonHour,
    selectedStationId,
    setSelectedStationId,
    isPlaying,
    togglePlay,
  };
}
