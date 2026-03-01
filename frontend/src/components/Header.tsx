import { Menu } from "lucide-react";
import { useLocation } from "react-router-dom";

import { ThemeToggle } from "./ThemeToggle";

const titleMap: Record<string, string> = {
  "/": "Inventory",
  "/logs": "Activity Logs",
  "/modules": "Modules",
  "/settings": "Settings",
};

interface HeaderProps {
  onOpenSidebar: () => void;
}

export function Header({ onOpenSidebar }: HeaderProps) {
  const location = useLocation();
  const title = titleMap[location.pathname] ?? "Inventory";

  return (
    <header className="sticky top-0 z-20 flex h-16 items-center justify-between border-b border-slate-200 bg-slate-50/95 px-4 backdrop-blur dark:border-slate-800 dark:bg-slate-950/95 md:px-6">
      <div className="flex items-center gap-3">
        <button
          type="button"
          className="inline-flex h-10 w-10 items-center justify-center rounded-md border border-slate-300 text-slate-700 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-500 dark:border-slate-700 dark:text-slate-100 md:hidden"
          onClick={onOpenSidebar}
          aria-label="Open navigation"
        >
          <Menu size={18} />
        </button>
        <h1 className="text-lg font-semibold text-slate-900 dark:text-slate-100">{title}</h1>
      </div>
      <ThemeToggle />
    </header>
  );
}
