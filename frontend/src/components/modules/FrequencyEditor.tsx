import { useSchedules, useUpdateSchedule } from "@/hooks/use-schedules";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Loader2 } from "lucide-react";
import type { Module } from "@/lib/api";

interface FrequencyEditorProps {
  module: Module;
}

const INTERVAL_OPTIONS = [
  { value: "1", label: "Every hour" },
  { value: "6", label: "Every 6 hours" },
  { value: "12", label: "Every 12 hours" },
  { value: "24", label: "Every 24 hours (Daily)" },
  { value: "48", label: "Every 2 days" },
  { value: "168", label: "Every 7 days (Weekly)" },
];

export function FrequencyEditor({ module }: FrequencyEditorProps) {
  const { data: schedules, isLoading, isError } = useSchedules();
  const updateScheduleMutation = useUpdateSchedule();

  if (isLoading) {
    return (
      <div className="flex items-center gap-2 text-xs text-muted-foreground">
        <Loader2 className="h-3.5 w-3.5 animate-spin" />
        <span>Loading frequency...</span>
      </div>
    );
  }

  const schedule = schedules?.find((s) => s.module_id === module.id);
  if (isError || !schedule) return <p role="alert">Check frequency unavailable. Refresh to retry.</p>;

  const handleValueChange = (val: string) => {
    const hours = parseInt(val, 10);
    if (!isNaN(hours)) {
      updateScheduleMutation.mutate({ moduleId: module.id, intervalHours: hours });
    }
  };

  const isUpdating = updateScheduleMutation.isPending;

  return (
    <div className="flex flex-col gap-1.5 mt-3 pt-3 border-t border-border/40">
      <div className="flex items-center justify-between">
        <span className="text-xs font-medium text-muted-foreground">Check Frequency</span>
        {isUpdating && (
          <Loader2 className="h-3 w-3 animate-spin text-blue-500" />
        )}
      </div>
      <Select
        value={String(schedule.interval_hours)}
        onValueChange={handleValueChange}
        disabled={isUpdating}
      >
        <SelectTrigger aria-label={`Check frequency for ${module.display_name || module.name}`} className="w-full h-8 text-xs bg-background border-border/60">
          <SelectValue placeholder="Select frequency" />
        </SelectTrigger>
        <SelectContent>
          {INTERVAL_OPTIONS.map((opt) => (
            <SelectItem key={opt.value} value={opt.value} className="text-xs">
              {opt.label}
            </SelectItem>
          ))}
        </SelectContent>
      </Select>
      {updateScheduleMutation.isError && <p role="alert">Frequency was not saved. {updateScheduleMutation.error.message}</p>}
      {isUpdating && <p role="status">Saving frequency…</p>}
      {module.status !== "active" && <p>Changing frequency does not resume automatic monitoring.</p>}
      {schedule.next_run && module.status === "active" && (
        <span className="text-[10px] text-muted-foreground/80 mt-0.5">
          Next check: {new Date(schedule.next_run).toLocaleString()}
        </span>
      )}
    </div>
  );
}
