import { act, render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter } from 'react-router-dom';

import { App } from './App';
import { ThemeProvider } from './theme/ThemeProvider';

const inventoryResponse = {
  groups: [
    {
      moduleId: 'sony-alpha',
      name: 'Sony Alpha',
      count: 2,
      devices: [
        {
          id: 1,
          moduleId: 'sony-alpha',
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
          moduleId: 'sony-alpha',
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

const modulesResponse = {
  modules: [
    {
      moduleId: 'sony-alpha',
      displayName: 'Sony Alpha',
      author: 'Binocular',
      version: '1.0.0',
      status: 'installed',
      validationStatus: 'valid',
      validationSummary: {
        overall_status: 'valid',
        static_phase: { phase: 'static', status: 'passed', findings: [] },
        runtime_phase: { phase: 'runtime', status: 'skipped', findings: [] },
      },
      sourceHash: 'abc123',
      lastValidatedAt: '2026-05-31T10:00:00Z',
      createdAt: '2026-05-31T10:00:00Z',
      updatedAt: '2026-05-31T10:00:00Z',
    },
  ],
};

const checkResult = {
  deviceId: 1,
  moduleId: 'sony-alpha',
  status: 'update_available',
  currentVersion: '2.00',
  latestVersion: '3.00',
  lastCheckedAt: '2026-05-31T10:00:00Z',
  lastSuccessAt: '2026-05-31T10:00:00Z',
  sourceUrl: 'https://vendor.example/a7iv',
  detail: null,
  diagnostics: { comparison: { is_newer: true } },
};

function mockInventoryFetch() {
  vi.spyOn(globalThis, 'fetch').mockImplementation(async (input, init) => {
    const url = String(input);
    const method = init?.method ?? 'GET';
    if (url === '/api/v1/inventory' && method === 'GET') {
      return new Response(JSON.stringify(inventoryResponse), { status: 200 });
    }
    if (url === '/api/v1/modules' && method === 'GET') {
      return new Response(JSON.stringify(modulesResponse), { status: 200 });
    }
    if (url === '/api/v1/modules' && method === 'POST') {
      return new Response(JSON.stringify(modulesResponse.modules[0]), { status: 201 });
    }
    if (url === '/api/v1/modules/sony-alpha' && method === 'DELETE') {
      return new Response(null, { status: 204 });
    }
    if (url === '/api/v1/checks/devices/1' && method === 'POST') {
      return new Response(JSON.stringify(checkResult), { status: 200 });
    }
    if (url === '/api/v1/checks/all' && method === 'POST') {
      return new Response(JSON.stringify({ results: [checkResult], total: 1, succeeded: 1, failed: 0 }), { status: 200 });
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
    expect(screen.getByText(/trusted Python code/i)).toBeInTheDocument();
  });

  it('loads and deletes installed modules', async () => {
    const user = userEvent.setup();
    renderApp('/modules');

    expect(await screen.findByText('Sony Alpha')).toBeInTheDocument();
    expect(screen.getByText('sony-alpha')).toBeInTheDocument();

    await user.click(screen.getByRole('button', { name: 'Delete' }));

    expect(fetch).toHaveBeenCalledWith('/api/v1/modules/sony-alpha', expect.objectContaining({ method: 'DELETE' }));
  });

  it('uploads modules and renders validation feedback', async () => {
    const user = userEvent.setup();
    renderApp('/modules');

    await user.upload(screen.getByLabelText('Module file'), new File(['module'], 'module.py'));
    await user.click(screen.getByRole('button', { name: 'Upload' }));

    expect(fetch).toHaveBeenCalledWith(
      '/api/v1/modules',
      expect.objectContaining({ method: 'POST', body: expect.any(FormData) }),
    );
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

  it('runs a manual check for one inventory device', async () => {
    const user = userEvent.setup();
    renderApp('/inventory');

    expect(await screen.findByText('Sony A7IV')).toBeInTheDocument();
    expect(await screen.findByRole('combobox', { name: 'Manual check module' })).toHaveValue('sony-alpha');

    await user.click(screen.getAllByRole('button', { name: 'Check Now' })[0]);

    expect(fetch).toHaveBeenCalledWith(
      '/api/v1/checks/devices/1',
      expect.objectContaining({ method: 'POST', body: JSON.stringify({ moduleId: 'sony-alpha' }) }),
    );
    expect(await screen.findByText('Manual result: update available')).toBeInTheDocument();
    expect(screen.getByText('Stored: 2.00')).toBeInTheDocument();
    expect(screen.getAllByText('Latest: 3.00')[0]).toBeInTheDocument();
  });

  it('runs a manual check for all inventory devices', async () => {
    const user = userEvent.setup();
    renderApp('/inventory');

    expect(await screen.findByText('Sony A7IV')).toBeInTheDocument();
    await user.click(await screen.findByRole('button', { name: 'Check All' }));

    expect(fetch).toHaveBeenCalledWith(
      '/api/v1/checks/all',
      expect.objectContaining({ method: 'POST', body: JSON.stringify({ moduleId: 'sony-alpha' }) }),
    );
    expect(await screen.findByText('Manual bulk check complete: 1/1 succeeded, 0 failed.')).toBeInTheDocument();
  });

  it('keeps inventory controls usable while a bulk check is running', async () => {
    const user = userEvent.setup();
    let resolveBulk: (response: Response) => void = () => undefined;
    vi.restoreAllMocks();
    vi.spyOn(globalThis, 'fetch').mockImplementation(async (input, init) => {
      const url = String(input);
      const method = init?.method ?? 'GET';
      if (url === '/api/v1/inventory' && method === 'GET') {
        return new Response(JSON.stringify(inventoryResponse), { status: 200 });
      }
      if (url === '/api/v1/modules' && method === 'GET') {
        return new Response(JSON.stringify(modulesResponse), { status: 200 });
      }
      if (url === '/api/v1/checks/all' && method === 'POST') {
        return new Promise<Response>((resolve) => {
          resolveBulk = resolve;
        });
      }
      return new Response(JSON.stringify(inventoryResponse.groups[0].devices[0]), { status: 200 });
    });
    renderApp('/inventory');

    expect(await screen.findByText('Sony A7IV')).toBeInTheDocument();
    await user.click(await screen.findByRole('button', { name: 'Check All' }));

    expect(screen.getByRole('button', { name: 'Checking...' })).toBeDisabled();
    expect(screen.getAllByRole('button', { name: 'Check Now' })[0]).not.toBeDisabled();

    await act(async () => {
      resolveBulk(new Response(JSON.stringify({ results: [checkResult], total: 1, succeeded: 1, failed: 0 }), { status: 200 }));
    });

    expect(await screen.findByText('Manual bulk check complete: 1/1 succeeded, 0 failed.')).toBeInTheDocument();
  });

  it('creates and archives inventory devices through the API', async () => {
    const user = userEvent.setup();
    renderApp('/inventory');

    await screen.findByText('Sony A7IV');
    await user.type(screen.getByLabelText('Name'), 'Lumix GH6');
    await user.type(screen.getByLabelText('Model'), 'DC-GH6');
    await user.selectOptions(screen.getByLabelText('Module'), 'sony-alpha');
    expect(screen.getByLabelText('Device Type')).toHaveValue('Sony Alpha');
    await user.type(screen.getByLabelText('Current version'), '2.3');
    await user.click(screen.getByRole('button', { name: 'Add' }));

    expect(fetch).toHaveBeenCalledWith(
      '/api/v1/inventory',
      expect.objectContaining({
        method: 'POST',
        body: JSON.stringify({
          name: 'Lumix GH6',
          model: 'DC-GH6',
          moduleId: 'sony-alpha',
          currentVersion: '2.3',
        }),
      }),
    );

    await user.click(screen.getAllByRole('button', { name: 'Archive' })[0]);

    expect(fetch).toHaveBeenCalledWith('/api/v1/inventory/1', expect.objectContaining({ method: 'DELETE' }));
  });
});
