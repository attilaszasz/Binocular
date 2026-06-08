import { useMemo } from 'react';
import {
  AlertCircle,
  Binoculars,
  CheckCircle2,
  Package,
  Plus,
  Server,
} from 'lucide-react';

import { CheckResult, DeviceInput, DeviceGroup, InstalledModule, InventoryDevice } from '@/api';
import { Button } from '@/components/ui/button';
import { DeviceCard } from '@/components/inventory/DeviceCard';
import { DeviceForm } from '@/components/inventory/DeviceForm';
import { StatCard } from '@/components/inventory/StatCard';

interface InventoryPageProps {
  groups: DeviceGroup[];
  stats: { total: number; updates: number; upToDate: number };
  isLoading: boolean;
  error: string | null;
  formValues: DeviceInput;
  editingDevice: InventoryDevice | null;
  showForm: boolean;
  onFormChange: (field: keyof DeviceInput, value: string) => void;
  onSubmit: (event: React.FormEvent<HTMLFormElement>) => void;
  onCancelEdit: () => void;
  onShowForm: (show: boolean) => void;
  onEdit: (device: InventoryDevice) => void;
  onArchive: (device: InventoryDevice) => void;
  onMarkUpdated: (device: InventoryDevice) => void;
  modules: InstalledModule[];
  manualResults: Record<number, CheckResult>;
  manualError: string | null;
  bulkSummary: { total: number; succeeded: number; failed: number } | null;
  checkingDeviceIds: Set<number>;
  isBulkChecking: boolean;
  onRunDeviceCheck: (device: InventoryDevice) => void;
  onRunAllChecks: () => void;
}

export function InventoryPage({
  groups,
  stats,
  isLoading,
  error,
  formValues,
  editingDevice,
  showForm,
  onFormChange,
  onSubmit,
  onCancelEdit,
  onShowForm,
  onEdit,
  onArchive,
  onMarkUpdated,
  modules,
  manualResults,
  manualError,
  bulkSummary,
  checkingDeviceIds,
  isBulkChecking,
  onRunDeviceCheck,
  onRunAllChecks,
}: InventoryPageProps) {
  const devices = useMemo(
    () => groups.flatMap((group) => group.devices),
    [groups],
  );
  const canCheckAll = devices.some((d) => d.moduleId !== null);

  const sortedGroups = useMemo(
    () =>
      [...groups].sort((a, b) => {
        const aUnlinked = a.name === 'Unlinked' ? 1 : 0;
        const bUnlinked = b.name === 'Unlinked' ? 1 : 0;
        return aUnlinked - bUnlinked;
      }),
    [groups],
  );

  return (
    <div className="space-y-8">
      <div className="flex flex-col justify-between gap-4 sm:flex-row sm:items-center">
        <div>
          <h2 className="text-2xl font-bold tracking-tight">Device Inventory</h2>
          <p className="mt-1 text-sm text-muted-foreground">
            Manage your hardware and monitor for firmware updates.
          </p>
        </div>
        <div className="flex flex-wrap items-center gap-3">
          <Button
            variant="outline"
            onClick={onRunAllChecks}
            disabled={!canCheckAll || isBulkChecking}
          >
            <Binoculars size={16} className="mr-2" />
            {isBulkChecking ? 'Checking...' : 'Check All'}
          </Button>
          <Button
            variant="outline"
            onClick={() => onShowForm(true)}
          >
            <Plus size={16} className="mr-2" />
            Add Device
          </Button>
        </div>
      </div>

      {(showForm || editingDevice !== null) && (
        <DeviceForm
          formValues={formValues}
          editingDevice={editingDevice}
          onFormChange={onFormChange}
          onSubmit={onSubmit}
          onCancelEdit={onCancelEdit}
          onShowForm={onShowForm}
          showForm={showForm}
          modules={modules}
        />
      )}

      {error !== null && (
        <div className="rounded-xl border border-destructive/30 bg-destructive/10 px-4 py-3 text-sm text-destructive">
          {error}
        </div>
      )}

      {manualError !== null && (
        <div className="rounded-xl border border-destructive/30 bg-destructive/10 px-4 py-3 text-sm text-destructive">
          {manualError}
        </div>
      )}

      {bulkSummary !== null && (
        <div className="rounded-xl border border-emerald-200 dark:border-emerald-800 bg-emerald-50 dark:bg-emerald-950 px-4 py-3 text-sm text-emerald-600 dark:text-emerald-400">
          Manual bulk check complete: {bulkSummary.succeeded}/{bulkSummary.total}{' '}
          succeeded, {bulkSummary.failed} failed.
        </div>
      )}

      <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
        <StatCard
          label="Total Devices"
          value={stats.total}
          icon={Server}
          tone="indigo"
        />
        <StatCard
          label="Updates Available"
          value={stats.updates}
          icon={AlertCircle}
          tone="rose"
        />
        <StatCard
          label="Up to Date"
          value={stats.upToDate}
          icon={CheckCircle2}
          tone="emerald"
        />
      </div>

      {isLoading && (
        <p className="text-sm text-muted-foreground">Loading inventory...</p>
      )}

      {!isLoading && groups.length === 0 && (
        <div className="rounded-2xl border border-dashed border p-8 text-center text-sm text-muted-foreground">
          No devices tracked yet.
        </div>
      )}

      {sortedGroups.map((group) => (
        <section key={group.moduleId ?? 'ungrouped'} className="space-y-4">
          <h3 className="flex items-center text-sm font-semibold uppercase tracking-wider text-muted-foreground">
            <Package size={16} className="mr-2" />
            {group.name} ({group.count})
          </h3>
          <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
            {group.devices.map((device) => (
              <DeviceCard
                key={device.id}
                device={device}
                onEdit={onEdit}
                onArchive={onArchive}
                onMarkUpdated={onMarkUpdated}
                manualResult={manualResults[device.id]}
                isChecking={checkingDeviceIds.has(device.id)}
                canCheck={device.moduleId !== null}
                onRunCheck={onRunDeviceCheck}
              />
            ))}
          </div>
        </section>
      ))}
    </div>
  );
}
