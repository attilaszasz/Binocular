import { ApiClient } from './client';

describe('ApiClient', () => {
  afterEach(() => {
    vi.restoreAllMocks();
  });

  it('parses successful JSON responses', async () => {
    vi.spyOn(globalThis, 'fetch').mockResolvedValue(
      new Response(JSON.stringify({ status: 'ok' }), {
        status: 200,
        headers: { 'Content-Type': 'application/json' },
      }),
    );

    const client = new ApiClient('/api/v1');

    await expect(client.get<{ status: string }>('/healthz')).resolves.toEqual({ status: 'ok' });
    expect(fetch).toHaveBeenCalledWith('/api/v1/healthz', expect.objectContaining({ method: 'GET' }));
  });

  it('raises typed errors for failed requests', async () => {
    vi.spyOn(globalThis, 'fetch').mockResolvedValue(new Response('not found', { status: 404 }));

    const client = new ApiClient('/api/v1');

    await expect(client.get('/missing')).rejects.toMatchObject({
      name: 'ApiError',
      status: 404,
      message: 'not found',
    });
  });
});
