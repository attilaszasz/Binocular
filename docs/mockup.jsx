import React, { useState, useEffect, useMemo } from 'react';
import { 
  Binoculars, 
  CheckCircle2, 
  RefreshCw, 
  AlertCircle, 
  Settings, 
  TerminalSquare, 
  Server, 
  Menu, 
  X, 
  Moon, 
  Sun,
  ArrowRight,
  Check,
  Package,
  Activity,
  Plus
} from 'lucide-react';

// --- MOCK DATA ---
const INITIAL_DEVICES = [
  { id: 1, name: "Sony A7IV", type: "Sony Alpha Bodies", localVersion: "2.00", webVersion: "3.00", lastChecked: "10 mins ago", isChecking: false },
  { id: 2, name: "Sony 24-70mm f/2.8 GM II", type: "Sony E-Mount Lenses", localVersion: "02", webVersion: "02", lastChecked: "1 hour ago", isChecking: false },
  { id: 3, name: "Sony 70-200mm f/2.8 GM II", type: "Sony E-Mount Lenses", localVersion: "03", webVersion: "04", lastChecked: "2 hours ago", isChecking: false },
  { id: 4, name: "Lumix GH6", type: "Panasonic Lumix Bodies", localVersion: "2.3", webVersion: "2.3", lastChecked: "1 day ago", isChecking: false },
  { id: 5, name: "Ubiquiti Dream Machine Pro", type: "Networking", localVersion: "3.2.12", webVersion: "3.2.12", lastChecked: "5 mins ago", isChecking: false },
];

const INITIAL_LOGS = [
  { id: 1, time: "10:42 AM", level: "INFO", message: "Manual check started for Sony A7IV" },
  { id: 2, time: "10:42 AM", level: "WARN", message: "New firmware v3.00 found for Sony A7IV (Local: v2.00)" },
  { id: 3, time: "09:00 AM", level: "INFO", message: "Scheduled check completed. 15 devices scanned." },
  { id: 4, time: "08:59 AM", level: "ERROR", message: "Failed to scrape Panasonic URL: HTTP 429 Too Many Requests" }
];

const MODULES = [
  { id: 1, name: "sony_alpha.py", status: "Active", devices: 3, version: "1.2.0" },
  { id: 2, name: "panasonic_lumix.py", status: "Active", devices: 1, version: "1.0.5" },
  { id: 3, name: "unifi_network.py", status: "Inactive", devices: 1, version: "0.9.1" },
];

export default function App() {
  const [devices, setDevices] = useState(INITIAL_DEVICES);
  const [logs, setLogs] = useState(INITIAL_LOGS);
  const [activeTab, setActiveTab] = useState('dashboard');
  const [isDarkMode, setIsDarkMode] = useState(true);
  const [isMobileMenuOpen, setIsMobileMenuOpen] = useState(false);
  const [isCheckingAll, setIsCheckingAll] = useState(false);

  // Group devices by type
  const groupedDevices = useMemo(() => {
    return devices.reduce((acc, device) => {
      if (!acc[device.type]) acc[device.type] = [];
      acc[device.type].push(device);
      return acc;
    }, {});
  }, [devices]);

  const stats = useMemo(() => {
    const total = devices.length;
    const updates = devices.filter(d => d.localVersion !== d.webVersion).length;
    return { total, updates, upToDate: total - updates };
  }, [devices]);

  // --- ACTIONS ---
  const handleCheckDevice = (id) => {
    setDevices(prev => prev.map(d => d.id === id ? { ...d, isChecking: true } : d));
    
    // Simulate network request
    setTimeout(() => {
      setDevices(prev => prev.map(d => {
        if (d.id === id) {
          return { ...d, isChecking: false, lastChecked: "Just now" };
        }
        return d;
      }));
      addLog("INFO", `Completed manual check for device ID ${id}`);
    }, 1500);
  };

  const handleCheckAll = () => {
    setIsCheckingAll(true);
    setDevices(prev => prev.map(d => ({ ...d, isChecking: true })));
    addLog("INFO", "Initiated bulk check for all devices");

    setTimeout(() => {
      setDevices(prev => prev.map(d => ({ ...d, isChecking: false, lastChecked: "Just now" })));
      setIsCheckingAll(false);
      addLog("INFO", "Bulk check completed successfully");
    }, 2500);
  };

  const handleMarkUpdated = (id) => {
    setDevices(prev => prev.map(d => {
      if (d.id === id) {
        addLog("INFO", `User confirmed update for ${d.name}. Version synced to ${d.webVersion}`);
        return { ...d, localVersion: d.webVersion };
      }
      return d;
    }));
  };

  const addLog = (level, message) => {
    const now = new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
    setLogs(prev => [{ id: Date.now(), time: now, level, message }, ...prev].slice(0, 50));
  };

  // --- COMPONENTS ---
  const NavItem = ({ icon: Icon, label, id }) => (
    <button
      onClick={() => { setActiveTab(id); setIsMobileMenuOpen(false); }}
      className={`w-full flex items-center space-x-3 px-4 py-3 rounded-xl transition-all duration-200 ${
        activeTab === id 
          ? (isDarkMode ? 'bg-indigo-500/10 text-indigo-400' : 'bg-indigo-50 text-indigo-600') 
          : (isDarkMode ? 'text-slate-400 hover:bg-slate-800 hover:text-slate-200' : 'text-slate-600 hover:bg-slate-100 hover:text-slate-900')
      }`}
    >
      <Icon size={20} className={activeTab === id ? (isDarkMode ? 'text-indigo-400' : 'text-indigo-600') : ''} />
      <span className="font-medium">{label}</span>
    </button>
  );

  return (
    <div className={`min-h-screen font-sans transition-colors duration-300 ${isDarkMode ? 'dark bg-slate-950' : 'bg-slate-50'}`}>
      
      {/* Sidebar - Desktop */}
      <aside className={`fixed inset-y-0 left-0 z-50 w-64 transform transition-transform duration-300 ease-in-out md:translate-x-0 ${isMobileMenuOpen ? 'translate-x-0' : '-translate-x-full'} ${isDarkMode ? 'bg-slate-900 border-slate-800' : 'bg-white border-slate-200'} border-r`}>
        <div className="flex items-center justify-between h-16 px-6 border-b border-inherit">
          <div className="flex items-center space-x-2">
            <div className={`p-1.5 rounded-lg ${isDarkMode ? 'bg-indigo-500/20 text-indigo-400' : 'bg-indigo-100 text-indigo-600'}`}>
              <Binoculars size={24} />
            </div>
            <span className={`text-xl font-bold tracking-tight ${isDarkMode ? 'text-white' : 'text-slate-900'}`}>Binocular</span>
          </div>
          <button className="md:hidden text-slate-400 hover:text-slate-600" onClick={() => setIsMobileMenuOpen(false)}>
            <X size={20} />
          </button>
        </div>

        <nav className="p-4 space-y-1.5">
          <NavItem icon={Server} label="Inventory" id="dashboard" />
          <NavItem icon={TerminalSquare} label="Activity Logs" id="logs" />
          <NavItem icon={Package} label="Modules" id="modules" />
          <NavItem icon={Settings} label="Settings" id="settings" />
        </nav>
      </aside>

      {/* Main Content */}
      <main className={`transition-all duration-300 ease-in-out md:ml-64 ${isMobileMenuOpen ? 'opacity-50 md:opacity-100' : ''}`}>
        
        {/* Top Header */}
        <header className={`sticky top-0 z-40 flex items-center justify-between h-16 px-4 sm:px-6 lg:px-8 border-b backdrop-blur-sm ${isDarkMode ? 'bg-slate-950/80 border-slate-800' : 'bg-white/80 border-slate-200'}`}>
          <div className="flex items-center">
            <button className="mr-4 md:hidden text-slate-500 hover:text-slate-700" onClick={() => setIsMobileMenuOpen(true)}>
              <Menu size={24} />
            </button>
            <h1 className={`text-lg font-semibold capitalize ${isDarkMode ? 'text-white' : 'text-slate-900'}`}>
              {activeTab.replace('-', ' ')}
            </h1>
          </div>
          
          <div className="flex items-center space-x-4">
            <button 
              onClick={() => setIsDarkMode(!isDarkMode)}
              className={`p-2 rounded-full transition-colors ${isDarkMode ? 'text-slate-400 hover:bg-slate-800 hover:text-slate-200' : 'text-slate-500 hover:bg-slate-100 hover:text-slate-700'}`}
            >
              {isDarkMode ? <Sun size={20} /> : <Moon size={20} />}
            </button>
          </div>
        </header>

        {/* Tab Content */}
        <div className="p-4 sm:px-6 lg:px-8 max-w-7xl mx-auto py-8">
          
          {/* Dashboard Tab */}
          {activeTab === 'dashboard' && (
            <div className="space-y-8 animate-in fade-in slide-in-from-bottom-4 duration-500">
              
              {/* Header & Actions */}
              <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
                <div>
                  <h2 className={`text-2xl font-bold tracking-tight ${isDarkMode ? 'text-white' : 'text-slate-900'}`}>Device Inventory</h2>
                  <p className={`mt-1 text-sm ${isDarkMode ? 'text-slate-400' : 'text-slate-500'}`}>Manage your hardware and monitor for firmware updates.</p>
                </div>
                <div className="flex items-center space-x-3">
                  <button className={`px-4 py-2 text-sm font-medium rounded-xl border shadow-sm transition-all focus:outline-none focus:ring-2 focus:ring-offset-2 flex items-center ${isDarkMode ? 'border-slate-700 bg-slate-800 text-slate-200 hover:bg-slate-700 focus:ring-offset-slate-900' : 'border-slate-200 bg-white text-slate-700 hover:bg-slate-50 focus:ring-offset-white'}`}>
                    <Plus size={16} className="mr-2" />
                    Add Device
                  </button>
                  <button 
                    onClick={handleCheckAll}
                    disabled={isCheckingAll}
                    className={`px-4 py-2 text-sm font-medium rounded-xl shadow-sm transition-all focus:outline-none focus:ring-2 focus:ring-offset-2 flex items-center ${isDarkMode ? 'bg-indigo-600 text-white hover:bg-indigo-500 focus:ring-indigo-500 focus:ring-offset-slate-900 disabled:bg-indigo-800 disabled:text-indigo-300' : 'bg-indigo-600 text-white hover:bg-indigo-700 focus:ring-indigo-500 disabled:bg-indigo-300'}`}
                  >
                    <RefreshCw size={16} className={`mr-2 ${isCheckingAll ? 'animate-spin' : ''}`} />
                    {isCheckingAll ? 'Checking All...' : 'Check All Now'}
                  </button>
                </div>
              </div>

              {/* Stats Row */}
              <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
                {[
                  { label: "Total Devices", value: stats.total, icon: Server, color: "indigo" },
                  { label: "Updates Available", value: stats.updates, icon: AlertCircle, color: "rose" },
                  { label: "Up to Date", value: stats.upToDate, icon: CheckCircle2, color: "emerald" },
                ].map((stat, i) => (
                  <div key={i} className={`p-5 rounded-2xl border shadow-sm ${isDarkMode ? 'bg-slate-900 border-slate-800' : 'bg-white border-slate-200'}`}>
                    <div className="flex items-center justify-between">
                      <div>
                        <p className={`text-sm font-medium ${isDarkMode ? 'text-slate-400' : 'text-slate-500'}`}>{stat.label}</p>
                        <p className={`mt-2 text-3xl font-bold ${isDarkMode ? 'text-white' : 'text-slate-900'}`}>{stat.value}</p>
                      </div>
                      <div className={`p-3 rounded-xl ${isDarkMode ? `bg-${stat.color}-500/10 text-${stat.color}-400` : `bg-${stat.color}-50 text-${stat.color}-600`}`}>
                        <stat.icon size={24} />
                      </div>
                    </div>
                  </div>
                ))}
              </div>

              {/* Grouped Devices */}
              {Object.entries(groupedDevices).map(([type, groupDevices]) => (
                <div key={type} className="space-y-4">
                  <h3 className={`text-sm font-semibold tracking-wider uppercase flex items-center ${isDarkMode ? 'text-slate-400' : 'text-slate-500'}`}>
                    <Package size={16} className="mr-2" />
                    {type}
                  </h3>
                  
                  <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
                    {groupDevices.map(device => {
                      const hasUpdate = device.localVersion !== device.webVersion;
                      return (
                        <div 
                          key={device.id} 
                          className={`relative p-5 rounded-2xl border transition-all duration-200 ${
                            isDarkMode 
                              ? `bg-slate-900 ${hasUpdate ? 'border-rose-500/50 shadow-[0_0_15px_rgba(244,63,94,0.1)]' : 'border-slate-800'}` 
                              : `bg-white shadow-sm ${hasUpdate ? 'border-rose-300 ring-1 ring-rose-300' : 'border-slate-200'}`
                          }`}
                        >
                          <div className="flex justify-between items-start mb-4">
                            <div>
                              <h4 className={`text-lg font-bold ${isDarkMode ? 'text-slate-100' : 'text-slate-900'}`}>{device.name}</h4>
                              <p className={`text-xs mt-1 ${isDarkMode ? 'text-slate-500' : 'text-slate-400'}`}>Last checked: {device.lastChecked}</p>
                            </div>
                            
                            <div className="flex items-center space-x-2">
                              <button 
                                onClick={() => handleCheckDevice(device.id)}
                                disabled={device.isChecking || isCheckingAll}
                                className={`p-2 rounded-lg transition-colors ${
                                  isDarkMode 
                                    ? 'bg-slate-800 text-slate-300 hover:bg-slate-700 disabled:opacity-50' 
                                    : 'bg-slate-100 text-slate-600 hover:bg-slate-200 disabled:opacity-50'
                                }`}
                                title="Check for updates"
                              >
                                <RefreshCw size={16} className={device.isChecking ? 'animate-spin' : ''} />
                              </button>
                            </div>
                          </div>

                          <div className={`p-4 rounded-xl flex items-center justify-between ${
                            isDarkMode 
                              ? (hasUpdate ? 'bg-rose-500/10' : 'bg-slate-800/50') 
                              : (hasUpdate ? 'bg-rose-50' : 'bg-slate-50')
                          }`}>
                            <div className="flex items-center space-x-4 flex-1">
                              <div className="flex-1">
                                <p className={`text-xs font-medium uppercase tracking-wider mb-1 ${isDarkMode ? 'text-slate-500' : 'text-slate-400'}`}>Local</p>
                                <p className={`text-lg font-semibold font-mono ${isDarkMode ? 'text-slate-300' : 'text-slate-700'}`}>v{device.localVersion}</p>
                              </div>
                              
                              {hasUpdate && (
                                <div className={`flex-shrink-0 animate-pulse ${isDarkMode ? 'text-rose-400' : 'text-rose-500'}`}>
                                  <ArrowRight size={20} />
                                </div>
                              )}

                              <div className="flex-1 text-right sm:text-left">
                                <p className={`text-xs font-medium uppercase tracking-wider mb-1 ${isDarkMode ? 'text-slate-500' : 'text-slate-400'}`}>Latest</p>
                                <p className={`text-lg font-semibold font-mono ${
                                  hasUpdate 
                                    ? (isDarkMode ? 'text-rose-400' : 'text-rose-600') 
                                    : (isDarkMode ? 'text-emerald-400' : 'text-emerald-600')
                                }`}>
                                  v{device.webVersion}
                                </p>
                              </div>
                            </div>

                            {/* One-Click Confirmation Action */}
                            {hasUpdate && (
                              <div className="ml-4 pl-4 border-l border-inherit flex-shrink-0">
                                <button 
                                  onClick={() => handleMarkUpdated(device.id)}
                                  className={`flex items-center space-x-1 px-3 py-2 rounded-lg text-sm font-medium transition-colors ${
                                    isDarkMode 
                                      ? 'bg-emerald-500/20 text-emerald-400 hover:bg-emerald-500/30 border border-emerald-500/30' 
                                      : 'bg-emerald-100 text-emerald-700 hover:bg-emerald-200 border border-emerald-200'
                                  }`}
                                  title="Mark as updated physically"
                                >
                                  <Check size={16} className="mr-1.5" />
                                  <span className="hidden sm:inline">Sync Local</span>
                                  <span className="sm:hidden">Sync</span>
                                </button>
                              </div>
                            )}
                          </div>
                        </div>
                      );
                    })}
                  </div>
                </div>
              ))}
            </div>
          )}

          {/* Activity Logs Tab */}
          {activeTab === 'logs' && (
            <div className="space-y-6 animate-in fade-in slide-in-from-bottom-4 duration-500">
              <div className="flex items-center justify-between">
                <div>
                  <h2 className={`text-2xl font-bold tracking-tight ${isDarkMode ? 'text-white' : 'text-slate-900'}`}>Activity Logs</h2>
                  <p className={`mt-1 text-sm ${isDarkMode ? 'text-slate-400' : 'text-slate-500'}`}>System execution and scraping history.</p>
                </div>
              </div>

              <div className={`rounded-2xl border overflow-hidden ${isDarkMode ? 'bg-slate-900 border-slate-800' : 'bg-white border-slate-200'}`}>
                <div className="overflow-x-auto">
                  <table className="min-w-full divide-y divide-inherit">
                    <thead className={isDarkMode ? 'bg-slate-800/50' : 'bg-slate-50'}>
                      <tr>
                        <th className={`px-6 py-3 text-left text-xs font-medium uppercase tracking-wider ${isDarkMode ? 'text-slate-400' : 'text-slate-500'}`}>Time</th>
                        <th className={`px-6 py-3 text-left text-xs font-medium uppercase tracking-wider ${isDarkMode ? 'text-slate-400' : 'text-slate-500'}`}>Level</th>
                        <th className={`px-6 py-3 text-left text-xs font-medium uppercase tracking-wider ${isDarkMode ? 'text-slate-400' : 'text-slate-500'}`}>Message</th>
                      </tr>
                    </thead>
                    <tbody className={`divide-y font-mono text-sm ${isDarkMode ? 'divide-slate-800' : 'divide-slate-200'}`}>
                      {logs.map(log => (
                        <tr key={log.id} className={`transition-colors ${isDarkMode ? 'hover:bg-slate-800/50' : 'hover:bg-slate-50'}`}>
                          <td className={`px-6 py-4 whitespace-nowrap ${isDarkMode ? 'text-slate-400' : 'text-slate-500'}`}>{log.time}</td>
                          <td className="px-6 py-4 whitespace-nowrap">
                            <span className={`inline-flex items-center px-2.5 py-0.5 rounded-md text-xs font-medium ${
                              log.level === 'INFO' ? (isDarkMode ? 'bg-blue-500/10 text-blue-400' : 'bg-blue-100 text-blue-700') :
                              log.level === 'WARN' ? (isDarkMode ? 'bg-amber-500/10 text-amber-400' : 'bg-amber-100 text-amber-700') :
                              (isDarkMode ? 'bg-rose-500/10 text-rose-400' : 'bg-rose-100 text-rose-700')
                            }`}>
                              {log.level}
                            </span>
                          </td>
                          <td className={`px-6 py-4 ${isDarkMode ? 'text-slate-300' : 'text-slate-700'}`}>{log.message}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            </div>
          )}

          {/* Modules Tab */}
          {activeTab === 'modules' && (
            <div className="space-y-6 animate-in fade-in slide-in-from-bottom-4 duration-500">
              <div className="flex items-center justify-between">
                <div>
                  <h2 className={`text-2xl font-bold tracking-tight ${isDarkMode ? 'text-white' : 'text-slate-900'}`}>Extension Modules</h2>
                  <p className={`mt-1 text-sm ${isDarkMode ? 'text-slate-400' : 'text-slate-500'}`}>Manage Python scripts that scrape firmware data.</p>
                </div>
                <button className={`px-4 py-2 text-sm font-medium rounded-xl border shadow-sm transition-all focus:outline-none focus:ring-2 focus:ring-offset-2 flex items-center ${isDarkMode ? 'border-slate-700 bg-slate-800 text-slate-200 hover:bg-slate-700' : 'border-slate-200 bg-white text-slate-700 hover:bg-slate-50'}`}>
                  <Plus size={16} className="mr-2" />
                  Upload Module
                </button>
              </div>

              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
                {MODULES.map(mod => (
                  <div key={mod.id} className={`p-6 rounded-2xl border shadow-sm ${isDarkMode ? 'bg-slate-900 border-slate-800' : 'bg-white border-slate-200'}`}>
                    <div className="flex items-start justify-between mb-4">
                      <div className={`p-3 rounded-xl ${isDarkMode ? 'bg-slate-800 text-indigo-400' : 'bg-indigo-50 text-indigo-600'}`}>
                        <TerminalSquare size={24} />
                      </div>
                      <span className={`inline-flex items-center px-2.5 py-1 rounded-full text-xs font-medium border ${
                        mod.status === 'Active' 
                          ? (isDarkMode ? 'bg-emerald-500/10 text-emerald-400 border-emerald-500/20' : 'bg-emerald-50 text-emerald-700 border-emerald-200')
                          : (isDarkMode ? 'bg-slate-800 text-slate-400 border-slate-700' : 'bg-slate-100 text-slate-500 border-slate-200')
                      }`}>
                        {mod.status}
                      </span>
                    </div>
                    <h3 className={`text-lg font-bold font-mono mb-1 truncate ${isDarkMode ? 'text-white' : 'text-slate-900'}`}>{mod.name}</h3>
                    <p className={`text-sm mb-4 ${isDarkMode ? 'text-slate-400' : 'text-slate-500'}`}>Version {mod.version}</p>
                    
                    <div className={`pt-4 border-t flex items-center justify-between ${isDarkMode ? 'border-slate-800' : 'border-slate-100'}`}>
                      <span className={`text-sm font-medium flex items-center ${isDarkMode ? 'text-slate-400' : 'text-slate-600'}`}>
                        <Server size={14} className="mr-1.5" />
                        {mod.devices} mapped devices
                      </span>
                      <button className={`text-sm font-medium ${isDarkMode ? 'text-indigo-400 hover:text-indigo-300' : 'text-indigo-600 hover:text-indigo-700'}`}>
                        Configure
                      </button>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Settings Tab Placeholder */}
          {activeTab === 'settings' && (
            <div className="flex flex-col items-center justify-center py-20 text-center animate-in fade-in duration-500">
              <div className={`p-4 rounded-full mb-4 ${isDarkMode ? 'bg-slate-800 text-slate-400' : 'bg-slate-100 text-slate-500'}`}>
                <Settings size={32} />
              </div>
              <h2 className={`text-xl font-semibold ${isDarkMode ? 'text-white' : 'text-slate-900'}`}>Settings configuration</h2>
              <p className={`mt-2 max-w-sm ${isDarkMode ? 'text-slate-400' : 'text-slate-500'}`}>Notification channels (Apprise), backup configurations, and global interval settings go here.</p>
            </div>
          )}

        </div>
      </main>
    </div>
  );
}