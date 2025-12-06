/**
 * Location CRUD Modal
 * Modal component for creating/editing locations with Google Places integration
 */

import { useState, useEffect, useRef } from 'react';
import Modal from '@/components/common/Modal';
import { useToast } from '@/contexts/ToastContext';
import locationService from '@/services/api/locationService';
import type { Location } from '@/types/settings';

interface LocationModalProps {
  isOpen: boolean;
  onClose: () => void;
  location?: Location;
  onSuccess: () => void;
}

export function LocationModal({ isOpen, onClose, location, onSuccess }: LocationModalProps) {
  const toast = useToast();
  const [loading, setLoading] = useState(false);
  const addressInputRef = useRef<HTMLInputElement>(null);
  const autocompleteRef = useRef<any>(null); // Google Maps types

  const [formData, setFormData] = useState({
    name: '',
    location_type: 'warehouse',
    address_line1: '',
    address_line2: '',
    city: '',
    state: '',
    country: '',
    postal_code: '',
    latitude: null as number | null,
    longitude: null as number | null,
    google_place_id: '',
    contact_person: '',
    contact_phone: '',
    contact_email: '',
    is_active: true,
  });

  useEffect(() => {
    if (location) {
      setFormData({
        name: location.name,
        location_type: location.location_type,
        address_line1: location.address_line1 || '',
        address_line2: location.address_line2 || '',
        city: location.city || '',
        state: location.state || '',
        country: location.country || '',
        postal_code: location.postal_code || '',
        latitude: location.latitude,
        longitude: location.longitude,
        google_place_id: location.google_place_id || '',
        contact_person: location.contact_person || '',
        contact_phone: location.contact_phone || '',
        contact_email: location.contact_email || '',
        is_active: location.is_active,
      });
    } else {
      setFormData({
        name: '',
        location_type: 'warehouse',
        address_line1: '',
        address_line2: '',
        city: '',
        state: '',
        country: '',
        postal_code: '',
        latitude: null,
        longitude: null,
        google_place_id: '',
        contact_person: '',
        contact_phone: '',
        contact_email: '',
        is_active: true,
      });
    }
  }, [location, isOpen]);

  // Initialize Google Places Autocomplete
  useEffect(() => {
    if (isOpen && addressInputRef.current && typeof (window as any).google !== 'undefined') {
      try {
        const google = (window as any).google;
        autocompleteRef.current = new google.maps.places.Autocomplete(
          addressInputRef.current,
          {
            types: ['address'],
            fields: ['address_components', 'formatted_address', 'geometry', 'place_id', 'name'],
          }
        );

        autocompleteRef.current.addListener('place_changed', () => {
          const place = autocompleteRef.current?.getPlace();
          if (place && place.address_components) {
            handlePlaceSelect(place);
          }
        });
      } catch (error) {
        console.warn('Google Places API not available:', error);
      }
    }

    return () => {
      if (autocompleteRef.current && typeof (window as any).google !== 'undefined') {
        (window as any).google.maps.event.clearInstanceListeners(autocompleteRef.current);
      }
    };
  }, [isOpen]);

  const handlePlaceSelect = (place: any) => {
    let address1 = '';
    let city = '';
    let state = '';
    let country = '';
    let postalCode = '';

    // Extract address components
    place.address_components?.forEach((component: any) => {
      const types = component.types;
      
      if (types.includes('street_number')) {
        address1 = component.long_name + ' ' + address1;
      }
      if (types.includes('route')) {
        address1 += component.long_name;
      }
      if (types.includes('locality')) {
        city = component.long_name;
      }
      if (types.includes('administrative_area_level_1')) {
        state = component.long_name;
      }
      if (types.includes('country')) {
        country = component.long_name;
      }
      if (types.includes('postal_code')) {
        postalCode = component.long_name;
      }
    });

    setFormData(prev => ({
      ...prev,
      address_line1: address1 || place.formatted_address || '',
      city,
      state,
      country,
      postal_code: postalCode,
      latitude: place.geometry?.location?.lat() || null,
      longitude: place.geometry?.location?.lng() || null,
      google_place_id: place.place_id || '',
    }));

    toast.success('Address details auto-filled from Google Places');
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    
    if (!formData.name || !formData.address_line1) {
      toast.error('Please fill in all required fields');
      return;
    }

    try {
      setLoading(true);
      if (location) {
        await locationService.updateLocation(location.id, formData);
        toast.success('Location updated successfully');
      } else {
        await locationService.createLocation(formData);
        toast.success('Location created successfully');
      }
      onSuccess();
      onClose();
    } catch (error: any) {
      toast.error(error.message || 'Failed to save location');
    } finally {
      setLoading(false);
    }
  };

  return (
    <Modal isOpen={isOpen} onClose={onClose} title={location ? 'Edit Location' : 'Add Location'} size="lg">
      <form onSubmit={handleSubmit} className="space-y-6">
        {/* Basic Information */}
        <div className="grid grid-cols-2 gap-4">
          <div>
            <label className="block text-sm font-medium text-pearl-200 mb-1">
              Location Name <span className="text-mars-400">*</span>
            </label>
            <input
              type="text"
              value={formData.name}
              onChange={(e) => setFormData({ ...formData, name: e.target.value })}
              className="w-full px-3 py-2 bg-pearl-900/50 border border-pearl-700/50 rounded text-pearl-100 focus:outline-none focus:border-sun-500"
              required
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-pearl-200 mb-1">
              Location Type <span className="text-mars-400">*</span>
            </label>
            <select
              value={formData.location_type}
              onChange={(e) => setFormData({ ...formData, location_type: e.target.value })}
              className="w-full px-3 py-2 bg-pearl-900/50 border border-pearl-700/50 rounded text-pearl-100 focus:outline-none focus:border-sun-500"
              required
            >
              <option value="warehouse">Warehouse</option>
              <option value="branch">Branch Office</option>
              <option value="factory">Factory</option>
              <option value="office">Head Office</option>
              <option value="storage">Storage Facility</option>
            </select>
          </div>
        </div>

        {/* Google Places Address Input */}
        <div>
          <label className="block text-sm font-medium text-pearl-200 mb-1">
            Search Address (Google Places) <span className="text-mars-400">*</span>
          </label>
          <input
            ref={addressInputRef}
            type="text"
            placeholder="Start typing to search address..."
            className="w-full px-3 py-2 bg-pearl-900/50 border border-pearl-700/50 rounded text-pearl-100 placeholder-pearl-500 focus:outline-none focus:border-sun-500"
          />
          <p className="text-pearl-500 text-xs mt-1">
            Type to search and select an address. Fields below will auto-populate.
          </p>
        </div>

        {/* Address Details */}
        <div className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-pearl-200 mb-1">
              Address Line 1 <span className="text-mars-400">*</span>
            </label>
            <input
              type="text"
              value={formData.address_line1}
              onChange={(e) => setFormData({ ...formData, address_line1: e.target.value })}
              className="w-full px-3 py-2 bg-pearl-900/50 border border-pearl-700/50 rounded text-pearl-100 focus:outline-none focus:border-sun-500"
              required
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-pearl-200 mb-1">Address Line 2</label>
            <input
              type="text"
              value={formData.address_line2}
              onChange={(e) => setFormData({ ...formData, address_line2: e.target.value })}
              className="w-full px-3 py-2 bg-pearl-900/50 border border-pearl-700/50 rounded text-pearl-100 focus:outline-none focus:border-sun-500"
            />
          </div>
        </div>

        {/* City, State, Country, Postal Code */}
        <div className="grid grid-cols-2 gap-4">
          <div>
            <label className="block text-sm font-medium text-pearl-200 mb-1">City</label>
            <input
              type="text"
              value={formData.city}
              onChange={(e) => setFormData({ ...formData, city: e.target.value })}
              className="w-full px-3 py-2 bg-pearl-900/50 border border-pearl-700/50 rounded text-pearl-100 focus:outline-none focus:border-sun-500"
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-pearl-200 mb-1">State/Province</label>
            <input
              type="text"
              value={formData.state}
              onChange={(e) => setFormData({ ...formData, state: e.target.value })}
              className="w-full px-3 py-2 bg-pearl-900/50 border border-pearl-700/50 rounded text-pearl-100 focus:outline-none focus:border-sun-500"
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-pearl-200 mb-1">Country</label>
            <input
              type="text"
              value={formData.country}
              onChange={(e) => setFormData({ ...formData, country: e.target.value })}
              className="w-full px-3 py-2 bg-pearl-900/50 border border-pearl-700/50 rounded text-pearl-100 focus:outline-none focus:border-sun-500"
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-pearl-200 mb-1">Postal Code</label>
            <input
              type="text"
              value={formData.postal_code}
              onChange={(e) => setFormData({ ...formData, postal_code: e.target.value })}
              className="w-full px-3 py-2 bg-pearl-900/50 border border-pearl-700/50 rounded text-pearl-100 focus:outline-none focus:border-sun-500"
            />
          </div>
        </div>

        {/* Coordinates (auto-filled, read-only) */}
        {(formData.latitude || formData.longitude) && (
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-pearl-200 mb-1">Latitude</label>
              <input
                type="text"
                value={formData.latitude || ''}
                readOnly
                className="w-full px-3 py-2 bg-pearl-900/30 border border-pearl-700/30 rounded text-pearl-300 cursor-not-allowed"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-pearl-200 mb-1">Longitude</label>
              <input
                type="text"
                value={formData.longitude || ''}
                readOnly
                className="w-full px-3 py-2 bg-pearl-900/30 border border-pearl-700/30 rounded text-pearl-300 cursor-not-allowed"
              />
            </div>
          </div>
        )}

        {/* Contact Information */}
        <div className="grid grid-cols-3 gap-4">
          <div>
            <label className="block text-sm font-medium text-pearl-200 mb-1">Contact Person</label>
            <input
              type="text"
              value={formData.contact_person}
              onChange={(e) => setFormData({ ...formData, contact_person: e.target.value })}
              className="w-full px-3 py-2 bg-pearl-900/50 border border-pearl-700/50 rounded text-pearl-100 focus:outline-none focus:border-sun-500"
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-pearl-200 mb-1">Contact Phone</label>
            <input
              type="tel"
              value={formData.contact_phone}
              onChange={(e) => setFormData({ ...formData, contact_phone: e.target.value })}
              className="w-full px-3 py-2 bg-pearl-900/50 border border-pearl-700/50 rounded text-pearl-100 focus:outline-none focus:border-sun-500"
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-pearl-200 mb-1">Contact Email</label>
            <input
              type="email"
              value={formData.contact_email}
              onChange={(e) => setFormData({ ...formData, contact_email: e.target.value })}
              className="w-full px-3 py-2 bg-pearl-900/50 border border-pearl-700/50 rounded text-pearl-100 focus:outline-none focus:border-sun-500"
            />
          </div>
        </div>

        {/* Flags */}
        <div className="flex items-center">
          <label className="flex items-center space-x-2 cursor-pointer">
            <input
              type="checkbox"
              checked={formData.is_active}
              onChange={(e) => setFormData({ ...formData, is_active: e.target.checked })}
              className="w-4 h-4 text-sun-500 bg-pearl-900 border-pearl-700 rounded focus:ring-sun-500"
            />
            <span className="text-sm text-pearl-200">Active</span>
          </label>
        </div>

        {/* Buttons */}
        <div className="flex justify-end space-x-3 pt-4 border-t border-pearl-700/30">
          <button
            type="button"
            onClick={onClose}
            className="px-4 py-2 bg-pearl-800 hover:bg-pearl-700 text-pearl-200 rounded transition-colors"
          >
            Cancel
          </button>
          <button
            type="submit"
            disabled={loading}
            className="px-4 py-2 bg-gradient-to-r from-saturn-500 to-sun-500 text-white rounded hover:from-saturn-600 hover:to-sun-600 transition-all disabled:opacity-50"
          >
            {loading ? 'Saving...' : location ? 'Update Location' : 'Create Location'}
          </button>
        </div>
      </form>
    </Modal>
  );
}
