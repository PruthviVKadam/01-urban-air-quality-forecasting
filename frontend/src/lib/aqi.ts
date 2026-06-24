import type { AQICategory } from "../api/client";

export type AqiShape = "circle" | "triangle" | "diamond" | "square" | "pentagon" | "hexagon";

export interface CategoryStyle {
  label: string;
  /** CSS custom property reference into the Atmosphere AQI ramp. */
  color: string;
  /** Non-color cue paired with every color use (rules.md G4). */
  shape: AqiShape;
}

export const AQI_STYLES: Record<AQICategory, CategoryStyle> = {
  good: { label: "Good", color: "var(--color-aqi-good)", shape: "circle" },
  moderate: { label: "Moderate", color: "var(--color-aqi-moderate)", shape: "triangle" },
  unhealthy_sensitive: {
    label: "Unhealthy for Sensitive Groups",
    color: "var(--color-aqi-usg)",
    shape: "diamond",
  },
  unhealthy: { label: "Unhealthy", color: "var(--color-aqi-unhealthy)", shape: "square" },
  very_unhealthy: {
    label: "Very Unhealthy",
    color: "var(--color-aqi-veryunhealthy)",
    shape: "pentagon",
  },
  hazardous: { label: "Hazardous", color: "var(--color-aqi-hazardous)", shape: "hexagon" },
};

export function categoryStyle(category: AQICategory): CategoryStyle {
  return AQI_STYLES[category];
}

const POLLUTANT_LABELS: Record<string, string> = {
  pm25: "PM₂.₅",
  o3: "O₃",
  no2: "NO₂",
};

export function pollutantLabel(pollutant: string): string {
  return POLLUTANT_LABELS[pollutant] ?? pollutant.toUpperCase();
}
