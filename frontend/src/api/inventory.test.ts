import { archiveDevice, confirmDeviceUpdate, createDevice, listInventory, updateDevice } from './inventory';

describe('inventory API', () => {
  afterEach(() => {
    vi.restoreAllMocks();
  });

  it('lists grouped inventory', async () => {
    vi.spyOn(globalThis, 'fetch').mockResolvedValue(
      new Response(JSON.stringify({ groups: [] }), { status: 200 }),
    );

    await expect(listInventory()).resolves.toEqual({ groups: [] });
    expect(fetch).toHaveBeenCalledWith('/api/v1/inventory', expect.objectContaining({ method: 'GET' }));
  });

  it('sends device mutations to the inventory endpoints', async () => {
    vi.spyOn(globalThis, 'fetch').mockImplementation(async () =>
      new Response(JSON.stringify({ id: 1 }), { status: 200 }),
    );
    const payload = {
      name: 'Sony A7IV',
      model: 'ILCE-7M4',
      deviceType: 'Sony Alpha',
      currentVersion: '02',
    };

    await createDevice(payload);
    await updateDevice(1, payload);
    await confirmDeviceUpdate(1);
    await archiveDevice(1);

    expect(fetch).toHaveBeenNthCalledWith(
      1,
      '/api/v1/inventory',
      expect.objectContaining({ method: 'POST', body: JSON.stringify(payload) }),
    );
    expect(fetch).toHaveBeenNthCalledWith(2, '/api/v1/inventory/1', expect.objectContaining({ method: 'PATCH' }));
    expect(fetch).toHaveBeenNthCalledWith(
      3,
      '/api/v1/inventory/1/confirm-update',
      expect.objectContaining({ method: 'POST' }),
    );
    expect(fetch).toHaveBeenNthCalledWith(4, '/api/v1/inventory/1', expect.objectContaining({ method: 'DELETE' }));
  });
});