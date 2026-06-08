import { Copy } from 'lucide-react';
import type { MouseEvent } from 'react';

import { Button } from '@/components/ui/button';

interface TracebackPanelProps {
  traceback: string;
  onCopy: (e: MouseEvent<HTMLButtonElement>) => void;
  copied: boolean;
}

export function TracebackPanel({ traceback, onCopy, copied }: TracebackPanelProps) {
  return (
    <div className="rounded-xl border bg-zinc-950 p-4 relative shadow-inner">
      <div className="flex items-center justify-between mb-2">
        <span className="text-xs font-semibold text-rose-400 tracking-wide uppercase">
          Failure Traceback Stack Trace
        </span>
        <Button
          variant="outline"
          size="sm"
          onClick={onCopy}
          className="h-7 border-zinc-800 bg-slate-900 hover:bg-slate-800 text-zinc-300 text-xs active:scale-95"
        >
          <Copy size={12} className="mr-1.5" />
          {copied ? 'Copied!' : 'Copy'}
        </Button>
      </div>
      <pre className="font-mono text-xs text-zinc-100 overflow-x-auto whitespace-pre-wrap leading-relaxed max-h-96 select-text selection:bg-rose-500/30 selection:text-white">
        {traceback}
      </pre>
    </div>
  );
}
