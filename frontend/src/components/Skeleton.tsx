export function StatsSkeleton() {
  return (
    <output
      className="grid grid-cols-1 gap-3 sm:grid-cols-3"
      aria-label="Loading stats"
      aria-live="polite"
    >
      {[1, 2, 3].map((slot) => (
        <div
          key={`stats-skeleton-${slot}`}
          className="h-24 animate-pulse rounded-lg bg-slate-200 dark:bg-slate-800"
        />
      ))}
    </output>
  );
}

export function CardSkeletonList({ count = 4 }: { count?: number }) {
  const slots = Array.from({ length: count }, (_, index) => index + 1);

  return (
    <output
      className="mt-4 grid grid-cols-1 gap-3 lg:grid-cols-2"
      aria-label="Loading devices"
      aria-live="polite"
    >
      {slots.map((slot) => (
        <div
          key={`card-skeleton-${slot}`}
          className="h-36 animate-pulse rounded-lg bg-slate-200 dark:bg-slate-800"
        />
      ))}
    </output>
  );
}
