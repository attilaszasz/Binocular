import { describe, expect, it, vi } from 'vitest';
import { listActivity } from './activity';
import { apiClient } from './client';

vi.mock('./client', () => ({
  apiClient: {
    get: vi.fn(),
  },
}));

describe('activity API', () => {
  it('lists activities without params', async () => {
    const mockActivities = [
      {
        id: 1,
        eventType: 'check',
        status: 'success',
        deviceName: 'Alpha 7 IV',
        moduleName: 'sony_alpha',
        message: 'Firmware check succeeded',
        traceback: null,
        createdAt: '2026-06-01T17:00:00Z',
      },
    ];
    vi.mocked(apiClient.get).mockResolvedValue(mockActivities);

    const result = await listActivity();
    expect(result).toEqual(mockActivities);
    expect(apiClient.get).toHaveBeenCalledWith('/audit-log');
  });

  it('lists activities with params', async () => {
    const mockActivities = [
      {
        id: 2,
        eventType: 'notification',
        status: 'failed',
        deviceName: null,
        moduleName: null,
        message: 'Notification failed',
        traceback: 'Traceback...',
        createdAt: '2026-06-01T17:05:00Z',
      },
    ];
    vi.mocked(apiClient.get).mockResolvedValue(mockActivities);

    const result = await listActivity({
      limit: 10,
      offset: 5,
      type: 'notification',
      status: 'failed',
    });
    expect(result).toEqual(mockActivities);
    expect(apiClient.get).toHaveBeenCalledWith('/audit-log?limit=10&offset=5&type=notification&status=failed');
  });
});
