import { describe, expect, it, vi } from 'vitest';
import { listChannels, configureChannel, testChannel } from './notifications';
import { apiClient } from './client';

vi.mock('./client', () => ({
  apiClient: {
    get: vi.fn(),
    request: vi.fn(),
  },
}));

describe('notifications API', () => {
  it('lists notification channels', async () => {
    const mockChannels = [
      { id: 1, type: 'smtp', enabled: true, config: {} },
    ];
    vi.mocked(apiClient.get).mockResolvedValue(mockChannels);

    const result = await listChannels();
    expect(result).toEqual(mockChannels);
    expect(apiClient.get).toHaveBeenCalledWith('/notifications');
  });

  it('updates notification channel config', async () => {
    const mockChannel = { id: 2, type: 'gotify', enabled: true, config: { token: 'x' } };
    vi.mocked(apiClient.request).mockResolvedValue(mockChannel);

    const payload = { enabled: true, config: { token: 'x' } };
    const result = await configureChannel('gotify', payload);
    
    expect(result).toEqual(mockChannel);
    expect(apiClient.request).toHaveBeenCalledWith('/notifications/gotify', {
      method: 'PUT',
      body: payload,
    });
  });

  it('tests notification channel', async () => {
    const mockResponse = { status: 'success', detail: 'dispatched' };
    vi.mocked(apiClient.request).mockResolvedValue(mockResponse);

    const payload = { config: { token: 'x' } };
    const result = await testChannel('gotify', payload);
    
    expect(result).toEqual(mockResponse);
    expect(apiClient.request).toHaveBeenCalledWith('/notifications/gotify/test', {
      method: 'POST',
      body: payload,
    });
  });
});
