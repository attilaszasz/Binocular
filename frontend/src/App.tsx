import {
  AlertCircle,
  ArrowRight,
  Binoculars,
  Check,
  CheckCircle2,
  Clock,
  Loader2,
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
import { FormEvent, Fragment, useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { NavLink, Navigate, Route, Routes, useLocation } from 'react-router-dom';
import { useMutation, useQueryClient } from '@tanstack/react-query';

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
import { updateSchedule } from './api/schedules';
import { FrequencyEditor } from './components/FrequencyEditor';
import { useTheme } from './theme/useTheme';

type LogEntry = {
  id: number;
  time: string;
  level: 'INFO' | 'WARN' | 'ERROR';
  message: string;
};

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
  const [manualResults, setManualResults] = useState<Record<number, CheckResult>>({});
  const [manualError, setManualError] = useState<string | null>(null);
  const [checkingDeviceIds, setCheckingDeviceIds] = useState<Set<number>>(new Set());
  const [isBulkChecking, setIsBulkChecking] = useState(false);
  const [bulkSummary, setBulkSummary] = useState<{ total: number; succeeded: number; failed: number } | null>(null);
  const [isModulesLoading, setIsModulesLoading] = useState(false);
  const [formValues, setFormValues] = useState<DeviceInput>(emptyDeviceInput);
  const [editingDevice, setEditingDevice] = useState<InventoryDevice | null>(null);
  const [showForm, setShowForm] = useState(false);
  const [logs, setLogs] = useState<LogEntry[]>([]);
  const [isMobileMenuOpen, setIsMobileMenuOpen] = useState(false);
  const menuButtonRef = useRef<HTMLButtonElement>(null);
  const { mode, toggleMode } = useTheme();
  const location = useLocation();

  const closeMobileMenu = useCallback(() => {
    setIsMobileMenuOpen(false);
    // Return focus to hamburger trigger on next frame
    requestAnimationFrame(() => {
      menuButtonRef.current?.focus();
    });
  }, []);

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
    } catch {
      setModuleError('Failed to load');
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
    setShowForm(false);
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
    const moduleId = device.moduleId;
    if (!moduleId) {
      setManualError('This device is not linked to a module');
      return;
    }
    setManualError(null);
    setCheckingDeviceIds((current) => new Set(current).add(device.id));
    try {
      const result = await runDeviceCheck(device.id, { moduleId });
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
    if (devices.length === 0) {
      setManualError('No devices to check');
      return;
    }
    setManualError(null);
    setBulkSummary(null);
    setIsBulkChecking(true);
    try {
      const response = await runAllChecks({});
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
    <div className="min-h-screen bg-surface text-ink motion-safe:transition-colors">
      {isMobileMenuOpen && (
        <button
          type="button"
          className="fixed inset-0 z-40 bg-slate-950/60 md:hidden"
           aria-label="Close navigation overlay"
           onClick={closeMobileMenu}
        />
      )}

      <aside
        className={`fixed inset-y-0 left-0 z-50 flex w-64 transform flex-col border-r border-panel bg-panel motion-safe:transition-transform motion-safe:duration-300 motion-safe:ease-in-out md:translate-x-0 ${
          isMobileMenuOpen ? 'translate-x-0' : '-translate-x-full'
        }`}
      >
        <div className="flex h-16 shrink-0 items-center justify-between border-b border-inherit px-6">
          <Brand />
          <button
            type="button"
            className="rounded-lg p-2 text-muted hover:text-ink-hover md:hidden"
            onClick={closeMobileMenu}
            aria-label="Close navigation"
          >
            <X size={20} />
          </button>
        </div>
        <nav className="flex-1 overflow-y-auto space-y-1.5 p-4" aria-label="Primary navigation">
          {navItems.map((item) => (
            <NavItem key={item.to} item={item} onNavigate={closeMobileMenu} />
          ))}
        </nav>
      </aside>

      <main className="min-h-screen motion-safe:transition-all motion-safe:duration-300 motion-safe:ease-in-out md:ml-64">
        <header className="sticky top-0 z-30 flex h-16 items-center justify-between border-b border-panel bg-panel/85 px-4 backdrop-blur-sm sm:px-6 lg:px-8">
          <div className="flex items-center">
            <button
              type="button"
              ref={menuButtonRef}
              className="mr-4 rounded-lg p-2 text-muted hover:bg-panel-hover hover:text-ink-hover md:hidden"
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
            className="rounded-full p-2 text-muted motion-safe:transition-colors hover:bg-panel-hover hover:text-ink-hover"
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
                  manualResults={manualResults}
                  manualError={manualError}
                  bulkSummary={bulkSummary}
                  checkingDeviceIds={checkingDeviceIds}
                  isBulkChecking={isBulkChecking}
                  showForm={showForm}
                  onShowForm={setShowForm}
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
                  onRetry={refreshModules}
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
      <div className="rounded-lg bg-accent/10 p-1.5 text-accent">
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
        `flex w-full items-center gap-3 rounded-xl px-4 py-3 text-sm font-medium motion-safe:transition-all motion-safe:duration-200 ${
          isActive
            ? 'bg-accent/10 text-accent'
            : 'text-muted hover:bg-panel-hover hover:text-ink-hover'
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
  showForm,
  onFormChange,
  onSubmit,
  onCancelEdit,
  onShowForm,
  onEdit,
  onArchive,
  onMarkUpdated,
  modules,
  manualResults,
  manualError,
  bulkSummary,
  checkingDeviceIds,
  isBulkChecking,
  onRunDeviceCheck,
  onRunAllChecks,
}: {
  groups: DeviceGroup[];
  stats: { total: number; updates: number; upToDate: number };
  isLoading: boolean;
  error: string | null;
  formValues: DeviceInput;
  editingDevice: InventoryDevice | null;
  showForm: boolean;
  onFormChange: (field: keyof DeviceInput, value: string) => void;
  onSubmit: (event: FormEvent<HTMLFormElement>) => void;
  onCancelEdit: () => void;
  onShowForm: (show: boolean) => void;
  onEdit: (device: InventoryDevice) => void;
  onArchive: (device: InventoryDevice) => void;
  onMarkUpdated: (device: InventoryDevice) => void;
  modules: InstalledModule[];
  manualResults: Record<number, CheckResult>;
  manualError: string | null;
  bulkSummary: { total: number; succeeded: number; failed: number } | null;
  checkingDeviceIds: Set<number>;
  isBulkChecking: boolean;
  onRunDeviceCheck: (device: InventoryDevice) => void;
  onRunAllChecks: () => void;
}) {
  const devices = useMemo(() => groups.flatMap((group) => group.devices), [groups]);
  const canCheckAll = devices.some((d) => d.moduleId !== null);

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
          <p className="mt-1 text-sm text-muted">
            Manage your hardware and monitor for firmware updates.
          </p>
        </div>
        <div className="flex flex-wrap items-center gap-3">
          <button
            type="button"
            onClick={onRunAllChecks}
            disabled={!canCheckAll || isBulkChecking}
            className="inline-flex h-10 items-center rounded-xl border border-muted bg-panel px-4 text-sm font-medium text-ink shadow-sm motion-safe:transition hover:bg-panel-hover disabled:cursor-not-allowed disabled:opacity-60"
          >
            <Binoculars size={16} className="mr-2" />
            {isBulkChecking ? 'Checking...' : 'Check All'}
          </button>
          <button
            type="button"
            onClick={() => onShowForm(true)}
            className="inline-flex items-center rounded-xl border border-muted bg-panel px-4 py-2 text-sm font-medium text-ink shadow-sm motion-safe:transition hover:bg-panel-hover"
          >
            <Plus size={16} className="mr-2" />
            Add Device
          </button>
        </div>
      </div>

      {(showForm || editingDevice !== null) && (
        <form
          id="inventory-form"
          onSubmit={onSubmit}
          className="grid gap-3 rounded-2xl border border-panel bg-panel p-4 shadow-sm md:grid-cols-5"
        >
        <InventoryInput label="Name" value={formValues.name} onChange={(value) => onFormChange('name', value)} />
        <InventoryInput label="Model" value={formValues.model} onChange={(value) => onFormChange('model', value)} />
        <label className="block text-sm font-medium text-muted">
          <span>Module</span>
          {modules.length > 0 ? (
            <select
              value={formValues.moduleId}
              onChange={(event) => onFormChange('moduleId', event.target.value)}
              className="mt-1 h-10 w-full rounded-xl border border-muted bg-panel px-3 text-sm text-ink outline-none motion-safe:transition focus:border-accent focus:ring-2 focus:ring-accent-focus/20"
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
                className="mt-1 h-10 w-full cursor-not-allowed rounded-xl border border-muted bg-panel px-3 text-sm text-ink opacity-60 outline-none"
              >
                <option value="">Select a module...</option>
              </select>
              <p className="mt-1 text-xs text-muted">Install and validate a module first</p>
            </>
          )}
        </label>
        <InventoryInput
          label="Current version"
          value={formValues.currentVersion}
          onChange={(value) => onFormChange('currentVersion', value)}
        />
        <div className="flex items-end gap-2">
          <button
            type="submit"
            className="inline-flex h-10 flex-1 items-center justify-center rounded-xl bg-accent px-4 text-sm font-medium text-white shadow-sm motion-safe:transition hover:bg-accent-hover"
          >
            {editingDevice === null ? 'Add' : 'Save'}
          </button>
          {editingDevice !== null ? (
            <button
              type="button"
              onClick={onCancelEdit}
              className="h-10 rounded-xl border border-muted px-3 text-sm text-ink"
            >
              Cancel
            </button>
          ) : (
            <button
              type="button"
              onClick={() => onShowForm(false)}
              className="h-10 rounded-xl border border-muted px-3 text-sm text-ink"
            >
              Cancel
            </button>
          )}
        </div>
      </form>
      )}

      {error !== null && (
        <div className="rounded-xl border border-error-border bg-error-bg px-4 py-3 text-sm text-error">
          {error}
        </div>
      )}

      {manualError !== null && (
        <div className="rounded-xl border border-error-border bg-error-bg px-4 py-3 text-sm text-error">
          {manualError}
        </div>
      )}

      {bulkSummary !== null && (
        <div className="rounded-xl border border-success-border bg-success-bg px-4 py-3 text-sm text-success">
          Manual bulk check complete: {bulkSummary.succeeded}/{bulkSummary.total} succeeded, {bulkSummary.failed} failed.
        </div>
      )}

      <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
        <StatCard label="Total Devices" value={stats.total} icon={Server} tone="indigo" />
        <StatCard label="Updates Available" value={stats.updates} icon={AlertCircle} tone="rose" />
        <StatCard label="Up to Date" value={stats.upToDate} icon={CheckCircle2} tone="emerald" />
      </div>

      {isLoading && <p className="text-sm text-muted">Loading inventory...</p>}

      {!isLoading && groups.length === 0 && (
        <div className="rounded-2xl border border-dashed border-muted p-8 text-center text-sm text-muted">
          No devices tracked yet.
        </div>
      )}

      {sortedGroups.map((group) => (
        <section key={group.moduleId ?? 'ungrouped'} className="space-y-4">
          <h3 className="flex items-center text-sm font-semibold uppercase tracking-wider text-muted">
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
                canCheck={device.moduleId !== null}
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
    <label className="block text-sm font-medium text-muted">
      <span>{label}</span>
      <input
        required
        value={value}
        onChange={(event) => onChange(event.target.value)}
        className="mt-1 h-10 w-full rounded-xl border border-muted bg-panel px-3 text-sm text-ink outline-none motion-safe:transition focus:border-accent focus:ring-2 focus:ring-accent-focus/20"
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
    indigo: 'bg-accent/10 text-accent',
    rose: 'bg-error-bg text-error',
    emerald: 'bg-success-bg text-success',
  }[tone];

  return (
    <div className="rounded-2xl border border-panel bg-panel p-5 shadow-sm">
      <div className="flex items-center justify-between">
        <div>
          <p className="text-sm font-medium text-muted">{label}</p>
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
      className={`rounded-2xl border bg-panel p-5 shadow-sm motion-safe:transition-all motion-safe:duration-200 ${
        hasUpdate
          ? 'border-error-border ring-1 ring-error-border dark:ring-0 dark:shadow-[0_0_15px_rgb(var(--color-error-border)/0.12)]'
          : 'border-panel'
      }`}
    >
      <div className="mb-4 flex items-start justify-between gap-4">
        <div>
          <h4 className="text-lg font-bold text-ink truncate max-w-full">{device.name}</h4>
          <p className="mt-1 font-mono text-xs font-semibold text-muted truncate max-w-full">{device.model}</p>
          {device.deviceType && (
            <p className="mt-1 text-xs font-medium text-accent">{device.deviceType}</p>
          )}
          {device.moduleId === null && (
            <span className="mt-2 inline-flex items-center gap-1 rounded-full border border-warning-border bg-warning-bg px-2.5 py-0.5 text-xs font-semibold text-warning">
              <Unlink size={12} />
              Unlinked
            </span>
          )}
          <p className="mt-1 text-xs text-muted">{statusLabel(device)}</p>
        </div>
        <div className="flex gap-2">
          <button
            type="button"
            onClick={() => onRunCheck(device)}
            disabled={!canCheck || isChecking}
            className="rounded-lg bg-accent/10 px-3 py-2 text-xs font-medium text-accent motion-safe:transition-colors hover:bg-accent/20 disabled:cursor-not-allowed disabled:opacity-60"
          >
            {isChecking ? 'Checking...' : 'Check Now'}
          </button>
          <button
            type="button"
            onClick={() => onEdit(device)}
            className="rounded-lg bg-panel-hover px-3 py-2 text-xs font-medium text-muted motion-safe:transition-colors hover:bg-surface-hover"
          >
            Edit
          </button>
          <button
            type="button"
            onClick={() => onArchive(device)}
            className="rounded-lg bg-panel-hover px-3 py-2 text-xs font-medium text-muted motion-safe:transition-colors hover:bg-surface-hover"
          >
            Archive
          </button>
        </div>
      </div>

      <div
        className={`flex items-center justify-between rounded-xl p-4 ${
          hasUpdate ? 'bg-error-bg' : 'bg-surface'
        }`}
      >
        <div className="flex flex-1 items-center gap-4">
          <VersionBlock label="Recorded" value={device.currentVersion} />
          {hasUpdate && <ArrowRight size={20} className="shrink-0 motion-safe:animate-pulse text-error" />}
          <VersionBlock label="Latest" value={latestVersion} highlight={hasUpdate ? 'update' : device.status === 'up_to_date' ? 'ok' : undefined} />
        </div>

        {hasUpdate && (
          <div className="ml-4 shrink-0 border-l border-muted pl-4">
            <button
              type="button"
              onClick={() => onMarkUpdated(device)}
              className="inline-flex items-center rounded-lg border border-success-border bg-success-bg px-3 py-2 text-sm font-medium text-success motion-safe:transition-colors hover:bg-success-border"
            >
              <Check size={16} className="mr-1.5" />
              Sync Local
            </button>
          </div>
        )}
      </div>

      {manualResult !== undefined && (
        <div className="mt-3 rounded-xl border border-muted bg-panel px-4 py-3 text-sm">
          <div className="flex flex-wrap items-center justify-between gap-2">
            <span className="font-medium capitalize text-ink">Manual result: {resultStatus}</span>
            <span className="text-xs text-muted">
              {manualResult.lastCheckedAt === null ? 'No timestamp' : new Date(manualResult.lastCheckedAt).toLocaleString()}
            </span>
          </div>
          <div className="mt-2 grid grid-cols-2 gap-3 font-mono text-xs text-muted">
            <span>Stored: {manualResult.currentVersion}</span>
            <span>Latest: {manualResult.latestVersion ?? 'Unavailable'}</span>
          </div>
          {manualResult.detail !== null && <p className="mt-2 text-xs text-error">{manualResult.detail}</p>}
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
      ? 'text-error'
      : highlight === 'ok'
        ? 'text-success'
        : 'text-ink';
  return (
    <div className="min-w-0 flex-1">
      <p className="mb-1 text-xs font-medium uppercase tracking-wider text-muted">{label}</p>
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
        deviceName: null,
        moduleName: null,
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
          className="inline-flex h-10 items-center justify-center rounded-xl border border-muted bg-panel px-4 text-sm font-medium text-ink shadow-sm motion-safe:transition hover:bg-panel-hover disabled:opacity-60"
        >
          <RefreshCw size={16} className={`mr-2 ${isLoading ? 'motion-safe:animate-spin' : ''}`} />
          Refresh
        </button>
      </div>

      {/* Filter Toolbar */}
      <div className="flex flex-wrap items-center gap-4 rounded-2xl border border-panel bg-panel p-4 shadow-sm">
        <div className="flex items-center gap-2">
          <Filter size={16} className="text-muted" />
          <span className="text-sm font-medium text-muted">Filters</span>
        </div>

        <div className="flex flex-wrap gap-3">
          <div>
            <label htmlFor="log-type-filter" className="sr-only">Event Type</label>
            <select
              id="log-type-filter"
              value={typeFilter}
              onChange={(e) => setTypeFilter(e.target.value as 'all' | 'check' | 'notification')}
              className="h-9 rounded-lg border border-muted bg-panel px-3 text-xs text-ink outline-none motion-safe:transition focus:border-accent"
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
              className="h-9 rounded-lg border border-muted bg-panel px-3 text-xs text-ink outline-none motion-safe:transition focus:border-accent"
            >
              <option value="all">All Statuses</option>
              <option value="success">Success</option>
              <option value="failed">Failed</option>
            </select>
          </div>
        </div>
      </div>

      {error !== null && (
        <div className="rounded-xl border border-error-border bg-error-bg px-4 py-3 text-sm text-error">
          {error}
        </div>
      )}

      <div className="relative overflow-hidden rounded-2xl border border-panel bg-panel shadow-sm">
        <div className="overflow-x-auto">
          <table className="min-w-full divide-y divide-muted">
            <thead className="bg-surface">
              <tr>
                <TableHead>Time</TableHead>
                <TableHead>Type</TableHead>
                <TableHead>Status</TableHead>
                <TableHead>Asset</TableHead>
                <TableHead>Message</TableHead>
                <TableHead>Details</TableHead>
              </tr>
            </thead>
            <tbody className="divide-y divide-muted text-sm">
              {isLoading && activities.length === 0 ? (
                <tr>
                  <td colSpan={6} className="px-6 py-10 text-center text-muted">
                    Loading activity history...
                  </td>
                </tr>
              ) : activities.length === 0 ? (
                <tr>
                  <td colSpan={6} className="px-6 py-10 text-center text-muted">
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
                        className={`motion-safe:transition-colors hover:bg-surface-hover ${
                          showChevron ? 'cursor-pointer' : ''
                        }`}
                        onClick={() => showChevron && toggleExpand(log.id)}
                      >
                        <td className="whitespace-nowrap px-6 py-4 font-mono text-xs text-muted">
                          {formattedTime}
                        </td>
                        <td className="whitespace-nowrap px-6 py-4">
                          <span
                            className={`inline-flex rounded-md px-2 py-0.5 text-xs font-semibold uppercase tracking-wider ${
                              log.eventType === 'check'
                                ? 'bg-accent/10 text-accent'
                                : 'bg-warning-bg text-warning'
                            }`}
                          >
                            {log.eventType}
                          </span>
                        </td>
                        <td className="whitespace-nowrap px-6 py-4">
                          <span
                            className={`inline-flex rounded-md px-2.5 py-0.5 text-xs font-semibold ${
                              log.status === 'success'
                                ? 'bg-success-bg text-success'
                                : 'bg-error-bg text-error'
                            }`}
                          >
                            {log.status === 'success' ? 'Success' : 'Failed'}
                          </span>
                        </td>
                        <td className="px-6 py-4 text-muted font-medium max-w-[160px]">
                          {log.deviceName || log.moduleName ? (
                            <div className="flex flex-col min-w-0">
                              {log.deviceName && <span className="truncate">{log.deviceName}</span>}
                              {log.moduleName && (
                                <span className="font-mono text-xs text-muted truncate">
                                  {log.moduleName}
                                </span>
                              )}
                            </div>
                            ) : (
                              <span className="text-muted">—</span>
                          )}
                        </td>
                        <td className="px-6 py-4 text-ink max-w-md sm:break-words max-sm:max-w-[180px] max-sm:truncate">
                          {log.message}
                        </td>
                        <td className="whitespace-nowrap px-6 py-4 text-muted">
                          {showChevron ? (
                            <button
                              type="button"
                              className="rounded-lg p-1 hover:bg-panel-hover text-muted"
                              onClick={(e) => {
                                e.stopPropagation();
                                toggleExpand(log.id);
                              }}
                              aria-label={isExpanded ? 'Collapse traceback' : 'Expand traceback'}
                            >
                              {isExpanded ? <ChevronUp size={16} /> : <ChevronDown size={16} />}
                            </button>
                          ) : (
                            <span className="text-muted">—</span>
                          )}
                        </td>
                      </tr>
                      {showChevron && isExpanded && (
                        <tr>
                          <td colSpan={6} className="bg-surface px-6 py-4">
                            <div className="rounded-xl border border-muted bg-slate-950 p-4 relative shadow-inner">
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
                                  className="inline-flex h-7 items-center justify-center rounded-lg border border-slate-800 bg-slate-900 hover:bg-slate-800 text-slate-300 px-3 text-xs font-medium motion-safe:transition motion-safe:active:scale-95"
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
        {/* Scroll hint gradient on right edge */}
        <div className="pointer-events-none absolute inset-y-0 right-0 w-8 bg-gradient-to-r from-transparent to-gradient-edge/50" aria-hidden="true" />
      </div>
    </div>
  );
}

function formatFrequencyLabel(intervalMinutes: number | null): string {
  if (intervalMinutes === null) return '24h';
  if (intervalMinutes >= 60 && intervalMinutes % 60 === 0) {
    return `${intervalMinutes / 60}h`;
  }
  return `${intervalMinutes}m`;
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
  onRetry,
}: {
  modules: InstalledModule[];
  isLoading: boolean;
  error: string | null;
  validation: ModuleValidationSummary | null;
  selectedFile: File | null;
  onFileSelect: (file: File | null) => void;
  onUpload: (event: FormEvent<HTMLFormElement>) => void;
  onDelete: (module: InstalledModule) => void;
  onRetry: () => void;
}) {
  const [editingModuleId, setEditingModuleId] = useState<string | null>(null);
  const [frequencyError, setFrequencyError] = useState<string | null>(null);
  const editingSnapshot = useRef<{ enabled: boolean; intervalMinutes: number } | null>(null);
  const queryClient = useQueryClient();

  const saveMutation = useMutation({
    mutationFn: ({
      moduleId,
      payload,
    }: {
      moduleId: number;
      payload: { enabled: boolean; intervalMinutes: number };
    }) => updateSchedule(moduleId, payload),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ['modules'] });
      setEditingModuleId(null);
      editingSnapshot.current = null;
      onRetry();
    },
    onError: (err: Error) => {
      setFrequencyError(err.message ?? 'Schedule update failed');
      setEditingModuleId(null);
      editingSnapshot.current = null;
    },
  });

  // External change detection: if schedule data changes while editor is open
  useEffect(() => {
    if (editingModuleId === null) return;
    const currentModule = modules.find((m) => m.moduleId === editingModuleId);
    if (currentModule === undefined) {
      // Module was deleted while editing
      queueMicrotask(() => {
        setEditingModuleId(null);
        editingSnapshot.current = null;
      });
      return;
    }
    const snapshot = editingSnapshot.current;
    if (snapshot !== null) {
      const currentSchedule = currentModule.schedule;
      const currentEnabled = currentSchedule?.enabled ?? false;
      const currentInterval = currentSchedule?.intervalMinutes ?? 1440;
      if (
        snapshot.enabled !== currentEnabled ||
        snapshot.intervalMinutes !== currentInterval
      ) {
        queueMicrotask(() => {
          setEditingModuleId(null);
          editingSnapshot.current = null;
        });
        setFrequencyError('This schedule was changed elsewhere. The editor will close.');
        setTimeout(() => setFrequencyError(null), 5000);
      }
    }
  }, [modules, editingModuleId]);

  // Auto-dismiss frequency error after 5 seconds
  useEffect(() => {
    if (frequencyError === null) return;
    const timer = setTimeout(() => setFrequencyError(null), 5000);
    return () => clearTimeout(timer);
  }, [frequencyError]);

  const startEditing = useCallback(
    (module: InstalledModule) => {
      setFrequencyError(null);
      setEditingModuleId(module.moduleId);
      editingSnapshot.current = module.schedule
        ? { enabled: module.schedule.enabled, intervalMinutes: module.schedule.intervalMinutes }
        : { enabled: false, intervalMinutes: 1440 };
    },
    [],
  );

  const handleCancel = useCallback(() => {
    setEditingModuleId(null);
    editingSnapshot.current = null;
    setFrequencyError(null);
  }, []);

  const handleSave = useCallback(
    (moduleId: string, payload: { enabled: boolean; intervalMinutes: number }) => {
      const module = modules.find((m) => m.moduleId === moduleId);
      if (!module) return;
      saveMutation.mutate({ moduleId: module.id, payload });
    },
    [modules, saveMutation],
  );

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
            className="block w-full rounded-xl border border-muted bg-panel px-3 py-2 text-sm text-ink shadow-sm file:mr-3 file:rounded-lg file:border-0 file:bg-surface file:px-3 file:py-1.5 file:text-sm file:font-medium file:text-ink sm:w-72"
          />
          {selectedFile !== null && <span className="text-xs text-muted">{selectedFile.name}</span>}
          <button
            type="submit"
            className="inline-flex items-center justify-center rounded-xl border border-muted bg-panel px-4 py-2 text-sm font-medium text-ink shadow-sm motion-safe:transition hover:bg-panel-hover"
          >
            <Plus size={16} className="mr-2" />
            Upload
          </button>
        </form>
      </div>

      <div className="rounded-2xl border border-warning-border bg-warning-bg px-4 py-3 text-sm text-warning">
        Modules are trusted Python code and run unsandboxed with application privileges.
      </div>

      {frequencyError !== null && (
        <div
          className="rounded-xl border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-800 dark:border-amber-800 dark:bg-amber-950 dark:text-amber-200"
          role="alert"
        >
          {frequencyError}
        </div>
      )}

      {validation !== null && <ValidationSummary summary={validation} />}

      {(isLoading || error !== null) && (
        <div className="grid grid-cols-1 gap-6 md:grid-cols-2 lg:grid-cols-3">
          {Array.from({ length: 6 }).map((_, i) => (
            <div key={i} className="animate-pulse rounded-2xl border border-panel bg-panel p-6 shadow-sm">
              <div className="mb-4 flex items-start justify-between">
                <div className="h-12 w-12 rounded-xl bg-muted/20" />
                <div className="h-5 w-16 rounded-full bg-muted/20" />
              </div>
              <div className="mb-1 h-5 w-3/4 rounded bg-muted/20" />
              <div className="mb-1 h-4 w-1/2 rounded bg-muted/20" />
              <div className="mb-5 h-4 w-1/3 rounded bg-muted/20" />
              {error !== null ? (
                <div className="mb-4 flex items-center gap-2">
                  <span className="text-sm font-medium text-error">Failed to load</span>
                  <button
                    type="button"
                    onClick={onRetry}
                    className="inline-flex items-center rounded-lg border border-error-border px-2 py-0.5 text-xs font-medium text-error hover:bg-error-bg"
                  >
                    <RefreshCw size={12} className="mr-1" />
                    Retry
                  </button>
                </div>
              ) : (
                <div className="flex items-center gap-2">
                  <div className="h-4 w-20 rounded bg-muted/20" />
                  <div className="h-4 w-16 rounded bg-muted/20" />
                </div>
              )}
              <div className="mt-3 flex items-center justify-between border-t border-panel pt-4">
                <div className="h-4 w-32 rounded bg-muted/20" />
                <div className="h-4 w-12 rounded bg-muted/20" />
              </div>
            </div>
          ))}
        </div>
      )}

      {!isLoading && error === null && modules.length === 0 && (
        <div className="rounded-2xl border border-dashed border-muted p-8 text-center text-sm text-muted">
          No modules installed yet.
        </div>
      )}

      {!isLoading && error === null && (
        <div className="grid grid-cols-1 gap-6 md:grid-cols-2 lg:grid-cols-3">
          {modules.map((module) => {
            const isEditing = editingModuleId === module.moduleId;

            return (
              <article
                key={module.moduleId}
                className="rounded-2xl border border-panel bg-panel p-6 shadow-sm"
              >
                <div className="mb-4 flex items-start justify-between">
                  <div className="rounded-xl bg-accent/10 p-3 text-accent">
                    <TerminalSquare size={24} />
                  </div>
                  <ModuleStatus status={module.validationStatus} />
                </div>
                <h3 className="truncate font-mono text-lg font-bold">{module.displayName}</h3>
                <p className="mt-1 text-sm text-muted">{module.moduleId}</p>
                <p className="mb-4 mt-1 text-sm text-muted">Version {module.version ?? 'unknown'}</p>

                {/* Frequency display or editor */}
                {isEditing ? (
                  <div
                    tabIndex={-1}
                    onBlur={(e) => {
                      // Close editor on click-away (blur) if the new focus target
                      // is outside the editor container.
                      const container = e.currentTarget;
                      requestAnimationFrame(() => {
                        if (!container.contains(document.activeElement)) {
                          handleCancel();
                        }
                      });
                    }}
                  >
                    <FrequencyEditor
                      currentIntervalMinutes={module.schedule?.intervalMinutes ?? null}
                      enabled={module.schedule?.enabled ?? false}
                      onSave={(payload) => handleSave(module.moduleId, payload)}
                      onCancel={handleCancel}
                      moduleId={module.id}
                    />
                    {saveMutation.isPending && (
                      <div className="mt-2 flex items-center gap-2 text-xs text-muted">
                        <Loader2 size={12} className="animate-spin" />
                        Saving...
                      </div>
                    )}
                  </div>
                ) : (
                  <div
                    className="mb-4 flex items-center gap-2"
                    role="button"
                    tabIndex={0}
                    onClick={() => startEditing(module)}
                    onKeyDown={(e) => {
                      if (e.key === 'Enter' || e.key === ' ') {
                        e.preventDefault();
                        startEditing(module);
                      }
                    }}
                    aria-label={`Edit check frequency for ${module.displayName}`}
                  >
                    <span className="inline-flex cursor-pointer items-center gap-1 rounded-full bg-surface px-2.5 py-1 text-xs font-medium text-ink hover:bg-panel-hover motion-safe:transition-colors">
                      <Clock size={12} />
                      {formatFrequencyLabel(module.schedule?.intervalMinutes ?? null)}
                    </span>
                    <span
                      className={[
                        'inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-xs font-medium',
                        module.schedule?.enabled
                          ? 'bg-emerald-600/10 text-emerald-600'
                          : 'bg-muted/30 text-muted',
                      ].join(' ')}
                    >
                      <span
                        className={[
                          'inline-block h-1.5 w-1.5 rounded-full',
                          module.schedule?.enabled ? 'bg-emerald-500' : 'bg-muted',
                        ].join(' ')}
                      />
                      {module.schedule?.enabled ? 'Active' : 'Paused'}
                    </span>
                  </div>
                )}

                <div className="flex items-center justify-between border-t border-panel pt-4">
                  <span className="flex items-center text-sm font-medium text-muted">
                    <Server size={14} className="mr-1.5" />
                    {module.lastValidatedAt === null
                      ? 'Not validated'
                      : `Validated ${new Date(module.lastValidatedAt).toLocaleString()}`}
                  </span>
                  <button
                    type="button"
                    onClick={() => onDelete(module)}
                    className="text-sm font-medium text-error hover:text-error"
                  >
                    Delete
                  </button>
                </div>
              </article>
            );
          })}
        </div>
      )}
    </div>
  );
}

function ValidationSummary({ summary }: { summary: ModuleValidationSummary }) {
  return (
    <div className="rounded-2xl border border-error-border bg-panel p-4 shadow-sm">
      <h3 className="text-sm font-semibold text-error">Validation feedback</h3>
      <div className="mt-3 grid gap-3 md:grid-cols-2">
        {[summary.static_phase, summary.runtime_phase].map((phase) => (
          <div key={phase.phase} className="rounded-xl bg-surface p-3 text-sm">
            <p className="font-semibold capitalize text-ink">
              {phase.phase} {phase.status}
            </p>
            {phase.findings.length === 0 ? (
              <p className="mt-1 text-muted">No findings.</p>
            ) : (
              <ul className="mt-2 space-y-1 text-muted">
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
        <p className="text-sm text-muted">Loading settings...</p>
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
          className={`rounded-xl border px-4 py-3 text-sm flex items-center justify-between motion-safe:transition-all ${
            statusMsg.type === 'success'
              ? 'border-success-border bg-success-bg text-success'
              : 'border-error-border bg-error-bg text-error'
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
        <section className="rounded-2xl border border-panel bg-panel p-6 shadow-sm flex flex-col justify-between">
          <div className="space-y-4">
            <div className="flex items-center justify-between border-b border-panel pb-3">
              <h3 className="flex items-center text-md font-bold text-ink">
                <Mail className="mr-2 text-indigo-500" size={18} />
                Email / SMTP Channel
              </h3>
              <label className="flex items-center gap-2 cursor-pointer">
                <input
                  type="checkbox"
                  checked={smtpEnabled}
                  onChange={(e) => setSmtpEnabled(e.target.checked)}
                  className="rounded border-muted text-accent focus:ring-accent-focus"
                />
                <span className="text-xs font-semibold text-muted">Enabled</span>
              </label>
            </div>

            <div className="grid grid-cols-1 gap-3 sm:grid-cols-3">
              <div className="col-span-2 sm:col-span-2">
                <label className="block text-xs font-medium text-muted">
                  SMTP Host
                  <input
                    type="text"
                    value={smtpHost}
                    onChange={(e) => setSmtpHost(e.target.value)}
                    placeholder="smtp.gmail.com"
                    className="mt-1 h-9 w-full rounded-xl border border-muted bg-panel px-3 text-xs text-ink outline-none motion-safe:transition focus:border-accent"
                  />
                </label>
              </div>
              <div>
                <label className="block text-xs font-medium text-muted">
                  Port
                  <input
                    type="text"
                    value={smtpPort}
                    onChange={(e) => setSmtpPort(e.target.value)}
                    placeholder="587"
                    className="mt-1 h-9 w-full rounded-xl border border-muted bg-panel px-3 text-xs text-ink outline-none motion-safe:transition focus:border-accent"
                  />
                </label>
              </div>
            </div>

            <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
              <div>
                <label className="block text-xs font-medium text-muted">
                  Username
                  <input
                    type="text"
                    value={smtpUsername}
                    onChange={(e) => setSmtpUsername(e.target.value)}
                    placeholder="user@gmail.com"
                    className="mt-1 h-9 w-full rounded-xl border border-muted bg-panel px-3 text-xs text-ink outline-none motion-safe:transition focus:border-accent"
                  />
                </label>
              </div>
              <div>
                <label className="block text-xs font-medium text-muted">
                  Password
                  <input
                    type="password"
                    value={smtpPassword}
                    onChange={(e) => setSmtpPassword(e.target.value)}
                    placeholder={smtpPassword === '•' ? '••••••••' : 'Enter Password'}
                    className="mt-1 h-9 w-full rounded-xl border border-muted bg-panel px-3 text-xs text-ink outline-none motion-safe:transition focus:border-accent"
                  />
                </label>
              </div>
            </div>

            <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
              <div>
                <label className="block text-xs font-medium text-muted">
                  Mail From
                  <input
                    type="text"
                    value={mailFrom}
                    onChange={(e) => setMailFrom(e.target.value)}
                    placeholder="binocular@homelab.lan"
                    className="mt-1 h-9 w-full rounded-xl border border-muted bg-panel px-3 text-xs text-ink outline-none motion-safe:transition focus:border-accent"
                  />
                </label>
              </div>
              <div>
                <label className="block text-xs font-medium text-muted">
                  Mail To
                  <input
                    type="text"
                    value={mailTo}
                    onChange={(e) => setMailTo(e.target.value)}
                    placeholder="owner@homelab.lan"
                    className="mt-1 h-9 w-full rounded-xl border border-muted bg-panel px-3 text-xs text-ink outline-none motion-safe:transition focus:border-accent"
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
                  className="rounded border-muted text-accent focus:ring-accent-focus"
                />
                <span className="text-xs text-muted">Use Secure TLS / STARTTLS</span>
              </label>
            </div>
          </div>

          <div className="mt-6 flex items-center justify-end gap-2 border-t border-panel pt-4">
            <button
              type="button"
              onClick={handleTestSmtp}
              disabled={isSmtpTesting || isSmtpSaving}
              className="inline-flex h-9 items-center justify-center rounded-xl border border-muted bg-panel px-4 text-xs font-medium text-ink shadow-sm motion-safe:transition hover:bg-panel-hover disabled:opacity-60"
            >
              {isSmtpTesting ? 'Sending Test...' : 'Send Test'}
            </button>
            <button
              type="button"
              onClick={handleSaveSmtp}
              disabled={isSmtpTesting || isSmtpSaving}
              className="inline-flex h-9 items-center justify-center rounded-xl bg-accent px-4 text-xs font-medium text-white shadow-sm motion-safe:transition hover:bg-accent-hover disabled:opacity-60"
            >
              {isSmtpSaving ? 'Saving...' : 'Save Settings'}
            </button>
          </div>
        </section>

        {/* Gotify Config */}
        <section className="rounded-2xl border border-panel bg-panel p-6 shadow-sm flex flex-col justify-between">
          <div className="space-y-4">
            <div className="flex items-center justify-between border-b border-panel pb-3">
              <h3 className="flex items-center text-md font-bold text-ink">
                <Send className="mr-2 text-indigo-500" size={18} />
                Gotify Push Channel
              </h3>
              <label className="flex items-center gap-2 cursor-pointer">
                <input
                  type="checkbox"
                  checked={gotifyEnabled}
                  onChange={(e) => setGotifyEnabled(e.target.checked)}
                  className="rounded border-muted text-accent focus:ring-accent-focus"
                />
                <span className="text-xs font-semibold text-muted">Enabled</span>
              </label>
            </div>

            <div>
              <label className="block text-xs font-medium text-muted">
                Gotify Server URL
                <input
                  type="text"
                  value={gotifyUrl}
                  onChange={(e) => setGotifyUrl(e.target.value)}
                  placeholder="https://gotify.homelab.lan"
                  className="mt-1 h-9 w-full rounded-xl border border-muted bg-panel px-3 text-xs text-ink outline-none motion-safe:transition focus:border-accent"
                />
              </label>
            </div>

            <div>
              <label className="block text-xs font-medium text-muted">
                Application Token
                <input
                  type="password"
                  value={gotifyToken}
                  onChange={(e) => setGotifyToken(e.target.value)}
                  placeholder={gotifyToken === '•' ? '••••••••' : 'Enter Application Token'}
                  className="mt-1 h-9 w-full rounded-xl border border-muted bg-panel px-3 text-xs text-ink outline-none motion-safe:transition focus:border-accent"
                />
              </label>
            </div>
          </div>

          <div className="mt-6 flex items-center justify-end gap-2 border-t border-panel pt-4">
            <button
              type="button"
              onClick={handleTestGotify}
              disabled={isGotifyTesting || isGotifySaving}
              className="inline-flex h-9 items-center justify-center rounded-xl border border-muted bg-panel px-4 text-xs font-medium text-ink shadow-sm motion-safe:transition hover:bg-panel-hover disabled:opacity-60"
            >
              {isGotifyTesting ? 'Sending Test...' : 'Send Test'}
            </button>
            <button
              type="button"
              onClick={handleSaveGotify}
              disabled={isGotifyTesting || isGotifySaving}
              className="inline-flex h-9 items-center justify-center rounded-xl bg-accent px-4 text-xs font-medium text-white shadow-sm motion-safe:transition hover:bg-accent-hover disabled:opacity-60"
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
      <p className="mt-1 text-sm text-muted">{description}</p>
    </div>
  );
}

function TableHead({ children }: { children: string }) {
  return (
    <th className="px-6 py-3 text-left text-xs font-medium uppercase tracking-wider text-muted">
      {children}
    </th>
  );
}


function ModuleStatus({ status }: { status: InstalledModule['validationStatus'] }) {
  const className =
    status === 'valid'
      ? 'border-success-border bg-success-bg text-success'
      : status === 'invalid'
        ? 'border-error-border bg-error-bg text-error'
        : 'border-muted bg-surface text-muted';
  return <span className={`rounded-full border px-2.5 py-1 text-xs font-medium ${className}`}>{status}</span>;
}
