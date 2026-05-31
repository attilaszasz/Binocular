import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter } from 'react-router-dom';

import { App } from './App';
import { ThemeProvider } from './theme/ThemeProvider';

function renderApp(initialPath = '/inventory') {
  return render(
    <MemoryRouter initialEntries={[initialPath]}>
      <ThemeProvider>
        <App />
      </ThemeProvider>
    </MemoryRouter>,
  );
}

describe('App shell', () => {
  beforeEach(() => {
    window.localStorage.clear();
    window.matchMedia = vi.fn().mockReturnValue({ matches: false });
  });

  it('renders deep-linked routes', () => {
    renderApp('/modules');

    expect(screen.getByRole('heading', { name: 'Extension Modules' })).toBeInTheDocument();
    expect(screen.getByText('sony_alpha.py')).toBeInTheDocument();
  });

  it('navigates without a page reload', async () => {
    const user = userEvent.setup();
    renderApp('/inventory');

    await user.click(screen.getAllByRole('link', { name: 'Activity Logs' })[0]);

    expect(screen.getByRole('heading', { level: 2, name: 'Activity Logs' })).toBeInTheDocument();
    expect(screen.getByText('Manual check started for Sony A7IV')).toBeInTheDocument();
  });

  it('renders inventory stats and syncs local versions', async () => {
    const user = userEvent.setup();
    renderApp('/inventory');

    expect(screen.getByRole('heading', { name: 'Device Inventory' })).toBeInTheDocument();
    expect(screen.getByText('Sony A7IV')).toBeInTheDocument();
    expect(screen.getByText('ILCE-7M4')).toBeInTheDocument();
    expect(screen.getByText('Updates Available')).toBeInTheDocument();

    expect(screen.getAllByRole('button', { name: 'Sync Local' })).toHaveLength(2);

    await user.click(screen.getAllByRole('button', { name: 'Sync Local' })[0]);

    expect(screen.getAllByRole('button', { name: 'Sync Local' })).toHaveLength(1);
  });
});
