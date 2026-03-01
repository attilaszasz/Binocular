import { type ReactNode, useEffect } from "react";

interface ConfirmDialogProps {
  isOpen: boolean;
  title: string;
  description: ReactNode;
  confirmLabel?: string;
  onCancel: () => void;
  onConfirm: () => void;
}

export function ConfirmDialog({
  isOpen,
  title,
  description,
  confirmLabel = "Confirm",
  onCancel,
  onConfirm,
}: ConfirmDialogProps) {
  useEffect(() => {
    if (!isOpen) {
      return;
    }

    const onEscape = (event: KeyboardEvent) => {
      if (event.key === "Escape") {
        onCancel();
      }
    };

    window.addEventListener("keydown", onEscape);
    return () => window.removeEventListener("keydown", onEscape);
  }, [isOpen, onCancel]);

  if (!isOpen) {
    return null;
  }

  return (
    <div className="fixed inset-0 z-50" role="dialog" aria-modal="true" aria-label={title}>
      <button
        type="button"
        className="absolute inset-0 bg-black/40"
        onClick={onCancel}
        aria-label="Close confirm dialog"
      />
      <section className="absolute left-1/2 top-1/2 w-[95vw] max-w-md -translate-x-1/2 -translate-y-1/2 rounded-lg border border-slate-200 bg-white p-5 shadow-xl dark:border-slate-700 dark:bg-slate-900">
        <h2 className="text-lg font-semibold">{title}</h2>
        <div className="mt-2 text-sm text-slate-600 dark:text-slate-300">{description}</div>
        <div className="mt-4 flex justify-end gap-2">
          <button
            type="button"
            onClick={onCancel}
            className="rounded-md border border-slate-300 px-3 py-2 text-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-500 dark:border-slate-700"
          >
            Cancel
          </button>
          <button
            type="button"
            onClick={onConfirm}
            className="rounded-md bg-red-600 px-3 py-2 text-sm font-medium text-white hover:bg-red-700 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-red-500"
          >
            {confirmLabel}
          </button>
        </div>
      </section>
    </div>
  );
}
