/**
 * Locations Settings Service
 * API calls for location management with Google Places integration
 */

import apiClient from './apiClient';
import { API_ENDPOINTS } from '@/config/api';
import type {
  Location,
  LocationCreate,
  LocationUpdate,
  LocationListResponse,
  GooglePlaceSuggestion,
  GooglePlaceDetails,
} from '@/types/settings';

class LocationService {
  // ==================== Location CRUD ====================
  
  async listLocations(params?: { 
    skip?: number; 
    limit?: number; 
    location_type?: string;
    is_active?: boolean;
  }): Promise<LocationListResponse> {
    const queryParams = new URLSearchParams();
    if (params?.skip) queryParams.append('skip', params.skip.toString());
    if (params?.limit) queryParams.append('limit', params.limit.toString());
    if (params?.location_type) queryParams.append('location_type', params.location_type);
    if (params?.is_active !== undefined) queryParams.append('is_active', params.is_active.toString());
    
    const response = await apiClient.get<LocationListResponse>(
      `${API_ENDPOINTS.LOCATIONS.LIST}?${queryParams.toString()}`
    );
    return response.data;
  }

  async createLocation(data: LocationCreate): Promise<Location> {
    const response = await apiClient.post<Location>(
      API_ENDPOINTS.LOCATIONS.CREATE,
      data
    );
    return response.data;
  }

  async getLocation(locationId: string): Promise<Location> {
    const response = await apiClient.get<Location>(
      API_ENDPOINTS.LOCATIONS.GET(locationId)
    );
    return response.data;
  }

  async updateLocation(locationId: string, data: LocationUpdate): Promise<Location> {
    const response = await apiClient.put<Location>(
      API_ENDPOINTS.LOCATIONS.UPDATE(locationId),
      data
    );
    return response.data;
  }

  async deleteLocation(locationId: string): Promise<void> {
    await apiClient.delete(API_ENDPOINTS.LOCATIONS.DELETE(locationId));
  }

  // ==================== Google Places Integration ====================
  
  async searchGooglePlaces(query: string): Promise<GooglePlaceSuggestion[]> {
    const response = await apiClient.post<GooglePlaceSuggestion[]>(
      API_ENDPOINTS.LOCATIONS.SEARCH_GOOGLE,
      { query }
    );
    return response.data;
  }

  async fetchPlaceDetails(placeId: string): Promise<GooglePlaceDetails> {
    const response = await apiClient.post<GooglePlaceDetails>(
      API_ENDPOINTS.LOCATIONS.FETCH_DETAILS,
      { place_id: placeId }
    );
    return response.data;
  }
}

export default new LocationService();
