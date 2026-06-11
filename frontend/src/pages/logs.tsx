import { useState } from "react";
import { ScrollText, ChevronLeft, ChevronRight, X, Terminal, Filter } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Badge } from "@/components/ui/badge";
import { useActivity } from "@/hooks/use-activity";
import { useDevices } from "@/hooks/use-devices";
import { type ActivityLogEntry } from "@/lib/api";

const PAGE_SIZE = 20;

export function LogsPage() {
  const [levelFilter, setLevelFilter] = useState<string>("all");
  const [categoryFilter, setCategoryFilter] = useState<string>("all");
  const [deviceFilter, setDeviceFilter] = useState<string>("all");
  const [page, setPage] = useState<number>(0);
  const [selectedLog, setSelectedLog] = useState<ActivityLogEntry | null>(null);

  // Fetch devices to populate the device filter dropdown
  const { data: devices } = useDevices();

  // Fetch activity logs
  const { data, isLoading } = useActivity({
    level: levelFilter === "all" ? undefined : levelFilter,
    category: categoryFilter === "all" ? undefined : categoryFilter,
    device_id: deviceFilter === "all" ? undefined : Number(deviceFilter),
    limit: PAGE_SIZE,
    offset: page * PAGE_SIZE,
  });

  const totalLogs = data?.total ?? 0;
  const logs = data?.items ?? [];
  const totalPages = Math.ceil(totalLogs / PAGE_SIZE);

  const handleLevelChange = (val: string) => {
    setLevelFilter(val);
    setPage(0);
  };

  const handleCategoryChange = (val: string) => {
    setCategoryFilter(val);
    setPage(0);
  };

  const handleDeviceChange = (val: string) => {
    setDeviceFilter(val);
    setPage(0);
  };

  const handleResetFilters = () => {
    setLevelFilter("all");
    setCategoryFilter("all");
    setDeviceFilter("all");
    setPage(0);
  };

  const formatDate = (isoStr: string) => {
    try {
      const date = new Date(isoStr);
      return date.toLocaleString();
    } catch {
      return isoStr;
    }
  };

  return (
    <div className="relative min-h-screen space-y-6 pb-12">
      <div className="flex items-center justify-between">
        <h1 className="text-3xl font-bold tracking-tight flex items-center gap-2 bg-gradient-to-r from-primary to-primary/70 bg-clip-text text-transparent">
          <ScrollText className="h-8 w-8 text-primary" />
          Activity Logs
        </h1>
      </div>

      {/* Filter Bar */}
      <Card className="border border-border/40 bg-card/60 backdrop-blur-md">
        <CardContent className="p-4 flex flex-col gap-4 sm:flex-row sm:items-center justify-between">
          <div className="flex flex-wrap items-center gap-3">
            <div className="flex items-center gap-1 text-sm text-muted-foreground mr-1">
              <Filter className="h-4 w-4" />
              <span>Filters:</span>
            </div>

            {/* Level Selector */}
            <Select value={levelFilter} onValueChange={handleLevelChange}>
              <SelectTrigger className="w-[140px] h-9">
                <SelectValue placeholder="All Levels" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">All Levels</SelectItem>
                <SelectItem value="INFO">INFO</SelectItem>
                <SelectItem value="WARNING">WARNING</SelectItem>
                <SelectItem value="ERROR">ERROR</SelectItem>
              </SelectContent>
            </Select>

            {/* Category Selector */}
            <Select value={categoryFilter} onValueChange={handleCategoryChange}>
              <SelectTrigger className="w-[150px] h-9">
                <SelectValue placeholder="All Categories" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">All Categories</SelectItem>
                <SelectItem value="check">Check</SelectItem>
                <SelectItem value="notification">Notification</SelectItem>
                <SelectItem value="system">System</SelectItem>
              </SelectContent>
            </Select>

            {/* Device Selector */}
            <Select value={deviceFilter} onValueChange={handleDeviceChange}>
              <SelectTrigger className="w-[180px] h-9">
                <SelectValue placeholder="All Devices" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">All Devices</SelectItem>
                {devices?.map((dev) => (
                  <SelectItem key={dev.id} value={String(dev.id)}>
                    {dev.name}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>

          {(levelFilter !== "all" || categoryFilter !== "all" || deviceFilter !== "all") && (
            <Button variant="ghost" size="sm" onClick={handleResetFilters} className="text-muted-foreground hover:text-foreground">
              Reset Filters
            </Button>
          )}
        </CardContent>
      </Card>

      {/* Log Table Card */}
      <Card className="border border-border/40 overflow-hidden bg-card/60 backdrop-blur-md shadow-lg">
        <CardContent className="p-0">
          <div className="overflow-x-auto">
            <Table>
              <TableHeader className="bg-muted/30">
                <TableRow>
                  <TableHead className="w-[180px]">Timestamp</TableHead>
                  <TableHead className="w-[110px]">Level</TableHead>
                  <TableHead className="w-[130px]">Category</TableHead>
                  <TableHead>Message</TableHead>
                  <TableHead className="w-[150px]">Device</TableHead>
                  <TableHead className="w-[80px] text-right">Details</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {isLoading ? (
                  // Skeleton state
                  Array.from({ length: 5 }).map((_, idx) => (
                    <TableRow key={idx} className="animate-pulse">
                      <TableCell className="h-12 bg-muted/10" colSpan={6} />
                    </TableRow>
                  ))
                ) : logs.length === 0 ? (
                  // Empty state
                  <TableRow>
                    <TableCell colSpan={6} className="h-48 text-center text-muted-foreground">
                      <ScrollText className="h-8 w-8 text-muted-foreground/35 mx-auto mb-2" />
                      No activity logs found.
                    </TableCell>
                  </TableRow>
                ) : (
                  // Log entries
                  logs.map((log) => (
                    <TableRow
                      key={log.id}
                      onClick={() => log.traceback && setSelectedLog(log)}
                      className={log.traceback ? "cursor-pointer hover:bg-muted/40" : ""}
                    >
                      <TableCell className="font-mono text-xs text-muted-foreground">
                        {formatDate(log.timestamp)}
                      </TableCell>
                      <TableCell>
                        <Badge
                          variant="outline"
                          className={
                            log.level === "ERROR"
                              ? "bg-red-500/10 text-red-500 border-red-500/20"
                              : log.level === "WARNING"
                              ? "bg-amber-500/10 text-amber-500 border-amber-500/20"
                              : "bg-blue-500/10 text-blue-500 border-blue-500/20"
                          }
                        >
                          {log.level}
                        </Badge>
                      </TableCell>
                      <TableCell>
                        <Badge
                          variant="outline"
                          className={
                            log.category === "check"
                              ? "bg-emerald-500/10 text-emerald-500 border-emerald-500/20"
                              : log.category === "notification"
                              ? "bg-purple-500/10 text-purple-500 border-purple-500/20"
                              : "bg-indigo-500/10 text-indigo-500 border-indigo-500/20"
                          }
                        >
                          {log.category}
                        </Badge>
                      </TableCell>
                      <TableCell className="max-w-[400px] truncate text-sm">
                        {log.message}
                      </TableCell>
                      <TableCell className="text-sm font-medium">
                        {log.device_name ?? (log.module_name ? `@${log.module_name}` : "System")}
                      </TableCell>
                      <TableCell className="text-right">
                        {log.traceback ? (
                          <Button
                            variant="ghost"
                            size="icon"
                            className="h-8 w-8 text-muted-foreground hover:text-foreground"
                            onClick={(e) => {
                              e.stopPropagation();
                              setSelectedLog(log);
                            }}
                            title="Inspect error traceback"
                          >
                            <Terminal className="h-4 w-4" />
                          </Button>
                        ) : (
                          <span className="text-xs text-muted-foreground/40">—</span>
                        )}
                      </TableCell>
                    </TableRow>
                  ))
                )}
              </TableBody>
            </Table>
          </div>

          {/* Pagination controls */}
          {!isLoading && totalPages > 1 && (
            <div className="flex items-center justify-between border-t border-border/40 px-4 py-3 bg-muted/10">
              <div className="text-sm text-muted-foreground">
                Showing <span className="font-medium">{page * PAGE_SIZE + 1}</span> to{" "}
                <span className="font-medium">
                  {Math.min((page + 1) * PAGE_SIZE, totalLogs)}
                </span>{" "}
                of <span className="font-medium">{totalLogs}</span> entries
              </div>
              <div className="flex items-center gap-2">
                <Button
                  variant="outline"
                  size="icon"
                  className="h-8 w-8"
                  onClick={() => setPage((p) => Math.max(0, p - 1))}
                  disabled={page === 0}
                >
                  <ChevronLeft className="h-4 w-4" />
                </Button>
                <div className="text-xs text-muted-foreground font-mono">
                  {page + 1} / {totalPages}
                </div>
                <Button
                  variant="outline"
                  size="icon"
                  className="h-8 w-8"
                  onClick={() => setPage((p) => Math.min(totalPages - 1, p + 1))}
                  disabled={page >= totalPages - 1}
                >
                  <ChevronRight className="h-4 w-4" />
                </Button>
              </div>
            </div>
          )}
        </CardContent>
      </Card>

      {/* Slide-out Traceback Drawer */}
      {selectedLog && (
        <div className="fixed inset-0 z-50 flex justify-end bg-background/80 backdrop-blur-sm transition-opacity duration-300 animate-in fade-in">
          {/* Overlay Click-to-dismiss */}
          <div className="absolute inset-0" onClick={() => setSelectedLog(null)} />

          {/* Panel */}
          <div className="relative z-10 w-full max-w-2xl h-full border-l border-border bg-card shadow-2xl flex flex-col animate-in slide-in-from-right duration-300">
            {/* Header */}
            <div className="flex items-center justify-between border-b border-border/60 px-6 py-4 bg-muted/20">
              <div className="space-y-1">
                <div className="flex items-center gap-2">
                  <Badge variant="outline" className="bg-red-500/10 text-red-500 border-red-500/20">
                    {selectedLog.level}
                  </Badge>
                  <Badge variant="outline" className="bg-emerald-500/10 text-emerald-500 border-emerald-500/20">
                    {selectedLog.category}
                  </Badge>
                  <span className="text-xs font-mono text-muted-foreground">
                    ID: #{selectedLog.id}
                  </span>
                </div>
                <h3 className="text-lg font-semibold tracking-tight">Traceback Details</h3>
              </div>
              <Button
                variant="ghost"
                size="icon"
                className="h-9 w-9 rounded-full"
                onClick={() => setSelectedLog(null)}
              >
                <X className="h-4 w-4" />
              </Button>
            </div>

            {/* Scrollable details */}
            <div className="flex-1 overflow-y-auto p-6 space-y-6">
              <div className="space-y-2">
                <h4 className="text-sm font-semibold text-muted-foreground">Error Message</h4>
                <p className="text-sm border border-border/50 bg-muted/10 p-3 rounded-md leading-relaxed">
                  {selectedLog.message}
                </p>
              </div>

              {selectedLog.device_name && (
                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <span className="text-xs text-muted-foreground block">Device</span>
                    <span className="text-sm font-medium">{selectedLog.device_name}</span>
                  </div>
                  {selectedLog.module_name && (
                    <div>
                      <span className="text-xs text-muted-foreground block">Module</span>
                      <span className="text-sm font-mono">{selectedLog.module_name}</span>
                    </div>
                  )}
                </div>
              )}

              <div className="space-y-2 flex-1 flex flex-col min-h-0">
                <h4 className="text-sm font-semibold text-muted-foreground flex items-center gap-2">
                  <Terminal className="h-4 w-4 text-red-500" />
                  Stack Trace
                </h4>
                <pre className="flex-1 overflow-auto bg-black text-red-400 font-mono text-xs p-4 rounded-md border border-border shadow-inner leading-relaxed select-text whitespace-pre">
                  {selectedLog.traceback}
                </pre>
              </div>
            </div>

            {/* Footer */}
            <div className="border-t border-border/60 px-6 py-4 bg-muted/10 flex justify-end">
              <Button onClick={() => setSelectedLog(null)}>Close Panel</Button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
