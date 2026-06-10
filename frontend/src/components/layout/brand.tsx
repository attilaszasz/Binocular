import { Binoculars } from "lucide-react"

interface BrandProps {
  collapsed?: boolean
}

export function Brand({ collapsed = false }: BrandProps) {
  return (
    <div className="flex items-center gap-2 px-2">
      <Binoculars className="h-6 w-6 shrink-0 text-primary" />
      {!collapsed && (
        <span className="text-lg font-semibold tracking-tight">
          Binocular
        </span>
      )}
    </div>
  )
}
