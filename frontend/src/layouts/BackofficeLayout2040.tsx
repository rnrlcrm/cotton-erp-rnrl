/**
 * 2040 Backoffice Layout
 * Features: Top nav with system switching, collapsible sidebar, Quantum Hub, footer status
 */

import { useState, useEffect } from 'react';
import { Outlet, Link, useLocation, useNavigate } from 'react-router-dom';
import { useAuth } from '@/hooks/useAuth';
import {
  HomeIcon,
  ChartBarIcon,
  UsersIcon,
  CogIcon,
  BellIcon,
  ArrowRightOnRectangleIcon,
  UserCircleIcon,
  ChevronDownIcon,
  ShieldCheckIcon,
  DocumentTextIcon,
  CurrencyDollarIcon,
  SparklesIcon,
} from '@heroicons/react/24/outline';
import { QuantumHub } from '@/components/2040/QuantumHub';

// Top navigation - All modules in one place
const systems = [
  { id: 'dashboard', name: 'Dashboard', href: '/backoffice', icon: HomeIcon },
  { id: 'trading', name: 'Trading', href: '/backoffice/trade-desk', icon: ChartBarIcon },
  { id: 'clearing', name: 'Clearing', href: '/backoffice/clearing', icon: ShieldCheckIcon },
  { id: 'risk', name: 'Risk', href: '/backoffice/risk', icon: ExclamationTriangleIcon },
  { id: 'accounts', name: 'Accounts', href: '/backoffice/accounts', icon: CurrencyDollarIcon },
  { id: 'audit', name: 'Audit', href: '/backoffice/audit', icon: DocumentTextIcon },
  { id: 'users', name: 'Users', href: '/backoffice/users', icon: UsersIcon },
  { id: 'settings', name: 'Settings', href: '/backoffice/settings', icon: CogIcon },
];

function ExclamationTriangleIcon(props: any) {
  return (
    <svg {...props} fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor">
      <path strokeLinecap="round" strokeLinejoin="round" d="M12 9v3.75m-9.303 3.376c-.866 1.5.217 3.374 1.948 3.374h14.71c1.73 0 2.813-1.874 1.948-3.374L13.949 3.378c-.866-1.5-3.032-1.5-3.898 0L2.697 16.126zM12 15.75h.007v.008H12v-.008z" />
    </svg>
  );
}

export function BackofficeLayout2040() {
  const location = useLocation();
  const navigate = useNavigate();
  const { user, logout } = useAuth();
  const [activeSystem, setActiveSystem] = useState('dashboard');
  const [quantumHubOpen, setQuantumHubOpen] = useState(false);
  const [showProfile, setShowProfile] = useState(false);
  const [showNotifications, setShowNotifications] = useState(false);
  
  // Panel management to prevent collisions
  const handleQuantumToggle = () => {
    setQuantumHubOpen(!quantumHubOpen);
  };
  
  // Handle logout
  const handleLogout = async () => {
    await logout();
    navigate('/login');
  };

  // Auto-detect active system from route
  useEffect(() => {
    const path = location.pathname;
    if (path === '/backoffice') setActiveSystem('dashboard');
    else if (path.includes('/trade-desk')) setActiveSystem('trading');
    else if (path.includes('/clearing')) setActiveSystem('clearing');
    else if (path.includes('/risk')) setActiveSystem('risk');
    else if (path.includes('/accounts')) setActiveSystem('accounts');
    else if (path.includes('/audit')) setActiveSystem('audit');
    else if (path.includes('/users')) setActiveSystem('users');
    else if (path.includes('/settings')) setActiveSystem('settings');
  }, [location.pathname]);

  // Close dropdowns when clicking outside
  useEffect(() => {
    const handleClickOutside = (e: MouseEvent) => {
      const target = e.target as HTMLElement;
      if (!target.closest('.profile-dropdown') && !target.closest('.profile-button')) {
        setShowProfile(false);
      }
      if (!target.closest('.notification-dropdown') && !target.closest('.notification-button')) {
        setShowNotifications(false);
      }
    };
    
    const handleEscape = (e: KeyboardEvent) => {
      if (e.key === 'Escape') {
        setShowProfile(false);
        setShowNotifications(false);
        if (quantumHubOpen) setQuantumHubOpen(false);
      }
    };
    
    document.addEventListener('click', handleClickOutside);
    document.addEventListener('keydown', handleEscape);
    return () => {
      document.removeEventListener('click', handleClickOutside);
      document.removeEventListener('keydown', handleEscape);
    };
  }, [quantumHubOpen]);

  const handleSystemSwitch = (systemId: string, href: string) => {
    setActiveSystem(systemId);
    navigate(href);
  };

  return (
    <div className="min-h-screen bg-pearl-50 relative overflow-hidden font-body">
      {/* Subtle background gradient */}
      <div className="fixed inset-0 pointer-events-none">
        <div className="absolute top-0 left-0 w-full h-64 bg-gradient-to-b from-saturn-50/30 to-transparent" />
      </div>

      {/* Top Navigation Bar - Matte dark with holographic glow on hover */}
      <header className="fixed top-0 left-0 right-0 h-14 bg-gradient-to-r from-space-900 via-space-800 to-space-900 border-b border-saturn-700/30 shadow-xl z-50">
        <div className="h-full px-6 flex items-center justify-between">
          {/* Logo */}
          <div className="flex items-center gap-3">
            <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-sun-400 via-saturn-500 to-mars-500 flex items-center justify-center shadow-lg">
              <span className="text-white font-heading font-bold text-sm">RN</span>
            </div>
            <span className="text-white font-heading font-bold text-base">RNRL Exchange</span>
            <span className="text-xs text-saturn-400 font-mono">2040</span>
          </div>

          {/* System Tabs - Holographic hover */}
          <div className="flex items-center gap-1">
            {systems.map((system) => {
              const Icon = system.icon;
              const isActive = activeSystem === system.id;
              return (
                <button
                  key={system.id}
                  onClick={() => handleSystemSwitch(system.id, system.href)}
                  className={`relative px-4 py-2 rounded-lg font-heading font-medium text-sm transition-all duration-120 group ${
                    isActive
                      ? 'bg-saturn-600 text-white shadow-lg shadow-saturn-500/50'
                      : 'text-saturn-300 hover:text-white hover:bg-saturn-800/50'
                  }`}
                >
                  {/* Holographic glow on hover */}
                  {!isActive && (
                    <div className="absolute inset-0 rounded-lg opacity-0 group-hover:opacity-100 transition-opacity duration-120 bg-gradient-to-r from-sun-500/20 via-saturn-500/20 to-mars-500/20" />
                  )}
                  
                  <div className="relative flex items-center gap-2">
                    <Icon className="w-4 h-4" />
                    <span>{system.name}</span>
                  </div>
                </button>
              );
            })}
          </div>

          {/* Right actions */}
          <div className="flex items-center gap-3">
            {/* Quantum Hub Toggle */}
            <button
              onClick={handleQuantumToggle}
              className={`p-2 rounded-lg transition-all duration-120 ${
                quantumHubOpen
                  ? 'bg-sun-500/20 text-sun-400'
                  : 'text-saturn-400 hover:text-white hover:bg-saturn-800/50'
              }`}
              aria-label="Toggle Quantum Hub"
            >
              <SparklesIcon className="w-5 h-5" />
            </button>

            {/* Notifications */}
            <div className="relative notification-dropdown">
              <button
                onClick={() => setShowNotifications(!showNotifications)}
                className="notification-button p-2 text-saturn-400 hover:text-white hover:bg-saturn-800/50 rounded-lg transition-all duration-120"
                aria-label="Notifications"
                aria-expanded={showNotifications}
              >
                <BellIcon className="w-5 h-5" />
                <span className="absolute top-1.5 right-1.5 w-2 h-2 bg-mars-500 rounded-full" />
              </button>
              
              {showNotifications && (
                <div className="absolute right-0 top-12 w-80 glass-neo border border-saturn-200 rounded-xl shadow-2xl p-3 animate-fadeIn z-50">
                  <h3 className="font-heading font-bold text-saturn-900 mb-2">Notifications</h3>
                  <div className="space-y-2">
                    {[1, 2, 3].map((i) => (
                      <div key={i} className="p-2 hover:bg-saturn-50 rounded-lg transition-all duration-120 cursor-pointer">
                        <p className="text-sm text-saturn-900">New trade request #{i}</p>
                        <p className="text-xs text-saturn-500 mt-1">{i * 5} mins ago</p>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>

            {/* Profile */}
            <div className="relative profile-dropdown">
              <button
                onClick={() => setShowProfile(!showProfile)}
                className="profile-button flex items-center gap-2 p-1.5 hover:bg-saturn-800/50 rounded-lg transition-all duration-120"
                aria-label="User profile"
                aria-expanded={showProfile}
              >
                <div className="w-7 h-7 rounded-lg bg-gradient-to-br from-sun-400 via-saturn-500 to-mars-500 flex items-center justify-center">
                  <span className="text-white text-xs font-bold">
                    {user?.full_name?.substring(0, 2).toUpperCase() || 'U'}
                  </span>
                </div>
                <ChevronDownIcon className="w-4 h-4 text-saturn-400" />
              </button>

              {showProfile && (
                <div className="absolute right-0 top-12 w-64 glass-neo border border-saturn-200 rounded-xl shadow-2xl overflow-hidden animate-fadeIn z-50">
                  <div className="p-4 border-b border-saturn-200">
                    <p className="font-heading font-bold text-saturn-900">{user?.full_name || 'User'}</p>
                    <p className="text-xs text-saturn-600 mt-1">{user?.email || ''}</p>
                    <p className="text-xs text-sun-600 font-medium mt-1">{user?.role || user?.user_type}</p>
                  </div>
                  <div className="p-2">
                    <button
                      onClick={() => {
                        setShowProfile(false);
                        navigate('/backoffice/settings/profile');
                      }}
                      className="w-full flex items-center gap-2 px-3 py-2 hover:bg-saturn-50 rounded-lg transition-all duration-120 text-left"
                    >
                      <UserCircleIcon className="w-4 h-4 text-saturn-600" />
                      <span className="text-sm text-saturn-900">Profile</span>
                    </button>
                    <button
                      onClick={() => {
                        setShowProfile(false);
                        navigate('/backoffice/settings/sessions');
                      }}
                      className="w-full flex items-center gap-2 px-3 py-2 hover:bg-saturn-50 rounded-lg transition-all duration-120 text-left"
                    >
                      <CogIcon className="w-4 h-4 text-saturn-600" />
                      <span className="text-sm text-saturn-900">Sessions</span>
                    </button>
                    <hr className="my-2 border-saturn-200" />
                    <button 
                      onClick={handleLogout}
                      className="w-full flex items-center gap-2 px-3 py-2 hover:bg-mars-50 rounded-lg transition-all duration-120"
                    >
                      <ArrowRightOnRectangleIcon className="w-4 h-4 text-mars-600" />
                      <span className="text-sm text-mars-700">Logout</span>
                    </button>
                  </div>
                </div>
              )}
            </div>
          </div>
        </div>
      </header>

      {/* Main Content Area - Full width adaptive workspace */}
      <main
        className={`pt-14 pb-8 ${
          quantumHubOpen ? 'pr-0 xl:pr-80' : 'pr-0'
        } transition-all duration-300 ease-in-out min-h-screen`}
      >
        <div className="p-4 md:p-6">
          <Outlet />
        </div>
      </main>

      {/* Quantum Hub Panel */}
      <QuantumHub isOpen={quantumHubOpen} onClose={() => setQuantumHubOpen(false)} />

      {/* Footer Status Strip */}
      <footer className="fixed bottom-0 left-0 right-0 h-8 bg-gradient-to-r from-space-900 via-space-800 to-space-900 border-t border-saturn-700/30 z-20">
        <div className="h-full px-6 flex items-center justify-between text-xs">
          <div className="flex items-center gap-6">
            <div className="flex items-center gap-2">
              <div className="w-2 h-2 bg-emerald-500 rounded-full shadow-sm shadow-emerald-500/50" />
              <span className="text-saturn-300 font-mono">Exchange Online</span>
            </div>
            <div className="flex items-center gap-2">
              <span className="text-saturn-400 font-mono">Node Sync:</span>
              <span className="text-emerald-400 font-mono font-bold">100%</span>
            </div>
            <div className="flex items-center gap-2">
              <span className="text-saturn-400 font-mono">Last Compliance Event:</span>
              <span className="text-sun-400 font-mono">2 mins ago</span>
            </div>
          </div>
          <div className="flex items-center gap-2">
            <span className="text-saturn-400 font-mono">v2.0.40</span>
            <span className="text-saturn-600">•</span>
            <span className="text-saturn-300 font-mono">{new Date().toLocaleTimeString()}</span>
          </div>
        </div>
      </footer>
    </div>
  );
}
