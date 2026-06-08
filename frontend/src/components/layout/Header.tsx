import { Menu, Moon, Sun } from 'lucide-react';
import { Button } from '@/components/ui/button';

type Props = {
  menuButtonRef: React.RefObject<HTMLButtonElement | null>;
  onOpenMobileMenu: () => void;
  pageTitle: string;
  mode: string;
  toggleMode: () => void;
};

export function Header({
  menuButtonRef,
  onOpenMobileMenu,
  pageTitle,
  mode,
  toggleMode,
}: Props) {
  return (
    <header className="sticky top-0 z-30 flex h-16 items-center justify-between border-b border-sky-200/70 bg-gradient-to-r from-white/95 via-sky-50/90 to-violet-50/80 px-4 backdrop-blur-sm dark:border-sky-400/15 dark:from-slate-950/95 dark:via-slate-900/90 dark:to-violet-950/40 sm:px-6 lg:px-8">
      <div className="flex items-center">
        <Button
          ref={menuButtonRef}
          variant="ghost"
          size="icon"
          className="mr-4 md:hidden"
          onClick={onOpenMobileMenu}
          aria-label="Open navigation"
        >
          <Menu size={24} />
        </Button>
        <h1 className="text-lg font-semibold">{pageTitle}</h1>
      </div>
      <Button
        variant="ghost"
        size="icon"
        onClick={toggleMode}
        aria-label={`Switch to ${mode === 'dark' ? 'light' : 'dark'} mode`}
      >
        {mode === 'dark' ? <Sun size={20} /> : <Moon size={20} />}
      </Button>
    </header>
  );
}
