import { createContext, useEffect, useState, type ReactNode } from 'react';
import { resolveTheme, STORAGE_KEY, type ThemeMode } from './resolveTheme';

type ThemeContextValue = {
  mode: ThemeMode;
  toggleMode: () => void;
};

export const ThemeContext = createContext<ThemeContextValue | null>(null);

// Re-export for consumers that previously imported from this module
export type { ThemeMode };

/**
 * Provides theme context and synchronizes the `dark` class on <html>.
 *
 * - On mount, reads theme via resolveTheme() (localStorage → system → fallback).
 * - On every mode change, persists to localStorage and toggles the class.
 */
export function ThemeProvider({ children }: { children: ReactNode }) {
  const [mode, setMode] = useState<ThemeMode>(resolveTheme);

  useEffect(() => {
    document.documentElement.classList.toggle('dark', mode === 'dark');
    try {
      window.localStorage.setItem(STORAGE_KEY, mode);
    } catch {
      // localStorage unavailable
    }
  }, [mode]);

  function toggleMode() {
    setMode((current) => (current === 'dark' ? 'light' : 'dark'));
  }

  return <ThemeContext.Provider value={{ mode, toggleMode }}>{children}</ThemeContext.Provider>;
}
