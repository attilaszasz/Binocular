import { ChevronDown, ChevronUp } from 'lucide-react';
import { Fragment } from 'react';

import type { ActivityLog } from '@/api';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table';

import { TracebackPanel } from './TracebackPanel';

interface LogTableProps {
  activities: ActivityLog[];
  isLoading: boolean;
  expandedIds: Set<number>;
  copiedId: number | null;
  onToggleExpand: (id: number) => void;
  onCopyTraceback: (id: number, traceback: string) => void;
}

export function LogTable({
  activities,
  isLoading,
  expandedIds,
  copiedId,
  onToggleExpand,
  onCopyTraceback,
}: LogTableProps) {
  return (
    <div className="relative overflow-hidden rounded-2xl border bg-card shadow-sm">
      <Table>
        <TableHeader>
          <TableRow className="bg-background">
            <TableHead>Time</TableHead>
            <TableHead>Type</TableHead>
            <TableHead>Status</TableHead>
            <TableHead>Asset</TableHead>
            <TableHead>Message</TableHead>
            <TableHead>Details</TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {isLoading && activities.length === 0 ? (
            <TableRow>
              <TableCell colSpan={6} className="px-6 py-10 text-center text-muted-foreground">
                Loading audit history...
              </TableCell>
            </TableRow>
          ) : activities.length === 0 ? (
            <TableRow>
              <TableCell colSpan={6} className="px-6 py-10 text-center text-muted-foreground">
                No audit logs match the selected filters.
              </TableCell>
            </TableRow>
          ) : (
            activities.map((log) => {
              const isExpanded = expandedIds.has(log.id);
              const showChevron = log.status === 'failed' && log.traceback;
              const formattedTime = (() => {
                try {
                  return new Date(log.createdAt).toLocaleString();
                } catch {
                  return log.createdAt;
                }
              })();

              return (
                <Fragment key={log.id}>
                  <TableRow
                    className={`transition-colors ${
                      showChevron ? 'cursor-pointer' : ''
                    }`}
                    onClick={() => showChevron && onToggleExpand(log.id)}
                  >
                    <TableCell className="whitespace-nowrap px-6 py-4 font-mono text-xs text-muted-foreground">
                      {formattedTime}
                    </TableCell>
                    <TableCell className="whitespace-nowrap px-6 py-4">
                      {log.eventType === 'check' ? (
                        <Badge variant="secondary" className="font-semibold uppercase tracking-wider">
                          {log.eventType}
                        </Badge>
                      ) : (
                        <Badge
                          variant="outline"
                          className="font-semibold uppercase tracking-wider bg-amber-50 dark:bg-amber-950 text-amber-700 dark:text-amber-300 border-amber-200 dark:border-amber-800"
                        >
                          {log.eventType}
                        </Badge>
                      )}
                    </TableCell>
                    <TableCell className="whitespace-nowrap px-6 py-4">
                      {log.status === 'success' ? (
                        <Badge
                          variant="outline"
                          className="font-semibold bg-emerald-50 dark:bg-emerald-950 text-emerald-600 dark:text-emerald-400 border-emerald-200 dark:border-emerald-800"
                        >
                          Success
                        </Badge>
                      ) : (
                        <Badge variant="destructive" className="font-semibold">
                          Failed
                        </Badge>
                      )}
                    </TableCell>
                    <TableCell className="px-6 py-4 text-muted-foreground font-medium max-w-[160px]">
                      {log.deviceName || log.moduleName ? (
                        <div className="flex flex-col min-w-0">
                          {log.deviceName && <span className="truncate">{log.deviceName}</span>}
                          {log.moduleName && (
                            <span className="font-mono text-xs text-muted-foreground truncate">
                              {log.moduleName}
                            </span>
                          )}
                        </div>
                      ) : (
                        <span className="text-muted-foreground">—</span>
                      )}
                    </TableCell>
                    <TableCell className="px-6 py-4 text-foreground max-w-md sm:break-words max-sm:max-w-[180px] max-sm:truncate">
                      {log.message}
                    </TableCell>
                    <TableCell className="whitespace-nowrap px-6 py-4 text-muted-foreground">
                      {showChevron ? (
                        <Button
                          variant="ghost"
                          size="icon"
                          onClick={(e) => {
                            e.stopPropagation();
                            onToggleExpand(log.id);
                          }}
                          aria-label={isExpanded ? 'Collapse traceback' : 'Expand traceback'}
                        >
                          {isExpanded ? <ChevronUp size={16} /> : <ChevronDown size={16} />}
                        </Button>
                      ) : (
                        <span className="text-muted-foreground">—</span>
                      )}
                    </TableCell>
                  </TableRow>
                  {showChevron && isExpanded && (
                    <TableRow>
                      <TableCell colSpan={6} className="bg-background px-6 py-4">
                        <TracebackPanel
                          traceback={log.traceback || ''}
                          copied={copiedId === log.id}
                          onCopy={(e) => {
                            e.stopPropagation();
                            void onCopyTraceback(log.id, log.traceback || '');
                          }}
                        />
                      </TableCell>
                    </TableRow>
                  )}
                </Fragment>
              );
            })
          )}
        </TableBody>
      </Table>
      {/* Scroll hint gradient on right edge */}
      <div className="pointer-events-none absolute inset-y-0 right-0 w-8 bg-linear-to-r from-transparent to-background/50" aria-hidden="true" />
    </div>
  );
}
