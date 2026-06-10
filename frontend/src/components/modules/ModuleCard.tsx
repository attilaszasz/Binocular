import { useState } from "react";
import { Trash2, ShieldAlert } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Switch } from "@/components/ui/switch";
import { Button } from "@/components/ui/button";
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from "@/components/ui/tooltip";
import { ModuleStatusBadge } from "./ModuleStatusBadge";
import { useUpdateModule, useDeleteModule } from "@/hooks/use-modules";
import type { Module } from "@/lib/api";

interface ModuleCardProps {
  module: Module;
  onDeleteError?: (error: string) => void;
}

export function ModuleCard({ module, onDeleteError }: ModuleCardProps) {
  const updateMutation = useUpdateModule();
  const deleteMutation = useDeleteModule();
  const [errorText, setErrorText] = useState<string | null>(null);

  const handleStatusToggle = (checked: boolean) => {
    const newStatus = checked ? "active" : "inactive";
    updateMutation.mutate({ id: module.id, status: newStatus });
  };

  const handleDelete = () => {
    if (
      window.confirm(`Are you sure you want to delete module "${module.name}"?`)
    ) {
      deleteMutation.mutate(module.id, {
        onError: (err: unknown) => {
          const error = err as Error;
          const msg = error.message || "Failed to delete module";
          setErrorText(msg);
          if (onDeleteError) onDeleteError(msg);
        },
        onSuccess: () => {
          setErrorText(null);
        },
      });
    }
  };

  const isDeleteDisabled = module.is_official;

  return (
    <Card className="flex flex-col h-full border border-border bg-card text-card-foreground">
      <CardHeader className="flex flex-row items-start justify-between space-y-0 pb-2">
        <div className="space-y-1">
          <CardTitle className="text-xl font-bold flex items-center gap-2">
            {module.name}
            {module.is_official && (
              <span className="text-[10px] bg-blue-500/10 text-blue-500 font-semibold px-2 py-0.5 rounded-full dark:bg-blue-500/20">
                Official
              </span>
            )}
          </CardTitle>
          <span className="text-sm text-muted-foreground capitalize">
            {module.device_type}
          </span>
        </div>
        <ModuleStatusBadge status={module.status} />
      </CardHeader>

      <CardContent className="flex-1 flex flex-col justify-between pt-4">
        <div className="space-y-2 text-sm">
          <div className="flex justify-between border-b border-border/40 pb-1">
            <span className="text-muted-foreground">Version</span>
            <span className="font-mono">{module.version || "—"}</span>
          </div>
          <div className="flex justify-between border-b border-border/40 pb-1">
            <span className="text-muted-foreground">Author</span>
            <span>{module.author || "—"}</span>
          </div>
          <div className="flex flex-col gap-0.5 border-b border-border/40 pb-1">
            <span className="text-muted-foreground">File Path</span>
            <span
              className="font-mono text-xs truncate"
              title={module.file_path}
            >
              {module.file_path || "—"}
            </span>
          </div>
        </div>

        {errorText && (
          <div className="mt-3 flex items-start gap-2 text-xs text-destructive bg-destructive/10 p-2 rounded border border-destructive/20">
            <ShieldAlert className="h-4 w-4 shrink-0 mt-0.5" />
            <span>{errorText}</span>
          </div>
        )}

        <div className="flex items-center justify-between mt-6 pt-4 border-t border-border/60">
          <div className="flex items-center gap-2">
            <Switch
              checked={module.status === "active"}
              onCheckedChange={handleStatusToggle}
              disabled={updateMutation.isPending}
            />
            <span className="text-sm text-muted-foreground">
              {module.status === "active" ? "Enabled" : "Disabled"}
            </span>
          </div>

          <TooltipProvider>
            <Tooltip>
              <TooltipTrigger asChild>
                <span>
                  <Button
                    variant="destructive"
                    size="icon"
                    className="h-8 w-8"
                    onClick={handleDelete}
                    disabled={isDeleteDisabled || deleteMutation.isPending}
                  >
                    <Trash2 className="h-4 w-4" />
                  </Button>
                </span>
              </TooltipTrigger>
              {isDeleteDisabled && (
                <TooltipContent>
                  <p>Cannot delete official built-in modules</p>
                </TooltipContent>
              )}
            </Tooltip>
          </TooltipProvider>
        </div>
      </CardContent>
    </Card>
  );
}
