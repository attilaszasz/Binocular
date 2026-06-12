export function VersionDisplay() {
  const version = import.meta.env.VITE_APP_VERSION ?? "dev"
  const displayVersion = version.startsWith("v") ? version : `v${version}`

  return (
    <span className="text-xs text-muted-foreground font-mono">
      {displayVersion}
    </span>
  )
}
