import { useState } from "react";

import type { DeviceType } from "../../api/types";
import { ConfirmDialog } from "../../components/ConfirmDialog";
import { ErrorBanner } from "../../components/ErrorBanner";
import { CardSkeletonList } from "../../components/Skeleton";
import { SlideOverPanel } from "../../components/SlideOverPanel";
import { DeviceTypeForm } from "../forms/DeviceTypeForm";
import {
  useCreateDeviceType,
  useDeleteDeviceType,
  useModuleDeviceTypes,
  useUpdateDeviceType,
} from "./hooks";
import { ModuleCard } from "./ModuleCard";

export function ModulesPage() {
  const modulesQuery = useModuleDeviceTypes();
  const createMutation = useCreateDeviceType();
  const updateMutation = useUpdateDeviceType();
  const deleteMutation = useDeleteDeviceType();

  const [isCreateOpen, setIsCreateOpen] = useState(false);
  const [editingModule, setEditingModule] = useState<DeviceType | null>(null);
  const [deletingModule, setDeletingModule] = useState<DeviceType | null>(null);

  if (modulesQuery.isLoading) {
    return <CardSkeletonList count={3} />;
  }

  if (modulesQuery.isError) {
    return (
      <ErrorBanner message="Failed to load modules." onRetry={() => void modulesQuery.refetch()} />
    );
  }

  const modules = modulesQuery.data ?? [];

  return (
    <section>
      <div className="mb-4 flex flex-wrap items-center justify-between gap-3">
        <h2 className="text-lg font-semibold">Extension Modules</h2>
        <button
          type="button"
          className="rounded-md bg-blue-600 px-3 py-2 text-sm font-medium text-white hover:bg-blue-700 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-500"
          onClick={() => setIsCreateOpen(true)}
        >
          Add Module
        </button>
      </div>

      {modules.length ? (
        <div className="grid grid-cols-1 gap-3 lg:grid-cols-2">
          {modules.map((module) => (
            <ModuleCard
              key={module.id}
              module={module}
              onEdit={setEditingModule}
              onDelete={setDeletingModule}
            />
          ))}
        </div>
      ) : (
        <div className="rounded-lg border border-dashed border-slate-300 p-6 text-sm text-slate-500 dark:border-slate-700 dark:text-slate-400">
          No modules yet. Create one to organize your devices.
        </div>
      )}

      <SlideOverPanel
        title="Add Module"
        isOpen={isCreateOpen}
        onClose={() => setIsCreateOpen(false)}
      >
        <DeviceTypeForm
          mode="create"
          onCancel={() => setIsCreateOpen(false)}
          isSubmitting={createMutation.isPending}
          onSubmit={async (values) => {
            await createMutation.mutateAsync({
              name: values.name,
              firmware_source_url: values.firmwareSourceUrl,
              check_frequency_minutes: values.checkFrequencyMinutes,
              extension_module_id: null,
            });
            setIsCreateOpen(false);
          }}
        />
      </SlideOverPanel>

      <SlideOverPanel
        title="Edit Module"
        isOpen={editingModule !== null}
        onClose={() => setEditingModule(null)}
      >
        {editingModule ? (
          <DeviceTypeForm
            key={editingModule.id}
            mode="edit"
            initialValues={{
              name: editingModule.name,
              firmwareSourceUrl: editingModule.firmware_source_url,
              checkFrequencyMinutes: editingModule.check_frequency_minutes,
            }}
            onCancel={() => setEditingModule(null)}
            isSubmitting={updateMutation.isPending}
            onSubmit={async (values) => {
              await updateMutation.mutateAsync({
                deviceTypeId: editingModule.id,
                payload: {
                  name: values.name,
                  firmware_source_url: values.firmwareSourceUrl,
                  check_frequency_minutes: values.checkFrequencyMinutes,
                  extension_module_id: null,
                },
              });
              setEditingModule(null);
            }}
          />
        ) : null}
      </SlideOverPanel>

      <ConfirmDialog
        isOpen={deletingModule !== null}
        title="Delete Module"
        description={
          deletingModule
            ? deletingModule.device_count > 0
              ? `Delete ${deletingModule.name}? This will also delete ${deletingModule.device_count} devices.`
              : `Delete ${deletingModule.name}?`
            : "Delete selected module?"
        }
        confirmLabel={deletingModule?.device_count ? "Delete All" : "Delete"}
        onCancel={() => setDeletingModule(null)}
        onConfirm={() => {
          if (!deletingModule) {
            return;
          }
          void deleteMutation
            .mutateAsync({
              deviceTypeId: deletingModule.id,
              confirmCascade: deletingModule.device_count > 0,
            })
            .then(() => {
              setDeletingModule(null);
            });
        }}
      />
    </section>
  );
}
