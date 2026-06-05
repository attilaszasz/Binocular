import { resolveTheme, STORAGE_KEY } from './resolveTheme';

describe('resolveTheme', () => {
  beforeEach(() => {
    window.localStorage.clear();
    document.documentElement.className = '';
  });

  it("returns 'dark' when localStorage has 'dark'", () => {
    window.localStorage.setItem(STORAGE_KEY, 'dark');
    expect(resolveTheme()).toBe('dark');
  });

  it("returns 'light' when localStorage has 'light'", () => {
    window.localStorage.setItem(STORAGE_KEY, 'light');
    expect(resolveTheme()).toBe('light');
  });

  it("falls back to 'dark' when prefers-color-scheme is dark and no localStorage is set", () => {
    window.localStorage.removeItem(STORAGE_KEY);
    window.matchMedia = vi.fn().mockReturnValue({ matches: true });
    expect(resolveTheme()).toBe('dark');
  });

  it("falls back to 'light' when no localStorage and no matchMedia support", () => {
    window.localStorage.removeItem(STORAGE_KEY);
    window.matchMedia = vi.fn().mockImplementation(() => {
      throw new Error('matchMedia not available');
    });
    expect(resolveTheme()).toBe('light');
  });

  it("falls back to 'light' when no localStorage and prefers-color-scheme is light", () => {
    window.localStorage.removeItem(STORAGE_KEY);
    window.matchMedia = vi.fn().mockReturnValue({ matches: false });
    expect(resolveTheme()).toBe('light');
  });

  it('handles localStorage errors gracefully and falls back to matchMedia', () => {
    window.matchMedia = vi.fn().mockReturnValue({ matches: true });

    // Make getItem throw
    const originalGetItem = window.localStorage.getItem;
    window.localStorage.getItem = vi.fn(() => {
      throw new Error('storage unavailable');
    });

    expect(resolveTheme()).toBe('dark');

    // Restore getItem for other tests
    window.localStorage.getItem = originalGetItem;
  });

  it('ignores invalid localStorage values', () => {
    window.localStorage.setItem(STORAGE_KEY, 'invalid-value');
    window.matchMedia = vi.fn().mockReturnValue({ matches: false });
    expect(resolveTheme()).toBe('light');
  });
});
