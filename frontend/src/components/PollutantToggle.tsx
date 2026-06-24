import { motion } from "framer-motion";
import { cn } from "../lib/utils";
import type { Pollutant } from "../api/client";

interface PollutantToggleProps {
  selected: Pollutant;
  onSelect: (p: Pollutant) => void;
}

const POLLUTANTS: { id: Pollutant; label: string }[] = [
  { id: "pm25", label: "PM₂.₅" },
  { id: "o3", label: "O₃" },
  { id: "no2", label: "NO₂" },
];

export function PollutantToggle({ selected, onSelect }: PollutantToggleProps) {
  return (
    <div className="flex bg-night-800/80 backdrop-blur-md rounded-full p-1 border border-night-600 shadow-lg">
      {POLLUTANTS.map((pol) => {
        const isSelected = selected === pol.id;
        return (
          <button
            key={pol.id}
            onClick={() => onSelect(pol.id)}
            className={cn(
              "relative px-4 py-2 text-sm font-medium transition-colors focus:outline-none rounded-full",
              isSelected ? "text-night-950" : "text-mist-400 hover:text-mist-200"
            )}
            aria-pressed={isSelected}
          >
            {isSelected && (
              <motion.div
                layoutId="pollutant-pill"
                className="absolute inset-0 bg-clean-400 rounded-full"
                initial={false}
                transition={{ type: "spring", stiffness: 500, damping: 30 }}
              />
            )}
            <span className="relative z-10">{pol.label}</span>
          </button>
        );
      })}
    </div>
  );
}
