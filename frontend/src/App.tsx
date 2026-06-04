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
  Server,
  Settings,
  Sun,
  TerminalSquare,
  Unlink,
  X,
  Mail,
  Send,
  ChevronDown,
  ChevronUp,
  Copy,
  RefreshCw,
  Filter,
} from 'lucide-react';
import { FormEvent, Fragment, useCallback, useEffect, useMemo, useState } from 'react';
import { NavLink, Navigate, Route, Routes, useLocation } from 'react-router-dom';

import {
  archiveDevice,
  CheckResult,
  confirmDeviceUpdate,
  createDevice,
  DeviceGroup,
  DeviceInput,
  deleteModule,
  InstalledModule,
  InventoryDevice,
  listInventory,
  listModules,
  ModuleUploadError,
  ModuleValidationSummary,
  runAllChecks,
  runDeviceCheck,
  uploadModule,
  updateDevice,
  listChannels,
  configureChannel,
  testChannel,
  listActivity,
  ActivityLog,
} from './api';
import { useTheme } from './theme/useTheme';

type LogEntry = {
  id: number;
  time: string;
  level: 'INFO' | 'WARN' | 'ERROR';
  message: string;
};

const initialLogs: LogEntry[] = [
  { id: 1, time: '10:42 AM', level: 'INFO', message: 'Manual check started for Sony A7IV' },
  { id: 2, time: '10:42 AM', level: 'WARN', message: 'New firmware v3.00 found for Sony A7IV (Local: v2.00)' },
  { id: 3, time: '09:00 AM', level: 'INFO', message: 'Scheduled check completed. 15 devices scanned.' },
  { id: 4, time: '08:59 AM', level: 'ERROR', message: 'Failed to scrape Panasonic URL: HTTP 429 Too Many Requests' },
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

const emptyDeviceInput: DeviceInput = {
  name: '',
  model: '',
  moduleId: '',
  currentVersion: '',
};

export function App() {
  const [groups, setGroups] = useState<DeviceGroup[]>([]);
  const [inventoryError, setInventoryError] = useState<string | null>(null);
  const [isInventoryLoading, setIsInventoryLoading] = useState(true);
  const [modules, setModules] = useState<InstalledModule[]>([]);
  const [moduleError, setModuleError] = useState<string | null>(null);
  const [moduleValidation, setModuleValidation] = useState<ModuleValidationSummary | null>(null);
  const [selectedModuleFile, setSelectedModuleFile] = useState<File | null>(null);
  const [preferredCheckModuleId, setPreferredCheckModuleId] = useState('');
  const [manualResults, setManualResults] = useState<Record<number, CheckResult>>({});
  const [manualError, setManualError] = useState<string | null>(null);
  const [checkingDeviceIds, setCheckingDeviceIds] = useState<Set<number>>(new Set());
  const [isBulkChecking, setIsBulkChecking] = useState(false);
  const [bulkSummary, setBulkSummary] = useState<{ total: number; succeeded: number; failed: number } | null>(null);
  const [isModulesLoading, setIsModulesLoading] = useState(false);
  const [formValues, setFormValues] = useState<DeviceInput>(emptyDeviceInput);
  const [editingDevice, setEditingDevice] = useState<InventoryDevice | null>(null);
  const [logs, setLogs] = useState<LogEntry[]>(initialLogs);
  const [isMobileMenuOpen, setIsMobileMenuOpen] = useState(false);
  const { mode, toggleMode } = useTheme();
  const location = useLocation();

  useEffect(() => {
    if (location.pathname === '/' || location.pathname === '/inventory') {
      void refreshInventory();
      void refreshModules();
    }
    if (location.pathname === '/modules') {
      void refreshModules();
    }
  }, [location.pathname]);

  const devices = useMemo(() => groups.flatMap((group) => group.devices), [groups]);
  const validModules = useMemo(
    () => modules.filter((module) => module.status === 'installed' && module.validationStatus === 'valid'),
    [modules],
  );
  const selectedCheckModuleId = validModules.some((module) => module.moduleId === preferredCheckModuleId)
    ? preferredCheckModuleId
    : (validModules[0]?.moduleId ?? '');

  const stats = useMemo(() => {
    const total = devices.length;
    const updates = devices.filter((device) => device.status === 'update_available').length;
    const upToDate = devices.filter((device) => device.status === 'up_to_date').length;
    return { total, updates, upToDate };
  }, [devices]);

  async function refreshInventory() {
    setIsInventoryLoading(true);
    setInventoryError(null);
    try {
      const inventory = await listInventory();
      setGroups(inventory.groups);
    } catch (error) {
      const message = error instanceof Error ? error.message : 'Inventory failed to load';
      setInventoryError(message);
    } finally {
      setIsInventoryLoading(false);
    }
  }

  async function refreshModules() {
    setIsModulesLoading(true);
    setModuleError(null);
    try {
      const response = await listModules();
      setModules(response.modules);
    } catch (error) {
      const message = error instanceof Error ? error.message : 'Modules failed to load';
      setModuleError(message);
    } finally {
      setIsModulesLoading(false);
    }
  }

  function addLog(level: LogEntry['level'], message: string) {
    const time = new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
    setLogs((current) => [{ id: Date.now(), time, level, message }, ...current].slice(0, 50));
  }

  function handleInputChange(field: keyof DeviceInput, value: string) {
    setFormValues((current) => ({ ...current, [field]: value }));
  }

  function startEditing(device: InventoryDevice) {
    setEditingDevice(device);
    setFormValues({
      name: device.name,
      model: device.model,
      moduleId: device.moduleId ?? '',
      currentVersion: device.currentVersion,
    });
  }

  function cancelEditing() {
    setEditingDevice(null);
    setFormValues(emptyDeviceInput);
  }

  async function handleSubmitDevice(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    try {
      if (editingDevice === null) {
        const device = await createDevice(formValues);
        addLog('INFO', `Added ${device.name} to inventory`);
      } else {
        const device = await updateDevice(editingDevice.id, formValues);
        addLog('INFO', `Updated ${device.name}`);
      }
      cancelEditing();
      await refreshInventory();
    } catch (error) {
      const message = error instanceof Error ? error.message : 'Inventory save failed';
      setInventoryError(message);
      addLog('ERROR', message);
    }
  }

  async function handleArchiveDevice(device: InventoryDevice) {
    await archiveDevice(device.id);
    addLog('INFO', `Archived ${device.name}`);
    await refreshInventory();
  }

  async function handleMarkUpdated(device: InventoryDevice) {
    try {
      const updated = await confirmDeviceUpdate(device.id, { version: device.latestVersion ?? '' });
      addLog('INFO', `User confirmed update for ${updated.name}. Version synced to ${updated.currentVersion}`);
      await refreshInventory();
    } catch (error) {
      const message = error instanceof Error ? error.message : 'No latest version is available';
      setInventoryError(message);
      addLog('WARN', message);
    }
  }

  async function handleRunDeviceCheck(device: InventoryDevice) {
    if (selectedCheckModuleId === '') {
      setManualError('Install and validate a module before running manual checks');
      return;
    }
    setManualError(null);
    setCheckingDeviceIds((current) => new Set(current).add(device.id));
    try {
      const result = await runDeviceCheck(device.id, { moduleId: selectedCheckModuleId });
      setManualResults((current) => ({ ...current, [device.id]: result }));
      setBulkSummary(null);
      addLog(result.status === 'failed' ? 'WARN' : 'INFO', `Manual check completed for ${device.name}`);
      await refreshInventory();
    } catch (error) {
      const message = error instanceof Error ? error.message : 'Manual check failed';
      setManualError(message);
      addLog('ERROR', message);
    } finally {
      setCheckingDeviceIds((current) => {
        const next = new Set(current);
        next.delete(device.id);
        return next;
      });
    }
  }

  async function handleRunAllChecks() {
    if (selectedCheckModuleId === '') {
      setManualError('Install and validate a module before running manual checks');
      return;
    }
    setManualError(null);
    setBulkSummary(null);
    setIsBulkChecking(true);
    try {
      const response = await runAllChecks({ moduleId: selectedCheckModuleId });
      setManualResults((current) => ({
        ...current,
        ...Object.fromEntries(response.results.map((result) => [result.deviceId, result])),
      }));
      setBulkSummary({ total: response.total, succeeded: response.succeeded, failed: response.failed });
      addLog('INFO', `Manual bulk check completed. ${response.succeeded}/${response.total} succeeded.`);
      await refreshInventory();
    } catch (error) {
      const message = error instanceof Error ? error.message : 'Manual bulk check failed';
      setManualError(message);
      addLog('ERROR', message);
    } finally {
      setIsBulkChecking(false);
    }
  }

  async function handleUploadModule(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const form = event.currentTarget;
    if (selectedModuleFile === null || selectedModuleFile.size === 0) {
      setModuleError('Choose a Python module file before uploading');
      return;
    }
    setModuleError(null);
    setModuleValidation(null);
    try {
      const installed = await uploadModule(selectedModuleFile);
      addLog('INFO', `Installed module ${installed.displayName}`);
      setSelectedModuleFile(null);
      form.reset();
      await refreshModules();
    } catch (error) {
      const message = error instanceof Error ? error.message : 'Module upload failed';
      setModuleError(message);
      if (error instanceof ModuleUploadError) {
        setModuleValidation(error.validationSummary);
      }
      addLog('ERROR', message);
    }
  }

  async function handleDeleteModule(module: InstalledModule) {
    try {
      await deleteModule(module.moduleId);
      addLog('INFO', `Deleted module ${module.displayName}`);
      await refreshModules();
    } catch (error) {
      const message = error instanceof Error ? error.message : 'Module delete failed';
      setModuleError(message);
      addLog('ERROR', message);
    }
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
                  groups={groups}
                  stats={stats}
                  isLoading={isInventoryLoading}
                  error={inventoryError}
                  formValues={formValues}
                  editingDevice={editingDevice}
                  onFormChange={handleInputChange}
                  onSubmit={handleSubmitDevice}
                  onCancelEdit={cancelEditing}
                  onEdit={startEditing}
                  onArchive={handleArchiveDevice}
                  onMarkUpdated={handleMarkUpdated}
                  modules={validModules}
                  selectedModuleId={selectedCheckModuleId}
                  manualResults={manualResults}
                  manualError={manualError}
                  bulkSummary={bulkSummary}
                  checkingDeviceIds={checkingDeviceIds}
                  isBulkChecking={isBulkChecking}
                  onModuleChange={setPreferredCheckModuleId}
                  onRunDeviceCheck={handleRunDeviceCheck}
                  onRunAllChecks={handleRunAllChecks}
                />
              }
            />
            <Route path="/logs" element={<LogsPage logs={logs} />} />
            <Route
              path="/modules"
              element={
                <ModulesPage
                  modules={modules}
                  isLoading={isModulesLoading}
                  error={moduleError}
                  validation={moduleValidation}
                  selectedFile={selectedModuleFile}
                  onFileSelect={setSelectedModuleFile}
                  onUpload={handleUploadModule}
                  onDelete={handleDeleteModule}
                />
              }
            />
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
  groups,
  stats,
  isLoading,
  error,
  formValues,
  editingDevice,
  onFormChange,
  onSubmit,
  onCancelEdit,
  onEdit,
  onArchive,
  onMarkUpdated,
  modules,
  selectedModuleId,
  manualResults,
  manualError,
  bulkSummary,
  checkingDeviceIds,
  isBulkChecking,
  onModuleChange,
  onRunDeviceCheck,
  onRunAllChecks,
}: {
  groups: DeviceGroup[];
  stats: { total: number; updates: number; upToDate: number };
  isLoading: boolean;
  error: string | null;
  formValues: DeviceInput;
  editingDevice: InventoryDevice | null;
  onFormChange: (field: keyof DeviceInput, value: string) => void;
  onSubmit: (event: FormEvent<HTMLFormElement>) => void;
  onCancelEdit: () => void;
  onEdit: (device: InventoryDevice) => void;
  onArchive: (device: InventoryDevice) => void;
  onMarkUpdated: (device: InventoryDevice) => void;
  modules: InstalledModule[];
  selectedModuleId: string;
  manualResults: Record<number, CheckResult>;
  manualError: string | null;
  bulkSummary: { total: number; succeeded: number; failed: number } | null;
  checkingDeviceIds: Set<number>;
  isBulkChecking: boolean;
  onModuleChange: (moduleId: string) => void;
  onRunDeviceCheck: (device: InventoryDevice) => void;
  onRunAllChecks: () => void;
}) {
  const canCheck = selectedModuleId !== '';

  const sortedGroups = useMemo(
    () =>
      [...groups].sort((a, b) => {
        const aUnlinked = a.name === 'Unlinked' ? 1 : 0;
        const bUnlinked = b.name === 'Unlinked' ? 1 : 0;
        return aUnlinked - bUnlinked;
      }),
    [groups],
  );

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
          <label className="sr-only" htmlFor="manualCheckModule">
            Manual check module
          </label>
          <select
            id="manualCheckModule"
            value={selectedModuleId}
            onChange={(event) => onModuleChange(event.target.value)}
            className="h-10 rounded-xl border border-slate-200 bg-white px-3 text-sm text-slate-700 shadow-sm outline-none transition focus:border-indigo-500 focus:ring-2 focus:ring-indigo-500/20 dark:border-slate-700 dark:bg-slate-800 dark:text-slate-200"
          >
            {modules.length === 0 ? (
              <option value="">No valid modules</option>
            ) : (
              modules.map((module) => (
                <option key={module.moduleId} value={module.moduleId}>
                  {module.displayName}
                </option>
              ))
            )}
          </select>
          <button
            type="button"
            onClick={onRunAllChecks}
            disabled={!canCheck || isBulkChecking}
            className="inline-flex h-10 items-center rounded-xl border border-slate-200 bg-white px-4 text-sm font-medium text-slate-700 shadow-sm transition hover:bg-slate-50 disabled:cursor-not-allowed disabled:opacity-60 dark:border-slate-700 dark:bg-slate-800 dark:text-slate-200 dark:hover:bg-slate-700"
          >
            <Binoculars size={16} className="mr-2" />
            {isBulkChecking ? 'Checking...' : 'Check All'}
          </button>
          <a
            href="#inventory-form"
            className="inline-flex items-center rounded-xl border border-slate-200 bg-white px-4 py-2 text-sm font-medium text-slate-700 shadow-sm transition hover:bg-slate-50 dark:border-slate-700 dark:bg-slate-800 dark:text-slate-200 dark:hover:bg-slate-700"
          >
            <Plus size={16} className="mr-2" />
            Add Device
          </a>
        </div>
      </div>

      <form
        id="inventory-form"
        onSubmit={onSubmit}
        className="grid gap-3 rounded-2xl border border-slate-200 bg-white p-4 shadow-sm dark:border-slate-800 dark:bg-slate-900 md:grid-cols-6"
      >
        <InventoryInput label="Name" value={formValues.name} onChange={(value) => onFormChange('name', value)} />
        <InventoryInput label="Model" value={formValues.model} onChange={(value) => onFormChange('model', value)} />
        <label className="block text-sm font-medium text-slate-600 dark:text-slate-300">
          <span>Module</span>
          {modules.length > 0 ? (
            <select
              value={formValues.moduleId}
              onChange={(event) => onFormChange('moduleId', event.target.value)}
              className="mt-1 h-10 w-full rounded-xl border border-slate-200 bg-white px-3 text-sm text-slate-900 outline-none transition focus:border-indigo-500 focus:ring-2 focus:ring-indigo-500/20 dark:border-slate-700 dark:bg-slate-950 dark:text-white"
            >
              <option value="">Select a module...</option>
              {modules.map((module) => (
                <option key={module.moduleId} value={module.moduleId}>
                  {module.displayName}
                </option>
              ))}
            </select>
          ) : (
            <>
              <select
                disabled
                value=""
                className="mt-1 h-10 w-full cursor-not-allowed rounded-xl border border-slate-200 bg-white px-3 text-sm text-slate-900 opacity-60 outline-none dark:border-slate-700 dark:bg-slate-950 dark:text-white"
              >
                <option value="">Select a module...</option>
              </select>
              <p className="mt-1 text-xs text-slate-400 dark:text-slate-500">Install and validate a module first</p>
            </>
          )}
        </label>
        <label className="block text-sm font-medium text-slate-600 dark:text-slate-300">
          <span>Device Type</span>
          <input
            readOnly
            tabIndex={-1}
            value={formValues.moduleId !== '' ? (modules.find((m) => m.moduleId === formValues.moduleId)?.displayName ?? '') : ''}
            className="mt-1 h-10 w-full rounded-xl border border-slate-200 bg-slate-50 px-3 text-sm text-slate-500 outline-none cursor-default dark:border-slate-700 dark:bg-slate-900/50 dark:text-slate-400"
          />
        </label>
        <InventoryInput
          label="Current version"
          value={formValues.currentVersion}
          onChange={(value) => onFormChange('currentVersion', value)}
        />
        <div className="flex items-end gap-2">
          <button
            type="submit"
            className="inline-flex h-10 flex-1 items-center justify-center rounded-xl bg-indigo-600 px-4 text-sm font-medium text-white shadow-sm transition hover:bg-indigo-700 dark:hover:bg-indigo-500"
          >
            {editingDevice === null ? 'Add' : 'Save'}
          </button>
          {editingDevice !== null && (
            <button
              type="button"
              onClick={onCancelEdit}
              className="h-10 rounded-xl border border-slate-200 px-3 text-sm dark:border-slate-700"
            >
              Cancel
            </button>
          )}
        </div>
      </form>

      {error !== null && (
        <div className="rounded-xl border border-rose-200 bg-rose-50 px-4 py-3 text-sm text-rose-700 dark:border-rose-500/40 dark:bg-rose-500/10 dark:text-rose-300">
          {error}
        </div>
      )}

      {manualError !== null && (
        <div className="rounded-xl border border-rose-200 bg-rose-50 px-4 py-3 text-sm text-rose-700 dark:border-rose-500/40 dark:bg-rose-500/10 dark:text-rose-300">
          {manualError}
        </div>
      )}

      {bulkSummary !== null && (
        <div className="rounded-xl border border-emerald-200 bg-emerald-50 px-4 py-3 text-sm text-emerald-800 dark:border-emerald-500/30 dark:bg-emerald-500/10 dark:text-emerald-200">
          Manual bulk check complete: {bulkSummary.succeeded}/{bulkSummary.total} succeeded, {bulkSummary.failed} failed.
        </div>
      )}

      <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
        <StatCard label="Total Devices" value={stats.total} icon={Server} tone="indigo" />
        <StatCard label="Updates Available" value={stats.updates} icon={AlertCircle} tone="rose" />
        <StatCard label="Up to Date" value={stats.upToDate} icon={CheckCircle2} tone="emerald" />
      </div>

      {isLoading && <p className="text-sm text-slate-500 dark:text-slate-400">Loading inventory...</p>}

      {!isLoading && groups.length === 0 && (
        <div className="rounded-2xl border border-dashed border-slate-300 p-8 text-center text-sm text-slate-500 dark:border-slate-700 dark:text-slate-400">
          No devices tracked yet.
        </div>
      )}

      {sortedGroups.map((group) => (
        <section key={group.moduleId ?? 'ungrouped'} className="space-y-4">
          <h3 className="flex items-center text-sm font-semibold uppercase tracking-wider text-slate-500 dark:text-slate-400">
            <Package size={16} className="mr-2" />
            {group.name} ({group.count})
          </h3>
          <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
            {group.devices.map((device) => (
              <DeviceCard
                key={device.id}
                device={device}
                onEdit={onEdit}
                onArchive={onArchive}
                onMarkUpdated={onMarkUpdated}
                manualResult={manualResults[device.id]}
                isChecking={checkingDeviceIds.has(device.id)}
                canCheck={canCheck}
                onRunCheck={onRunDeviceCheck}
              />
            ))}
          </div>
        </section>
      ))}
    </div>
  );
}

function InventoryInput({ label, value, onChange }: { label: string; value: string; onChange: (value: string) => void }) {
  return (
    <label className="block text-sm font-medium text-slate-600 dark:text-slate-300">
      <span>{label}</span>
      <input
        required
        value={value}
        onChange={(event) => onChange(event.target.value)}
        className="mt-1 h-10 w-full rounded-xl border border-slate-200 bg-white px-3 text-sm text-slate-900 outline-none transition focus:border-indigo-500 focus:ring-2 focus:ring-indigo-500/20 dark:border-slate-700 dark:bg-slate-950 dark:text-white"
      />
    </label>
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
  onEdit,
  onArchive,
  onMarkUpdated,
  manualResult,
  isChecking,
  canCheck,
  onRunCheck,
}: {
  device: InventoryDevice;
  onEdit: (device: InventoryDevice) => void;
  onArchive: (device: InventoryDevice) => void;
  onMarkUpdated: (device: InventoryDevice) => void;
  manualResult: CheckResult | undefined;
  isChecking: boolean;
  canCheck: boolean;
  onRunCheck: (device: InventoryDevice) => void;
}) {
  const hasUpdate = device.status === 'update_available' && device.latestVersion !== null;
  const latestVersion = device.latestVersion ?? 'Not checked';
  const resultStatus = manualResult?.status.replaceAll('_', ' ');
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
          {device.deviceType && (
            <p className="mt-1 text-xs font-medium text-indigo-600 dark:text-indigo-400">{device.deviceType}</p>
          )}
          {device.moduleId === null && (
            <span className="mt-2 inline-flex items-center gap-1 rounded-full border border-amber-200 bg-amber-50 px-2.5 py-0.5 text-xs font-semibold text-amber-700 dark:border-amber-500/30 dark:bg-amber-500/10 dark:text-amber-400">
              <Unlink size={12} />
              Unlinked
            </span>
          )}
          <p className="mt-1 text-xs text-slate-400 dark:text-slate-500">{statusLabel(device)}</p>
        </div>
        <div className="flex gap-2">
          <button
            type="button"
            onClick={() => onRunCheck(device)}
            disabled={!canCheck || isChecking}
            className="rounded-lg bg-indigo-50 px-3 py-2 text-xs font-medium text-indigo-700 transition-colors hover:bg-indigo-100 disabled:cursor-not-allowed disabled:opacity-60 dark:bg-indigo-500/10 dark:text-indigo-300 dark:hover:bg-indigo-500/20"
          >
            {isChecking ? 'Checking...' : 'Check Now'}
          </button>
          <button
            type="button"
            onClick={() => onEdit(device)}
            className="rounded-lg bg-slate-100 px-3 py-2 text-xs font-medium text-slate-600 transition-colors hover:bg-slate-200 dark:bg-slate-800 dark:text-slate-300 dark:hover:bg-slate-700"
          >
            Edit
          </button>
          <button
            type="button"
            onClick={() => onArchive(device)}
            className="rounded-lg bg-slate-100 px-3 py-2 text-xs font-medium text-slate-600 transition-colors hover:bg-slate-200 dark:bg-slate-800 dark:text-slate-300 dark:hover:bg-slate-700"
          >
            Archive
          </button>
        </div>
      </div>

      <div
        className={`flex items-center justify-between rounded-xl p-4 ${
          hasUpdate ? 'bg-rose-50 dark:bg-rose-500/10' : 'bg-slate-50 dark:bg-slate-800/50'
        }`}
      >
        <div className="flex flex-1 items-center gap-4">
          <VersionBlock label="Recorded" value={device.currentVersion} />
          {hasUpdate && <ArrowRight size={20} className="shrink-0 animate-pulse text-rose-500 dark:text-rose-400" />}
          <VersionBlock label="Latest" value={latestVersion} highlight={hasUpdate ? 'update' : device.status === 'up_to_date' ? 'ok' : undefined} />
        </div>

        {hasUpdate && (
          <div className="ml-4 shrink-0 border-l border-slate-200 pl-4 dark:border-slate-700">
            <button
              type="button"
              onClick={() => onMarkUpdated(device)}
              className="inline-flex items-center rounded-lg border border-emerald-200 bg-emerald-100 px-3 py-2 text-sm font-medium text-emerald-700 transition-colors hover:bg-emerald-200 dark:border-emerald-500/30 dark:bg-emerald-500/20 dark:text-emerald-400 dark:hover:bg-emerald-500/30"
            >
              <Check size={16} className="mr-1.5" />
              Sync Local
            </button>
          </div>
        )}
      </div>

      {manualResult !== undefined && (
        <div className="mt-3 rounded-xl border border-slate-200 bg-white px-4 py-3 text-sm dark:border-slate-700 dark:bg-slate-950/40">
          <div className="flex flex-wrap items-center justify-between gap-2">
            <span className="font-medium capitalize text-slate-700 dark:text-slate-200">Manual result: {resultStatus}</span>
            <span className="text-xs text-slate-500 dark:text-slate-400">
              {manualResult.lastCheckedAt === null ? 'No timestamp' : new Date(manualResult.lastCheckedAt).toLocaleString()}
            </span>
          </div>
          <div className="mt-2 grid grid-cols-2 gap-3 font-mono text-xs text-slate-600 dark:text-slate-300">
            <span>Stored: {manualResult.currentVersion}</span>
            <span>Latest: {manualResult.latestVersion ?? 'Unavailable'}</span>
          </div>
          {manualResult.detail !== null && <p className="mt-2 text-xs text-rose-600 dark:text-rose-300">{manualResult.detail}</p>}
        </div>
      )}
    </article>
  );
}

function statusLabel(device: InventoryDevice) {
  if (device.status === 'never_checked') {
    return 'Not checked yet';
  }
  if (device.status === 'check_failed') {
    return 'Last check failed';
  }
  if (device.lastCheckedAt !== null) {
    return `Last checked: ${new Date(device.lastCheckedAt).toLocaleString()}`;
  }
  return device.status === 'update_available' ? 'Update available' : 'Up to date';
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
      <p className={`font-mono text-lg font-semibold ${colorClass}`}>{value}</p>
    </div>
  );
}

function LogsPage({ logs: fallbackLogs }: { logs: LogEntry[] }) {
  const [activities, setActivities] = useState<ActivityLog[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [typeFilter, setTypeFilter] = useState<'all' | 'check' | 'notification'>('all');
  const [statusFilter, setStatusFilter] = useState<'all' | 'success' | 'failed'>('all');
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
        throw new TypeError('API response is not an array of activity logs');
      }
      setActivities(data);
    } catch (err) {
      console.warn('API logs fetch failed, using fallback logs', err);
      const mapped = fallbackLogs.map((log) => ({
        id: log.id,
        eventType: log.message.toLowerCase().includes('notification') ? ('notification' as const) : ('check' as const),
        status: log.level === 'ERROR' ? ('failed' as const) : ('success' as const),
        deviceName: log.message.includes('Sony') ? 'Sony A7IV' : null,
        moduleName: log.message.includes('Sony') ? 'sony-alpha' : null,
        message: log.message,
        traceback: log.level === 'ERROR' ? 'Traceback (mock):\n  File "scraper.py", line 42, in scrape\n    raise HTTPError("429 Too Many Requests")' : null,
        createdAt: new Date().toISOString(),
      }));
      setActivities(mapped);
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
        <PageHeader title="Activity Logs" description="System execution, background checks, and notification dispatches." />
        <button
          type="button"
          onClick={() => void fetchLogs()}
          disabled={isLoading}
          className="inline-flex h-10 items-center justify-center rounded-xl border border-slate-200 bg-white px-4 text-sm font-medium text-slate-700 shadow-sm transition hover:bg-slate-50 disabled:opacity-60 dark:border-slate-700 dark:bg-slate-800 dark:text-slate-200 dark:hover:bg-slate-700"
        >
          <RefreshCw size={16} className={`mr-2 ${isLoading ? 'animate-spin' : ''}`} />
          Refresh
        </button>
      </div>

      {/* Filter Toolbar */}
      <div className="flex flex-wrap items-center gap-4 rounded-2xl border border-slate-200 bg-white p-4 shadow-sm dark:border-slate-800 dark:bg-slate-900">
        <div className="flex items-center gap-2">
          <Filter size={16} className="text-slate-400" />
          <span className="text-sm font-medium text-slate-500 dark:text-slate-400">Filters</span>
        </div>

        <div className="flex flex-wrap gap-3">
          <div>
            <label htmlFor="log-type-filter" className="sr-only">Event Type</label>
            <select
              id="log-type-filter"
              value={typeFilter}
              onChange={(e) => setTypeFilter(e.target.value as 'all' | 'check' | 'notification')}
              className="h-9 rounded-lg border border-slate-200 bg-white px-3 text-xs text-slate-700 outline-none transition focus:border-indigo-500 dark:border-slate-700 dark:bg-slate-800 dark:text-slate-200"
            >
              <option value="all">All Types</option>
              <option value="check">Checks</option>
              <option value="notification">Notifications</option>
            </select>
          </div>

          <div>
            <label htmlFor="log-status-filter" className="sr-only">Status</label>
            <select
              id="log-status-filter"
              value={statusFilter}
              onChange={(e) => setStatusFilter(e.target.value as 'all' | 'success' | 'failed')}
              className="h-9 rounded-lg border border-slate-200 bg-white px-3 text-xs text-slate-700 outline-none transition focus:border-indigo-500 dark:border-slate-700 dark:bg-slate-800 dark:text-slate-200"
            >
              <option value="all">All Statuses</option>
              <option value="success">Success</option>
              <option value="failed">Failed</option>
            </select>
          </div>
        </div>
      </div>

      {error !== null && (
        <div className="rounded-xl border border-rose-200 bg-rose-50 px-4 py-3 text-sm text-rose-700 dark:border-rose-500/40 dark:bg-rose-500/10 dark:text-rose-300">
          {error}
        </div>
      )}

      <div className="overflow-hidden rounded-2xl border border-slate-200 bg-white dark:border-slate-800 dark:bg-slate-900 shadow-sm">
        <div className="overflow-x-auto">
          <table className="min-w-full divide-y divide-slate-200 dark:divide-slate-800">
            <thead className="bg-slate-50 dark:bg-slate-800/50">
              <tr>
                <TableHead>Time</TableHead>
                <TableHead>Type</TableHead>
                <TableHead>Status</TableHead>
                <TableHead>Asset</TableHead>
                <TableHead>Message</TableHead>
                <TableHead>Details</TableHead>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-200 text-sm dark:divide-slate-800">
              {isLoading && activities.length === 0 ? (
                <tr>
                  <td colSpan={6} className="px-6 py-10 text-center text-slate-500 dark:text-slate-400">
                    Loading activity history...
                  </td>
                </tr>
              ) : activities.length === 0 ? (
                <tr>
                  <td colSpan={6} className="px-6 py-10 text-center text-slate-500 dark:text-slate-400">
                    No activity logs match the selected filters.
                  </td>
                </tr>
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
                      <tr
                        className={`transition-colors hover:bg-slate-50 dark:hover:bg-slate-800/50 ${
                          showChevron ? 'cursor-pointer' : ''
                        }`}
                        onClick={() => showChevron && toggleExpand(log.id)}
                      >
                        <td className="whitespace-nowrap px-6 py-4 font-mono text-xs text-slate-500 dark:text-slate-400">
                          {formattedTime}
                        </td>
                        <td className="whitespace-nowrap px-6 py-4">
                          <span
                            className={`inline-flex rounded-md px-2 py-0.5 text-xs font-semibold uppercase tracking-wider ${
                              log.eventType === 'check'
                                ? 'bg-indigo-50 text-indigo-700 dark:bg-indigo-500/10 dark:text-indigo-400'
                                : 'bg-amber-50 text-amber-700 dark:bg-amber-500/10 dark:text-amber-400'
                            }`}
                          >
                            {log.eventType}
                          </span>
                        </td>
                        <td className="whitespace-nowrap px-6 py-4">
                          <span
                            className={`inline-flex rounded-md px-2.5 py-0.5 text-xs font-semibold ${
                              log.status === 'success'
                                ? 'bg-emerald-50 text-emerald-700 dark:bg-emerald-500/10 dark:text-emerald-400'
                                : 'bg-rose-50 text-rose-700 dark:bg-rose-500/10 dark:text-rose-400'
                            }`}
                          >
                            {log.status === 'success' ? 'Success' : 'Failed'}
                          </span>
                        </td>
                        <td className="px-6 py-4 text-slate-600 dark:text-slate-300 font-medium">
                          {log.deviceName || log.moduleName ? (
                            <div className="flex flex-col">
                              {log.deviceName && <span>{log.deviceName}</span>}
                              {log.moduleName && (
                                <span className="font-mono text-xs text-slate-400 dark:text-slate-500">
                                  {log.moduleName}
                                </span>
                              )}
                            </div>
                          ) : (
                            <span className="text-slate-400 dark:text-slate-500">—</span>
                          )}
                        </td>
                        <td className="px-6 py-4 text-slate-700 dark:text-slate-300 break-words max-w-md">
                          {log.message}
                        </td>
                        <td className="whitespace-nowrap px-6 py-4 text-slate-500">
                          {showChevron ? (
                            <button
                              type="button"
                              className="rounded-lg p-1 hover:bg-slate-100 dark:hover:bg-slate-800 text-slate-500 dark:text-slate-400"
                              onClick={(e) => {
                                e.stopPropagation();
                                toggleExpand(log.id);
                              }}
                              aria-label={isExpanded ? 'Collapse traceback' : 'Expand traceback'}
                            >
                              {isExpanded ? <ChevronUp size={16} /> : <ChevronDown size={16} />}
                            </button>
                          ) : (
                            <span className="text-slate-400 dark:text-slate-500">—</span>
                          )}
                        </td>
                      </tr>
                      {showChevron && isExpanded && (
                        <tr>
                          <td colSpan={6} className="bg-slate-50/50 dark:bg-slate-900/50 px-6 py-4">
                            <div className="rounded-xl border border-slate-200 dark:border-slate-800 bg-slate-950 p-4 relative shadow-inner">
                              <div className="flex items-center justify-between mb-2">
                                <span className="text-xs font-semibold text-rose-400 tracking-wide uppercase">
                                  Failure Traceback Stack Trace
                                </span>
                                <button
                                  type="button"
                                  onClick={(e) => {
                                    e.stopPropagation();
                                    void handleCopyTraceback(log.id, log.traceback || '');
                                  }}
                                  className="inline-flex h-7 items-center justify-center rounded-lg border border-slate-800 bg-slate-900 hover:bg-slate-800 text-slate-300 px-3 text-xs font-medium transition active:scale-95"
                                >
                                  <Copy size={12} className="mr-1.5" />
                                  {copiedId === log.id ? 'Copied!' : 'Copy'}
                                </button>
                              </div>
                              <pre className="font-mono text-xs text-slate-100 overflow-x-auto whitespace-pre-wrap leading-relaxed max-h-96 select-text selection:bg-rose-500/30 selection:text-white">
                                {log.traceback}
                              </pre>
                            </div>
                          </td>
                        </tr>
                      )}
                    </Fragment>
                  );
                })
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}

function ModulesPage({
  modules,
  isLoading,
  error,
  validation,
  selectedFile,
  onFileSelect,
  onUpload,
  onDelete,
}: {
  modules: InstalledModule[];
  isLoading: boolean;
  error: string | null;
  validation: ModuleValidationSummary | null;
  selectedFile: File | null;
  onFileSelect: (file: File | null) => void;
  onUpload: (event: FormEvent<HTMLFormElement>) => void;
  onDelete: (module: InstalledModule) => void;
}) {
  return (
    <div className="space-y-6">
      <div className="flex flex-col justify-between gap-4 lg:flex-row lg:items-start">
        <PageHeader title="Extension Modules" description="Manage Python scripts that scrape firmware data." />
        <form onSubmit={onUpload} className="flex flex-col gap-2 sm:flex-row sm:items-center">
          <label className="sr-only" htmlFor="moduleFile">
            Module file
          </label>
          <input
            id="moduleFile"
            name="moduleFile"
            type="file"
            accept=".py,text/x-python"
            onChange={(event) => onFileSelect(event.currentTarget.files?.[0] ?? null)}
            className="block w-full rounded-xl border border-slate-200 bg-white px-3 py-2 text-sm text-slate-700 shadow-sm file:mr-3 file:rounded-lg file:border-0 file:bg-slate-100 file:px-3 file:py-1.5 file:text-sm file:font-medium file:text-slate-700 dark:border-slate-700 dark:bg-slate-800 dark:text-slate-200 dark:file:bg-slate-700 dark:file:text-slate-200 sm:w-72"
          />
          {selectedFile !== null && <span className="text-xs text-slate-500 dark:text-slate-400">{selectedFile.name}</span>}
          <button
            type="submit"
            className="inline-flex items-center justify-center rounded-xl border border-slate-200 bg-white px-4 py-2 text-sm font-medium text-slate-700 shadow-sm transition hover:bg-slate-50 dark:border-slate-700 dark:bg-slate-800 dark:text-slate-200 dark:hover:bg-slate-700"
          >
            <Plus size={16} className="mr-2" />
            Upload
          </button>
        </form>
      </div>

      <div className="rounded-2xl border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-800 dark:border-amber-500/30 dark:bg-amber-500/10 dark:text-amber-200">
        Modules are trusted Python code and run unsandboxed with application privileges.
      </div>

      {error !== null && (
        <div className="rounded-xl border border-rose-200 bg-rose-50 px-4 py-3 text-sm text-rose-700 dark:border-rose-500/40 dark:bg-rose-500/10 dark:text-rose-300">
          {error}
        </div>
      )}

      {validation !== null && <ValidationSummary summary={validation} />}

      {isLoading && <p className="text-sm text-slate-500 dark:text-slate-400">Loading modules...</p>}

      {!isLoading && modules.length === 0 && (
        <div className="rounded-2xl border border-dashed border-slate-300 p-8 text-center text-sm text-slate-500 dark:border-slate-700 dark:text-slate-400">
          No modules installed yet.
        </div>
      )}

      <div className="grid grid-cols-1 gap-6 md:grid-cols-2 lg:grid-cols-3">
        {modules.map((module) => (
          <article
            key={module.moduleId}
            className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm dark:border-slate-800 dark:bg-slate-900"
          >
            <div className="mb-4 flex items-start justify-between">
              <div className="rounded-xl bg-indigo-50 p-3 text-indigo-600 dark:bg-slate-800 dark:text-indigo-400">
                <TerminalSquare size={24} />
              </div>
              <ModuleStatus status={module.validationStatus} />
            </div>
            <h3 className="truncate font-mono text-lg font-bold">{module.displayName}</h3>
            <p className="mt-1 text-sm text-slate-500 dark:text-slate-400">{module.moduleId}</p>
            <p className="mb-4 mt-1 text-sm text-slate-500 dark:text-slate-400">Version {module.version ?? 'unknown'}</p>
            <div className="flex items-center justify-between border-t border-slate-100 pt-4 dark:border-slate-800">
              <span className="flex items-center text-sm font-medium text-slate-600 dark:text-slate-400">
                <Server size={14} className="mr-1.5" />
                {module.lastValidatedAt === null ? 'Not validated' : `Validated ${new Date(module.lastValidatedAt).toLocaleString()}`}
              </span>
              <button
                type="button"
                onClick={() => onDelete(module)}
                className="text-sm font-medium text-rose-600 hover:text-rose-700 dark:text-rose-400 dark:hover:text-rose-300"
              >
                Delete
              </button>
            </div>
          </article>
        ))}
      </div>
    </div>
  );
}

function ValidationSummary({ summary }: { summary: ModuleValidationSummary }) {
  return (
    <div className="rounded-2xl border border-rose-200 bg-white p-4 shadow-sm dark:border-rose-500/30 dark:bg-slate-900">
      <h3 className="text-sm font-semibold text-rose-700 dark:text-rose-300">Validation feedback</h3>
      <div className="mt-3 grid gap-3 md:grid-cols-2">
        {[summary.static_phase, summary.runtime_phase].map((phase) => (
          <div key={phase.phase} className="rounded-xl bg-slate-50 p-3 text-sm dark:bg-slate-800/70">
            <p className="font-semibold capitalize text-slate-900 dark:text-slate-100">
              {phase.phase} {phase.status}
            </p>
            {phase.findings.length === 0 ? (
              <p className="mt-1 text-slate-500 dark:text-slate-400">No findings.</p>
            ) : (
              <ul className="mt-2 space-y-1 text-slate-600 dark:text-slate-300">
                {phase.findings.map((finding) => (
                  <li key={`${phase.phase}-${finding.code}`}>{finding.message}</li>
                ))}
              </ul>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}

function SettingsPage() {
  const [smtpEnabled, setSmtpEnabled] = useState(false);
  const [smtpHost, setSmtpHost] = useState('');
  const [smtpPort, setSmtpPort] = useState('587');
  const [smtpUsername, setSmtpUsername] = useState('');
  const [smtpPassword, setSmtpPassword] = useState('');
  const [smtpUseTls, setSmtpUseTls] = useState(true);
  const [mailFrom, setMailFrom] = useState('');
  const [mailTo, setMailTo] = useState('');

  const [gotifyEnabled, setGotifyEnabled] = useState(false);
  const [gotifyUrl, setGotifyUrl] = useState('');
  const [gotifyToken, setGotifyToken] = useState('');

  const [isLoading, setIsLoading] = useState(true);
  const [statusMsg, setStatusMsg] = useState<{ type: 'success' | 'error'; message: string } | null>(null);
  const [isSmtpSaving, setIsSmtpSaving] = useState(false);
  const [isSmtpTesting, setIsSmtpTesting] = useState(false);
  const [isGotifySaving, setIsGotifySaving] = useState(false);
  const [isGotifyTesting, setIsGotifyTesting] = useState(false);

  useEffect(() => {
    async function loadData() {
      try {
        const channels = await listChannels();
        const smtp = channels.find((c) => c.type === 'smtp');
        if (smtp) {
          setSmtpEnabled(smtp.enabled);
          setSmtpHost(String(smtp.config.smtpHost || smtp.config.smtp_host || ''));
          setSmtpPort(String(smtp.config.smtpPort || smtp.config.smtp_port || '587'));
          setSmtpUsername(String(smtp.config.smtpUsername || smtp.config.smtp_username || ''));
          setSmtpPassword(String(smtp.config.smtpPassword || smtp.config.smtp_password || ''));
          setSmtpUseTls(
            smtp.config.smtpUseTls !== undefined
              ? (smtp.config.smtpUseTls as boolean)
              : smtp.config.smtp_use_tls !== undefined
              ? (smtp.config.smtp_use_tls as boolean)
              : true
          );
          setMailFrom(String(smtp.config.mailFrom || smtp.config.mail_from || ''));
          setMailTo(String(smtp.config.mailTo || smtp.config.mail_to || ''));
        }
        const gotify = channels.find((c) => c.type === 'gotify');
        if (gotify) {
          setGotifyEnabled(gotify.enabled);
          setGotifyUrl(String(gotify.config.gotifyUrl || gotify.config.gotify_url || ''));
          setGotifyToken(String(gotify.config.gotifyToken || gotify.config.gotify_token || ''));
        }
      } catch (err) {
        console.error('Failed to load settings', err);
      } finally {
        setIsLoading(false);
      }
    }
    loadData();
  }, []);

  async function handleSaveSmtp() {
    setIsSmtpSaving(true);
    setStatusMsg(null);
    try {
      await configureChannel('smtp', {
        enabled: smtpEnabled,
        config: {
          smtpHost,
          smtpPort: parseInt(smtpPort, 10),
          smtpUsername,
          smtpPassword,
          smtpUseTls,
          mailFrom,
          mailTo,
        },
      });
      setStatusMsg({ type: 'success', message: 'SMTP configurations saved successfully!' });
    } catch (err) {
      setStatusMsg({
        type: 'error',
        message: err instanceof Error ? err.message : 'Failed to save SMTP configurations',
      });
    } finally {
      setIsSmtpSaving(false);
    }
  }

  async function handleTestSmtp() {
    setIsSmtpTesting(true);
    setStatusMsg(null);
    try {
      const resp = await testChannel('smtp', {
        config: {
          smtpHost,
          smtpPort: parseInt(smtpPort, 10),
          smtpUsername,
          smtpPassword,
          smtpUseTls,
          mailFrom,
          mailTo,
        },
      });
      setStatusMsg({ type: 'success', message: resp.detail || 'Test email dispatched successfully!' });
    } catch (err) {
      setStatusMsg({
        type: 'error',
        message: err instanceof Error ? err.message : 'Test email failed to send',
      });
    } finally {
      setIsSmtpTesting(false);
    }
  }

  async function handleSaveGotify() {
    setIsGotifySaving(true);
    setStatusMsg(null);
    try {
      await configureChannel('gotify', {
        enabled: gotifyEnabled,
        config: {
          gotifyUrl,
          gotifyToken,
        },
      });
      setStatusMsg({ type: 'success', message: 'Gotify configurations saved successfully!' });
    } catch (err) {
      setStatusMsg({
        type: 'error',
        message: err instanceof Error ? err.message : 'Failed to save Gotify configurations',
      });
    } finally {
      setIsGotifySaving(false);
    }
  }

  async function handleTestGotify() {
    setIsGotifyTesting(true);
    setStatusMsg(null);
    try {
      const resp = await testChannel('gotify', {
        config: {
          gotifyUrl,
          gotifyToken,
        },
      });
      setStatusMsg({ type: 'success', message: resp.detail || 'Test push alert dispatched successfully!' });
    } catch (err) {
      setStatusMsg({
        type: 'error',
        message: err instanceof Error ? err.message : 'Test push alert failed to send',
      });
    } finally {
      setIsGotifyTesting(false);
    }
  }

  if (isLoading) {
    return (
      <div className="flex justify-center py-20">
        <p className="text-sm text-slate-500 dark:text-slate-400">Loading settings...</p>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <PageHeader
        title="Settings Configuration"
        description="Configure notification dispatchers, SMTP parameters, and Gotify push alerts."
      />

      {statusMsg !== null && (
        <div
          className={`rounded-xl border px-4 py-3 text-sm flex items-center justify-between transition-all ${
            statusMsg.type === 'success'
              ? 'border-emerald-200 bg-emerald-50 text-emerald-800 dark:border-emerald-500/30 dark:bg-emerald-500/10 dark:text-emerald-200'
              : 'border-rose-200 bg-rose-50 text-rose-700 dark:border-rose-500/40 dark:bg-rose-500/10 dark:text-rose-300'
          }`}
        >
          <span>{statusMsg.message}</span>
          <button type="button" onClick={() => setStatusMsg(null)} className="ml-3 font-bold hover:opacity-85">
            ✕
          </button>
        </div>
      )}

      <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
        {/* Email/SMTP Config */}
        <section className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm dark:border-slate-800 dark:bg-slate-900 flex flex-col justify-between">
          <div className="space-y-4">
            <div className="flex items-center justify-between border-b border-slate-100 pb-3 dark:border-slate-800">
              <h3 className="flex items-center text-md font-bold text-slate-800 dark:text-slate-100">
                <Mail className="mr-2 text-indigo-500" size={18} />
                Email / SMTP Channel
              </h3>
              <label className="flex items-center gap-2 cursor-pointer">
                <input
                  type="checkbox"
                  checked={smtpEnabled}
                  onChange={(e) => setSmtpEnabled(e.target.checked)}
                  className="rounded border-slate-300 text-indigo-600 focus:ring-indigo-500 dark:border-slate-700 dark:bg-slate-950"
                />
                <span className="text-xs font-semibold text-slate-500 dark:text-slate-400">Enabled</span>
              </label>
            </div>

            <div className="grid grid-cols-3 gap-3">
              <div className="col-span-2">
                <label className="block text-xs font-medium text-slate-500 dark:text-slate-400">
                  SMTP Host
                  <input
                    type="text"
                    value={smtpHost}
                    onChange={(e) => setSmtpHost(e.target.value)}
                    placeholder="smtp.gmail.com"
                    className="mt-1 h-9 w-full rounded-xl border border-slate-200 bg-white px-3 text-xs text-slate-900 outline-none transition focus:border-indigo-500 dark:border-slate-700 dark:bg-slate-950 dark:text-white"
                  />
                </label>
              </div>
              <div>
                <label className="block text-xs font-medium text-slate-500 dark:text-slate-400">
                  Port
                  <input
                    type="text"
                    value={smtpPort}
                    onChange={(e) => setSmtpPort(e.target.value)}
                    placeholder="587"
                    className="mt-1 h-9 w-full rounded-xl border border-slate-200 bg-white px-3 text-xs text-slate-900 outline-none transition focus:border-indigo-500 dark:border-slate-700 dark:bg-slate-950 dark:text-white"
                  />
                </label>
              </div>
            </div>

            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="block text-xs font-medium text-slate-500 dark:text-slate-400">
                  Username
                  <input
                    type="text"
                    value={smtpUsername}
                    onChange={(e) => setSmtpUsername(e.target.value)}
                    placeholder="user@gmail.com"
                    className="mt-1 h-9 w-full rounded-xl border border-slate-200 bg-white px-3 text-xs text-slate-900 outline-none transition focus:border-indigo-500 dark:border-slate-700 dark:bg-slate-950 dark:text-white"
                  />
                </label>
              </div>
              <div>
                <label className="block text-xs font-medium text-slate-500 dark:text-slate-400">
                  Password
                  <input
                    type="password"
                    value={smtpPassword}
                    onChange={(e) => setSmtpPassword(e.target.value)}
                    placeholder={smtpPassword === '•' ? '••••••••' : 'Enter Password'}
                    className="mt-1 h-9 w-full rounded-xl border border-slate-200 bg-white px-3 text-xs text-slate-900 outline-none transition focus:border-indigo-500 dark:border-slate-700 dark:bg-slate-950 dark:text-white"
                  />
                </label>
              </div>
            </div>

            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="block text-xs font-medium text-slate-500 dark:text-slate-400">
                  Mail From
                  <input
                    type="text"
                    value={mailFrom}
                    onChange={(e) => setMailFrom(e.target.value)}
                    placeholder="binocular@homelab.lan"
                    className="mt-1 h-9 w-full rounded-xl border border-slate-200 bg-white px-3 text-xs text-slate-900 outline-none transition focus:border-indigo-500 dark:border-slate-700 dark:bg-slate-950 dark:text-white"
                  />
                </label>
              </div>
              <div>
                <label className="block text-xs font-medium text-slate-500 dark:text-slate-400">
                  Mail To
                  <input
                    type="text"
                    value={mailTo}
                    onChange={(e) => setMailTo(e.target.value)}
                    placeholder="owner@homelab.lan"
                    className="mt-1 h-9 w-full rounded-xl border border-slate-200 bg-white px-3 text-xs text-slate-900 outline-none transition focus:border-indigo-500 dark:border-slate-700 dark:bg-slate-950 dark:text-white"
                  />
                </label>
              </div>
            </div>

            <div className="pt-2">
              <label className="flex items-center gap-2 cursor-pointer">
                <input
                  type="checkbox"
                  checked={smtpUseTls}
                  onChange={(e) => setSmtpUseTls(e.target.checked)}
                  className="rounded border-slate-300 text-indigo-600 focus:ring-indigo-500 dark:border-slate-700 dark:bg-slate-950"
                />
                <span className="text-xs text-slate-600 dark:text-slate-300">Use Secure TLS / STARTTLS</span>
              </label>
            </div>
          </div>

          <div className="mt-6 flex items-center justify-end gap-2 border-t border-slate-100 pt-4 dark:border-slate-800">
            <button
              type="button"
              onClick={handleTestSmtp}
              disabled={isSmtpTesting || isSmtpSaving}
              className="inline-flex h-9 items-center justify-center rounded-xl border border-slate-200 bg-white px-4 text-xs font-medium text-slate-700 shadow-sm transition hover:bg-slate-50 disabled:opacity-60 dark:border-slate-700 dark:bg-slate-800 dark:text-slate-200 dark:hover:bg-slate-700"
            >
              {isSmtpTesting ? 'Sending Test...' : 'Send Test'}
            </button>
            <button
              type="button"
              onClick={handleSaveSmtp}
              disabled={isSmtpTesting || isSmtpSaving}
              className="inline-flex h-9 items-center justify-center rounded-xl bg-indigo-600 px-4 text-xs font-medium text-white shadow-sm transition hover:bg-indigo-700 disabled:opacity-60 dark:hover:bg-indigo-500"
            >
              {isSmtpSaving ? 'Saving...' : 'Save Settings'}
            </button>
          </div>
        </section>

        {/* Gotify Config */}
        <section className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm dark:border-slate-800 dark:bg-slate-900 flex flex-col justify-between">
          <div className="space-y-4">
            <div className="flex items-center justify-between border-b border-slate-100 pb-3 dark:border-slate-800">
              <h3 className="flex items-center text-md font-bold text-slate-800 dark:text-slate-100">
                <Send className="mr-2 text-indigo-500" size={18} />
                Gotify Push Channel
              </h3>
              <label className="flex items-center gap-2 cursor-pointer">
                <input
                  type="checkbox"
                  checked={gotifyEnabled}
                  onChange={(e) => setGotifyEnabled(e.target.checked)}
                  className="rounded border-slate-300 text-indigo-600 focus:ring-indigo-500 dark:border-slate-700 dark:bg-slate-950"
                />
                <span className="text-xs font-semibold text-slate-500 dark:text-slate-400">Enabled</span>
              </label>
            </div>

            <div>
              <label className="block text-xs font-medium text-slate-500 dark:text-slate-400">
                Gotify Server URL
                <input
                  type="text"
                  value={gotifyUrl}
                  onChange={(e) => setGotifyUrl(e.target.value)}
                  placeholder="https://gotify.homelab.lan"
                  className="mt-1 h-9 w-full rounded-xl border border-slate-200 bg-white px-3 text-xs text-slate-900 outline-none transition focus:border-indigo-500 dark:border-slate-700 dark:bg-slate-950 dark:text-white"
                />
              </label>
            </div>

            <div>
              <label className="block text-xs font-medium text-slate-500 dark:text-slate-400">
                Application Token
                <input
                  type="password"
                  value={gotifyToken}
                  onChange={(e) => setGotifyToken(e.target.value)}
                  placeholder={gotifyToken === '•' ? '••••••••' : 'Enter Application Token'}
                  className="mt-1 h-9 w-full rounded-xl border border-slate-200 bg-white px-3 text-xs text-slate-900 outline-none transition focus:border-indigo-500 dark:border-slate-700 dark:bg-slate-950 dark:text-white"
                />
              </label>
            </div>
          </div>

          <div className="mt-6 flex items-center justify-end gap-2 border-t border-slate-100 pt-4 dark:border-slate-800">
            <button
              type="button"
              onClick={handleTestGotify}
              disabled={isGotifyTesting || isGotifySaving}
              className="inline-flex h-9 items-center justify-center rounded-xl border border-slate-200 bg-white px-4 text-xs font-medium text-slate-700 shadow-sm transition hover:bg-slate-50 disabled:opacity-60 dark:border-slate-700 dark:bg-slate-800 dark:text-slate-200 dark:hover:bg-slate-700"
            >
              {isGotifyTesting ? 'Sending Test...' : 'Send Test'}
            </button>
            <button
              type="button"
              onClick={handleSaveGotify}
              disabled={isGotifyTesting || isGotifySaving}
              className="inline-flex h-9 items-center justify-center rounded-xl bg-indigo-600 px-4 text-xs font-medium text-white shadow-sm transition hover:bg-indigo-700 disabled:opacity-60 dark:hover:bg-indigo-500"
            >
              {isGotifySaving ? 'Saving...' : 'Save Settings'}
            </button>
          </div>
        </section>
      </div>
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


function ModuleStatus({ status }: { status: InstalledModule['validationStatus'] }) {
  const className =
    status === 'valid'
      ? 'border-emerald-200 bg-emerald-50 text-emerald-700 dark:border-emerald-500/20 dark:bg-emerald-500/10 dark:text-emerald-400'
      : status === 'invalid'
        ? 'border-rose-200 bg-rose-50 text-rose-700 dark:border-rose-500/20 dark:bg-rose-500/10 dark:text-rose-400'
        : 'border-slate-200 bg-slate-100 text-slate-500 dark:border-slate-700 dark:bg-slate-800 dark:text-slate-400';
  return <span className={`rounded-full border px-2.5 py-1 text-xs font-medium ${className}`}>{status}</span>;
}
