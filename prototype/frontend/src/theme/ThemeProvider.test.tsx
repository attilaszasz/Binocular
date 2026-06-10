import { act, render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';

import { ThemeProvider } from './ThemeProvider';
import { useTheme } from './useTheme';

function ThemeProbe() {
  const { mode, toggleMode } = useTheme();
  return (
    <button type="button" onClick={toggleMode}>
      {mode}
    </button>
  );
}

function ThemeProbeRaw() {
  const { mode } = useTheme();
  return <span>{mode}</span>;
}

describe('ThemeProvider', () => {
  beforeEach(() => {
    window.localStorage.clear();
    window.matchMedia = vi.fn().mockReturnValue({ matches: false });
    document.documentElement.className = '';
  });

  it('toggles and persists theme mode', async () => {
    const user = userEvent.setup();
    render(
      <ThemeProvider>
        <ThemeProbe />
      </ThemeProvider>,
    );

    expect(screen.getByRole('button', { name: 'light' })).toBeInTheDocument();

    await user.click(screen.getByRole('button', { name: 'light' }));

    expect(screen.getByRole('button', { name: 'dark' })).toBeInTheDocument();
    expect(window.localStorage.getItem('binocular-theme')).toBe('dark');
    expect(document.documentElement).toHaveClass('dark');
  });

  it('resolves dark mode from localStorage on mount', () => {
    window.localStorage.setItem('binocular-theme', 'dark');
    render(
      <ThemeProvider>
        <ThemeProbe />
      </ThemeProvider>,
    );

    expect(screen.getByRole('button', { name: 'dark' })).toBeInTheDocument();
    expect(document.documentElement).toHaveClass('dark');
  });

  it('resolves dark mode from system preference on mount', () => {
    window.matchMedia = vi.fn().mockReturnValue({ matches: true });
    render(
      <ThemeProvider>
        <ThemeProbe />
      </ThemeProvider>,
    );

    expect(screen.getByRole('button', { name: 'dark' })).toBeInTheDocument();
    expect(document.documentElement).toHaveClass('dark');
  });
});

describe('useTheme error boundary', () => {
  it('throws when used outside ThemeProvider', () => {
    // Suppress React error boundary logging during test
    const spy = vi.spyOn(console, 'error').mockImplementation(() => {});

    expect(() => {
      act(() => {
        render(<ThemeProbeRaw />);
      });
    }).toThrow('useTheme must be used within ThemeProvider');

    spy.mockRestore();
  });
});
