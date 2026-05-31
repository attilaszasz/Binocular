import { createContext, useEffect, useState, type ReactNode } from 'react';

export type ThemeMode = 'light' | 'dark';

type ThemeContextValue = {
  mode: ThemeMode;
  toggleMode: () => void;
};

const storageKey = 'binocular-theme';

export const ThemeContext = createContext<ThemeContextValue | null>(null);

function getInitialMode(): ThemeMode {
  const stored = window.localStorage.getItem(storageKey);
  if (stored === 'light' || stored === 'dark') {
    return stored;
  }
  return window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light';
}

export function ThemeProvider({ children }: { children: ReactNode }) {
  const [mode, setMode] = useState<ThemeMode>(getInitialMode);

  useEffect(() => {
    document.documentElement.classList.toggle('dark', mode === 'dark');
    window.localStorage.setItem(storageKey, mode);
  }, [mode]);

  function toggleMode() {
    setMode((current) => (current === 'dark' ? 'light' : 'dark'));
  }

  return <ThemeContext.Provider value={{ mode, toggleMode }}>{children}</ThemeContext.Provider>;
}
