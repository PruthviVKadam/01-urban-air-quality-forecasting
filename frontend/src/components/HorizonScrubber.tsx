import { Play, Pause } from "lucide-react";

interface ScrubberProps {
  horizonHour: number;
  setHorizonHour: (val: number) => void;
  isPlaying: boolean;
  togglePlay: () => void;
}

export function HorizonScrubber({
  horizonHour,
  setHorizonHour,
  isPlaying,
  togglePlay,
}: ScrubberProps) {
  return (
    <div className="flex items-center gap-4 bg-night-800/80 backdrop-blur-md border border-night-600 rounded-full px-5 py-3 shadow-xl">
      <button
        onClick={togglePlay}
        className="flex items-center justify-center w-10 h-10 rounded-full bg-clean-400 text-night-950 hover:bg-clean-300 transition-colors focus:outline-none focus-visible:ring-2 focus-visible:ring-offset-2 focus-visible:ring-clean-400 focus-visible:ring-offset-night-900"
        aria-label={isPlaying ? "Pause forecast animation" : "Play forecast animation"}
      >
        {isPlaying ? <Pause size={20} fill="currentColor" /> : <Play size={20} fill="currentColor" className="ml-1" />}
      </button>

      <div className="flex-1 flex flex-col gap-1">
        <div className="flex justify-between text-xs font-medium text-mist-400 px-1">
          <span>Now</span>
          <span className="text-mist-200 font-bold">{horizonHour > 0 ? `+${horizonHour}h` : "Live"}</span>
          <span>+24h</span>
        </div>
        <input
          type="range"
          min="0"
          max="24"
          step="1"
          value={horizonHour}
          onChange={(e) => setHorizonHour(parseInt(e.target.value, 10))}
          className="w-full accent-clean-400 h-2 bg-night-600 rounded-full appearance-none cursor-pointer focus:outline-none focus-visible:ring-2 focus-visible:ring-clean-400"
          style={{
            background: `linear-gradient(to right, var(--color-clean-400) ${(horizonHour / 24) * 100}%, var(--color-night-600) ${(horizonHour / 24) * 100}%)`,
          }}
          aria-label="Scrub forecast horizon"
        />
      </div>
    </div>
  );
}
