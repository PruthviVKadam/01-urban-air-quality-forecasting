import type { components } from "../api/types";

type DataSource = components["schemas"]["DataSource"];

/** Freshness chip (HL1). Turns amber when the reading is past the stale threshold. */
export function FreshnessBadge({ label, stale }: { label: string; stale: boolean }) {
  return (
    <span
      className={
        "inline-flex items-center gap-1.5 rounded-full px-2.5 py-0.5 text-xs font-medium " +
        (stale
          ? "bg-aqi-moderate/15 text-aqi-moderate"
          : "bg-night-700/70 text-mist-400")
      }
    >
      <span
        className={
          "h-1.5 w-1.5 rounded-full " + (stale ? "bg-aqi-moderate" : "bg-clean-400")
        }
        aria-hidden="true"
      />
      {stale ? `Stale · ${label}` : label}
    </span>
  );
}

/**
 * Provenance chip. Phase 0 serves clearly-labeled seed data, so the UI never
 * passes a placeholder off as a real measurement (DESIGN.md honesty rule).
 */
export function SourceBadge({ source }: { source: DataSource }) {
  if (source === "live") return null;
  const text = source === "seed" ? "Preview data" : "Cached";
  return (
    <span className="inline-flex items-center rounded-full border border-mist-500/40 px-2.5 py-0.5 text-xs font-medium uppercase tracking-wide text-mist-400">
      {text}
    </span>
  );
}
