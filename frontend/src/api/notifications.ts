import { apiClient } from './client';

export type NotificationChannel = {
  id: number;
  type: 'smtp' | 'gotify';
  enabled: boolean;
  config: Record<string, any>;
};

export type UpdateChannelRequest = {
  enabled: boolean;
  config: Record<string, any>;
};

export type TestChannelRequest = {
  config: Record<string, any>;
};

export type TestChannelResponse = {
  status: string;
  detail: string;
};

export function listChannels() {
  return apiClient.get<NotificationChannel[]>('/notifications');
}

export function configureChannel(channelType: 'smtp' | 'gotify', payload: UpdateChannelRequest) {
  return apiClient.request<NotificationChannel>(`/notifications/${channelType}`, {
    method: 'PUT',
    body: payload,
  });
}

export function testChannel(channelType: 'smtp' | 'gotify', payload: TestChannelRequest) {
  return apiClient.request<TestChannelResponse>(`/notifications/${channelType}/test`, {
    method: 'POST',
    body: payload,
  });
}
