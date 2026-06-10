import { Outlet } from "react-router-dom"

import { TooltipProvider } from "@/components/ui/tooltip"
import { Sidebar } from "@/components/layout/sidebar"
import { Header } from "@/components/layout/header"
import { useSidebar } from "@/hooks/use-sidebar"

export function AppLayout() {
  const { collapsed, toggle } = useSidebar()

  return (
    <TooltipProvider delayDuration={300}>
      <div className="flex h-screen overflow-hidden">
        <Sidebar collapsed={collapsed} onToggle={toggle} />
        <div className="flex flex-1 flex-col overflow-hidden">
          <Header
            sidebarCollapsed={collapsed}
            onSidebarToggle={toggle}
          />
          <main className="flex-1 overflow-y-auto p-6">
            <Outlet />
          </main>
        </div>
      </div>
    </TooltipProvider>
  )
}
