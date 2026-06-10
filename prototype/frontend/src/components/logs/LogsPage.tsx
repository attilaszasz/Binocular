import { useCallback, useEffect, useState } from 'react';

import { listActivity, type ActivityLog } from '@/api';

import { FilterBar } from './FilterBar';
import { LogTable } from './LogTable';

type TypeFilter = 'all' | 'check' | 'notification';
type StatusFilter = 'all' | 'success' | 'failed';

type LogEntry = {
  id: number;
  time: string;
  level: 'INFO' | 'WARN' | 'ERROR';
  message: string;
};

interface LogsPageProps {
  logs: LogEntry[];
}

function PageHeader({ title, description }: { title: string; description: string }) {
  return (
    <div>
      <h2 className="text-2xl font-bold tracking-tight">{title}</h2>
      <p className="mt-1 text-sm text-muted-foreground">{description}</p>
    </div>
  );
}

export function LogsPage({ logs: fallbackLogs }: LogsPageProps) {
  const [activities, setActivities] = useState<ActivityLog[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [typeFilter, setTypeFilter] = useState<TypeFilter>('all');
  const [statusFilter, setStatusFilter] = useState<StatusFilter>('all');
  const [expandedIds, setExpandedIds] = useState<Set<number>>(new Set());
  const [copiedId, setCopiedId] = useState<number | null>(null);

  const fetchLogs = useCallback(async () => {
    setIsLoading(true);
    setError(null);
    try {
      const data = await listActivity({
        type: typeFilter === 'all' ? undefined : typeFilter,
        status: statusFilter === 'all' ? undefined : statusFilter,
      });
      if (!Array.isArray(data)) {
        throw new TypeError('API response is not an array of audit logs');
      }
      setActivities(data);
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Failed to load audit logs';
      setError(message);
      if (fallbackLogs.length > 0) {
        const mapped = fallbackLogs.map((log) => ({
          id: log.id,
          eventType: (log.message.toLowerCase().includes('notification')
            ? 'notification'
            : 'check') as 'check' | 'notification',
          status: (log.level === 'ERROR' ? 'failed' : 'success') as 'success' | 'failed',
          deviceName: null,
          moduleName: null,
          message: log.message,
          traceback:
            log.level === 'ERROR'
              ? 'Traceback (mock):\n  File "scraper.py", line 42, in scrape\n    raise HTTPError("429 Too Many Requests")'
              : null,
          createdAt: new Date().toISOString(),
        }));
        setActivities(mapped);
      }
    } finally {
      setIsLoading(false);
    }
  }, [typeFilter, statusFilter, fallbackLogs]);

  useEffect(() => {
    let active = true;
    void (async () => {
      await Promise.resolve();
      if (!active) return;
      void fetchLogs();
    })();
    return () => {
      active = false;
    };
  }, [fetchLogs]);

  const toggleExpand = (id: number) => {
    setExpandedIds((current) => {
      const next = new Set(current);
      if (next.has(id)) {
        next.delete(id);
      } else {
        next.add(id);
      }
      return next;
    });
  };

  const handleCopyTraceback = async (id: number, traceback: string) => {
    try {
      await navigator.clipboard.writeText(traceback);
      setCopiedId(id);
      setTimeout(() => setCopiedId(null), 2000);
    } catch (err) {
      console.error('Failed to copy traceback text', err);
    }
  };

  return (
    <div className="space-y-6">
      <div className="flex flex-col justify-between gap-4 sm:flex-row sm:items-center">
        <PageHeader
          title="Activity Logs"
          description="System execution, background checks, and notification dispatches."
        />
      </div>

      <FilterBar
        typeFilter={typeFilter}
        onTypeFilterChange={setTypeFilter}
        statusFilter={statusFilter}
        onStatusFilterChange={setStatusFilter}
        onRefresh={() => void fetchLogs()}
        isLoading={isLoading}
      />

      {error !== null && (
        <div className="rounded-xl border border-destructive/30 bg-destructive/10 px-4 py-3 text-sm text-destructive">
          {error}
        </div>
      )}

      <LogTable
        activities={activities}
        isLoading={isLoading}
        expandedIds={expandedIds}
        copiedId={copiedId}
        onToggleExpand={toggleExpand}
        onCopyTraceback={handleCopyTraceback}
      />
    </div>
  );
}
