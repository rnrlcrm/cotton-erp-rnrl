/**
 * Settings Module Types
 * Matching backend schemas for Organization, Commodities, and Locations
 */

// ==================== Organization Types ====================

export interface Organization {
  id: string;
  name: string;
  legal_name: string | null;
  type: string | null;
  CIN: string | null;
  PAN: string | null;
  base_currency: string;
  address_line1: string | null;
  address_line2: string | null;
  city: string | null;
  state: string | null;
  pincode: string | null;
  contact_email: string | null;
  contact_phone: string | null;
  is_active: boolean;
  threshold_limit: number | null;
  einvoice_required: boolean;
  auto_block_if_einvoice_required: boolean;
  fx_enabled: boolean;
  logo_url: string | null;
  theme_color: string | null;
  invoice_footer: string | null;
  digital_signature_url: string | null;
  tds_rate: number | null;
  tcs_rate: number | null;
  audit_firm_name: string | null;
  audit_firm_email: string | null;
  audit_firm_phone: string | null;
  gst_audit_required: boolean;
  auto_invoice: boolean;
  auto_contract_number: boolean;
  extra_config: Record<string, any>;
  created_at: string;
  updated_at: string | null;
}

export interface OrganizationCreate {
  name: string;
  legal_name?: string | null;
  type?: string | null;
  CIN?: string | null;
  PAN?: string | null;
  base_currency?: string;
  address_line1?: string | null;
  address_line2?: string | null;
  city?: string | null;
  state?: string | null;
  pincode?: string | null;
  contact_email?: string | null;
  contact_phone?: string | null;
  threshold_limit?: number | null;
  einvoice_required?: boolean;
  auto_block_if_einvoice_required?: boolean;
  fx_enabled?: boolean;
  logo_url?: string | null;
  theme_color?: string | null;
  invoice_footer?: string | null;
  digital_signature_url?: string | null;
  tds_rate?: number | null;
  tcs_rate?: number | null;
  audit_firm_name?: string | null;
  audit_firm_email?: string | null;
  audit_firm_phone?: string | null;
  gst_audit_required?: boolean;
  auto_invoice?: boolean;
  auto_contract_number?: boolean;
  extra_config?: Record<string, any>;
}

export interface OrganizationUpdate extends Partial<OrganizationCreate> {
  is_active?: boolean;
}

export interface OrganizationGST {
  id: string;
  organization_id: string;
  gstin: string;
  legal_name: string | null;
  address: string | null;
  state: string | null;
  branch_code: string | null;
  is_primary: boolean;
  is_active: boolean;
  created_at: string;
  updated_at: string | null;
}

export interface OrganizationGSTCreate {
  organization_id: string;
  gstin: string;
  legal_name?: string | null;
  address?: string | null;
  state?: string | null;
  branch_code?: string | null;
  is_primary?: boolean;
}

export interface OrganizationGSTUpdate {
  legal_name?: string | null;
  address?: string | null;
  state?: string | null;
  branch_code?: string | null;
  is_primary?: boolean;
  is_active?: boolean;
}

export interface OrganizationBankAccount {
  id: string;
  organization_id: string;
  bank_name: string;
  account_number: string;
  account_holder_name: string;
  ifsc_code: string;
  branch_name: string | null;
  account_type: string | null;
  is_primary: boolean;
  is_active: boolean;
  created_at: string;
  updated_at: string | null;
}

export interface OrganizationBankAccountCreate {
  organization_id: string;
  bank_name: string;
  account_number: string;
  account_holder_name: string;
  ifsc_code: string;
  branch_name?: string | null;
  account_type?: string | null;
  is_primary?: boolean;
}

export interface OrganizationBankAccountUpdate {
  bank_name?: string;
  account_holder_name?: string;
  ifsc_code?: string;
  branch_name?: string | null;
  account_type?: string | null;
  is_primary?: boolean;
  is_active?: boolean;
}

export interface OrganizationFinancialYear {
  id: string;
  organization_id: string;
  year_name: string;
  start_date: string;
  end_date: string;
  is_active: boolean;
  is_current: boolean;
  created_at: string;
  updated_at: string | null;
}

export interface OrganizationFinancialYearCreate {
  organization_id: string;
  year_name: string;
  start_date: string;
  end_date: string;
  is_current?: boolean;
}

export interface OrganizationFinancialYearUpdate {
  year_name?: string;
  start_date?: string;
  end_date?: string;
  is_active?: boolean;
  is_current?: boolean;
}

export interface OrganizationDocumentSeries {
  id: string;
  organization_id: string;
  document_type: string;
  prefix: string;
  current_number: number;
  padding_length: number;
  suffix: string | null;
  is_active: boolean;
  created_at: string;
  updated_at: string | null;
}

export interface OrganizationDocumentSeriesCreate {
  organization_id: string;
  document_type: string;
  prefix: string;
  current_number?: number;
  padding_length?: number;
  suffix?: string | null;
}

export interface OrganizationDocumentSeriesUpdate {
  prefix?: string;
  current_number?: number;
  padding_length?: number;
  suffix?: string | null;
  is_active?: boolean;
}

export interface NextDocumentNumberResponse {
  next_number: string;
  current_count: number;
}

// ==================== Commodity Types ====================

export interface Commodity {
  id: string;
  name: string;
  category: string;
  hsn_code: string | null;
  gst_rate: number | null;
  description: string | null;
  uom: string | null;
  base_unit: string;
  trade_unit: string | null;
  rate_unit: string | null;
  standard_weight_per_unit: number | null;
  default_currency: string;
  supported_currencies: string[] | null;
  international_pricing_unit: string | null;
  hs_code_6digit: string | null;
  country_tax_codes: Record<string, any> | null;
  quality_standards: string[] | null;
  international_grades: Record<string, any> | null;
  certification_required: Record<string, any> | null;
  major_producing_countries: string[] | null;
  major_consuming_countries: string[] | null;
  trading_hubs: string[] | null;
  traded_on_exchanges: string[] | null;
  contract_specifications: Record<string, any> | null;
  price_volatility: string | null;
  export_regulations: Record<string, any> | null;
  import_regulations: Record<string, any> | null;
  phytosanitary_required: boolean;
  fumigation_required: boolean;
  seasonal_commodity: boolean;
  harvest_season: Record<string, any> | null;
  shelf_life_days: number | null;
  storage_conditions: Record<string, any> | null;
  standard_lot_size: Record<string, any> | null;
  min_order_quantity: Record<string, any> | null;
  delivery_tolerance_pct: number | null;
  weight_tolerance_pct: number | null;
  is_active: boolean;
  created_at: string;
  updated_at: string | null;
}

export interface CommodityCreate {
  name: string;
  category: string;
  hsn_code?: string | null;
  gst_rate?: number | null;
  description?: string | null;
  uom?: string | null;
  base_unit?: string;
  trade_unit?: string | null;
  rate_unit?: string | null;
  standard_weight_per_unit?: number | null;
  default_currency?: string;
  supported_currencies?: string[] | null;
  international_pricing_unit?: string | null;
  hs_code_6digit?: string | null;
  country_tax_codes?: Record<string, any> | null;
  quality_standards?: string[] | null;
  international_grades?: Record<string, any> | null;
  certification_required?: Record<string, any> | null;
  major_producing_countries?: string[] | null;
  major_consuming_countries?: string[] | null;
  trading_hubs?: string[] | null;
  traded_on_exchanges?: string[] | null;
  contract_specifications?: Record<string, any> | null;
  price_volatility?: string | null;
  export_regulations?: Record<string, any> | null;
  import_regulations?: Record<string, any> | null;
  phytosanitary_required?: boolean;
  fumigation_required?: boolean;
  seasonal_commodity?: boolean;
  harvest_season?: Record<string, any> | null;
  shelf_life_days?: number | null;
  storage_conditions?: Record<string, any> | null;
  standard_lot_size?: Record<string, any> | null;
  min_order_quantity?: Record<string, any> | null;
  delivery_tolerance_pct?: number | null;
  weight_tolerance_pct?: number | null;
  is_active?: boolean;
}

export interface CommodityUpdate extends Partial<CommodityCreate> {}

export interface CommodityVariety {
  id: string;
  commodity_id: string;
  name: string;
  description: string | null;
  is_active: boolean;
  created_at: string;
  updated_at: string | null;
}

export interface CommodityParameter {
  id: string;
  commodity_id: string;
  parameter_name: string;
  data_type: string;
  unit: string | null;
  min_value: number | null;
  max_value: number | null;
  default_value: string | null;
  is_required: boolean;
  display_order: number;
  created_at: string;
  updated_at: string | null;
}

export interface TradeType {
  id: string;
  name: string;
  description: string | null;
  is_active: boolean;
  created_at: string;
  updated_at: string | null;
}

export interface BargainType {
  id: string;
  name: string;
  description: string | null;
  is_active: boolean;
  created_at: string;
  updated_at: string | null;
}

export interface PassingTerm {
  id: string;
  name: string;
  description: string | null;
  is_active: boolean;
  created_at: string;
  updated_at: string | null;
}

export interface WeightmentTerm {
  id: string;
  name: string;
  description: string | null;
  is_active: boolean;
  created_at: string;
  updated_at: string | null;
}

export interface DeliveryTerm {
  id: string;
  name: string;
  description: string | null;
  is_active: boolean;
  created_at: string;
  updated_at: string | null;
}

export interface PaymentTerm {
  id: string;
  name: string;
  description: string | null;
  days: number | null;
  is_active: boolean;
  created_at: string;
  updated_at: string | null;
}

// ==================== Location Types ====================

export interface Location {
  id: string;
  name: string;
  location_type: string;
  google_place_id: string | null;
  address_line1: string | null;
  address_line2: string | null;
  city: string | null;
  state: string | null;
  country: string | null;
  postal_code: string | null;
  latitude: number | null;
  longitude: number | null;
  contact_person: string | null;
  contact_phone: string | null;
  contact_email: string | null;
  is_active: boolean;
  created_at: string;
  updated_at: string | null;
}

export interface LocationCreate {
  name: string;
  location_type: string;
  google_place_id?: string | null;
  address_line1?: string | null;
  address_line2?: string | null;
  city?: string | null;
  state?: string | null;
  country?: string | null;
  postal_code?: string | null;
  latitude?: number | null;
  longitude?: number | null;
  contact_person?: string | null;
  contact_phone?: string | null;
  contact_email?: string | null;
}

export interface LocationUpdate extends Partial<LocationCreate> {
  is_active?: boolean;
}

export interface GooglePlaceSuggestion {
  description: string;
  place_id: string;
}

export interface GooglePlaceDetails {
  name: string;
  address: string;
  city: string | null;
  state: string | null;
  country: string | null;
  postal_code: string | null;
  latitude: number;
  longitude: number;
  place_id: string;
}

export interface LocationListResponse {
  locations: Location[];
  total: number;
}
