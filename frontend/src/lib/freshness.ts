const HOUR_MS = 3_600_000;

/** Default staleness threshold mirrors the backend (HL1 — 3 hours). */
export const STALE_THRESHOLD_HOURS = 3;

export function relativeTime(iso: string, now: number = Date.now()): string {
  const minutes = Math.round((now - new Date(iso).getTime()) / 60_000);
  if (minutes <= 0) return "just now";
  if (minutes < 60) return `${minutes} min ago`;
  const hours = Math.round(minutes / 60);
  if (hours < 24) return `${hours} h ago`;
  const days = Math.round(hours / 24);
  return `${days} d ago`;
}

export function isStale(
  iso: string,
  thresholdHours: number = STALE_THRESHOLD_HOURS,
  now: number = Date.now(),
): boolean {
  return now - new Date(iso).getTime() > thresholdHours * HOUR_MS;
}
