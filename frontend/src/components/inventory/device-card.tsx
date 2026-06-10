/**
 * DeviceCard — displays a single device with key details and actions.
 */
import {
  ArrowUpCircle,
  CheckCircle2,
  Monitor,
  Pencil,
  Trash2,
} from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
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
  return (
    <Card>
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
        <div className="flex flex-wrap gap-2">
          <Badge variant="secondary">{device.device_type}</Badge>
          <Badge variant="outline">v{device.current_version || "—"}</Badge>
          {device.has_update && (
            <Badge variant="default" className="bg-amber-500 text-white">
              <ArrowUpCircle className="mr-1 h-3 w-3" />
              Update: v{device.latest_detected_version}
            </Badge>
          )}
        </div>

        {device.last_checked && (
          <p className="text-xs text-muted-foreground">
            Last checked:{" "}
            {new Date(device.last_checked).toLocaleDateString()}
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
