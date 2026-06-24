import type { LatestReading, Station } from "../api/client";
import { categoryStyle, pollutantLabel } from "../lib/aqi";
import { isStale, relativeTime } from "../lib/freshness";
import { FreshnessBadge, SourceBadge } from "./Badges";
import { CategoryShape } from "./CategoryShape";

function ReadingChip({ reading }: { reading: LatestReading }) {
  const style = categoryStyle(reading.category);
  return (
    <div className="flex items-center gap-2 rounded-lg bg-night-850/70 px-3 py-2">
      <CategoryShape shape={style.shape} color={style.color} title={style.label} />
      <div className="leading-tight">
        <div className="text-xs text-mist-500">{pollutantLabel(reading.pollutant)}</div>
        <div className="font-display text-sm text-mist-200">
          {reading.value}
          <span className="ml-1 text-xs text-mist-500">{reading.unit}</span>
        </div>
      </div>
    </div>
  );
}

export function StationCard({ station }: { station: Station }) {
  const primary =
    station.latest.find((r) => r.pollutant === "pm25") ?? station.latest[0];
  const primaryStyle = categoryStyle(primary.category);
  const stale = isStale(station.data_as_of);

  return (
    <article className="group flex flex-col gap-4 rounded-card border border-night-600/60 bg-night-800/55 p-5 transition hover:border-clean-400/30">
      <header className="flex items-start justify-between gap-3">
        <div>
          <h3 className="font-display text-lg font-semibold text-mist-100">{station.name}</h3>
          <p className="text-sm text-mist-500">
            {station.city}, {station.country}
          </p>
        </div>
        <SourceBadge source={station.data_source} />
      </header>

      <div className="flex items-end gap-4">
        <div className="flex items-baseline gap-2">
          <span
            className="font-display text-5xl font-bold leading-none"
            style={{ color: primaryStyle.color }}
          >
            {primary.aqi}
          </span>
          <span className="text-xs uppercase tracking-wide text-mist-500">AQI</span>
        </div>
        <div className="flex items-center gap-2 pb-1">
          <CategoryShape shape={primaryStyle.shape} color={primaryStyle.color} size={16} />
          <span className="text-sm font-medium" style={{ color: primaryStyle.color }}>
            {primaryStyle.label}
          </span>
        </div>
      </div>

      <div className="grid grid-cols-3 gap-2">
        {station.latest.map((reading) => (
          <ReadingChip key={reading.pollutant} reading={reading} />
        ))}
      </div>

      <footer className="mt-auto">
        <FreshnessBadge label={relativeTime(station.data_as_of)} stale={stale} />
      </footer>
    </article>
  );
}
