/**
 * Capabilities Management Module
 * Capability-based authorization (replacing role-based)
 * Purpose: Manage user capabilities, role capabilities, and permission assignments
 */

import { useState, useEffect } from 'react';
import { 
  UserCircleIcon,
  ShieldCheckIcon,
  KeyIcon,
  ClockIcon,
  CheckCircleIcon,
  XCircleIcon,
  MagnifyingGlassIcon,
  FunnelIcon,
} from '@heroicons/react/24/outline';
import capabilitiesService from '@/services/api/capabilitiesService';
import type { 
  Capability, 
  UserCapabilitiesResponse,
  CapabilityCategory 
} from '@/types/capability';

export function CapabilitiesManagementPage() {
  const [allCapabilities, setAllCapabilities] = useState<Capability[]>([]);
  const [capabilitiesByCategory, setCapabilitiesByCategory] = useState<Record<string, Capability[]>>({});
  const [selectedUser, setSelectedUser] = useState<UserCapabilitiesResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [activeTab, setActiveTab] = useState<'overview' | 'users' | 'roles' | 'matrix'>('overview');
  const [searchQuery, setSearchQuery] = useState('');
  const [filterCategory, setFilterCategory] = useState<string | null>(null);

  useEffect(() => {
    loadCapabilities();
  }, []);

  const loadCapabilities = async () => {
    try {
      setLoading(true);
      const [capabilities, categorized] = await Promise.all([
        capabilitiesService.getAllCapabilities(),
        capabilitiesService.getCapabilitiesByCategory(),
      ]);
      setAllCapabilities(capabilities);
      setCapabilitiesByCategory(categorized);
    } catch (error) {
      console.error('Failed to load capabilities:', error);
    } finally {
      setLoading(false);
    }
  };

  const getCategoryColor = (category: string) => {
    const colors: Record<string, string> = {
      auth: 'emerald',
      organization: 'saturn',
      partner: 'sun',
      commodity: 'mars',
      location: 'purple',
      availability: 'blue',
      requirement: 'indigo',
      matching: 'teal',
      settings: 'gray',
      admin: 'red',
      system: 'slate',
    };
    return colors[category] || 'gray';
  };

  const stats = [
    { 
      label: 'Total Capabilities', 
      value: allCapabilities.length.toString(), 
      icon: KeyIcon, 
      color: 'saturn',
      description: 'Fine-grained permissions'
    },
    { 
      label: 'Active Users', 
      value: '12', 
      icon: UserCircleIcon, 
      color: 'sun',
      description: 'With assigned capabilities'
    },
    { 
      label: 'Permission Roles', 
      value: '8', 
      icon: ShieldCheckIcon, 
      color: 'mars',
      description: 'Capability groups'
    },
    { 
      label: 'Categories', 
      value: Object.keys(capabilitiesByCategory).length.toString(), 
      icon: FunnelIcon, 
      color: 'emerald',
      description: 'Organized by module'
    },
  ];

  const filteredCapabilities = allCapabilities.filter(cap => {
    const matchesSearch = cap.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
                         cap.code.toLowerCase().includes(searchQuery.toLowerCase()) ||
                         cap.description?.toLowerCase().includes(searchQuery.toLowerCase());
    const matchesCategory = !filterCategory || cap.category === filterCategory;
    return matchesSearch && matchesCategory;
  });

  if (loading) {
    return (
      <div className="flex items-center justify-center h-96">
        <div className="text-center">
          <div className="inline-block animate-spin rounded-full h-12 w-12 border-b-2 border-saturn-600"></div>
          <p className="mt-4 text-saturn-600">Loading capabilities...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="max-w-7xl mx-auto space-y-6 animate-fadeIn">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-heading font-bold text-space-900">
            Capabilities Management
          </h1>
          <p className="text-saturn-600 mt-1">
            Fine-grained permission control • 91 capabilities across {Object.keys(capabilitiesByCategory).length} modules
          </p>
        </div>
        <button className="px-6 py-3 bg-gradient-to-r from-saturn-500 to-sun-500 hover:from-saturn-600 hover:to-sun-600 text-white font-heading font-bold rounded-xl shadow-lg hover:shadow-xl transition-all duration-120">
          + Assign Capability
        </button>
      </div>

      {/* Stats Grid */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        {stats.map((stat, idx) => {
          const Icon = stat.icon;
          return (
            <div
              key={idx}
              className="bg-white/80 backdrop-blur-sm border-2 border-space-200/30 rounded-2xl p-5 hover:shadow-lg transition-all duration-120 hover:scale-102 cursor-pointer"
            >
              <div className="flex items-center gap-3">
                <div className={`w-12 h-12 rounded-xl bg-gradient-to-br from-${stat.color}-400 to-${stat.color}-600 flex items-center justify-center shadow-md flex-shrink-0`}>
                  <Icon className="w-6 h-6 text-white" />
                </div>
                <div className="flex-1 min-w-0">
                  <p className="text-2xl font-heading font-bold text-space-900">{stat.value}</p>
                  <p className="text-sm font-bold text-saturn-700">{stat.label}</p>
                  <p className="text-xs text-saturn-500 mt-0.5">{stat.description}</p>
                </div>
              </div>
            </div>
          );
        })}
      </div>

      {/* Tabs */}
      <div className="bg-white/80 backdrop-blur-sm border-2 border-space-200/30 rounded-2xl p-2">
        <div className="flex gap-2">
          {[
            { id: 'overview', label: 'Overview', icon: KeyIcon },
            { id: 'users', label: 'User Capabilities', icon: UserCircleIcon },
            { id: 'roles', label: 'Role Capabilities', icon: ShieldCheckIcon },
            { id: 'matrix', label: 'Permission Matrix', icon: FunnelIcon },
          ].map((tab) => {
            const Icon = tab.icon;
            return (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id as any)}
                className={`flex-1 flex items-center justify-center gap-2 px-4 py-3 rounded-xl font-heading font-bold transition-all duration-120 ${
                  activeTab === tab.id
                    ? 'bg-gradient-to-r from-saturn-500 to-sun-500 text-white shadow-lg'
                    : 'text-saturn-700 hover:bg-space-100/50'
                }`}
              >
                <Icon className="w-5 h-5" />
                <span>{tab.label}</span>
              </button>
            );
          })}
        </div>
      </div>

      {/* Search and Filter */}
      {activeTab === 'overview' && (
        <div className="bg-white/80 backdrop-blur-sm border-2 border-space-200/30 rounded-2xl p-6">
          <div className="flex gap-4 mb-6">
            <div className="flex-1 relative">
              <MagnifyingGlassIcon className="absolute left-4 top-1/2 -translate-y-1/2 w-5 h-5 text-saturn-400" />
              <input
                type="text"
                placeholder="Search capabilities..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="w-full pl-12 pr-4 py-3 border-2 border-space-200 rounded-xl focus:outline-none focus:border-saturn-400 transition-colors"
              />
            </div>
            <select
              value={filterCategory || ''}
              onChange={(e) => setFilterCategory(e.target.value || null)}
              className="px-4 py-3 border-2 border-space-200 rounded-xl focus:outline-none focus:border-saturn-400 transition-colors"
            >
              <option value="">All Categories</option>
              {Object.keys(capabilitiesByCategory).sort().map((category) => (
                <option key={category} value={category}>
                  {category.charAt(0).toUpperCase() + category.slice(1)} ({capabilitiesByCategory[category].length})
                </option>
              ))}
            </select>
          </div>

          {/* Capabilities Grid */}
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {filteredCapabilities.map((capability) => (
              <div
                key={capability.id}
                className="border-2 border-space-200/50 rounded-xl p-4 hover:shadow-md hover:border-saturn-300 transition-all duration-120 cursor-pointer group"
              >
                <div className="flex items-start gap-3">
                  <div className={`w-10 h-10 rounded-lg bg-gradient-to-br from-${getCategoryColor(capability.category)}-400 to-${getCategoryColor(capability.category)}-600 flex items-center justify-center shadow-sm flex-shrink-0`}>
                    <KeyIcon className="w-5 h-5 text-white" />
                  </div>
                  <div className="flex-1 min-w-0">
                    <h3 className="font-heading font-bold text-space-900 group-hover:text-saturn-700 transition-colors">
                      {capability.name}
                    </h3>
                    <p className="text-xs font-mono text-saturn-500 mt-0.5">{capability.code}</p>
                    {capability.description && (
                      <p className="text-sm text-saturn-600 mt-2 line-clamp-2">
                        {capability.description}
                      </p>
                    )}
                    <div className="flex items-center gap-2 mt-3">
                      <span className={`px-2 py-1 rounded-md text-xs font-bold bg-${getCategoryColor(capability.category)}-100 text-${getCategoryColor(capability.category)}-700`}>
                        {capability.category}
                      </span>
                      {capability.is_system && (
                        <span className="px-2 py-1 rounded-md text-xs font-bold bg-red-100 text-red-700">
                          SYSTEM
                        </span>
                      )}
                    </div>
                  </div>
                </div>
              </div>
            ))}
          </div>

          {filteredCapabilities.length === 0 && (
            <div className="text-center py-12">
              <KeyIcon className="w-16 h-16 text-saturn-300 mx-auto mb-4" />
              <p className="text-saturn-600 font-medium">No capabilities found</p>
              <p className="text-sm text-saturn-500 mt-1">Try adjusting your search or filter</p>
            </div>
          )}
        </div>
      )}

      {/* User Capabilities Tab */}
      {activeTab === 'users' && (
        <div className="bg-white/80 backdrop-blur-sm border-2 border-space-200/30 rounded-2xl p-6">
          <div className="text-center py-12">
            <UserCircleIcon className="w-16 h-16 text-saturn-300 mx-auto mb-4" />
            <p className="text-saturn-600 font-medium">User Capabilities Management</p>
            <p className="text-sm text-saturn-500 mt-1">Assign and manage individual user permissions</p>
            <button className="mt-6 px-6 py-3 bg-gradient-to-r from-saturn-500 to-sun-500 text-white font-heading font-bold rounded-xl shadow-lg hover:shadow-xl transition-all duration-120">
              View Users
            </button>
          </div>
        </div>
      )}

      {/* Role Capabilities Tab */}
      {activeTab === 'roles' && (
        <div className="bg-white/80 backdrop-blur-sm border-2 border-space-200/30 rounded-2xl p-6">
          <div className="text-center py-12">
            <ShieldCheckIcon className="w-16 h-16 text-saturn-300 mx-auto mb-4" />
            <p className="text-saturn-600 font-medium">Role Capabilities Management</p>
            <p className="text-sm text-saturn-500 mt-1">Configure role-based capability templates</p>
            <button className="mt-6 px-6 py-3 bg-gradient-to-r from-saturn-500 to-sun-500 text-white font-heading font-bold rounded-xl shadow-lg hover:shadow-xl transition-all duration-120">
              Manage Roles
            </button>
          </div>
        </div>
      )}

      {/* Permission Matrix Tab */}
      {activeTab === 'matrix' && (
        <div className="bg-white/80 backdrop-blur-sm border-2 border-space-200/30 rounded-2xl p-6">
          <h2 className="text-lg font-heading font-bold text-space-900 mb-4">Permission Matrix by Category</h2>
          <div className="space-y-6">
            {Object.entries(capabilitiesByCategory).sort().map(([category, capabilities]) => (
              <div key={category} className="border-2 border-space-200/50 rounded-xl p-4">
                <div className="flex items-center gap-3 mb-3">
                  <div className={`w-8 h-8 rounded-lg bg-gradient-to-br from-${getCategoryColor(category)}-400 to-${getCategoryColor(category)}-600 flex items-center justify-center shadow-sm`}>
                    <KeyIcon className="w-4 h-4 text-white" />
                  </div>
                  <div>
                    <h3 className="font-heading font-bold text-space-900">
                      {category.charAt(0).toUpperCase() + category.slice(1)}
                    </h3>
                    <p className="text-xs text-saturn-500">{capabilities.length} capabilities</p>
                  </div>
                </div>
                <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-2">
                  {capabilities.map((cap) => (
                    <div
                      key={cap.id}
                      className="flex items-center gap-2 p-2 rounded-lg hover:bg-space-50 transition-colors"
                    >
                      <CheckCircleIcon className={`w-4 h-4 text-${getCategoryColor(category)}-500 flex-shrink-0`} />
                      <span className="text-sm text-space-700 truncate">{cap.name}</span>
                    </div>
                  ))}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

export default CapabilitiesManagementPage;
