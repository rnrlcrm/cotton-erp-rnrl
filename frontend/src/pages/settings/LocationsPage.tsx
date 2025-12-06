/**
 * Locations Settings Page
 * Manage warehouses, branches, and other locations with Google Places integration
 */

import { useState, useEffect } from 'react';
import {
  MapPinIcon,
  BuildingStorefrontIcon,
  BuildingOfficeIcon,
  PlusIcon,
  PencilIcon,
  TrashIcon,
  MagnifyingGlassIcon,
  GlobeAltIcon,
  CheckCircleIcon,
  XCircleIcon,
} from '@heroicons/react/24/outline';
import { useToast } from '@/contexts/ToastContext';
import { LocationModal } from '@/components/settings/LocationModal';
import locationService from '@/services/api/locationService';
import type { Location } from '@/types/settings';

export default function LocationsPage() {
  const toast = useToast();
  const [locations, setLocations] = useState<Location[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [filterType, setFilterType] = useState<string>('all');
  const [filterActive, setFilterActive] = useState<boolean | null>(null);
  const [searchTerm, setSearchTerm] = useState('');
  const [locationModal, setLocationModal] = useState<{ open: boolean; data?: Location }>({ open: false });

  useEffect(() => {
    loadLocations();
  }, [filterType, filterActive]);

  const loadLocations = async () => {
    try {
      setLoading(true);
      const filters: any = {};
      if (filterType !== 'all') filters.location_type = filterType;
      if (filterActive !== null) filters.is_active = filterActive;

      const data = await locationService.listLocations(filters);
      setLocations(data.locations);
    } catch (err: any) {
      setError(err.message || 'Failed to load locations');
    } finally {
      setLoading(false);
    }
  };

  const handleDeleteLocation = async (id: string) => {
    if (!confirm('Are you sure you want to delete this location?')) return;
    try {
      await locationService.deleteLocation(id);
      toast.success('Location deleted successfully');
      loadLocations();
    } catch (error: any) {
      toast.error(error.message || 'Failed to delete location');
    }
  };

  const filteredLocations = locations.filter(loc => {
    const address = `${loc.address_line1 || ''} ${loc.address_line2 || ''}`.trim();
    return (
      loc.name.toLowerCase().includes(searchTerm.toLowerCase()) ||
      address.toLowerCase().includes(searchTerm.toLowerCase()) ||
      (loc.city && loc.city.toLowerCase().includes(searchTerm.toLowerCase()))
    );
  });

  const locationTypes = [
    { value: 'all', label: 'All Types' },
    { value: 'warehouse', label: 'Warehouse' },
    { value: 'branch', label: 'Branch' },
    { value: 'factory', label: 'Factory' },
    { value: 'office', label: 'Office' },
  ];

  const getLocationIcon = (type: string) => {
    switch (type?.toLowerCase()) {
      case 'warehouse':
        return BuildingStorefrontIcon;
      case 'branch':
      case 'office':
        return BuildingOfficeIcon;
      default:
        return MapPinIcon;
    }
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-space-900 via-space-800 to-saturn-900 p-6">
        <div className="flex items-center justify-center h-96">
          <div className="text-pearl-100">Loading locations...</div>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-space-900 via-space-800 to-saturn-900 p-6">
        <div className="bg-mars-500/20 border border-mars-500/30 rounded-lg p-4">
          <p className="text-mars-200">{error}</p>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-space-900 via-space-800 to-saturn-900 p-6">
      {/* Header */}
      <div className="mb-6">
        <h1 className="text-3xl font-bold bg-gradient-to-r from-sun-400 to-saturn-400 bg-clip-text text-transparent">
          Location Settings
        </h1>
        <p className="text-pearl-300 mt-2">Manage warehouses, branches, and other locations</p>
      </div>

      {/* Filters and Search */}
      <div className="mb-6 bg-pearl-900/20 backdrop-blur-sm border border-pearl-700/30 rounded-xl p-4">
        <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4">
          {/* Type Filter */}
          <div className="flex items-center space-x-4">
            <label className="text-pearl-300 text-sm font-medium">Type:</label>
            <div className="flex space-x-2">
              {locationTypes.map((type) => (
                <button
                  key={type.value}
                  onClick={() => setFilterType(type.value)}
                  className={`px-3 py-1.5 rounded-lg text-sm transition-all ${
                    filterType === type.value
                      ? 'bg-gradient-to-r from-saturn-500 to-sun-500 text-white'
                      : 'bg-pearl-800/50 text-pearl-300 hover:bg-pearl-800'
                  }`}
                >
                  {type.label}
                </button>
              ))}
            </div>
          </div>

          {/* Active Filter */}
          <div className="flex items-center space-x-4">
            <label className="text-pearl-300 text-sm font-medium">Status:</label>
            <div className="flex space-x-2">
              <button
                onClick={() => setFilterActive(null)}
                className={`px-3 py-1.5 rounded-lg text-sm transition-all ${
                  filterActive === null
                    ? 'bg-gradient-to-r from-saturn-500 to-sun-500 text-white'
                    : 'bg-pearl-800/50 text-pearl-300 hover:bg-pearl-800'
                }`}
              >
                All
              </button>
              <button
                onClick={() => setFilterActive(true)}
                className={`px-3 py-1.5 rounded-lg text-sm transition-all ${
                  filterActive === true
                    ? 'bg-gradient-to-r from-saturn-500 to-sun-500 text-white'
                    : 'bg-pearl-800/50 text-pearl-300 hover:bg-pearl-800'
                }`}
              >
                Active
              </button>
              <button
                onClick={() => setFilterActive(false)}
                className={`px-3 py-1.5 rounded-lg text-sm transition-all ${
                  filterActive === false
                    ? 'bg-gradient-to-r from-saturn-500 to-sun-500 text-white'
                    : 'bg-pearl-800/50 text-pearl-300 hover:bg-pearl-800'
                }`}
              >
                Inactive
              </button>
            </div>
          </div>

          {/* Search */}
          <div className="flex items-center space-x-4">
            <div className="relative">
              <MagnifyingGlassIcon className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-pearl-400" />
              <input
                type="text"
                placeholder="Search locations..."
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
                className="pl-10 pr-4 py-2 bg-pearl-800/50 border border-pearl-700/30 rounded-lg text-pearl-100 placeholder-pearl-500 focus:outline-none focus:ring-2 focus:ring-sun-500"
              />
            </div>
            <button 
              onClick={() => setLocationModal({ open: true })}
              className="px-4 py-2 bg-gradient-to-r from-saturn-500 to-sun-500 text-white rounded-lg hover:from-saturn-600 hover:to-sun-600 transition-all flex items-center space-x-2"
            >
              <PlusIcon className="w-4 h-4" />
              <span>Add Location</span>
            </button>
          </div>
        </div>
      </div>

      {/* Locations Grid */}
      <div className="bg-pearl-900/20 backdrop-blur-sm border border-pearl-700/30 rounded-xl p-6">
        {filteredLocations.length === 0 ? (
          <div className="text-center py-12 text-pearl-400">
            {searchTerm ? 'No locations found matching your search' : 'No locations added yet'}
          </div>
        ) : (
          <div className="grid gap-4">
            {filteredLocations.map((location) => {
              const Icon = getLocationIcon(location.location_type);
              return (
                <div
                  key={location.id}
                  className="bg-pearl-800/30 rounded-lg p-5 border border-pearl-700/30 hover:border-sun-500/30 transition-colors"
                >
                  <div className="flex justify-between items-start">
                    <div className="flex-1">
                      {/* Header */}
                      <div className="flex items-start space-x-3">
                        <div className="p-2 bg-gradient-to-br from-saturn-500/20 to-sun-500/20 rounded-lg">
                          <Icon className="w-6 h-6 text-sun-400" />
                        </div>
                        <div className="flex-1">
                          <div className="flex items-center space-x-2">
                            <h3 className="text-pearl-100 font-semibold text-lg">{location.name}</h3>
                            <span className="px-2 py-1 bg-saturn-500/20 text-saturn-400 text-xs rounded uppercase">
                              {location.location_type}
                            </span>
                            {location.is_active ? (
                              <span className="flex items-center space-x-1 px-2 py-1 bg-moon-500/20 text-moon-400 text-xs rounded">
                                <CheckCircleIcon className="w-3 h-3" />
                                <span>Active</span>
                              </span>
                            ) : (
                              <span className="flex items-center space-x-1 px-2 py-1 bg-mars-500/20 text-mars-400 text-xs rounded">
                                <XCircleIcon className="w-3 h-3" />
                                <span>Inactive</span>
                              </span>
                            )}
                          </div>

                          {/* Address */}
                          <div className="mt-2 flex items-start space-x-2">
                            <MapPinIcon className="w-4 h-4 text-pearl-400 mt-0.5 flex-shrink-0" />
                            <p className="text-pearl-300 text-sm">
                              {location.address_line1}
                              {location.address_line2 && `, ${location.address_line2}`}
                            </p>
                          </div>

                          {/* Details Grid */}
                          <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mt-4">
                            {location.city && (
                              <div>
                                <p className="text-pearl-500 text-xs">City</p>
                                <p className="text-pearl-300 text-sm">{location.city}</p>
                              </div>
                            )}
                            {location.state && (
                              <div>
                                <p className="text-pearl-500 text-xs">State</p>
                                <p className="text-pearl-300 text-sm">{location.state}</p>
                              </div>
                            )}
                            {location.postal_code && (
                              <div>
                                <p className="text-pearl-500 text-xs">Postal Code</p>
                                <p className="text-pearl-300 text-sm">{location.postal_code}</p>
                              </div>
                            )}
                            {location.country && (
                              <div>
                                <p className="text-pearl-500 text-xs">Country</p>
                                <p className="text-pearl-300 text-sm">{location.country}</p>
                              </div>
                            )}
                          </div>

                          {/* Google Place Info */}
                          {location.google_place_id && (
                            <div className="mt-3 flex items-center space-x-2 text-xs text-pearl-400">
                              <GlobeAltIcon className="w-4 h-4" />
                              <span>Verified with Google Places</span>
                              {location.latitude && location.longitude && (
                                <span className="text-pearl-500">
                                  • {location.latitude.toFixed(6)}, {location.longitude.toFixed(6)}
                                </span>
                              )}
                            </div>
                          )}
                        </div>
                      </div>
                    </div>

                    {/* Actions */}
                    <div className="flex space-x-2">
                      <button 
                        onClick={() => setLocationModal({ open: true, data: location })}
                        className="p-2 hover:bg-pearl-700/30 rounded transition-colors"
                      >
                        <PencilIcon className="w-4 h-4 text-pearl-400" />
                      </button>
                      <button 
                        onClick={() => handleDeleteLocation(location.id)}
                        className="p-2 hover:bg-mars-500/20 rounded transition-colors"
                      >
                        <TrashIcon className="w-4 h-4 text-mars-400" />
                      </button>
                    </div>
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </div>

      {/* Location Modal */}
      <LocationModal
        isOpen={locationModal.open}
        onClose={() => setLocationModal({ open: false })}
        location={locationModal.data}
        onSuccess={loadLocations}
      />
    </div>
  );
}
