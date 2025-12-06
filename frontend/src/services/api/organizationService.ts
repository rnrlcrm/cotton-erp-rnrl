/**
 * Organization Settings Service
 * API calls for organization management
 */

import apiClient from './apiClient';
import { API_ENDPOINTS } from '@/config/api';
import type {
  Organization,
  OrganizationCreate,
  OrganizationUpdate,
  OrganizationGST,
  OrganizationGSTCreate,
  OrganizationGSTUpdate,
  OrganizationBankAccount,
  OrganizationBankAccountCreate,
  OrganizationBankAccountUpdate,
  OrganizationFinancialYear,
  OrganizationFinancialYearCreate,
  OrganizationFinancialYearUpdate,
  OrganizationDocumentSeries,
  OrganizationDocumentSeriesCreate,
  OrganizationDocumentSeriesUpdate,
  NextDocumentNumberResponse,
} from '@/types/settings';

class OrganizationService {
  // ==================== Organization CRUD ====================
  
  async listOrganizations(skip = 0, limit = 100): Promise<Organization[]> {
    const response = await apiClient.get<Organization[]>(
      `${API_ENDPOINTS.ORGANIZATIONS.LIST}?skip=${skip}&limit=${limit}`
    );
    return response.data;
  }

  async createOrganization(data: OrganizationCreate): Promise<Organization> {
    const response = await apiClient.post<Organization>(
      API_ENDPOINTS.ORGANIZATIONS.CREATE,
      data
    );
    return response.data;
  }

  async getOrganization(orgId: string): Promise<Organization> {
    const response = await apiClient.get<Organization>(
      API_ENDPOINTS.ORGANIZATIONS.GET(orgId)
    );
    return response.data;
  }

  async updateOrganization(orgId: string, data: OrganizationUpdate): Promise<Organization> {
    const response = await apiClient.patch<Organization>(
      API_ENDPOINTS.ORGANIZATIONS.UPDATE(orgId),
      data
    );
    return response.data;
  }

  async deleteOrganization(orgId: string): Promise<void> {
    await apiClient.delete(API_ENDPOINTS.ORGANIZATIONS.DELETE(orgId));
  }

  // ==================== GST Management ====================
  
  async listGST(orgId: string): Promise<OrganizationGST[]> {
    const response = await apiClient.get<OrganizationGST[]>(
      API_ENDPOINTS.ORGANIZATIONS.GST_LIST(orgId)
    );
    return response.data;
  }

  async createGST(data: OrganizationGSTCreate): Promise<OrganizationGST> {
    const response = await apiClient.post<OrganizationGST>(
      API_ENDPOINTS.ORGANIZATIONS.GST_CREATE,
      data
    );
    return response.data;
  }

  async getGST(gstId: string): Promise<OrganizationGST> {
    const response = await apiClient.get<OrganizationGST>(
      API_ENDPOINTS.ORGANIZATIONS.GST_GET(gstId)
    );
    return response.data;
  }

  async updateGST(gstId: string, data: OrganizationGSTUpdate): Promise<OrganizationGST> {
    const response = await apiClient.patch<OrganizationGST>(
      API_ENDPOINTS.ORGANIZATIONS.GST_UPDATE(gstId),
      data
    );
    return response.data;
  }

  async deleteGST(gstId: string): Promise<void> {
    await apiClient.delete(API_ENDPOINTS.ORGANIZATIONS.GST_DELETE(gstId));
  }

  // ==================== Bank Account Management ====================
  
  async listBankAccounts(orgId: string): Promise<OrganizationBankAccount[]> {
    const response = await apiClient.get<OrganizationBankAccount[]>(
      API_ENDPOINTS.ORGANIZATIONS.BANK_LIST(orgId)
    );
    return response.data;
  }

  async createBankAccount(data: OrganizationBankAccountCreate): Promise<OrganizationBankAccount> {
    const response = await apiClient.post<OrganizationBankAccount>(
      API_ENDPOINTS.ORGANIZATIONS.BANK_CREATE,
      data
    );
    return response.data;
  }

  async getBankAccount(accountId: string): Promise<OrganizationBankAccount> {
    const response = await apiClient.get<OrganizationBankAccount>(
      API_ENDPOINTS.ORGANIZATIONS.BANK_GET(accountId)
    );
    return response.data;
  }

  async updateBankAccount(accountId: string, data: OrganizationBankAccountUpdate): Promise<OrganizationBankAccount> {
    const response = await apiClient.patch<OrganizationBankAccount>(
      API_ENDPOINTS.ORGANIZATIONS.BANK_UPDATE(accountId),
      data
    );
    return response.data;
  }

  async deleteBankAccount(accountId: string): Promise<void> {
    await apiClient.delete(API_ENDPOINTS.ORGANIZATIONS.BANK_DELETE(accountId));
  }

  // ==================== Financial Year Management ====================
  
  async listFinancialYears(orgId: string): Promise<OrganizationFinancialYear[]> {
    const response = await apiClient.get<OrganizationFinancialYear[]>(
      API_ENDPOINTS.ORGANIZATIONS.FY_LIST(orgId)
    );
    return response.data;
  }

  async createFinancialYear(data: OrganizationFinancialYearCreate): Promise<OrganizationFinancialYear> {
    const response = await apiClient.post<OrganizationFinancialYear>(
      API_ENDPOINTS.ORGANIZATIONS.FY_CREATE,
      data
    );
    return response.data;
  }

  async getFinancialYear(fyId: string): Promise<OrganizationFinancialYear> {
    const response = await apiClient.get<OrganizationFinancialYear>(
      API_ENDPOINTS.ORGANIZATIONS.FY_GET(fyId)
    );
    return response.data;
  }

  async updateFinancialYear(fyId: string, data: OrganizationFinancialYearUpdate): Promise<OrganizationFinancialYear> {
    const response = await apiClient.patch<OrganizationFinancialYear>(
      API_ENDPOINTS.ORGANIZATIONS.FY_UPDATE(fyId),
      data
    );
    return response.data;
  }

  async deleteFinancialYear(fyId: string): Promise<void> {
    await apiClient.delete(API_ENDPOINTS.ORGANIZATIONS.FY_DELETE(fyId));
  }

  // ==================== Document Series Management ====================
  
  async listDocumentSeries(orgId: string): Promise<OrganizationDocumentSeries[]> {
    const response = await apiClient.get<OrganizationDocumentSeries[]>(
      API_ENDPOINTS.ORGANIZATIONS.DOC_SERIES_LIST(orgId)
    );
    return response.data;
  }

  async createDocumentSeries(data: OrganizationDocumentSeriesCreate): Promise<OrganizationDocumentSeries> {
    const response = await apiClient.post<OrganizationDocumentSeries>(
      API_ENDPOINTS.ORGANIZATIONS.DOC_SERIES_CREATE,
      data
    );
    return response.data;
  }

  async getDocumentSeries(seriesId: string): Promise<OrganizationDocumentSeries> {
    const response = await apiClient.get<OrganizationDocumentSeries>(
      API_ENDPOINTS.ORGANIZATIONS.DOC_SERIES_GET(seriesId)
    );
    return response.data;
  }

  async updateDocumentSeries(seriesId: string, data: OrganizationDocumentSeriesUpdate): Promise<OrganizationDocumentSeries> {
    const response = await apiClient.patch<OrganizationDocumentSeries>(
      API_ENDPOINTS.ORGANIZATIONS.DOC_SERIES_UPDATE(seriesId),
      data
    );
    return response.data;
  }

  async deleteDocumentSeries(seriesId: string): Promise<void> {
    await apiClient.delete(API_ENDPOINTS.ORGANIZATIONS.DOC_SERIES_DELETE(seriesId));
  }

  async getNextDocumentNumber(orgId: string, docType: string): Promise<NextDocumentNumberResponse> {
    const response = await apiClient.post<NextDocumentNumberResponse>(
      API_ENDPOINTS.ORGANIZATIONS.NEXT_DOC_NUMBER(orgId, docType)
    );
    return response.data;
  }
}

export default new OrganizationService();
