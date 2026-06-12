import { Link, useLocation } from "react-router-dom"
import type { LucideIcon } from "lucide-react"

import { cn } from "@/lib/utils"
import {
  Tooltip,
  TooltipContent,
  TooltipTrigger,
} from "@/components/ui/tooltip"

interface NavItemProps {
  to: string
  label: string
  icon: LucideIcon
  collapsed?: boolean
}

export function NavItem({ to, label, icon: Icon, collapsed = false }: NavItemProps) {
  const location = useLocation()
  const isActive = location.pathname === to || location.pathname.startsWith(to + "/")

  const link = (
    <Link
      to={to}
      className={cn(
        "flex items-center rounded-md py-2 text-sm font-medium transition-colors",
        "hover:bg-sidebar-accent hover:text-sidebar-accent-foreground",
        isActive
          ? "bg-sidebar-accent text-sidebar-accent-foreground"
          : "text-sidebar-foreground/70",
        collapsed ? "justify-center px-2" : "gap-3 px-3",
      )}
    >
      <Icon className="h-4 w-4 shrink-0" />
      {!collapsed && <span>{label}</span>}
    </Link>
  )

  if (collapsed) {
    return (
      <Tooltip>
        <TooltipTrigger asChild>{link}</TooltipTrigger>
        <TooltipContent side="right" sideOffset={8}>
          {label}
        </TooltipContent>
      </Tooltip>
    )
  }

  return link
}

