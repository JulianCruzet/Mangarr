import { SeriesCard } from './SeriesCard';
import type { Series } from '../../types';

interface SeriesGridProps {
  series: Series[];
  isLoading?: boolean;
  emptyState?: React.ReactNode;
}

function SkeletonCard() {
  return (
    <div className="bg-mangarr-card border border-mangarr-border rounded-lg overflow-hidden">
      <div className="w-full animate-pulse" style={{ paddingBottom: '150%', position: 'relative' }}>
        <div className="absolute inset-0 bg-mangarr-input" />
        <div className="absolute bottom-0 left-0 right-0 p-2.5 space-y-1.5">
          <div className="h-3 bg-white/10 rounded w-4/5" />
          <div className="h-2 bg-white/5 rounded w-2/3" />
        </div>
      </div>
    </div>
  );
}

export function SeriesGrid({ series, isLoading = false, emptyState }: SeriesGridProps) {
  if (isLoading) {
    return (
      <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5 xl:grid-cols-6 2xl:grid-cols-8 gap-4">
        {Array.from({ length: 18 }).map((_, i) => (
          <SkeletonCard key={i} />
        ))}
      </div>
    );
  }

  if (series.length === 0 && emptyState) {
    return <>{emptyState}</>;
  }

  return (
    <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5 xl:grid-cols-6 2xl:grid-cols-8 gap-4">
      {series.map((s) => (
        <SeriesCard key={s.id} series={s} />
      ))}
    </div>
  );
}
