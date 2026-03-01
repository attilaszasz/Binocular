import { type ReactNode, useEffect } from "react";

interface SlideOverPanelProps {
  title: string;
  isOpen: boolean;
  onClose: () => void;
  children: ReactNode;
}

export function SlideOverPanel({ title, isOpen, onClose, children }: SlideOverPanelProps) {
  useEffect(() => {
    if (!isOpen) {
      return;
    }

    const onEscape = (event: KeyboardEvent) => {
      if (event.key === "Escape") {
        onClose();
      }
    };

    window.addEventListener("keydown", onEscape);
    return () => window.removeEventListener("keydown", onEscape);
  }, [isOpen, onClose]);

  if (!isOpen) {
    return null;
  }

  return (
    <div className="fixed inset-0 z-50" role="dialog" aria-modal="true" aria-label={title}>
      <button
        type="button"
        className="absolute inset-0 bg-black/40"
        onClick={onClose}
        aria-label="Close panel"
      />
      <section className="absolute right-0 top-0 h-dvh w-full overflow-y-auto bg-white p-4 shadow-xl dark:bg-slate-900 sm:w-[400px]">
        <div className="mb-4 flex items-center justify-between">
          <h2 className="text-lg font-semibold">{title}</h2>
          <button
            type="button"
            onClick={onClose}
            className="rounded-md border border-slate-300 px-2 py-1 text-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-500 dark:border-slate-700"
          >
            Close
          </button>
        </div>
        {children}
      </section>
    </div>
  );
}
