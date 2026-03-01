interface StatsRowProps {
  totalDevices: number;
  updatesAvailable: number;
  upToDate: number;
}

function StatCard({ label, value }: { label: string; value: number }) {
  return (
    <article className="rounded-lg border border-slate-200 bg-white p-4 shadow-sm dark:border-slate-800 dark:bg-slate-900">
      <p className="text-sm text-slate-500 dark:text-slate-400">{label}</p>
      <p className="mt-2 text-2xl font-semibold text-slate-900 dark:text-slate-100">{value}</p>
    </article>
  );
}

export function StatsRow({ totalDevices, updatesAvailable, upToDate }: StatsRowProps) {
  return (
    <div className="grid grid-cols-1 gap-3 sm:grid-cols-3" aria-live="polite">
      <StatCard label="Total Devices" value={totalDevices} />
      <StatCard label="Updates Available" value={updatesAvailable} />
      <StatCard label="Up to Date" value={upToDate} />
    </div>
  );
}
