/**
 * Theme resolution logic shared between:
 * 1. FOUC-prevention inline script in index.html (copy-pasted)
 * 2. ThemeProvider React component (imported)
 *
 * Resolution order:
 *   1. localStorage key "binocular-theme" → returns validated value
 *   2. prefers-color-scheme media query      → returns system preference
 *   3. Fallback                              → returns "light"
 */

export type ThemeMode = 'light' | 'dark';

/** Key used for localStorage persistence. Must match the inline script in index.html. */
export const STORAGE_KEY = 'binocular-theme';

/**
 * Resolve the current theme mode from localStorage, system preference, or fallback.
 * Safe to call in SSR/non-browser environments (returns 'light').
 */
export function resolveTheme(): ThemeMode {
  try {
    const stored = window.localStorage.getItem(STORAGE_KEY);
    if (stored === 'light' || stored === 'dark') {
      return stored;
    }
  } catch {
    // localStorage unavailable (SSR, privacy mode, etc.)
  }

  try {
    return window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light';
  } catch {
    return 'light';
  }
}
