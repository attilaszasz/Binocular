import { runAllChecks, runDeviceCheck } from './checks';

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

describe('checks API', () => {
  afterEach(() => {
    vi.restoreAllMocks();
  });

  it('runs a manual check for one device', async () => {
    vi.spyOn(globalThis, 'fetch').mockResolvedValue(new Response(JSON.stringify(checkResult), { status: 200 }));

    await expect(runDeviceCheck(1, { moduleId: 'sony-alpha' })).resolves.toEqual(checkResult);

    expect(fetch).toHaveBeenCalledWith(
      '/api/v1/checks/devices/1',
      expect.objectContaining({
        method: 'POST',
        body: JSON.stringify({ moduleId: 'sony-alpha' }),
      }),
    );
  });

  it('runs manual checks for all devices', async () => {
    const bulkResponse = { results: [checkResult], total: 1, succeeded: 1, failed: 0 };
    vi.spyOn(globalThis, 'fetch').mockResolvedValue(new Response(JSON.stringify(bulkResponse), { status: 200 }));

    await expect(runAllChecks({ moduleId: 'sony-alpha', maxConcurrency: 2 })).resolves.toEqual(bulkResponse);

    expect(fetch).toHaveBeenCalledWith(
      '/api/v1/checks/all',
      expect.objectContaining({
        method: 'POST',
        body: JSON.stringify({ moduleId: 'sony-alpha', maxConcurrency: 2 }),
      }),
    );
  });
});
