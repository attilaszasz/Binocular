import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter } from 'react-router-dom';

import { App } from './App';
import { ThemeProvider } from './theme/ThemeProvider';

const inventoryResponse = {
  groups: [
    {
      id: 1,
      name: 'Sony Alpha',
      count: 2,
      devices: [
        {
          id: 1,
          deviceTypeId: 1,
          deviceType: 'Sony Alpha',
          name: 'Sony A7IV',
          model: 'ILCE-7M4',
          currentVersion: '2.00',
          latestVersion: '3.00',
          lastCheckedAt: null,
          lastSuccessAt: null,
          status: 'update_available',
          createdAt: '2026-05-31T10:00:00Z',
          updatedAt: '2026-05-31T10:00:00Z',
        },
        {
          id: 2,
          deviceTypeId: 1,
          deviceType: 'Sony Alpha',
          name: 'Sony 24-70mm',
          model: 'SEL2470GM2',
          currentVersion: '02',
          latestVersion: null,
          lastCheckedAt: null,
          lastSuccessAt: null,
          status: 'never_checked',
          createdAt: '2026-05-31T10:00:00Z',
          updatedAt: '2026-05-31T10:00:00Z',
        },
      ],
    },
  ],
};

function mockInventoryFetch() {
  vi.spyOn(globalThis, 'fetch').mockImplementation(async (input, init) => {
    const url = String(input);
    const method = init?.method ?? 'GET';
    if (url === '/api/v1/inventory' && method === 'GET') {
      return new Response(JSON.stringify(inventoryResponse), { status: 200 });
    }
    return new Response(JSON.stringify(inventoryResponse.groups[0].devices[0]), {
      status: method === 'POST' && url === '/api/v1/inventory' ? 201 : 200,
    });
  });
}

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
    mockInventoryFetch();
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it('renders deep-linked routes', () => {
    renderApp('/modules');

    expect(screen.getByRole('heading', { name: 'Extension Modules' })).toBeInTheDocument();
    expect(screen.getByText('sony_alpha.py')).toBeInTheDocument();
  });

  it('navigates without a page reload', async () => {
    const user = userEvent.setup();
    renderApp('/inventory');

    await screen.findByText('Sony A7IV');

    await user.click(screen.getAllByRole('link', { name: 'Activity Logs' })[0]);

    expect(screen.getByRole('heading', { level: 2, name: 'Activity Logs' })).toBeInTheDocument();
    expect(screen.getByText('Manual check started for Sony A7IV')).toBeInTheDocument();
  });

  it('renders inventory stats and confirms latest versions', async () => {
    const user = userEvent.setup();
    renderApp('/inventory');

    expect(screen.getByRole('heading', { name: 'Device Inventory' })).toBeInTheDocument();
    expect(await screen.findByText('Sony A7IV')).toBeInTheDocument();
    expect(screen.getByText('ILCE-7M4')).toBeInTheDocument();
    expect(screen.getByText('Updates Available')).toBeInTheDocument();
    expect(screen.getByText('Sony Alpha (2)')).toBeInTheDocument();
    expect(screen.getByText('Not checked yet')).toBeInTheDocument();

    expect(screen.getAllByRole('button', { name: 'Sync Local' })).toHaveLength(1);

    await user.click(screen.getAllByRole('button', { name: 'Sync Local' })[0]);

    expect(fetch).toHaveBeenCalledWith('/api/v1/inventory/1/confirm-update', expect.objectContaining({ method: 'POST' }));
  });

  it('creates and archives inventory devices through the API', async () => {
    const user = userEvent.setup();
    renderApp('/inventory');

    await screen.findByText('Sony A7IV');
    await user.type(screen.getByLabelText('Name'), 'Lumix GH6');
    await user.type(screen.getByLabelText('Model'), 'DC-GH6');
    await user.type(screen.getByLabelText('Device type'), 'Panasonic Lumix');
    await user.type(screen.getByLabelText('Current version'), '2.3');
    await user.click(screen.getByRole('button', { name: 'Add' }));

    expect(fetch).toHaveBeenCalledWith(
      '/api/v1/inventory',
      expect.objectContaining({
        method: 'POST',
        body: JSON.stringify({
          name: 'Lumix GH6',
          model: 'DC-GH6',
          deviceType: 'Panasonic Lumix',
          currentVersion: '2.3',
        }),
      }),
    );

    await user.click(screen.getAllByRole('button', { name: 'Archive' })[0]);

    expect(fetch).toHaveBeenCalledWith('/api/v1/inventory/1', expect.objectContaining({ method: 'DELETE' }));
  });
});
