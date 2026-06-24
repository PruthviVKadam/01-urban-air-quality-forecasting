import { useMemo } from "react";
import MapLibre, { Marker } from "react-map-gl/maplibre";
import type { Station, ForecastResponse } from "../api/client";
import { cn } from "../lib/utils";
import "maplibre-gl/dist/maplibre-gl.css";

interface MapProps {
  stations: Station[];
  forecasts: Record<string, ForecastResponse | null>;
  horizonHour: number;
  selectedStationId: string | null;
  onSelectStation: (id: string | null) => void;
}

const AQI_COLORS: Record<string, string> = {
  good: "var(--color-aqi-good)",
  moderate: "var(--color-aqi-moderate)",
  unhealthy_sensitive: "var(--color-aqi-usg)",
  unhealthy: "var(--color-aqi-unhealthy)",
  very_unhealthy: "var(--color-aqi-veryunhealthy)",
  hazardous: "var(--color-aqi-hazardous)",
};

export function Map({
  stations,
  forecasts,
  horizonHour,
  selectedStationId,
  onSelectStation,
}: MapProps) {
  // Center roughly on the first station if any, or a default fallback
  const initialViewState = useMemo(() => {
    if (stations.length > 0) {
      return {
        longitude: stations[0].coordinates.lon,
        latitude: stations[0].coordinates.lat,
        zoom: 10,
      };
    }
    return { longitude: -74.006, latitude: 40.7128, zoom: 10 }; // NYC fallback
  }, [stations]);

  return (
    <div className="absolute inset-0 w-full h-full">
      <MapLibre
        initialViewState={initialViewState}
        mapStyle="https://basemaps.cartocdn.com/gl/dark-matter-gl-style/style.json"
        interactiveLayerIds={["stations"]}
        onClick={(e) => {
          // If clicked on background, deselect
          if (!e.features || e.features.length === 0) {
            onSelectStation(null);
          }
        }}
      >
        {stations.map((station) => {
          const forecast = forecasts[station.id];
          
          let aqiCategory = "good";
          let aqiValue = 0;
          let isStale = station.stale;
          
          if (horizonHour === 0) {
            const reading = station.latest[0];
            if (reading) {
              aqiCategory = reading.category;
              aqiValue = reading.aqi;
            }
          } else if (forecast && forecast.points.length >= horizonHour) {
            const pt = forecast.points[horizonHour - 1];
            if (pt) {
              aqiCategory = pt.category;
              aqiValue = pt.aqi;
              isStale = forecast.stale;
            }
          }

          const color = AQI_COLORS[aqiCategory] || AQI_COLORS.good;
          const isSelected = station.id === selectedStationId;

          return (
            <Marker
              key={station.id}
              longitude={station.coordinates.lon}
              latitude={station.coordinates.lat}
              anchor="center"
              onClick={(e) => {
                e.originalEvent.stopPropagation();
                onSelectStation(station.id);
              }}
            >
              <div
                className={cn(
                  "relative flex items-center justify-center rounded-full transition-all duration-300 ease-spring cursor-pointer shadow-lg",
                  isSelected ? "w-12 h-12 z-20" : "w-8 h-8 z-10 hover:scale-110",
                  isStale && "opacity-50 grayscale"
                )}
                style={{ backgroundColor: color }}
                title={`${station.name} - AQI: ${aqiValue}`}
              >
                {/* Pulse ring for selected station */}
                {isSelected && (
                  <span
                    className="absolute inset-0 rounded-full animate-ping opacity-50"
                    style={{ backgroundColor: color }}
                  />
                )}
                <span className="font-display font-bold text-night-950 text-xs shadow-none">
                  {aqiValue}
                </span>
              </div>
            </Marker>
          );
        })}
      </MapLibre>
    </div>
  );
}
