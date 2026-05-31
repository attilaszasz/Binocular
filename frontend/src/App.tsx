import {
  AlertCircle,
  ArrowRight,
  Binoculars,
  Check,
  CheckCircle2,
  Menu,
  Moon,
  Package,
  Plus,
  RefreshCw,
  Server,
  Settings,
  Sun,
  TerminalSquare,
  X,
} from 'lucide-react';
import { useMemo, useState } from 'react';
import { NavLink, Navigate, Route, Routes, useLocation } from 'react-router-dom';

import { useTheme } from './theme/useTheme';

type Device = {
  id: number;
  name: string;
  model: string;
  type: string;
  localVersion: string;
  webVersion: string;
  lastChecked: string;
  isChecking: boolean;
};

type LogEntry = {
  id: number;
  time: string;
  level: 'INFO' | 'WARN' | 'ERROR';
  message: string;
};

type ModuleEntry = {
  id: number;
  name: string;
  status: 'Active' | 'Inactive';
  devices: number;
  version: string;
};

const initialDevices: Device[] = [
  {
    id: 1,
    name: 'Sony A7IV',
    model: 'ILCE-7M4',
    type: 'Sony Alpha Bodies',
    localVersion: '2.00',
    webVersion: '3.00',
    lastChecked: '10 mins ago',
    isChecking: false,
  },
  {
    id: 2,
    name: 'Sony 24-70mm f/2.8 GM II',
    model: 'SEL2470GM2',
    type: 'Sony E-Mount Lenses',
    localVersion: '02',
    webVersion: '02',
    lastChecked: '1 hour ago',
    isChecking: false,
  },
  {
    id: 3,
    name: 'Sony 70-200mm f/2.8 GM II',
    model: 'SEL70200GM2',
    type: 'Sony E-Mount Lenses',
    localVersion: '03',
    webVersion: '04',
    lastChecked: '2 hours ago',
    isChecking: false,
  },
  {
    id: 4,
    name: 'Lumix GH6',
    model: 'DC-GH6',
    type: 'Panasonic Lumix Bodies',
    localVersion: '2.3',
    webVersion: '2.3',
    lastChecked: '1 day ago',
    isChecking: false,
  },
  {
    id: 5,
    name: 'Ubiquiti Dream Machine Pro',
    model: 'UDM-Pro',
    type: 'Networking',
    localVersion: '3.2.12',
    webVersion: '3.2.12',
    lastChecked: '5 mins ago',
    isChecking: false,
  },
];

const initialLogs: LogEntry[] = [
  { id: 1, time: '10:42 AM', level: 'INFO', message: 'Manual check started for Sony A7IV' },
  { id: 2, time: '10:42 AM', level: 'WARN', message: 'New firmware v3.00 found for Sony A7IV (Local: v2.00)' },
  { id: 3, time: '09:00 AM', level: 'INFO', message: 'Scheduled check completed. 15 devices scanned.' },
  { id: 4, time: '08:59 AM', level: 'ERROR', message: 'Failed to scrape Panasonic URL: HTTP 429 Too Many Requests' },
];

const modules: ModuleEntry[] = [
  { id: 1, name: 'sony_alpha.py', status: 'Active', devices: 3, version: '1.2.0' },
  { id: 2, name: 'panasonic_lumix.py', status: 'Active', devices: 1, version: '1.0.5' },
  { id: 3, name: 'unifi_network.py', status: 'Inactive', devices: 1, version: '0.9.1' },
];

const navItems = [
  { to: '/inventory', label: 'Inventory', icon: Server },
  { to: '/logs', label: 'Activity Logs', icon: TerminalSquare },
  { to: '/modules', label: 'Modules', icon: Package },
  { to: '/settings', label: 'Settings', icon: Settings },
];

const pageTitles: Record<string, string> = {
  '/inventory': 'Inventory',
  '/logs': 'Activity Logs',
  '/modules': 'Modules',
  '/settings': 'Settings',
};

export function App() {
  const [devices, setDevices] = useState<Device[]>(initialDevices);
  const [logs, setLogs] = useState<LogEntry[]>(initialLogs);
  const [isMobileMenuOpen, setIsMobileMenuOpen] = useState(false);
  const [isCheckingAll, setIsCheckingAll] = useState(false);
  const { mode, toggleMode } = useTheme();
  const location = useLocation();

  const groupedDevices = useMemo(() => {
    return devices.reduce<Record<string, Device[]>>((groups, device) => {
      groups[device.type] = [...(groups[device.type] ?? []), device];
      return groups;
    }, {});
  }, [devices]);

  const stats = useMemo(() => {
    const total = devices.length;
    const updates = devices.filter((device) => device.localVersion !== device.webVersion).length;
    return { total, updates, upToDate: total - updates };
  }, [devices]);

  function addLog(level: LogEntry['level'], message: string) {
    const time = new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
    setLogs((current) => [{ id: Date.now(), time, level, message }, ...current].slice(0, 50));
  }

  function handleCheckDevice(id: number) {
    setDevices((current) =>
      current.map((device) => (device.id === id ? { ...device, isChecking: true } : device)),
    );

    window.setTimeout(() => {
      setDevices((current) =>
        current.map((device) =>
          device.id === id ? { ...device, isChecking: false, lastChecked: 'Just now' } : device,
        ),
      );
      addLog('INFO', `Completed manual check for device ID ${id}`);
    }, 600);
  }

  function handleCheckAll() {
    setIsCheckingAll(true);
    setDevices((current) => current.map((device) => ({ ...device, isChecking: true })));
    addLog('INFO', 'Initiated bulk check for all devices');

    window.setTimeout(() => {
      setDevices((current) =>
        current.map((device) => ({ ...device, isChecking: false, lastChecked: 'Just now' })),
      );
      setIsCheckingAll(false);
      addLog('INFO', 'Bulk check completed successfully');
    }, 900);
  }

  function handleMarkUpdated(id: number) {
    setDevices((current) =>
      current.map((device) => {
        if (device.id !== id) {
          return device;
        }
        addLog('INFO', `User confirmed update for ${device.name}. Version synced to ${device.webVersion}`);
        return { ...device, localVersion: device.webVersion };
      }),
    );
  }

  return (
    <div className="min-h-screen bg-slate-50 text-slate-900 transition-colors dark:bg-slate-950 dark:text-white">
      {isMobileMenuOpen && (
        <button
          type="button"
          className="fixed inset-0 z-40 bg-slate-950/60 md:hidden"
          aria-label="Close navigation overlay"
          onClick={() => setIsMobileMenuOpen(false)}
        />
      )}

      <aside
        className={`fixed inset-y-0 left-0 z-50 w-64 transform border-r bg-white transition-transform duration-300 ease-in-out dark:border-slate-800 dark:bg-slate-900 md:translate-x-0 ${
          isMobileMenuOpen ? 'translate-x-0' : '-translate-x-full'
        }`}
      >
        <div className="flex h-16 items-center justify-between border-b border-inherit px-6">
          <Brand />
          <button
            type="button"
            className="rounded-lg p-2 text-slate-400 hover:text-slate-600 dark:hover:text-slate-200 md:hidden"
            onClick={() => setIsMobileMenuOpen(false)}
            aria-label="Close navigation"
          >
            <X size={20} />
          </button>
        </div>
        <nav className="space-y-1.5 p-4" aria-label="Primary navigation">
          {navItems.map((item) => (
            <NavItem key={item.to} item={item} onNavigate={() => setIsMobileMenuOpen(false)} />
          ))}
        </nav>
      </aside>

      <main className="min-h-screen transition-all duration-300 ease-in-out md:ml-64">
        <header className="sticky top-0 z-30 flex h-16 items-center justify-between border-b border-slate-200 bg-white/85 px-4 backdrop-blur-sm dark:border-slate-800 dark:bg-slate-950/85 sm:px-6 lg:px-8">
          <div className="flex items-center">
            <button
              type="button"
              className="mr-4 rounded-lg p-2 text-slate-500 hover:bg-slate-100 hover:text-slate-700 dark:hover:bg-slate-800 dark:hover:text-slate-200 md:hidden"
              onClick={() => setIsMobileMenuOpen(true)}
              aria-label="Open navigation"
            >
              <Menu size={24} />
            </button>
            <h1 className="text-lg font-semibold">{pageTitles[location.pathname] ?? 'Inventory'}</h1>
          </div>

          <button
            type="button"
            onClick={toggleMode}
            className="rounded-full p-2 text-slate-500 transition-colors hover:bg-slate-100 hover:text-slate-700 dark:text-slate-400 dark:hover:bg-slate-800 dark:hover:text-slate-200"
            aria-label={`Switch to ${mode === 'dark' ? 'light' : 'dark'} mode`}
          >
            {mode === 'dark' ? <Sun size={20} /> : <Moon size={20} />}
          </button>
        </header>

        <div className="mx-auto max-w-7xl px-4 py-8 sm:px-6 lg:px-8">
          <Routes>
            <Route path="/" element={<Navigate to="/inventory" replace />} />
            <Route
              path="/inventory"
              element={
                <InventoryPage
                  devicesByType={groupedDevices}
                  stats={stats}
                  isCheckingAll={isCheckingAll}
                  onCheckAll={handleCheckAll}
                  onCheckDevice={handleCheckDevice}
                  onMarkUpdated={handleMarkUpdated}
                />
              }
            />
            <Route path="/logs" element={<LogsPage logs={logs} />} />
            <Route path="/modules" element={<ModulesPage />} />
            <Route path="/settings" element={<SettingsPage />} />
            <Route path="*" element={<Navigate to="/inventory" replace />} />
          </Routes>
        </div>
      </main>
    </div>
  );
}

function Brand() {
  return (
    <div className="flex items-center gap-2">
      <div className="rounded-lg bg-indigo-100 p-1.5 text-indigo-600 dark:bg-indigo-500/20 dark:text-indigo-400">
        <Binoculars size={24} />
      </div>
      <span className="text-xl font-bold tracking-tight">Binocular</span>
    </div>
  );
}

function NavItem({ item, onNavigate }: { item: (typeof navItems)[number]; onNavigate: () => void }) {
  const Icon = item.icon;
  return (
    <NavLink
      to={item.to}
      onClick={onNavigate}
      className={({ isActive }) =>
        `flex w-full items-center gap-3 rounded-xl px-4 py-3 text-sm font-medium transition-all duration-200 ${
          isActive
            ? 'bg-indigo-50 text-indigo-600 dark:bg-indigo-500/10 dark:text-indigo-400'
            : 'text-slate-600 hover:bg-slate-100 hover:text-slate-900 dark:text-slate-400 dark:hover:bg-slate-800 dark:hover:text-slate-200'
        }`
      }
    >
      <Icon size={20} />
      <span>{item.label}</span>
    </NavLink>
  );
}

function InventoryPage({
  devicesByType,
  stats,
  isCheckingAll,
  onCheckAll,
  onCheckDevice,
  onMarkUpdated,
}: {
  devicesByType: Record<string, Device[]>;
  stats: { total: number; updates: number; upToDate: number };
  isCheckingAll: boolean;
  onCheckAll: () => void;
  onCheckDevice: (id: number) => void;
  onMarkUpdated: (id: number) => void;
}) {
  return (
    <div className="space-y-8">
      <div className="flex flex-col justify-between gap-4 sm:flex-row sm:items-center">
        <div>
          <h2 className="text-2xl font-bold tracking-tight">Device Inventory</h2>
          <p className="mt-1 text-sm text-slate-500 dark:text-slate-400">
            Manage your hardware and monitor for firmware updates.
          </p>
        </div>
        <div className="flex flex-wrap items-center gap-3">
          <button className="inline-flex items-center rounded-xl border border-slate-200 bg-white px-4 py-2 text-sm font-medium text-slate-700 shadow-sm transition hover:bg-slate-50 dark:border-slate-700 dark:bg-slate-800 dark:text-slate-200 dark:hover:bg-slate-700">
            <Plus size={16} className="mr-2" />
            Add Device
          </button>
          <button
            type="button"
            onClick={onCheckAll}
            disabled={isCheckingAll}
            className="inline-flex items-center rounded-xl bg-indigo-600 px-4 py-2 text-sm font-medium text-white shadow-sm transition hover:bg-indigo-700 disabled:bg-indigo-300 dark:hover:bg-indigo-500 dark:disabled:bg-indigo-800 dark:disabled:text-indigo-300"
          >
            <RefreshCw size={16} className={`mr-2 ${isCheckingAll ? 'animate-spin' : ''}`} />
            {isCheckingAll ? 'Checking All...' : 'Check All Now'}
          </button>
        </div>
      </div>

      <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
        <StatCard label="Total Devices" value={stats.total} icon={Server} tone="indigo" />
        <StatCard label="Updates Available" value={stats.updates} icon={AlertCircle} tone="rose" />
        <StatCard label="Up to Date" value={stats.upToDate} icon={CheckCircle2} tone="emerald" />
      </div>

      {Object.entries(devicesByType).map(([type, devices]) => (
        <section key={type} className="space-y-4">
          <h3 className="flex items-center text-sm font-semibold uppercase tracking-wider text-slate-500 dark:text-slate-400">
            <Package size={16} className="mr-2" />
            {type}
          </h3>
          <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
            {devices.map((device) => (
              <DeviceCard
                key={device.id}
                device={device}
                onCheckDevice={onCheckDevice}
                onMarkUpdated={onMarkUpdated}
                isCheckingAll={isCheckingAll}
              />
            ))}
          </div>
        </section>
      ))}
    </div>
  );
}

function StatCard({
  label,
  value,
  icon: Icon,
  tone,
}: {
  label: string;
  value: number;
  icon: typeof Server;
  tone: 'indigo' | 'rose' | 'emerald';
}) {
  const toneClass = {
    indigo: 'bg-indigo-50 text-indigo-600 dark:bg-indigo-500/10 dark:text-indigo-400',
    rose: 'bg-rose-50 text-rose-600 dark:bg-rose-500/10 dark:text-rose-400',
    emerald: 'bg-emerald-50 text-emerald-600 dark:bg-emerald-500/10 dark:text-emerald-400',
  }[tone];

  return (
    <div className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm dark:border-slate-800 dark:bg-slate-900">
      <div className="flex items-center justify-between">
        <div>
          <p className="text-sm font-medium text-slate-500 dark:text-slate-400">{label}</p>
          <p className="mt-2 text-3xl font-bold">{value}</p>
        </div>
        <div className={`rounded-xl p-3 ${toneClass}`}>
          <Icon size={24} />
        </div>
      </div>
    </div>
  );
}

function DeviceCard({
  device,
  isCheckingAll,
  onCheckDevice,
  onMarkUpdated,
}: {
  device: Device;
  isCheckingAll: boolean;
  onCheckDevice: (id: number) => void;
  onMarkUpdated: (id: number) => void;
}) {
  const hasUpdate = device.localVersion !== device.webVersion;
  return (
    <article
      className={`rounded-2xl border bg-white p-5 shadow-sm transition-all duration-200 dark:bg-slate-900 ${
        hasUpdate
          ? 'border-rose-300 ring-1 ring-rose-300 dark:border-rose-500/50 dark:ring-0 dark:shadow-[0_0_15px_rgba(244,63,94,0.12)]'
          : 'border-slate-200 dark:border-slate-800'
      }`}
    >
      <div className="mb-4 flex items-start justify-between gap-4">
        <div>
          <h4 className="text-lg font-bold text-slate-900 dark:text-slate-100">{device.name}</h4>
          <p className="mt-1 font-mono text-xs font-semibold text-slate-500 dark:text-slate-400">{device.model}</p>
          <p className="mt-1 text-xs text-slate-400 dark:text-slate-500">Last checked: {device.lastChecked}</p>
        </div>
        <button
          type="button"
          onClick={() => onCheckDevice(device.id)}
          disabled={device.isChecking || isCheckingAll}
          className="rounded-lg bg-slate-100 p-2 text-slate-600 transition-colors hover:bg-slate-200 disabled:opacity-50 dark:bg-slate-800 dark:text-slate-300 dark:hover:bg-slate-700"
          aria-label={`Check ${device.name} for updates`}
        >
          <RefreshCw size={16} className={device.isChecking ? 'animate-spin' : ''} />
        </button>
      </div>

      <div
        className={`flex items-center justify-between rounded-xl p-4 ${
          hasUpdate ? 'bg-rose-50 dark:bg-rose-500/10' : 'bg-slate-50 dark:bg-slate-800/50'
        }`}
      >
        <div className="flex flex-1 items-center gap-4">
          <VersionBlock label="Local" value={device.localVersion} />
          {hasUpdate && <ArrowRight size={20} className="shrink-0 animate-pulse text-rose-500 dark:text-rose-400" />}
          <VersionBlock label="Latest" value={device.webVersion} highlight={hasUpdate ? 'update' : 'ok'} />
        </div>

        {hasUpdate && (
          <div className="ml-4 shrink-0 border-l border-slate-200 pl-4 dark:border-slate-700">
            <button
              type="button"
              onClick={() => onMarkUpdated(device.id)}
              className="inline-flex items-center rounded-lg border border-emerald-200 bg-emerald-100 px-3 py-2 text-sm font-medium text-emerald-700 transition-colors hover:bg-emerald-200 dark:border-emerald-500/30 dark:bg-emerald-500/20 dark:text-emerald-400 dark:hover:bg-emerald-500/30"
            >
              <Check size={16} className="mr-1.5" />
              Sync Local
            </button>
          </div>
        )}
      </div>
    </article>
  );
}

function VersionBlock({ label, value, highlight }: { label: string; value: string; highlight?: 'update' | 'ok' }) {
  const colorClass =
    highlight === 'update'
      ? 'text-rose-600 dark:text-rose-400'
      : highlight === 'ok'
        ? 'text-emerald-600 dark:text-emerald-400'
        : 'text-slate-700 dark:text-slate-300';
  return (
    <div className="min-w-0 flex-1">
      <p className="mb-1 text-xs font-medium uppercase tracking-wider text-slate-400 dark:text-slate-500">{label}</p>
      <p className={`font-mono text-lg font-semibold ${colorClass}`}>v{value}</p>
    </div>
  );
}

function LogsPage({ logs }: { logs: LogEntry[] }) {
  return (
    <div className="space-y-6">
      <PageHeader title="Activity Logs" description="System execution and scraping history." />
      <div className="overflow-hidden rounded-2xl border border-slate-200 bg-white dark:border-slate-800 dark:bg-slate-900">
        <div className="overflow-x-auto">
          <table className="min-w-full divide-y divide-slate-200 dark:divide-slate-800">
            <thead className="bg-slate-50 dark:bg-slate-800/50">
              <tr>
                <TableHead>Time</TableHead>
                <TableHead>Level</TableHead>
                <TableHead>Message</TableHead>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-200 font-mono text-sm dark:divide-slate-800">
              {logs.map((log) => (
                <tr key={log.id} className="transition-colors hover:bg-slate-50 dark:hover:bg-slate-800/50">
                  <td className="whitespace-nowrap px-6 py-4 text-slate-500 dark:text-slate-400">{log.time}</td>
                  <td className="whitespace-nowrap px-6 py-4">
                    <LogBadge level={log.level} />
                  </td>
                  <td className="px-6 py-4 text-slate-700 dark:text-slate-300">{log.message}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}

function ModulesPage() {
  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between gap-4">
        <PageHeader title="Extension Modules" description="Manage Python scripts that scrape firmware data." />
        <button className="inline-flex items-center rounded-xl border border-slate-200 bg-white px-4 py-2 text-sm font-medium text-slate-700 shadow-sm transition hover:bg-slate-50 dark:border-slate-700 dark:bg-slate-800 dark:text-slate-200 dark:hover:bg-slate-700">
          <Plus size={16} className="mr-2" />
          Upload Module
        </button>
      </div>
      <div className="grid grid-cols-1 gap-6 md:grid-cols-2 lg:grid-cols-3">
        {modules.map((module) => (
          <article
            key={module.id}
            className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm dark:border-slate-800 dark:bg-slate-900"
          >
            <div className="mb-4 flex items-start justify-between">
              <div className="rounded-xl bg-indigo-50 p-3 text-indigo-600 dark:bg-slate-800 dark:text-indigo-400">
                <TerminalSquare size={24} />
              </div>
              <ModuleStatus status={module.status} />
            </div>
            <h3 className="truncate font-mono text-lg font-bold">{module.name}</h3>
            <p className="mb-4 mt-1 text-sm text-slate-500 dark:text-slate-400">Version {module.version}</p>
            <div className="flex items-center justify-between border-t border-slate-100 pt-4 dark:border-slate-800">
              <span className="flex items-center text-sm font-medium text-slate-600 dark:text-slate-400">
                <Server size={14} className="mr-1.5" />
                {module.devices} mapped devices
              </span>
              <button className="text-sm font-medium text-indigo-600 hover:text-indigo-700 dark:text-indigo-400 dark:hover:text-indigo-300">
                Configure
              </button>
            </div>
          </article>
        ))}
      </div>
    </div>
  );
}

function SettingsPage() {
  return (
    <div className="flex flex-col items-center justify-center py-20 text-center">
      <div className="mb-4 rounded-full bg-slate-100 p-4 text-slate-500 dark:bg-slate-800 dark:text-slate-400">
        <Settings size={32} />
      </div>
      <h2 className="text-xl font-semibold">Settings configuration</h2>
      <p className="mt-2 max-w-sm text-slate-500 dark:text-slate-400">
        Notification channels, backup configurations, and global interval settings go here.
      </p>
    </div>
  );
}

function PageHeader({ title, description }: { title: string; description: string }) {
  return (
    <div>
      <h2 className="text-2xl font-bold tracking-tight">{title}</h2>
      <p className="mt-1 text-sm text-slate-500 dark:text-slate-400">{description}</p>
    </div>
  );
}

function TableHead({ children }: { children: string }) {
  return (
    <th className="px-6 py-3 text-left text-xs font-medium uppercase tracking-wider text-slate-500 dark:text-slate-400">
      {children}
    </th>
  );
}

function LogBadge({ level }: { level: LogEntry['level'] }) {
  const className = {
    INFO: 'bg-blue-100 text-blue-700 dark:bg-blue-500/10 dark:text-blue-400',
    WARN: 'bg-amber-100 text-amber-700 dark:bg-amber-500/10 dark:text-amber-400',
    ERROR: 'bg-rose-100 text-rose-700 dark:bg-rose-500/10 dark:text-rose-400',
  }[level];
  return <span className={`inline-flex rounded-md px-2.5 py-0.5 text-xs font-medium ${className}`}>{level}</span>;
}

function ModuleStatus({ status }: { status: ModuleEntry['status'] }) {
  const className =
    status === 'Active'
      ? 'border-emerald-200 bg-emerald-50 text-emerald-700 dark:border-emerald-500/20 dark:bg-emerald-500/10 dark:text-emerald-400'
      : 'border-slate-200 bg-slate-100 text-slate-500 dark:border-slate-700 dark:bg-slate-800 dark:text-slate-400';
  return <span className={`rounded-full border px-2.5 py-1 text-xs font-medium ${className}`}>{status}</span>;
}
