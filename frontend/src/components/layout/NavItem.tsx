import type { LucideIcon } from 'lucide-react';
import { NavLink } from 'react-router-dom';
import { Tooltip, TooltipTrigger, TooltipContent } from '@/components/ui/tooltip';

export type NavItemData = {
  to: string;
  label: string;
  icon: LucideIcon;
};

type Props = {
  item: NavItemData;
  isCollapsed: boolean;
  onNavigate: () => void;
};

export function NavItem({ item, isCollapsed, onNavigate }: Props) {
  const Icon = item.icon;

  const link = (
    <NavLink
      to={item.to}
      onClick={onNavigate}
      aria-label={isCollapsed ? item.label : undefined}
      className={({ isActive }) =>
        `group relative flex items-center rounded-xl py-3 text-sm font-medium transition-all duration-200 focus-visible:ring-2 focus-visible:ring-ring/40 ${
          isCollapsed ? 'justify-center h-10 w-10' : 'w-full gap-3 px-4'
        } ${
          isActive
            ? 'bg-gradient-to-r from-sky-500/15 to-violet-500/15 text-sky-700 shadow-sm dark:text-sky-300'
            : 'text-muted-foreground hover:bg-sky-500/10 hover:text-sky-700 dark:hover:text-sky-300'
        }`
      }
    >
      <Icon size={20} />
      <span className={isCollapsed ? 'hidden' : ''}>{item.label}</span>
    </NavLink>
  );

  if (!isCollapsed) {
    return link;
  }

  return (
    <Tooltip>
      <TooltipTrigger asChild>{link}</TooltipTrigger>
      <TooltipContent side="right">{item.label}</TooltipContent>
    </Tooltip>
  );
}
