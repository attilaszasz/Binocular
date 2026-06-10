import { useCallback, useEffect, useRef, useState } from 'react';
import { useMutation, useQueryClient } from '@tanstack/react-query';
import { Check, ClipboardCopy, RefreshCw } from 'lucide-react';
import type { InstalledModule, ModuleValidationSummary } from '@/api';
import { updateSchedule } from '@/api/schedules';
import { Button } from '@/components/ui/button';
import { ModuleUploadForm } from './ModuleUploadForm';
import { ModuleCard } from './ModuleCard';
import { ModuleGuidanceSection } from './ModuleGuidanceSection';
import { copyErrorsToClipboard, hasFindings } from './copyErrorsForAI';

function PageHeader({ title, description }: { title: string; description: string }) {
  return (
    <div>
      <h2 className="text-2xl font-bold tracking-tight">{title}</h2>
      <p className="mt-1 text-sm text-muted-foreground">{description}</p>
    </div>
  );
}

function ValidationSummary({ summary }: { summary: ModuleValidationSummary }) {
  const [copyState, setCopyState] = useState<'idle' | 'copied' | 'failed'>('idle');

  const handleCopy = useCallback(async () => {
    const ok = await copyErrorsToClipboard(summary);
    setCopyState(ok ? 'copied' : 'failed');
    setTimeout(() => setCopyState('idle'), 2000);
  }, [summary]);

  return (
    <div className="rounded-2xl border border-destructive/30 bg-card p-4 shadow-sm">
      <div className="flex items-center justify-between">
        <h3 className="text-sm font-semibold text-destructive">Validation feedback</h3>
        {hasFindings(summary) && (
          <Button
            type="button"
            variant="ghost"
            size="sm"
            onClick={handleCopy}
            className="gap-1.5 text-xs text-muted-foreground hover:text-foreground"
          >
            {copyState === 'copied' ? (
              <>
                <Check size={14} />
                Copied!
              </>
            ) : copyState === 'failed' ? (
              'Copy failed'
            ) : (
              <>
                <ClipboardCopy size={14} />
                Copy errors for AI
              </>
            )}
          </Button>
        )}
      </div>
      <div className="mt-3 grid gap-3 md:grid-cols-2">
        {[summary.static_phase, summary.runtime_phase].map((phase) => (
          <div key={phase.phase} className="rounded-xl bg-background p-3 text-sm">
            <p className="font-semibold capitalize text-foreground">
              {phase.phase} {phase.status}
            </p>
            {phase.findings.length === 0 ? (
              <p className="mt-1 text-muted-foreground">No findings.</p>
            ) : (
              <ul className="mt-2 space-y-1 text-muted-foreground">
                {phase.findings.map((finding) => (
                  <li key={`${phase.phase}-${finding.code}`}>{finding.message}</li>
                ))}
              </ul>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}

export function ModulesPage({
  modules,
  isLoading,
  error,
  validation,
  selectedFile,
  onFileSelect,
  onUpload,
  onDelete,
  onRetry,
}: {
  modules: InstalledModule[];
  isLoading: boolean;
  error: string | null;
  validation: ModuleValidationSummary | null;
  selectedFile: File | null;
  onFileSelect: (file: File | null) => void;
  onUpload: (event: React.FormEvent<HTMLFormElement>) => void;
  onDelete: (module: InstalledModule) => void;
  onRetry: () => void;
}) {
  const [editingModuleId, setEditingModuleId] = useState<string | null>(null);
  const [frequencyError, setFrequencyError] = useState<string | null>(null);
  const editingSnapshot = useRef<{ enabled: boolean; intervalMinutes: number } | null>(null);
  const queryClient = useQueryClient();

  const saveMutation = useMutation({
    mutationFn: ({
      moduleId,
      payload,
    }: {
      moduleId: number;
      payload: { enabled: boolean; intervalMinutes: number };
    }) => updateSchedule(moduleId, payload),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ['modules'] });
      setEditingModuleId(null);
      editingSnapshot.current = null;
      onRetry();
    },
    onError: (err: Error) => {
      setFrequencyError(err.message ?? 'Schedule update failed');
      setEditingModuleId(null);
      editingSnapshot.current = null;
    },
  });

  // External change detection: if schedule data changes while editor is open
  useEffect(() => {
    if (editingModuleId === null) return;
    const currentModule = modules.find((m) => m.moduleId === editingModuleId);
    if (currentModule === undefined) {
      // Module was deleted while editing
      queueMicrotask(() => {
        setEditingModuleId(null);
        editingSnapshot.current = null;
      });
      return;
    }
    const snapshot = editingSnapshot.current;
    if (snapshot !== null) {
      const currentSchedule = currentModule.schedule;
      const currentEnabled = currentSchedule?.enabled ?? false;
      const currentInterval = currentSchedule?.intervalMinutes ?? 1440;
      if (
        snapshot.enabled !== currentEnabled ||
        snapshot.intervalMinutes !== currentInterval
      ) {
        queueMicrotask(() => {
          setEditingModuleId(null);
          editingSnapshot.current = null;
        });
        setFrequencyError('This schedule was changed elsewhere. The editor will close.');
        setTimeout(() => setFrequencyError(null), 5000);
      }
    }
  }, [modules, editingModuleId]);

  // Auto-dismiss frequency error after 5 seconds
  useEffect(() => {
    if (frequencyError === null) return;
    const timer = setTimeout(() => setFrequencyError(null), 5000);
    return () => clearTimeout(timer);
  }, [frequencyError]);

  const startEditing = useCallback(
    (module: InstalledModule) => {
      setFrequencyError(null);
      setEditingModuleId(module.moduleId);
      editingSnapshot.current = module.schedule
        ? { enabled: module.schedule.enabled, intervalMinutes: module.schedule.intervalMinutes }
        : { enabled: false, intervalMinutes: 1440 };
    },
    [],
  );

  const handleCancel = useCallback(() => {
    setEditingModuleId(null);
    editingSnapshot.current = null;
    setFrequencyError(null);
  }, []);

  const handleSave = useCallback(
    (moduleId: string, payload: { enabled: boolean; intervalMinutes: number }) => {
      const module = modules.find((m) => m.moduleId === moduleId);
      if (!module) return;
      saveMutation.mutate({ moduleId: module.id, payload });
    },
    [modules, saveMutation],
  );

  return (
    <div className="space-y-6">
      <div className="flex flex-col justify-between gap-4 lg:flex-row lg:items-start">
        <PageHeader
          title="Extension Modules"
          description="Manage Python scripts that scrape firmware data."
        />
        <ModuleUploadForm
          selectedFile={selectedFile}
          onFileSelect={onFileSelect}
          onUpload={onUpload}
        />
      </div>

      <div className="rounded-2xl border border-amber-200 dark:border-amber-800 bg-amber-50 dark:bg-amber-950 px-4 py-3 text-sm text-amber-700 dark:text-amber-300">
        Modules are trusted Python code and run unsandboxed with application privileges.
      </div>

      <ModuleGuidanceSection />

      {frequencyError !== null && (
        <div
          className="rounded-xl border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-800 dark:border-amber-800 dark:bg-amber-950 dark:text-amber-200"
          role="alert"
        >
          {frequencyError}
        </div>
      )}

      {validation !== null && <ValidationSummary summary={validation} />}

      {(isLoading || error !== null) && (
        <div className="grid grid-cols-1 gap-6 md:grid-cols-2 lg:grid-cols-3">
          {Array.from({ length: 6 }).map((_, i) => (
            <div
              key={i}
              className="animate-pulse rounded-2xl border bg-card p-6 shadow-sm"
            >
              <div className="mb-4 flex items-start justify-between">
                <div className="h-12 w-12 rounded-xl bg-muted/20" />
                <div className="h-5 w-16 rounded-full bg-muted/20" />
              </div>
              <div className="mb-1 h-5 w-3/4 rounded bg-muted/20" />
              <div className="mb-1 h-4 w-1/2 rounded bg-muted/20" />
              <div className="mb-5 h-4 w-1/3 rounded bg-muted/20" />
              {error !== null ? (
                <div className="mb-4 flex items-center gap-2">
                  <span className="text-sm font-medium text-destructive">Failed to load</span>
                  <Button
                    type="button"
                    variant="destructive"
                    size="xs"
                    onClick={onRetry}
                  >
                    <RefreshCw size={12} className="mr-1" />
                    Retry
                  </Button>
                </div>
              ) : (
                <div className="flex items-center gap-2">
                  <div className="h-4 w-20 rounded bg-muted/20" />
                  <div className="h-4 w-16 rounded bg-muted/20" />
                </div>
              )}
              <div className="mt-3 flex items-center justify-between border-t pt-4">
                <div className="h-4 w-32 rounded bg-muted/20" />
                <div className="h-4 w-12 rounded bg-muted/20" />
              </div>
            </div>
          ))}
        </div>
      )}

      {!isLoading && error === null && modules.length === 0 && (
        <div className="rounded-2xl border border-dashed p-8 text-center text-sm text-muted-foreground">
          No modules installed yet.
        </div>
      )}

      {!isLoading && error === null && (
        <div className="grid grid-cols-1 gap-6 md:grid-cols-2 lg:grid-cols-3">
          {modules.map((module) => {
            const isEditing = editingModuleId === module.moduleId;

            return (
              <ModuleCard
                key={module.moduleId}
                module={module}
                isEditing={isEditing}
                onStartEdit={startEditing}
                onCancel={handleCancel}
                onSave={handleSave}
                onDelete={onDelete}
                savePending={
                  editingModuleId === module.moduleId && saveMutation.isPending
                }
                frequencyError={
                  editingModuleId === module.moduleId ? frequencyError : null
                }
              />
            );
          })}
        </div>
      )}
    </div>
  );
}
