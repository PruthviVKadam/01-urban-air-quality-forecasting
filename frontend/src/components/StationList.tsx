import { api } from "../api/client";
import { useApi } from "../hooks/useApi";
import { StationCard } from "./StationCard";
import { EmptyState, ErrorState, Skeleton } from "./StateView";

export function StationList() {
  const { data, error, loading, refresh } = useApi((signal) => api.stations(signal));

  if (loading) {
    return (
      <div className="grid gap-5 sm:grid-cols-2 xl:grid-cols-3" aria-busy="true">
        {Array.from({ length: 6 }).map((_, i) => (
          <Skeleton key={i} className="h-60" />
        ))}
      </div>
    );
  }

  if (error) {
    return <ErrorState message={error.message} onRetry={refresh} />;
  }

  if (!data || data.length === 0) {
    return <EmptyState>No monitoring stations are reporting right now.</EmptyState>;
  }

  return (
    <div className="grid gap-5 sm:grid-cols-2 xl:grid-cols-3">
      {data.map((station) => (
        <StationCard key={station.id} station={station} />
      ))}
    </div>
  );
}
