import { Binoculars } from "lucide-react"
import { cn } from "@/lib/utils"

interface BrandProps {
  collapsed?: boolean
}

export function Brand({ collapsed = false }: BrandProps) {
  return (
    <div className={cn("flex items-center gap-2 px-2", collapsed && "px-0")}>
      <Binoculars className="h-6 w-6 shrink-0 text-primary" />
      {!collapsed && (
        <span className="text-lg font-semibold tracking-tight">
          Binocular
        </span>
      )}
    </div>
  )
}

