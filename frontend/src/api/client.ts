import type { components } from "./types";

// Types are derived from the backend OpenAPI contract — never hand-synced.
export type Station = components["schemas"]["Station"];
export type LatestReading = components["schemas"]["LatestReading"];
export type ForecastResponse = components["schemas"]["ForecastResponse"];
export type ForecastPoint = components["schemas"]["ForecastPoint"];
export type HealthResponse = components["schemas"]["HealthResponse"];
export type Pollutant = components["schemas"]["Pollutant"];
export type AQICategory = components["schemas"]["AQICategory"];

export const BASE_URL = (
  import.meta.env.VITE_API_BASE_URL ?? "http://127.0.0.1:8000"
).replace(/\/$/, "");

const REQUEST_TIMEOUT_MS = 6000;

/** Network/HTTP failure surfaced to the UI so it can render an honest error state. */
export class ApiError extends Error {
  readonly status: number | null;
  constructor(message: string, status: number | null) {
    super(message);
    this.name = "ApiError";
    this.status = status;
  }
}

async function getJson<T>(path: string, signal?: AbortSignal): Promise<T> {
  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), REQUEST_TIMEOUT_MS);
  signal?.addEventListener("abort", () => controller.abort());
  try {
    const res = await fetch(`${BASE_URL}${path}`, {
      headers: { Accept: "application/json" },
      signal: controller.signal,
    });
    if (!res.ok) {
      let detail = res.statusText;
      try {
        const body = (await res.json()) as { detail?: string; error?: string };
        detail = body.detail ?? body.error ?? detail;
      } catch {
        /* response had no JSON body */
      }
      throw new ApiError(detail || `Request failed (${res.status})`, res.status);
    }
    return (await res.json()) as T;
  } catch (err) {
    if (err instanceof ApiError) throw err;
    if (err instanceof DOMException && err.name === "AbortError") {
      throw new ApiError("Request timed out.", null);
    }
    throw new ApiError("Could not reach the forecast API. Is the backend running?", null);
  } finally {
    clearTimeout(timeout);
  }
}

export interface ForecastQuery {
  stationId: string;
  pollutant: Pollutant;
  horizon: number;
}

export const api = {
  health: (signal?: AbortSignal) => getJson<HealthResponse>("/health", signal),
  stations: (signal?: AbortSignal) => getJson<Station[]>("/stations", signal),
  forecast: (q: ForecastQuery, signal?: AbortSignal) =>
    getJson<ForecastResponse>(
      `/forecast?station_id=${encodeURIComponent(q.stationId)}` +
        `&pollutant=${q.pollutant}&horizon=${q.horizon}`,
      signal,
    ),
};
