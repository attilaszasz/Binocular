import { Outlet } from "react-router-dom";

import { useSidebar } from "../hooks/useSidebar";
import { Header } from "./Header";
import { Sidebar } from "./Sidebar";

export function AppShell() {
  const { isOpen, open, close } = useSidebar();

  return (
    <div className="min-h-screen bg-slate-50 text-slate-900 dark:bg-slate-950 dark:text-slate-100 md:grid md:grid-cols-[16rem_1fr]">
      <Sidebar isOpen={isOpen} onClose={close} />
      <div className="min-w-0">
        <Header onOpenSidebar={open} />
        <main className="p-4 md:p-6">
          <Outlet />
        </main>
      </div>
    </div>
  );
}
