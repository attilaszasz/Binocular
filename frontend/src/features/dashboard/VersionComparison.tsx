interface VersionComparisonProps {
  localVersion: string;
  latestVersion: string | null;
}

export function VersionComparison({ localVersion, latestVersion }: VersionComparisonProps) {
  return (
    <div className="flex flex-col gap-1 text-sm sm:flex-row sm:items-center sm:gap-3">
      <span className="text-slate-700 dark:text-slate-200">Local: v{localVersion}</span>
      <span className="hidden text-slate-400 sm:inline">→</span>
      <span className="text-slate-700 dark:text-slate-200">
        Latest: {latestVersion ? `v${latestVersion}` : "Not checked"}
      </span>
    </div>
  );
}
