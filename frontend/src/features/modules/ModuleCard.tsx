import { Pencil, Trash2 } from "lucide-react";

import type { DeviceType } from "../../api/types";

interface ModuleCardProps {
  module: DeviceType;
  onEdit: (module: DeviceType) => void;
  onDelete: (module: DeviceType) => void;
}

export function ModuleCard({ module, onEdit, onDelete }: ModuleCardProps) {
  return (
    <article className="rounded-lg border border-slate-200 bg-white p-4 shadow-sm dark:border-slate-800 dark:bg-slate-900">
      <h3 className="text-base font-semibold text-slate-900 dark:text-slate-100">{module.name}</h3>
      <p className="mt-1 break-all text-sm text-slate-600 dark:text-slate-300">
        {module.firmware_source_url}
      </p>
      <p className="mt-1 text-xs text-slate-500 dark:text-slate-400">
        Every {module.check_frequency_minutes} minutes · {module.device_count}{" "}
        {module.device_count === 1 ? "device" : "devices"}
      </p>

      <div className="mt-4 flex items-center gap-2">
        <button
          type="button"
          onClick={() => onEdit(module)}
          aria-label={`Edit ${module.name}`}
          className="inline-flex items-center gap-1 rounded-md border border-slate-300 px-3 py-2 text-xs font-medium text-slate-700 hover:bg-slate-100 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-500 dark:border-slate-700 dark:text-slate-200 dark:hover:bg-slate-800"
        >
          <Pencil size={14} />
          Edit
        </button>

        <button
          type="button"
          onClick={() => onDelete(module)}
          aria-label={`Delete ${module.name}`}
          className="inline-flex items-center gap-1 rounded-md border border-red-300 px-3 py-2 text-xs font-medium text-red-700 hover:bg-red-50 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-red-500 dark:border-red-700 dark:text-red-300 dark:hover:bg-red-900/20"
        >
          <Trash2 size={14} />
          Delete
        </button>
      </div>
    </article>
  );
}
