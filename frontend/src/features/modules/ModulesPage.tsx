import { useState } from "react";
import { RefreshCw } from "lucide-react";

import type { ExtensionModule } from "../../api/types";
import { ConfirmDialog } from "../../components/ConfirmDialog";
import { ErrorBanner } from "../../components/ErrorBanner";
import { CardSkeletonList } from "../../components/Skeleton";
import { ModuleTable } from "./ModuleTable";
import { ModuleUploadArea } from "./ModuleUploadArea";
import { useDeleteModule, useModules, useReloadModules, useUploadModule } from "./hooks";

export function ModulesPage() {
  const modulesQuery = useModules();
  const uploadMutation = useUploadModule();
  const deleteMutation = useDeleteModule();
  const reloadMutation = useReloadModules();

  const [deletingModule, setDeletingModule] = useState<ExtensionModule | null>(null);

  const handleUpload = (file: File, options?: { testUrl?: string; testModel?: string }) => {
    uploadMutation.mutateAsync({ file, options }).catch(() => {
      // Error is surfaced via uploadMutation.error
    });
  };

  const handleConfirmDelete = () => {
    if (!deletingModule) return;
    void deleteMutation.mutateAsync(deletingModule.filename).then(() => {
      setDeletingModule(null);
    });
  };

  const modules = modulesQuery.data ?? [];

  return (
    <section>
      <div className="mb-4 flex flex-wrap items-center justify-between gap-3">
        <h2 className="text-lg font-semibold">Extension Modules</h2>
        <button
          type="button"
          className="inline-flex items-center gap-1.5 rounded-md border border-slate-300 px-3 py-2 text-sm font-medium text-slate-700 hover:bg-slate-100 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-500 dark:border-slate-700 dark:text-slate-200 dark:hover:bg-slate-800"
          onClick={() => void reloadMutation.mutateAsync()}
          disabled={reloadMutation.isPending}
        >
          <RefreshCw size={14} className={reloadMutation.isPending ? "animate-spin" : ""} />
          Reload Modules
        </button>
      </div>

      <div className="mb-6">
        <ModuleUploadArea
          onUpload={handleUpload}
          isUploading={uploadMutation.isPending}
          error={uploadMutation.error?.message ?? null}
        />
      </div>

      {modulesQuery.isLoading ? (
        <CardSkeletonList count={3} />
      ) : modulesQuery.isError ? (
        <ErrorBanner
          message="Failed to load modules."
          onRetry={() => void modulesQuery.refetch()}
        />
      ) : modules.length === 0 ? (
        <div className="rounded-lg border border-dashed border-slate-300 p-6 text-center text-sm text-slate-500 dark:border-slate-700 dark:text-slate-400">
          No extension modules registered yet. Upload a .py module file above.
        </div>
      ) : (
        <ModuleTable modules={modules} onDelete={setDeletingModule} />
      )}

      <ConfirmDialog
        isOpen={deletingModule !== null}
        title="Delete Module"
        description={
          deletingModule
            ? `Delete ${deletingModule.filename}? This action cannot be undone.`
            : "Delete selected module?"
        }
        confirmLabel="Delete"
        onCancel={() => setDeletingModule(null)}
        onConfirm={handleConfirmDelete}
      />
    </section>
  );
}
