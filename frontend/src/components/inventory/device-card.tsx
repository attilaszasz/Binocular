import { useState } from "react";
import {
  ArrowUpCircle,
  CheckCircle2,
  Monitor,
  Pencil,
  Trash2,
  RefreshCw,
  AlertCircle,
} from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { useCheckDevice } from "@/hooks/use-devices";
import type { Device } from "@/lib/api";

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

  const handleCheck = () => {
    setCheckError(null);
    checkDevice.mutate(device.id, {
      onSuccess: (data) => {
        if (!data.success) {
          setCheckError(data.error_message || "Check failed");
        }
      },
      onError: (err: any) => {
        setCheckError(err.message || "Network error");
      },
    });
  };

  return (
    <Card className="relative overflow-hidden">
      <CardHeader className="flex flex-row items-start justify-between space-y-0 pb-2">
        <div className="space-y-1">
          <CardTitle className="flex items-center gap-2 text-base">
            <Monitor className="h-4 w-4 text-muted-foreground" />
            {device.name}
          </CardTitle>
          {device.model && (
            <p className="text-sm text-muted-foreground">{device.model}</p>
          )}
        </div>
        <div className="flex items-center gap-1">
          <Button
            variant="ghost"
            size="icon"
            className="h-8 w-8"
            onClick={handleCheck}
            disabled={checkDevice.isPending}
            title="Check for update"
          >
            <RefreshCw className={`h-4 w-4 ${checkDevice.isPending ? "animate-spin" : ""}`} />
          </Button>
          <Button
            variant="ghost"
            size="icon"
            className="h-8 w-8"
            onClick={() => onEdit(device)}
            title="Edit device"
          >
            <Pencil className="h-4 w-4" />
          </Button>
          <Button
            variant="ghost"
            size="icon"
            className="h-8 w-8 text-destructive hover:text-destructive"
            onClick={() => onDelete(device)}
            title="Delete device"
          >
            <Trash2 className="h-4 w-4" />
          </Button>
        </div>
      </CardHeader>
      <CardContent className="space-y-3">
        <div className="flex flex-wrap gap-2 items-center">
          <Badge variant="secondary">{device.device_type}</Badge>
          
          {device.has_update ? (
            <div className="flex items-center gap-1.5 text-xs font-medium bg-amber-50 dark:bg-amber-950/30 text-amber-800 dark:text-amber-300 px-2 py-0.5 rounded-md border border-amber-200/50 dark:border-amber-900/30">
              <span>v{device.current_version}</span>
              <span className="text-amber-400">→</span>
              <span className="font-semibold text-amber-900 dark:text-amber-200 flex items-center gap-1">
                <ArrowUpCircle className="h-3 w-3 animate-bounce" />
                v{device.latest_detected_version}
              </span>
            </div>
          ) : (
            <div className="flex items-center gap-1.5 text-xs text-muted-foreground bg-muted px-2 py-0.5 rounded-md border border-transparent">
              <span>v{device.current_version || "—"}</span>
              <span className="text-[10px] px-1 py-0.2 rounded bg-emerald-100 dark:bg-emerald-950 text-emerald-800 dark:text-emerald-300 font-semibold flex items-center gap-0.5">
                <CheckCircle2 className="h-2.5 w-2.5" /> Latest
              </span>
            </div>
          )}
        </div>

        {checkError && (
          <div className="flex items-start gap-1.5 text-xs text-destructive bg-destructive/10 p-2 rounded border border-destructive/20">
            <AlertCircle className="h-3.5 w-3.5 shrink-0 mt-0.5" />
            <span className="break-all">{checkError}</span>
          </div>
        )}

        {device.last_checked && (
          <p className="text-xs text-muted-foreground">
            Last checked:{" "}
            {new Date(device.last_checked).toLocaleString()}
          </p>
        )}

        {device.has_update && (
          <Button
            size="sm"
            variant="outline"
            className="mt-2"
            onClick={() => onConfirm(device)}
          >
            <CheckCircle2 className="mr-1 h-4 w-4" />
            Confirm Update
          </Button>
        )}
      </CardContent>
    </Card>
  );
}

