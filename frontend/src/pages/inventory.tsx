/**
 * InventoryPage — device inventory dashboard with stat cards, device list,
 * and add/edit form.
 */
import { useState } from "react";
import { ArrowUpCircle, CheckCircle, Monitor, Plus, RefreshCw } from "lucide-react";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { DeviceCard } from "@/components/inventory/device-card";
import { DeviceForm } from "@/components/inventory/device-form";
import { EmptyState } from "@/components/inventory/empty-state";
import { StatCard } from "@/components/inventory/stat-card";
import {
  useConfirmUpdate,
  useCreateDevice,
  useDeleteDevice,
  useDevices,
  useUpdateDevice,
  useCheckBulk,
} from "@/hooks/use-devices";
import type { Device, DeviceCreate, DeviceUpdate } from "@/lib/api";

type FormMode = { type: "closed" } | { type: "add" } | { type: "edit"; device: Device };

export function InventoryPage() {
  const { data: devices, isLoading, error } = useDevices();
  const createDevice = useCreateDevice();
  const updateDevice = useUpdateDevice();
  const deleteDevice = useDeleteDevice();
  const confirmUpdate = useConfirmUpdate();
  const checkBulk = useCheckBulk();

  const [formMode, setFormMode] = useState<FormMode>({ type: "closed" });

  const totalDevices = devices?.length ?? 0;
  const updatesAvailable =
    devices?.filter((d) => d.has_update).length ?? 0;
  const checkedDevices =
    devices?.filter((d) => d.last_checked !== null).length ?? 0;

  const handleAdd = () => setFormMode({ type: "add" });
  const handleEdit = (device: Device) => setFormMode({ type: "edit", device });
  const handleCancel = () => setFormMode({ type: "closed" });

  const handleCheckAll = () => {
    checkBulk.mutate();
  };

  const handleSubmit = (data: DeviceCreate | DeviceUpdate) => {
    if (formMode.type === "add") {
      createDevice.mutate(data as DeviceCreate, {
        onSuccess: () => setFormMode({ type: "closed" }),
      });
    } else if (formMode.type === "edit") {
      updateDevice.mutate(
        { id: formMode.device.id, data: data as DeviceUpdate },
        { onSuccess: () => setFormMode({ type: "closed" }) },
      );
    }
  };

  const handleDelete = (device: Device) => {
    if (window.confirm(`Delete "${device.name}"?`)) {
      deleteDevice.mutate(device.id);
    }
  };

  const handleConfirm = (device: Device) => {
    confirmUpdate.mutate(device.id);
  };

  if (error) {
    return (
      <div className="space-y-6">
        <h1 className="text-3xl font-bold tracking-tight">Inventory</h1>
        <Card>
          <CardContent className="p-6">
            <p className="text-destructive">
              Failed to load devices. Please try again later.
            </p>
          </CardContent>
        </Card>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-3xl font-bold tracking-tight">Inventory</h1>
        {totalDevices > 0 && formMode.type === "closed" && (
          <div className="flex items-center gap-2">
            <Button
              variant="outline"
              onClick={handleCheckAll}
              disabled={checkBulk.isPending}
            >
              <RefreshCw className={`mr-2 h-4 w-4 ${checkBulk.isPending ? "animate-spin" : ""}`} />
              Check All
            </Button>
            <Button onClick={handleAdd}>
              <Plus className="mr-2 h-4 w-4" />
              Add Device
            </Button>
          </div>
        )}
      </div>

      {/* Summary stats */}
      {!isLoading && totalDevices > 0 && (
        <div className="grid gap-4 sm:grid-cols-3">
          <StatCard
            title="Devices"
            value={totalDevices}
            icon={Monitor}
          />
          <StatCard
            title="Updates Available"
            value={updatesAvailable}
            icon={ArrowUpCircle}
          />
          <StatCard
            title="Checked"
            value={checkedDevices}
            icon={CheckCircle}
            description={`of ${totalDevices} devices`}
          />
        </div>
      )}

      {/* Add / Edit form */}
      {formMode.type !== "closed" && (
        <Card>
          <CardHeader>
            <CardTitle>
              {formMode.type === "add" ? "Add Device" : "Edit Device"}
            </CardTitle>
            <CardDescription>
              {formMode.type === "add"
                ? "Register a new device for firmware monitoring."
                : `Editing "${formMode.device.name}"`}
            </CardDescription>
          </CardHeader>
          <CardContent>
            <DeviceForm
              device={formMode.type === "edit" ? formMode.device : undefined}
              onSubmit={handleSubmit}
              onCancel={handleCancel}
              isPending={createDevice.isPending || updateDevice.isPending}
            />
          </CardContent>
        </Card>
      )}

      {/* Loading skeleton */}
      {isLoading && (
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
          {[1, 2, 3].map((i) => (
            <Card key={i} className="animate-pulse">
              <CardContent className="h-40 p-6" />
            </Card>
          ))}
        </div>
      )}

      {/* Empty state */}
      {!isLoading && totalDevices === 0 && formMode.type === "closed" && (
        <EmptyState onAdd={handleAdd} />
      )}

      {/* Device grid */}
      {!isLoading && totalDevices > 0 && (
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
          {devices!.map((device) => (
            <DeviceCard
              key={device.id}
              device={device}
              onEdit={handleEdit}
              onDelete={handleDelete}
              onConfirm={handleConfirm}
            />
          ))}
        </div>
      )}
    </div>
  );
}
