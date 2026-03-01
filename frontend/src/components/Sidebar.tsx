import { Activity, Blocks, LayoutGrid, Settings, X } from "lucide-react";
import { NavLink } from "react-router-dom";

interface SidebarProps {
  isOpen: boolean;
  onClose: () => void;
}

const navItems = [
  { to: "/", label: "Inventory", icon: LayoutGrid },
  { to: "/logs", label: "Activity Logs", icon: Activity },
  { to: "/modules", label: "Modules", icon: Blocks },
  { to: "/settings", label: "Settings", icon: Settings },
] as const;

function SidebarContent({ onClose }: { onClose: () => void }) {
  return (
    <div className="flex h-full flex-col bg-white dark:bg-slate-900">
      <div className="flex h-16 items-center justify-between border-b border-slate-200 px-4 dark:border-slate-800">
        <span className="text-base font-semibold">Binocular</span>
        <button
          type="button"
          onClick={onClose}
          className="inline-flex h-9 w-9 items-center justify-center rounded-md border border-slate-300 text-slate-700 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-500 dark:border-slate-700 dark:text-slate-100 md:hidden"
          aria-label="Close navigation"
        >
          <X size={16} />
        </button>
      </div>
      <nav className="space-y-1 px-3 py-4">
        {navItems.map(({ to, label, icon: Icon }) => (
          <NavLink
            key={to}
            to={to}
            onClick={onClose}
            className={({ isActive }) =>
              [
                "flex items-center gap-3 rounded-md px-3 py-2 text-sm font-medium transition focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-500",
                isActive
                  ? "bg-blue-100 text-blue-800 dark:bg-blue-900/30 dark:text-blue-200"
                  : "text-slate-700 hover:bg-slate-100 dark:text-slate-200 dark:hover:bg-slate-800",
              ].join(" ")
            }
          >
            <Icon size={16} />
            <span>{label}</span>
          </NavLink>
        ))}
      </nav>
    </div>
  );
}

export function Sidebar({ isOpen, onClose }: SidebarProps) {
  return (
    <>
      <aside className="hidden h-screen w-64 border-r border-slate-200 bg-white dark:border-slate-800 dark:bg-slate-900 md:block">
        <SidebarContent onClose={onClose} />
      </aside>

      <div
        className={`fixed inset-0 z-40 md:hidden ${isOpen ? "block" : "hidden"}`}
        role="dialog"
        aria-modal="true"
        onKeyDown={(event) => {
          if (event.key === "Escape") {
            onClose();
          }
        }}
      >
        <button
          type="button"
          className="absolute inset-0 bg-black/50"
          aria-label="Close navigation overlay"
          onClick={onClose}
        />
        <div className="absolute left-0 top-0 h-dvh w-64">
          <SidebarContent onClose={onClose} />
        </div>
      </div>
    </>
  );
}
