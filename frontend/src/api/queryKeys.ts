export const queryKeys = {
  deviceTypes: {
    all: () => ["device-types"] as const,
  },
  devices: {
    all: () => ["devices"] as const,
    byType: (deviceTypeId: number) => ["devices", { device_type_id: deviceTypeId }] as const,
  },
} as const;
