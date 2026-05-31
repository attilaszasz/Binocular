import { render, screen } from '@testing-library/react';
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
});
