import type { Device } from "../../api/types";
import { DeviceCard } from "./DeviceCard";

interface DeviceTypeGroupProps {
  name: string;
  deviceCount: number;
  devices: Device[];
  onConfirm: (deviceId: number) => void;
  onEdit: (device: Device) => void;
  onDelete: (device: Device) => void;
  pendingConfirmIds: Set<number>;
  confirmErrors: Record<number, string | undefined>;
}

export function DeviceTypeGroup({
  name,
  deviceCount,
  devices,
  onConfirm,
  onEdit,
  onDelete,
  pendingConfirmIds,
  confirmErrors,
}: DeviceTypeGroupProps) {
  return (
    <section className="mt-6">
      <div className="mb-3 flex items-center justify-between gap-3">
        <h2 className="text-lg font-semibold">{name}</h2>
        <span className="rounded-full bg-slate-200 px-2 py-1 text-xs text-slate-700 dark:bg-slate-800 dark:text-slate-300">
          {deviceCount} {deviceCount === 1 ? "device" : "devices"}
        </span>
      </div>
      {devices.length ? (
        <div className="grid grid-cols-1 gap-3 lg:grid-cols-2">
          {devices.map((device) => (
            <DeviceCard
              key={device.id}
              device={device}
              onConfirm={onConfirm}
              onEdit={onEdit}
              onDelete={onDelete}
              isConfirmPending={pendingConfirmIds.has(device.id)}
              errorMessage={confirmErrors[device.id]}
            />
          ))}
        </div>
      ) : (
        <div className="rounded-lg border border-dashed border-slate-300 px-4 py-6 text-sm text-slate-500 dark:border-slate-700 dark:text-slate-400">
          No devices in this group yet.
        </div>
      )}
    </section>
  );
}
