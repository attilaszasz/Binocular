import { AlertCircle, CheckCircle2, Clock3 } from "lucide-react";

import type { DeviceStatus } from "../../api/types";

interface StatusIndicatorProps {
  status: DeviceStatus;
}

export function StatusIndicator({ status }: StatusIndicatorProps) {
  if (status === "update_available") {
    return (
      <span className="inline-flex items-center gap-1 rounded-full bg-rose-100 px-2 py-1 text-xs font-medium text-rose-700 dark:bg-rose-900/30 dark:text-rose-300">
        <AlertCircle size={14} />
        Update Available
      </span>
    );
  }

  if (status === "up_to_date") {
    return (
      <span className="inline-flex items-center gap-1 rounded-full bg-emerald-100 px-2 py-1 text-xs font-medium text-emerald-700 dark:bg-emerald-900/30 dark:text-emerald-300">
        <CheckCircle2 size={14} />
        Up to Date
      </span>
    );
  }

  return (
    <span className="inline-flex items-center gap-1 rounded-full bg-slate-200 px-2 py-1 text-xs font-medium text-slate-700 dark:bg-slate-800 dark:text-slate-300">
      <Clock3 size={14} />
      Not Checked
    </span>
  );
}
