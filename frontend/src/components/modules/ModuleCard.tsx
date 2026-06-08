import { Clock, Loader2, Server, TerminalSquare } from 'lucide-react';
import type { InstalledModule } from '@/api';
import { Button } from '@/components/ui/button';
import { Card, CardContent } from '@/components/ui/card';
import { FrequencyEditor } from '@/components/FrequencyEditor';
import { ModuleStatusBadge } from './ModuleStatusBadge';

function formatFrequencyLabel(intervalMinutes: number | null): string {
  if (intervalMinutes === null) return '24h';
  if (intervalMinutes >= 60 && intervalMinutes % 60 === 0) {
    return `${intervalMinutes / 60}h`;
  }
  return `${intervalMinutes}m`;
}

export function ModuleCard({
  module,
  isEditing,
  onStartEdit,
  onCancel,
  onSave,
  onDelete,
  savePending,
  frequencyError,
}: {
  module: InstalledModule;
  isEditing: boolean;
  onStartEdit: (module: InstalledModule) => void;
  onCancel: () => void;
  onSave: (moduleId: string, payload: { enabled: boolean; intervalMinutes: number }) => void;
  onDelete: (module: InstalledModule) => void;
  savePending: boolean;
  frequencyError: string | null;
}) {
  return (
    <Card>
      <CardContent className="pt-6">
        <div className="mb-4 flex items-start justify-between">
          <div className="rounded-xl bg-primary/10 p-3 text-primary">
            <TerminalSquare size={24} />
          </div>
          <ModuleStatusBadge status={module.validationStatus} />
        </div>
        <h3 className="truncate font-mono text-lg font-bold">{module.displayName}</h3>
        <p className="mt-1 text-sm text-muted-foreground">{module.moduleId}</p>
        <p className="mb-4 mt-1 text-sm text-muted-foreground">
          Version {module.version ?? 'unknown'}
        </p>

        {/* Frequency display or editor */}
        {isEditing ? (
          <div
            tabIndex={-1}
            onBlur={(e) => {
              const container = e.currentTarget;
              requestAnimationFrame(() => {
                if (!container.contains(document.activeElement)) {
                  onCancel();
                }
              });
            }}
          >
            <FrequencyEditor
              currentIntervalMinutes={module.schedule?.intervalMinutes ?? null}
              enabled={module.schedule?.enabled ?? false}
              onSave={(payload) => onSave(module.moduleId, payload)}
              onCancel={onCancel}
              moduleId={module.id}
            />
            {savePending && (
              <div className="mt-2 flex items-center gap-2 text-xs text-muted-foreground">
                <Loader2 size={12} className="animate-spin" />
                Saving...
              </div>
            )}
          </div>
        ) : (
          <div
            className="mb-4 flex items-center gap-2"
            role="button"
            tabIndex={0}
            onClick={() => onStartEdit(module)}
            onKeyDown={(e) => {
              if (e.key === 'Enter' || e.key === ' ') {
                e.preventDefault();
                onStartEdit(module);
              }
            }}
            aria-label={`Edit check frequency for ${module.displayName}`}
          >
            <span className="inline-flex cursor-pointer items-center gap-1 rounded-full bg-background px-2.5 py-1 text-xs font-medium text-foreground hover:bg-muted transition-colors">
              <Clock size={12} />
              {formatFrequencyLabel(module.schedule?.intervalMinutes ?? null)}
            </span>
            <span
              className={
                [
                  'inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-xs font-medium',
                  module.schedule?.enabled
                    ? 'bg-emerald-600/10 text-emerald-600'
                    : 'bg-muted-foreground/15 text-muted-foreground',
                ].join(' ')
              }
            >
              <span
                className={
                  [
                    'inline-block h-1.5 w-1.5 rounded-full',
                    module.schedule?.enabled ? 'bg-emerald-500' : 'bg-muted',
                  ].join(' ')
                }
              />
              {module.schedule?.enabled ? 'Active' : 'Paused'}
            </span>
          </div>
        )}

        {frequencyError !== null && (
          <div
            className="mb-4 rounded-lg border border-amber-200 bg-amber-50 px-3 py-2 text-xs text-amber-800 dark:border-amber-800 dark:bg-amber-950 dark:text-amber-200"
            role="alert"
          >
            {frequencyError}
          </div>
        )}

        <div className="flex items-center justify-between border-t pt-4">
          <span className="flex items-center text-sm font-medium text-muted-foreground">
            <Server size={14} className="mr-1.5" />
            {module.lastValidatedAt === null
              ? 'Not validated'
              : `Validated ${new Date(module.lastValidatedAt).toLocaleString()}`}
          </span>
          <Button
            type="button"
            variant="destructive"
            size="sm"
            onClick={() => onDelete(module)}
          >
            Delete
          </Button>
        </div>
      </CardContent>
    </Card>
  );
}
