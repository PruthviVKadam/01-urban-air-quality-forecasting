import type { ReactNode } from "react";

/** Loading skeleton block (shimmer defined in index.css; snaps under reduced-motion). */
export function Skeleton({ className = "" }: { className?: string }) {
  return <div className={`skeleton rounded-lg ${className}`} aria-hidden="true" />;
}

interface ErrorStateProps {
  title?: string;
  message: string;
  onRetry?: () => void;
}

/** Explicit error state with a retry affordance — never an infinite spinner (HL5). */
export function ErrorState({ title = "Something went dark", message, onRetry }: ErrorStateProps) {
  return (
    <div
      role="alert"
      className="flex flex-col items-start gap-3 rounded-card border border-aqi-unhealthy/30 bg-night-800/60 p-6"
    >
      <p className="font-display text-lg text-mist-200">{title}</p>
      <p className="text-sm text-mist-400">{message}</p>
      {onRetry && (
        <button
          type="button"
          onClick={onRetry}
          className="mt-1 rounded-full border border-clean-400/40 bg-clean-500/10 px-4 py-1.5 text-sm font-medium text-clean-300 transition hover:bg-clean-500/20"
        >
          Retry
        </button>
      )}
    </div>
  );
}

export function EmptyState({ children }: { children: ReactNode }) {
  return (
    <div className="rounded-card border border-night-600/60 bg-night-850/50 p-6 text-sm text-mist-400">
      {children}
    </div>
  );
}
