import { PanelLeftClose, PanelLeftOpen, X } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { TooltipProvider } from '@/components/ui/tooltip';
import { Brand } from '@/components/layout/Brand';
import { NavItem, type NavItemData } from '@/components/layout/NavItem';
import { VersionDisplay } from '@/components/layout/VersionDisplay';

type Props = {
  isMobileMenuOpen: boolean;
  closeMobileMenu: () => void;
  isCollapsed: boolean;
  onToggleCollapse: () => void;
  navItems: NavItemData[];
};

export function Sidebar({
  isMobileMenuOpen,
  closeMobileMenu,
  isCollapsed,
  onToggleCollapse,
  navItems,
}: Props) {
  return (
    <aside
      role="complementary"
      aria-label="Sidebar"
      className={`fixed inset-y-0 left-0 z-50 flex transform flex-col border-r border-sky-200/70 bg-gradient-to-b from-sky-50 via-white to-violet-50/70 transition-[width] duration-300 ease-in-out dark:border-sky-400/15 dark:from-slate-950 dark:via-slate-950 dark:to-violet-950/40 md:translate-x-0 ${
        isMobileMenuOpen ? 'translate-x-0' : '-translate-x-full'
      } ${isCollapsed ? 'md:w-16' : 'md:w-64'}`}
    >
      <div
        className={`flex h-16 shrink-0 items-center border-b border-inherit ${
          isCollapsed ? 'justify-center' : 'justify-between px-6'
        }`}
      >
        <Brand isCollapsed={isCollapsed} />
        <Button
          variant="ghost"
          size="icon"
          className="md:hidden"
          onClick={closeMobileMenu}
          aria-label="Close navigation"
        >
          <X size={20} />
        </Button>
      </div>
      <TooltipProvider delayDuration={200}>
        <nav
          className={`flex-1 overflow-y-auto space-y-1.5 ${isCollapsed ? 'flex flex-col items-center py-2' : 'p-4'}`}
          aria-label="Primary navigation"
        >
          {navItems.map((item) => (
            <NavItem
              key={item.to}
              item={item}
              onNavigate={closeMobileMenu}
              isCollapsed={isCollapsed}
            />
          ))}
        </nav>
        <div className="mt-auto" />
        <div className={isCollapsed ? 'flex justify-center' : 'px-4'}>
          <Button
            variant="ghost"
            size="icon"
            onClick={onToggleCollapse}
            aria-label={isCollapsed ? 'Expand sidebar' : 'Collapse sidebar'}
            aria-expanded={!isCollapsed}
            className={!isCollapsed ? 'w-full bg-white/60 dark:bg-white/5' : 'bg-white/60 dark:bg-white/5'}
          >
            {isCollapsed ? (
              <PanelLeftOpen size={20} />
            ) : (
              <PanelLeftClose size={20} />
            )}
          </Button>
        </div>
        <VersionDisplay isCollapsed={isCollapsed} />
      </TooltipProvider>
    </aside>
  );
}
