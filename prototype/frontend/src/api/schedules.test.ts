import { describe, expect, it, vi } from 'vitest';
import { listSchedules } from './schedules';
import { apiClient } from './client';

vi.mock('./client', () => ({
  apiClient: {
    get: vi.fn(),
    request: vi.fn(),
  },
}));

describe('schedules API', () => {
  it('fetches schedule list', async () => {
    const mockSchedules = { schedules: [] };
    vi.mocked(apiClient.get).mockResolvedValue(mockSchedules);

    const result = await listSchedules();
    expect(result).toEqual(mockSchedules);
    expect(apiClient.get).toHaveBeenCalledWith('/schedules');
  });
});
