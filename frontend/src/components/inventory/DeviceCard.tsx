import { ArrowRight, Check, Unlink } from 'lucide-react';

import { CheckResult, InventoryDevice } from '@/api';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardFooter, CardHeader } from '@/components/ui/card';

interface DeviceCardProps {
  device: InventoryDevice;
  onEdit: (device: InventoryDevice) => void;
  onArchive: (device: InventoryDevice) => void;
  onMarkUpdated: (device: InventoryDevice) => void;
  manualResult: CheckResult | undefined;
  isChecking: boolean;
  canCheck: boolean;
  onRunCheck: (device: InventoryDevice) => void;
}

function statusLabel(device: InventoryDevice) {
  if (device.status === 'never_checked') {
    return 'Not checked yet';
  }
  if (device.status === 'check_failed') {
    return 'Last check failed';
  }
  if (device.lastCheckedAt !== null) {
    return `Last checked: ${new Date(device.lastCheckedAt).toLocaleString()}`;
  }
  return device.status === 'update_available' ? 'Update available' : 'Up to date';
}

function VersionBlock({
  label,
  value,
  highlight,
}: {
  label: string;
  value: string;
  highlight?: 'update' | 'ok';
}) {
  const colorClass =
    highlight === 'update'
      ? 'text-destructive'
      : highlight === 'ok'
        ? 'text-emerald-600 dark:text-emerald-400'
        : 'text-foreground';
  return (
    <div className="min-w-0 flex-1">
      <p className="mb-1 text-xs font-medium uppercase tracking-wider text-muted-foreground">
        {label}
      </p>
      <p className={`font-mono text-lg font-semibold ${colorClass}`}>{value}</p>
    </div>
  );
}

export function DeviceCard({
  device,
  onEdit,
  onArchive,
  onMarkUpdated,
  manualResult,
  isChecking,
  canCheck,
  onRunCheck,
}: DeviceCardProps) {
  const hasUpdate =
    device.status === 'update_available' && device.latestVersion !== null;
  const latestVersion = device.latestVersion ?? 'Not checked';
  const resultStatus = manualResult?.status.replaceAll('_', ' ');

  return (
    <Card
      className={
        hasUpdate
          ? 'border-destructive/30 ring-1 ring-destructive/30 dark:ring-0 dark:shadow-[0_0_15px_hsl(var(--destructive)/0.12)]'
          : ''
      }
    >
      <CardHeader>
        <div className="flex items-start justify-between gap-4">
          <div>
            <h4 className="text-lg font-bold text-foreground truncate max-w-full">
              {device.name}
            </h4>
            <p className="mt-1 font-mono text-xs font-semibold text-muted-foreground truncate max-w-full">
              {device.model}
            </p>
            {device.deviceType && (
              <p className="mt-1 text-xs font-medium text-primary">
                {device.deviceType}
              </p>
            )}
            {device.moduleId === null && (
              <Badge
                variant="outline"
                className="mt-2 gap-1 border-amber-200 dark:border-amber-800 bg-amber-50 dark:bg-amber-950 text-amber-700 dark:text-amber-300"
              >
                <Unlink size={12} />
                Unlinked
              </Badge>
            )}
            <p className="mt-1 text-xs text-muted-foreground">
              {statusLabel(device)}
            </p>
          </div>
          <div className="flex gap-2">
            <Button
              variant="outline"
              size="sm"
              onClick={() => onRunCheck(device)}
              disabled={!canCheck || isChecking}
            >
              {isChecking ? 'Checking...' : 'Check Now'}
            </Button>
            <Button variant="ghost" size="sm" onClick={() => onEdit(device)}>
              Edit
            </Button>
            <Button variant="ghost" size="sm" onClick={() => onArchive(device)}>
              Archive
            </Button>
          </div>
        </div>
      </CardHeader>

      <CardContent>
        <div
          className={`flex items-center justify-between rounded-xl p-4 ${
            hasUpdate ? 'bg-destructive/10' : 'bg-background'
          }`}
        >
          <div className="flex flex-1 items-center gap-4">
            <VersionBlock label="Recorded" value={device.currentVersion} />
            {hasUpdate && (
              <ArrowRight
                size={20}
                className="shrink-0 animate-pulse text-destructive"
              />
            )}
            <VersionBlock
              label="Latest"
              value={latestVersion}
              highlight={
                hasUpdate
                  ? 'update'
                  : device.status === 'up_to_date'
                    ? 'ok'
                    : undefined
              }
            />
          </div>

          {hasUpdate && (
            <div className="ml-4 shrink-0 border-l border pl-4">
              <Button
                variant="outline"
                size="sm"
                onClick={() => onMarkUpdated(device)}
              >
                <Check size={16} className="mr-1.5" />
                Sync Local
              </Button>
            </div>
          )}
        </div>
      </CardContent>

      {manualResult !== undefined && (
        <CardFooter className="flex-col items-start">
          <div className="mt-3 w-full rounded-xl border bg-card px-4 py-3 text-sm">
            <div className="flex flex-wrap items-center justify-between gap-2">
              <span className="font-medium capitalize text-foreground">
                Manual result: {resultStatus}
              </span>
              <span className="text-xs text-muted-foreground">
                {manualResult.lastCheckedAt === null
                  ? 'No timestamp'
                  : new Date(manualResult.lastCheckedAt).toLocaleString()}
              </span>
            </div>
            <div className="mt-2 grid grid-cols-2 gap-3 font-mono text-xs text-muted-foreground">
              <span>Stored: {manualResult.currentVersion}</span>
              <span>
                Latest: {manualResult.latestVersion ?? 'Unavailable'}
              </span>
            </div>
            {manualResult.detail !== null && (
              <p className="mt-2 text-xs text-destructive">
                {manualResult.detail}
              </p>
            )}
          </div>
        </CardFooter>
      )}
    </Card>
  );
}
