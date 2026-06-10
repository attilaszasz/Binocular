export function VersionDisplay() {
  const version = import.meta.env.VITE_APP_VERSION ?? "dev"

  return (
    <span className="text-xs text-muted-foreground font-mono">
      v{version}
    </span>
  )
}
