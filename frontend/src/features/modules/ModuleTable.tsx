import { Trash2 } from "lucide-react";

import type { ExtensionModule } from "../../api/types";

interface ModuleTableProps {
  modules: ExtensionModule[];
  onDelete: (module: ExtensionModule) => void;
}

export function ModuleTable({ modules, onDelete }: ModuleTableProps) {
  return (
    <div className="overflow-x-auto rounded-lg border border-slate-200 dark:border-slate-800">
      <table className="min-w-full divide-y divide-slate-200 dark:divide-slate-800">
        <thead className="bg-slate-50 dark:bg-slate-900">
          <tr>
            <th scope="col" className="px-4 py-3 text-left text-xs font-medium uppercase tracking-wider text-slate-500 dark:text-slate-400">
              Filename
            </th>
            <th scope="col" className="px-4 py-3 text-left text-xs font-medium uppercase tracking-wider text-slate-500 dark:text-slate-400">
              Version
            </th>
            <th scope="col" className="px-4 py-3 text-left text-xs font-medium uppercase tracking-wider text-slate-500 dark:text-slate-400">
              Device Type
            </th>
            <th scope="col" className="px-4 py-3 text-left text-xs font-medium uppercase tracking-wider text-slate-500 dark:text-slate-400">
              Status
            </th>
            <th scope="col" className="px-4 py-3 text-right text-xs font-medium uppercase tracking-wider text-slate-500 dark:text-slate-400">
              Actions
            </th>
          </tr>
        </thead>
        <tbody className="divide-y divide-slate-200 bg-white dark:divide-slate-800 dark:bg-slate-950">
          {modules.map((mod) => (
            <tr key={mod.id}>
              <td className="whitespace-nowrap px-4 py-3 text-sm font-medium text-slate-900 dark:text-slate-100">
                {mod.filename}
              </td>
              <td className="whitespace-nowrap px-4 py-3 text-sm text-slate-600 dark:text-slate-300">
                {mod.module_version ?? "—"}
              </td>
              <td className="whitespace-nowrap px-4 py-3 text-sm text-slate-600 dark:text-slate-300">
                {mod.supported_device_type ?? "—"}
              </td>
              <td className="whitespace-nowrap px-4 py-3 text-sm">
                {mod.is_active ? (
                  <span className="inline-flex items-center rounded-full bg-green-100 px-2 py-0.5 text-xs font-medium text-green-800 dark:bg-green-900/30 dark:text-green-300">
                    Active
                  </span>
                ) : (
                  <div>
                    <span className="inline-flex items-center rounded-full bg-red-100 px-2 py-0.5 text-xs font-medium text-red-800 dark:bg-red-900/30 dark:text-red-300">
                      Error
                    </span>
                    {mod.last_error && (
                      <p className="mt-1 text-xs text-red-600 dark:text-red-400">
                        {mod.last_error}
                      </p>
                    )}
                  </div>
                )}
              </td>
              <td className="whitespace-nowrap px-4 py-3 text-right text-sm">
                <button
                  type="button"
                  onClick={() => onDelete(mod)}
                  aria-label={`Delete ${mod.filename}`}
                  className="inline-flex items-center gap-1 rounded-md border border-red-300 px-2 py-1 text-xs font-medium text-red-700 hover:bg-red-50 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-red-500 dark:border-red-700 dark:text-red-300 dark:hover:bg-red-900/20"
                >
                  <Trash2 size={14} />
                  Delete
                </button>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
