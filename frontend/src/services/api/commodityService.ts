/**
 * Commodities Settings Service
 * API calls for commodity management
 */

import apiClient from './apiClient';
import { API_ENDPOINTS } from '@/config/api';
import type {
  Commodity,
  CommodityCreate,
  CommodityUpdate,
  CommodityVariety,
  CommodityParameter,
  TradeType,
  BargainType,
  PassingTerm,
  WeightmentTerm,
  DeliveryTerm,
  PaymentTerm,
} from '@/types/settings';

class CommodityService {
  // ==================== Commodity CRUD ====================
  
  async listCommodities(params?: { skip?: number; limit?: number; category?: string }): Promise<Commodity[]> {
    const queryParams = new URLSearchParams();
    if (params?.skip) queryParams.append('skip', params.skip.toString());
    if (params?.limit) queryParams.append('limit', params.limit.toString());
    if (params?.category) queryParams.append('category', params.category);
    
    const response = await apiClient.get<Commodity[]>(
      `${API_ENDPOINTS.COMMODITIES.LIST}?${queryParams.toString()}`
    );
    return response.data;
  }

  async createCommodity(data: CommodityCreate): Promise<Commodity> {
    const response = await apiClient.post<Commodity>(
      API_ENDPOINTS.COMMODITIES.CREATE,
      data
    );
    return response.data;
  }

  async getCommodity(commodityId: string): Promise<Commodity> {
    const response = await apiClient.get<Commodity>(
      API_ENDPOINTS.COMMODITIES.GET(commodityId)
    );
    return response.data;
  }

  async updateCommodity(commodityId: string, data: CommodityUpdate): Promise<Commodity> {
    const response = await apiClient.put<Commodity>(
      API_ENDPOINTS.COMMODITIES.UPDATE(commodityId),
      data
    );
    return response.data;
  }

  async deleteCommodity(commodityId: string): Promise<void> {
    await apiClient.delete(API_ENDPOINTS.COMMODITIES.DELETE(commodityId));
  }

  async searchCommodities(filters: any): Promise<Commodity[]> {
    const response = await apiClient.get<Commodity[]>(
      API_ENDPOINTS.COMMODITIES.SEARCH_ADVANCED,
      { params: filters }
    );
    return response.data;
  }

  // ==================== Variety Management ====================
  
  async listVarieties(commodityId: string): Promise<CommodityVariety[]> {
    const response = await apiClient.get<CommodityVariety[]>(
      API_ENDPOINTS.COMMODITIES.VARIETY_LIST(commodityId)
    );
    return response.data;
  }

  async createVariety(commodityId: string, data: { name: string; description?: string }): Promise<CommodityVariety> {
    const response = await apiClient.post<CommodityVariety>(
      API_ENDPOINTS.COMMODITIES.VARIETY_CREATE(commodityId),
      data
    );
    return response.data;
  }

  async updateVariety(varietyId: string, data: { name?: string; description?: string; is_active?: boolean }): Promise<CommodityVariety> {
    const response = await apiClient.put<CommodityVariety>(
      API_ENDPOINTS.COMMODITIES.VARIETY_UPDATE(varietyId),
      data
    );
    return response.data;
  }

  // ==================== Parameter Management ====================
  
  async listParameters(commodityId: string): Promise<CommodityParameter[]> {
    const response = await apiClient.get<CommodityParameter[]>(
      API_ENDPOINTS.COMMODITIES.PARAMETER_LIST(commodityId)
    );
    return response.data;
  }

  async createParameter(commodityId: string, data: any): Promise<CommodityParameter> {
    const response = await apiClient.post<CommodityParameter>(
      API_ENDPOINTS.COMMODITIES.PARAMETER_CREATE(commodityId),
      data
    );
    return response.data;
  }

  async updateParameter(parameterId: string, data: any): Promise<CommodityParameter> {
    const response = await apiClient.put<CommodityParameter>(
      API_ENDPOINTS.COMMODITIES.PARAMETER_UPDATE(parameterId),
      data
    );
    return response.data;
  }

  // ==================== System Parameters ====================
  
  async listSystemParameters(): Promise<any[]> {
    const response = await apiClient.get<any[]>(
      API_ENDPOINTS.COMMODITIES.SYSTEM_PARAM_LIST
    );
    return response.data;
  }

  async createSystemParameter(data: any): Promise<any> {
    const response = await apiClient.post<any>(
      API_ENDPOINTS.COMMODITIES.SYSTEM_PARAM_CREATE,
      data
    );
    return response.data;
  }

  async updateSystemParameter(parameterId: string, data: any): Promise<any> {
    const response = await apiClient.put<any>(
      API_ENDPOINTS.COMMODITIES.SYSTEM_PARAM_UPDATE(parameterId),
      data
    );
    return response.data;
  }

  // ==================== Trade Types ====================
  
  async listTradeTypes(): Promise<TradeType[]> {
    const response = await apiClient.get<TradeType[]>(
      API_ENDPOINTS.COMMODITIES.TRADE_TYPE_LIST
    );
    return response.data;
  }

  async createTradeType(data: { name: string; description?: string }): Promise<TradeType> {
    const response = await apiClient.post<TradeType>(
      API_ENDPOINTS.COMMODITIES.TRADE_TYPE_CREATE,
      data
    );
    return response.data;
  }

  async updateTradeType(tradeTypeId: string, data: { name?: string; description?: string; is_active?: boolean }): Promise<TradeType> {
    const response = await apiClient.put<TradeType>(
      API_ENDPOINTS.COMMODITIES.TRADE_TYPE_UPDATE(tradeTypeId),
      data
    );
    return response.data;
  }

  // ==================== Bargain Types ====================
  
  async listBargainTypes(): Promise<BargainType[]> {
    const response = await apiClient.get<BargainType[]>(
      API_ENDPOINTS.COMMODITIES.BARGAIN_TYPE_LIST
    );
    return response.data;
  }

  async createBargainType(data: { name: string; description?: string }): Promise<BargainType> {
    const response = await apiClient.post<BargainType>(
      API_ENDPOINTS.COMMODITIES.BARGAIN_TYPE_CREATE,
      data
    );
    return response.data;
  }

  async updateBargainType(bargainTypeId: string, data: { name?: string; description?: string; is_active?: boolean }): Promise<BargainType> {
    const response = await apiClient.put<BargainType>(
      API_ENDPOINTS.COMMODITIES.BARGAIN_TYPE_UPDATE(bargainTypeId),
      data
    );
    return response.data;
  }

  // ==================== Passing Terms ====================
  
  async listPassingTerms(): Promise<PassingTerm[]> {
    const response = await apiClient.get<PassingTerm[]>(
      API_ENDPOINTS.COMMODITIES.PASSING_TERM_LIST
    );
    return response.data;
  }

  async createPassingTerm(data: { name: string; description?: string }): Promise<PassingTerm> {
    const response = await apiClient.post<PassingTerm>(
      API_ENDPOINTS.COMMODITIES.PASSING_TERM_CREATE,
      data
    );
    return response.data;
  }

  async updatePassingTerm(termId: string, data: { name?: string; description?: string; is_active?: boolean }): Promise<PassingTerm> {
    const response = await apiClient.put<PassingTerm>(
      API_ENDPOINTS.COMMODITIES.PASSING_TERM_UPDATE(termId),
      data
    );
    return response.data;
  }

  // ==================== Weightment Terms ====================
  
  async listWeightmentTerms(): Promise<WeightmentTerm[]> {
    const response = await apiClient.get<WeightmentTerm[]>(
      API_ENDPOINTS.COMMODITIES.WEIGHTMENT_TERM_LIST
    );
    return response.data;
  }

  async createWeightmentTerm(data: { name: string; description?: string }): Promise<WeightmentTerm> {
    const response = await apiClient.post<WeightmentTerm>(
      API_ENDPOINTS.COMMODITIES.WEIGHTMENT_TERM_CREATE,
      data
    );
    return response.data;
  }

  async updateWeightmentTerm(termId: string, data: { name?: string; description?: string; is_active?: boolean }): Promise<WeightmentTerm> {
    const response = await apiClient.put<WeightmentTerm>(
      API_ENDPOINTS.COMMODITIES.WEIGHTMENT_TERM_UPDATE(termId),
      data
    );
    return response.data;
  }

  // ==================== Delivery Terms ====================
  
  async listDeliveryTerms(): Promise<DeliveryTerm[]> {
    const response = await apiClient.get<DeliveryTerm[]>(
      API_ENDPOINTS.COMMODITIES.DELIVERY_TERM_LIST
    );
    return response.data;
  }

  async createDeliveryTerm(data: { name: string; description?: string }): Promise<DeliveryTerm> {
    const response = await apiClient.post<DeliveryTerm>(
      API_ENDPOINTS.COMMODITIES.DELIVERY_TERM_CREATE,
      data
    );
    return response.data;
  }

  async updateDeliveryTerm(termId: string, data: { name?: string; description?: string; is_active?: boolean }): Promise<DeliveryTerm> {
    const response = await apiClient.put<DeliveryTerm>(
      API_ENDPOINTS.COMMODITIES.DELIVERY_TERM_UPDATE(termId),
      data
    );
    return response.data;
  }

  // ==================== Payment Terms ====================
  
  async listPaymentTerms(): Promise<PaymentTerm[]> {
    const response = await apiClient.get<PaymentTerm[]>(
      API_ENDPOINTS.COMMODITIES.PAYMENT_TERM_LIST
    );
    return response.data;
  }

  async createPaymentTerm(data: { name: string; description?: string; days?: number }): Promise<PaymentTerm> {
    const response = await apiClient.post<PaymentTerm>(
      API_ENDPOINTS.COMMODITIES.PAYMENT_TERM_CREATE,
      data
    );
    return response.data;
  }

  async updatePaymentTerm(termId: string, data: { name?: string; description?: string; days?: number; is_active?: boolean }): Promise<PaymentTerm> {
    const response = await apiClient.put<PaymentTerm>(
      API_ENDPOINTS.COMMODITIES.PAYMENT_TERM_UPDATE(termId),
      data
    );
    return response.data;
  }

  // ==================== AI Helpers ====================
  
  async detectCategory(commodityName: string): Promise<any> {
    const response = await apiClient.post<any>(
      API_ENDPOINTS.COMMODITIES.AI_DETECT_CATEGORY,
      { commodity_name: commodityName }
    );
    return response.data;
  }

  async suggestHSN(commodityName: string, category: string): Promise<any> {
    const response = await apiClient.post<any>(
      API_ENDPOINTS.COMMODITIES.AI_SUGGEST_HSN,
      { commodity_name: commodityName, category }
    );
    return response.data;
  }

  async suggestInternationalFields(commodityName: string, category: string): Promise<any> {
    const response = await apiClient.post<any>(
      API_ENDPOINTS.COMMODITIES.AI_SUGGEST_INTERNATIONAL,
      { commodity_name: commodityName, category }
    );
    return response.data;
  }

  async suggestParameters(commodityId: string): Promise<any[]> {
    const response = await apiClient.post<any[]>(
      API_ENDPOINTS.COMMODITIES.AI_SUGGEST_PARAMETERS(commodityId)
    );
    return response.data;
  }

  // ==================== Unit Conversion ====================
  
  async calculateConversion(commodityId: string, data: any): Promise<any> {
    const response = await apiClient.post<any>(
      API_ENDPOINTS.COMMODITIES.CALCULATE_CONVERSION(commodityId),
      data
    );
    return response.data;
  }

  async listUnits(): Promise<any> {
    const response = await apiClient.get<any>(
      API_ENDPOINTS.COMMODITIES.UNITS_LIST
    );
    return response.data;
  }

  // ==================== Bulk Operations ====================
  
  async uploadBulk(file: File): Promise<any> {
    const formData = new FormData();
    formData.append('file', file);
    
    const response = await apiClient.post<any>(
      API_ENDPOINTS.COMMODITIES.BULK_UPLOAD,
      formData,
      {
        headers: {
          'Content-Type': 'multipart/form-data',
        },
      }
    );
    return response.data;
  }

  async downloadBulk(): Promise<Blob> {
    const response = await apiClient.get<Blob>(
      API_ENDPOINTS.COMMODITIES.BULK_DOWNLOAD,
      { responseType: 'blob' }
    );
    return response.data;
  }

  async validateBulk(file: File): Promise<any> {
    const formData = new FormData();
    formData.append('file', file);
    
    const response = await apiClient.post<any>(
      API_ENDPOINTS.COMMODITIES.BULK_VALIDATE,
      formData,
      {
        headers: {
          'Content-Type': 'multipart/form-data',
        },
      }
    );
    return response.data;
  }
}

export default new CommodityService();
