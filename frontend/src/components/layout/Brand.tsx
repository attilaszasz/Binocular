import { Binoculars } from 'lucide-react';

type Props = {
  isCollapsed: boolean;
};

export function Brand({ isCollapsed }: Props) {
  return (
    <div className="flex items-center gap-2">
      <div className="rounded-lg bg-gradient-to-br from-sky-500/20 to-violet-500/20 p-1.5 text-sky-600 dark:from-sky-500/25 dark:to-violet-500/25 dark:text-sky-300">
        <Binoculars size={24} />
      </div>
      {!isCollapsed && (
        <span className="text-xl font-bold tracking-tight">Binocular</span>
      )}
    </div>
  );
}
