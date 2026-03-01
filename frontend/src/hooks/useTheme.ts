import { useEffect, useMemo, useState } from "react";

export type Theme = "light" | "dark";

const THEME_STORAGE_KEY = "binocular-theme";

function getSystemTheme(): Theme {
  return window.matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light";
}

function getStoredTheme(): Theme | null {
  try {
    const value = localStorage.getItem(THEME_STORAGE_KEY);
    if (value === "dark" || value === "light") {
      return value;
    }
    return null;
  } catch {
    return null;
  }
}

function saveTheme(theme: Theme): void {
  try {
    localStorage.setItem(THEME_STORAGE_KEY, theme);
  } catch {
    // ignore
  }
}

export function useTheme() {
  const [theme, setTheme] = useState<Theme>(() => getStoredTheme() ?? getSystemTheme());
  const [hasStoredPreference, setHasStoredPreference] = useState<boolean>(
    () => getStoredTheme() !== null,
  );

  useEffect(() => {
    if (theme === "dark") {
      document.documentElement.classList.add("dark");
    } else {
      document.documentElement.classList.remove("dark");
    }
  }, [theme]);

  useEffect(() => {
    const media = window.matchMedia("(prefers-color-scheme: dark)");
    const listener = () => {
      if (!hasStoredPreference) {
        setTheme(media.matches ? "dark" : "light");
      }
    };

    media.addEventListener("change", listener);
    return () => media.removeEventListener("change", listener);
  }, [hasStoredPreference]);

  const toggleTheme = useMemo(
    () => () => {
      setTheme((current) => {
        const next = current === "dark" ? "light" : "dark";
        saveTheme(next);
        setHasStoredPreference(true);
        return next;
      });
    },
    [],
  );

  return {
    theme,
    isDark: theme === "dark",
    toggleTheme,
  };
}
