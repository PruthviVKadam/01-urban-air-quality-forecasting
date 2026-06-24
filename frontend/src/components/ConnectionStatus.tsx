import { api } from "../api/client";
import { useApi } from "../hooks/useApi";

/** Live backend health chip in the header. Interactive: retries on click when down. */
export function ConnectionStatus() {
  const { data, error, loading, refresh } = useApi((signal) => api.health(signal));

  let dot = "bg-mist-500";
  let text = "Connecting…";
  if (!loading && error) {
    dot = "bg-aqi-unhealthy";
    text = "API offline";
  } else if (data) {
    dot = "bg-clean-400";
    text = `API online · v${data.version}`;
  }

  return (
    <button
      type="button"
      onClick={refresh}
      title={error ? error.message : "Backend health — click to refresh"}
      className="inline-flex items-center gap-2 rounded-full border border-night-600/70 bg-night-800/60 px-3 py-1.5 text-xs font-medium text-mist-300 transition hover:border-clean-400/40"
    >
      <span className={`h-2 w-2 rounded-full ${dot}`} aria-hidden="true" />
      {text}
    </button>
  );
}
