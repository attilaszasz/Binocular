import { Button } from '@/components/ui/button';

interface StatusMessageProps {
  type: 'success' | 'error';
  message: string;
  onDismiss: () => void;
}

export function StatusMessage({ type, message, onDismiss }: StatusMessageProps) {
  return (
    <div
      className={`rounded-xl border px-4 py-3 text-sm flex items-center justify-between transition-all ${
        type === 'success'
          ? 'border-emerald-200 dark:border-emerald-800 bg-emerald-50 dark:bg-emerald-950 text-emerald-600 dark:text-emerald-400'
          : 'border-destructive/30 bg-destructive/10 text-destructive'
      }`}
    >
      <span>{message}</span>
      <Button variant="ghost" size="icon" onClick={onDismiss} className="shrink-0">
        ✕
      </Button>
    </div>
  );
}
