import { useState } from "react";
import {
  ArrowUpCircle,
  ArrowRight,
  CheckCircle2,
  Monitor,
  Pencil,
  Trash2,
  RefreshCw,
  AlertCircle,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { useCheckDevice } from "@/hooks/use-devices";
import { deviceComparisonStatus, type ComparisonStatus, type Device } from "@/lib/api";

const statusLabels: Record<ComparisonStatus, string> = {
  unknown: "Installed version unknown",
  comparison_unknown: "Versions cannot be compared",
  unverified: "Not verified",
  current: "Latest",
  update_available: "Update available",
  no_firmware: "No firmware available",
  stale: "Verification stale",
  failed: "Verification failed",
};

interface DeviceCardProps {
  device: Device;
  onEdit: (device: Device) => void;
  onDelete: (device: Device) => void;
  onConfirm: (device: Device) => void;
}

export function DeviceCard({
  device,
  onEdit,
  onDelete,
  onConfirm,
}: DeviceCardProps) {
  const checkDevice = useCheckDevice();
  const [checkError, setCheckError] = useState<string | null>(null);
  const status = checkError ? "failed" : deviceComparisonStatus(device);
  const hasUpdate = status === "update_available" && !!device.latest_detected_version?.trim();

  const handleCheck = () => {
    setCheckError(null);
    checkDevice.mutate(device.id, {
      onSuccess: (data) => {
        if (!data.success) {
          setCheckError(data.error_message || "Check failed");
        }
      },
      onError: (err: Error) => {
        setCheckError(err.message || "Network error");
      },
    });
  };

  return (
    <Card className="relative overflow-hidden">
      <CardHeader className="flex flex-row items-start justify-between space-y-0 p-3.5 pb-1.5 gap-2">
        <div className="space-y-0.5 min-w-0 flex-1">
          <CardTitle className="flex items-center gap-1.5 text-sm font-semibold">
            <Monitor className="h-3.5 w-3.5 text-muted-foreground shrink-0" />
            <span className="truncate" title={device.name}>{device.name}</span>
          </CardTitle>
          {device.model && (
            <p className="text-xs text-muted-foreground truncate" title={device.model}>
              {device.model}
            </p>
          )}
        </div>
        <div className="flex items-center gap-0.5 shrink-0">
          <Button
            variant="ghost"
            size="icon-sm"
            onClick={handleCheck}
            disabled={checkDevice.isPending}
            title="Check for update"
            aria-label="Check for update"
          >
            <RefreshCw className={`h-3.5 w-3.5 ${checkDevice.isPending ? "animate-spin" : ""}`} />
          </Button>
          <Button
            variant="ghost"
            size="icon-sm"
            onClick={() => onEdit(device)}
            title="Edit device"
            aria-label="Edit device"
          >
            <Pencil className="h-3.5 w-3.5" />
          </Button>
          <Button
            variant="ghost"
            size="icon-sm"
            className="text-destructive hover:text-destructive"
            onClick={() => onDelete(device)}
            title="Delete device"
            aria-label="Delete device"
          >
            <Trash2 className="h-3.5 w-3.5" />
          </Button>
        </div>
      </CardHeader>
      <CardContent className="p-3.5 pt-0 space-y-2">
        <div role="status" aria-label="Firmware status" className="flex flex-wrap gap-1.5 items-center">
          {hasUpdate ? (
            <div className="flex items-center gap-1 text-[11px] font-medium bg-amber-50 dark:bg-amber-950/30 text-amber-800 dark:text-amber-300 px-1.5 py-0.5 rounded border border-amber-200/50 dark:border-amber-900/30">
              <span className="sr-only">{statusLabels[status]}: </span>
              <span>{device.current_version}</span>
              <ArrowRight aria-hidden="true" className="h-3 w-3" />
              <span className="font-semibold text-amber-900 dark:text-amber-200 flex items-center gap-0.5">
                <ArrowUpCircle className="h-3 w-3 animate-bounce" />
                {device.latest_detected_version}
              </span>
            </div>
          ) : (
            <div className="flex items-center gap-1 text-[11px] text-foreground bg-muted px-1.5 py-0.5 rounded border border-transparent">
              <span>{device.current_version || "—"}</span>
              <span className="text-[9px] px-1 py-0.1 rounded font-semibold flex items-center gap-0.5">
                {status === "current" && <CheckCircle2 className="h-2.5 w-2.5" />}
                {statusLabels[status]}
              </span>
            </div>
          )}
        </div>

        {!hasUpdate && status !== "current" && device.latest_detected_version && (
          <p className="text-[11px] text-muted-foreground">
            Last detected version (reference only): {device.latest_detected_version}
          </p>
        )}
        {device.catalog_link_state === "legacy" && (
          <p className="text-[11px] text-muted-foreground">Legacy manual entry · per-model checks</p>
        )}
        {device.catalog_link_state === "unresolved" && (
          <p className="text-[11px] text-muted-foreground">Catalog link unresolved</p>
        )}

        {checkError && (
          <div role="alert" className="flex items-start gap-1.5 text-[11px] text-destructive bg-destructive/10 p-2 rounded border border-destructive/20">
            <AlertCircle className="h-3 w-3 shrink-0 mt-0.5" />
            <span className="break-all">{checkError}</span>
          </div>
        )}

        {!checkError && device.comparison_status === "failed" && (
          <p role="alert" className="text-[11px] text-destructive">
            Last verification failed; retained firmware is reference only.
          </p>
        )}

        {device.last_checked && (
          <p className="text-[11px] text-muted-foreground">
            Last successfully checked:{" "}
            {new Date(device.last_checked).toLocaleString()}
          </p>
        )}

        {device.last_check_attempt_at && device.last_check_attempt_at !== device.last_checked && (
          <p className="text-[11px] text-muted-foreground">
            Last check attempt: {new Date(device.last_check_attempt_at).toLocaleString()}
          </p>
        )}

        {hasUpdate && (
          <Button
            size="sm"
            variant="outline"
            className="mt-1"
            onClick={() => onConfirm(device)}
          >
            <CheckCircle2 className="mr-1 h-3.5 w-3.5" />
            Confirm Update
          </Button>
        )}
      </CardContent>
    </Card>
  );
}
