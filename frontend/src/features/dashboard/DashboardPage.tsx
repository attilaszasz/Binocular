import { useQueryClient } from "@tanstack/react-query";
import { useMemo, useState } from "react";
import { queryKeys } from "../../api/queryKeys";
import { ApiError, type Device } from "../../api/types";
import { ConfirmDialog } from "../../components/ConfirmDialog";
import { ErrorBanner } from "../../components/ErrorBanner";
import { CardSkeletonList, StatsSkeleton } from "../../components/Skeleton";
import { SlideOverPanel } from "../../components/SlideOverPanel";
import { DeviceForm } from "../forms/DeviceForm";
import { DeviceTypeGroup } from "./DeviceTypeGroup";
import { EmptyState } from "./EmptyState";
import {
  useConfirmDevice,
  useCreateDevice,
  useDeleteDevice,
  useDevices,
  useDeviceTypes,
  useUpdateDevice,
} from "./hooks";
import { StatsRow } from "./StatsRow";

export function DashboardPage() {
  const queryClient = useQueryClient();
  const devicesQuery = useDevices();
  const deviceTypesQuery = useDeviceTypes();
  const createMutation = useCreateDevice();
  const updateMutation = useUpdateDevice();
  const deleteMutation = useDeleteDevice();
  const confirmMutation = useConfirmDevice();

  const [isCreateOpen, setIsCreateOpen] = useState(false);
  const [editingDevice, setEditingDevice] = useState<Device | null>(null);
  const [deletingDevice, setDeletingDevice] = useState<Device | null>(null);
  const [confirmErrors, setConfirmErrors] = useState<Record<number, string | undefined>>({});
  const [pendingConfirmIds, setPendingConfirmIds] = useState<Set<number>>(new Set());

  const devices = devicesQuery.data ?? [];
  const deviceTypes = deviceTypesQuery.data ?? [];

  const stats = useMemo(() => {
    const updatesAvailable = devices.filter(
      (device) => device.status === "update_available",
    ).length;
    const upToDate = devices.filter((device) => device.status === "up_to_date").length;
    return {
      totalDevices: devices.length,
      updatesAvailable,
      upToDate,
    };
  }, [devices]);

  const groupedByType = useMemo(() => {
    return deviceTypes.map((deviceType) => ({
      id: deviceType.id,
      name: deviceType.name,
      count: deviceType.device_count,
      devices: devices.filter((device) => device.device_type_id === deviceType.id),
    }));
  }, [deviceTypes, devices]);

  const isLoading = devicesQuery.isLoading || deviceTypesQuery.isLoading;
  const hasError = devicesQuery.isError || deviceTypesQuery.isError;

  async function handleConfirm(deviceId: number) {
    setConfirmErrors((current) => ({ ...current, [deviceId]: undefined }));
    setPendingConfirmIds((current) => new Set(current).add(deviceId));

    try {
      await confirmMutation.mutateAsync(deviceId);
    } catch (error) {
      const message =
        error instanceof ApiError ? error.message : "Something went wrong. Please try again.";
      setConfirmErrors((current) => ({ ...current, [deviceId]: message }));
    } finally {
      setPendingConfirmIds((current) => {
        const next = new Set(current);
        next.delete(deviceId);
        return next;
      });
    }
  }

  if (hasError) {
    return (
      <ErrorBanner
        message="Failed to load dashboard data."
        onRetry={() => {
          void Promise.all([devicesQuery.refetch(), deviceTypesQuery.refetch()]);
        }}
      />
    );
  }

  if (isLoading) {
    return (
      <section>
        <StatsSkeleton />
        <CardSkeletonList />
      </section>
    );
  }

  return (
    <section>
      <StatsRow {...stats} />

      <div className="mt-4 flex flex-wrap gap-2">
        <button
          type="button"
          onClick={() => setIsCreateOpen(true)}
          className="rounded-md bg-blue-600 px-3 py-2 text-sm font-medium text-white hover:bg-blue-700 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-500"
        >
          Add Device
        </button>
        <button
          type="button"
          onClick={() => {
            void Promise.all([
              queryClient.invalidateQueries({ queryKey: queryKeys.devices.all() }),
              queryClient.invalidateQueries({ queryKey: queryKeys.deviceTypes.all() }),
            ]);
          }}
          className="rounded-md border border-slate-300 px-3 py-2 text-sm font-medium text-slate-700 hover:bg-slate-100 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-500 dark:border-slate-700 dark:text-slate-200 dark:hover:bg-slate-800"
        >
          Refresh
        </button>
      </div>

      {!deviceTypes.length && !devices.length ? (
        <EmptyState />
      ) : (
        groupedByType.map((group) => (
          <DeviceTypeGroup
            key={group.id}
            name={group.name}
            deviceCount={group.count}
            devices={group.devices}
            onConfirm={handleConfirm}
            onEdit={setEditingDevice}
            onDelete={setDeletingDevice}
            pendingConfirmIds={pendingConfirmIds}
            confirmErrors={confirmErrors}
          />
        ))
      )}

      <SlideOverPanel
        title="Add Device"
        isOpen={isCreateOpen}
        onClose={() => {
          if (!createMutation.isPending) {
            setIsCreateOpen(false);
          }
        }}
      >
        <DeviceForm
          mode="create"
          deviceTypes={deviceTypes}
          onCancel={() => setIsCreateOpen(false)}
          isSubmitting={createMutation.isPending}
          onSubmit={async (values) => {
            await createMutation.mutateAsync({
              deviceTypeId: values.deviceTypeId,
              payload: {
                name: values.name,
                current_version: values.currentVersion,
                model: values.model,
                notes: values.notes,
              },
            });
            setIsCreateOpen(false);
          }}
        />
      </SlideOverPanel>

      <SlideOverPanel
        title="Edit Device"
        isOpen={editingDevice !== null}
        onClose={() => {
          if (!updateMutation.isPending) {
            setEditingDevice(null);
          }
        }}
      >
        {editingDevice ? (
          <DeviceForm
            key={editingDevice.id}
            mode="edit"
            deviceTypes={deviceTypes}
            initialValues={{
              name: editingDevice.name,
              currentVersion: editingDevice.current_version,
              model: editingDevice.model ?? "",
              notes: editingDevice.notes ?? "",
              deviceTypeId: editingDevice.device_type_id,
            }}
            onCancel={() => setEditingDevice(null)}
            isSubmitting={updateMutation.isPending}
            onSubmit={async (values) => {
              await updateMutation.mutateAsync({
                deviceId: editingDevice.id,
                payload: {
                  name: values.name,
                  current_version: values.currentVersion,
                  model: values.model,
                  notes: values.notes,
                },
              });
              setEditingDevice(null);
            }}
          />
        ) : null}
      </SlideOverPanel>

      <ConfirmDialog
        isOpen={deletingDevice !== null}
        title="Delete Device"
        description={
          deletingDevice
            ? `Delete ${deletingDevice.name}? This action cannot be undone.`
            : "Delete selected device?"
        }
        confirmLabel="Delete"
        onCancel={() => setDeletingDevice(null)}
        onConfirm={() => {
          if (!deletingDevice) {
            return;
          }
          void deleteMutation.mutateAsync(deletingDevice.id).then(() => {
            setDeletingDevice(null);
          });
        }}
      />
    </section>
  );
}
