import { ConnectionStatus } from "./components/ConnectionStatus";
import { Disclaimer } from "./components/Disclaimer";
import { StationList } from "./components/StationList";

export function App() {
  return (
    <div className="mx-auto flex min-h-screen max-w-6xl flex-col px-5 sm:px-8">
      <header className="flex items-center justify-between gap-4 py-6">
        <div className="flex items-center gap-3">
          <span
            className="block h-7 w-7 rounded-full bg-gradient-to-br from-clean-300 via-clean-500 to-night-700"
            aria-hidden="true"
          />
          <div className="leading-tight">
            <p className="font-display text-lg font-bold tracking-tight text-mist-100">
              Atmosphere
            </p>
            <p className="text-xs text-mist-500">Urban Air Quality Forecasting</p>
          </div>
        </div>
        <ConnectionStatus />
      </header>

      {/* Asymmetric hero — bold statement on the left, status rail on the right.
          Deliberately NOT a centered headline + two pills over a gradient. */}
      <section className="grid items-end gap-6 border-b border-night-700/60 pb-10 pt-4 lg:grid-cols-[1.5fr_1fr]">
        <div>
          <h1 className="font-display text-4xl font-bold leading-[1.05] text-mist-100 sm:text-6xl">
            The city is
            <span className="bg-gradient-to-r from-clean-300 to-aqi-veryunhealthy bg-clip-text text-transparent">
              {" "}
              breathing.
            </span>
          </h1>
          <p className="mt-5 max-w-xl text-base leading-relaxed text-mist-400">
            A living, reliability-first explorer for urban air quality. Every reading carries its
            own freshness, its baseline, and an honest note about how it was produced — no silent
            gaps, no spinners that never end.
          </p>
        </div>
        <aside className="rounded-card border border-night-600/60 bg-night-800/40 p-5 text-sm text-mist-400">
          <p className="font-display text-mist-200">Phase 0 · Foundations</p>
          <p className="mt-2 leading-relaxed">
            The typed contract is live and the resilient shell is wired. The signature
            horizon-scrubber map — drag time forward and watch the city haze and clear — arrives in
            a later phase.
          </p>
        </aside>
      </section>

      <main className="flex-1 py-10">
        <div className="mb-5 flex items-baseline justify-between">
          <h2 className="font-display text-xl font-semibold text-mist-100">
            Live monitoring stations
          </h2>
          <span className="text-xs text-mist-500">latest readings</span>
        </div>
        <StationList />
      </main>

      <footer className="space-y-3 border-t border-night-700/60 py-6">
        <Disclaimer />
        <p className="text-xs text-mist-500">
          Data: OpenAQ (CC BY 4.0), US EPA AirNow, and Open-Meteo (CC BY 4.0). Attribution honored
          per each provider's license.
        </p>
      </footer>
    </div>
  );
}
