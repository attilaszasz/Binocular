import { Pencil, Trash2 } from "lucide-react";

import type { Device } from "../../api/types";
import { ErrorBanner } from "../../components/ErrorBanner";
import { StatusIndicator } from "./StatusIndicator";
import { VersionComparison } from "./VersionComparison";

interface DeviceCardProps {
  device: Device;
  onConfirm: (deviceId: number) => void;
  onEdit: (device: Device) => void;
  onDelete: (device: Device) => void;
  isConfirmPending: boolean;
  errorMessage?: string;
}

function formatLastChecked(value: string | null): string {
  if (!value) {
    return "Never checked";
  }

  const parsed = new Date(value);
  const deltaSeconds = Math.floor((Date.now() - parsed.getTime()) / 1000);
  if (deltaSeconds < 60) {
    return "just now";
  }
  const deltaMinutes = Math.floor(deltaSeconds / 60);
  if (deltaMinutes < 60) {
    return `${deltaMinutes} minute${deltaMinutes === 1 ? "" : "s"} ago`;
  }
  const deltaHours = Math.floor(deltaMinutes / 60);
  if (deltaHours < 24) {
    return `${deltaHours} hour${deltaHours === 1 ? "" : "s"} ago`;
  }
  const deltaDays = Math.floor(deltaHours / 24);
  return `${deltaDays} day${deltaDays === 1 ? "" : "s"} ago`;
}

export function DeviceCard({
  device,
  onConfirm,
  onEdit,
  onDelete,
  isConfirmPending,
  errorMessage,
}: DeviceCardProps) {
  return (
    <article className="rounded-lg border border-slate-200 bg-white p-4 shadow-sm dark:border-slate-800 dark:bg-slate-900">
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0">
          <h3
            className="truncate text-base font-semibold text-slate-900 dark:text-slate-100"
            title={device.name}
          >
            {device.name}
          </h3>
          <p
            className="mt-1 text-xs text-slate-500 dark:text-slate-400"
            title={device.last_checked_at ?? "Never checked"}
          >
            Last checked: {formatLastChecked(device.last_checked_at)}
          </p>
        </div>
        <StatusIndicator status={device.status} />
      </div>

      <div className="mt-3">
        <VersionComparison
          localVersion={device.current_version}
          latestVersion={device.latest_seen_version}
        />
      </div>

      {errorMessage ? (
        <div className="mt-3">
          <ErrorBanner message={errorMessage} />
        </div>
      ) : null}

      <div className="mt-4 flex flex-wrap items-center gap-2">
        {device.status === "update_available" && device.latest_seen_version ? (
          <button
            type="button"
            onClick={() => onConfirm(device.id)}
            disabled={isConfirmPending}
            className="rounded-md bg-blue-600 px-3 py-2 text-xs font-medium text-white hover:bg-blue-700 disabled:cursor-not-allowed disabled:opacity-50 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-500"
          >
            {isConfirmPending ? "Syncing..." : "Sync Local"}
          </button>
        ) : null}

        <button
          type="button"
          onClick={() => onEdit(device)}
          className="inline-flex items-center gap-1 rounded-md border border-slate-300 px-3 py-2 text-xs font-medium text-slate-700 hover:bg-slate-100 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-500 dark:border-slate-700 dark:text-slate-200 dark:hover:bg-slate-800"
        >
          <Pencil size={14} />
          Edit
        </button>

        <button
          type="button"
          onClick={() => onDelete(device)}
          className="inline-flex items-center gap-1 rounded-md border border-red-300 px-3 py-2 text-xs font-medium text-red-700 hover:bg-red-50 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-red-500 dark:border-red-700 dark:text-red-300 dark:hover:bg-red-900/20"
        >
          <Trash2 size={14} />
          Delete
        </button>
      </div>
    </article>
  );
}
