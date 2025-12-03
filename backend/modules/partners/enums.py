"""
Business Partner Enums

All partner type enumerations for type safety
"""

from enum import Enum


class ServiceProviderType(str, Enum):
    """Service provider sub-types"""
    BROKER = "broker"
    SUB_BROKER = "sub_broker"
    TRANSPORTER = "transporter"
    CONTROLLER = "controller"
    FINANCER = "financer"
    SHIPPING_AGENT = "shipping_agent"


class TransporterType(str, Enum):
    """Transporter sub-types"""
    LORRY_OWNER = "lorry_owner"  # Has own vehicles - needs RC, Insurance, Fitness
    COMMISSION_AGENT = "commission_agent"  # Arranges transport - NO vehicle docs needed


class PartnerStatus(str, Enum):
    """Partner approval status"""
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    SUSPENDED = "suspended"
    INACTIVE = "inactive"


class KYCStatus(str, Enum):
    """KYC verification status"""
    PENDING = "pending"
    VERIFIED = "verified"
    EXPIRED = "expired"
    RENEWAL_REQUIRED = "renewal_required"


class RiskCategory(str, Enum):
    """Risk assessment categories"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class BusinessEntityType(str, Enum):
    """
    Legal entity types for business entities (non-service providers).
    Used when entity_class = 'business_entity'
    """
    PROPRIETORSHIP = "proprietorship"
    PARTNERSHIP = "partnership"
    LLP = "llp"
    PRIVATE_LIMITED = "private_limited"
    PUBLIC_LIMITED = "public_limited"
    LLC = "llc"
    CORPORATION = "corporation"
    TRUST = "trust"
    SOCIETY = "society"
    FOREIGN_ENTITY = "foreign_entity"  # For foreign companies


class LocationType(str, Enum):
    """Location classifications"""
    PRINCIPAL = "principal"
    ADDITIONAL_SAME_STATE = "additional_same_state"
    BRANCH_DIFFERENT_STATE = "branch_different_state"
    WAREHOUSE = "warehouse"
    FACTORY = "factory"
    SHIP_TO = "ship_to"
    BILL_TO = "bill_to"
    PORT = "port"
    ICD = "icd"


class DocumentType(str, Enum):
    """Document types"""
    # Indian Domestic Trading Documents
    GST_CERTIFICATE = "gst_certificate"
    PAN_CARD = "pan_card"
    
    # Indian Import/Export Documents
    IEC = "iec"  # Import Export Code - Requires GST+PAN
    
    # Foreign Entity Documents
    FOREIGN_TAX_ID = "foreign_tax_id"  # Foreign company tax registration
    FOREIGN_IMPORT_LICENSE = "foreign_import_license"  # Foreign import license
    FOREIGN_EXPORT_LICENSE = "foreign_export_license"  # Foreign export license
    
    # Banking Documents
    BANK_PROOF = "bank_proof"
    CANCELLED_CHEQUE = "cancelled_cheque"
    BANK_STATEMENT = "bank_statement"  # International
    
    # Vehicle Documents (Transporter - Lorry Owner only)
    VEHICLE_RC = "vehicle_rc"  # Only for LORRY OWNERS
    VEHICLE_INSURANCE = "vehicle_insurance"  # Only for LORRY OWNERS
    VEHICLE_FITNESS = "vehicle_fitness"  # Only for LORRY OWNERS
    VEHICLE_PERMIT = "vehicle_permit"  # Only for LORRY OWNERS
    
    # General Business Documents
    TRADE_LICENSE = "trade_license"
    INCORPORATION_CERT = "incorporation_cert"
    NO_GST_DECLARATION = "no_gst_declaration"
    FINANCIAL_STATEMENT = "financial_statement"
    ITR = "itr"
    TAX_ID_CERTIFICATE = "tax_id_certificate"  # International
    BUSINESS_REGISTRATION = "business_registration"  # International
    ADDRESS_PROOF = "address_proof"  # International
    
    # Service Provider Specific Documents
    LAB_ACCREDITATION = "lab_accreditation"  # Controller
    EQUIPMENT_CALIBRATION = "equipment_calibration"  # Controller
    INSPECTOR_QUALIFICATION = "inspector_qualification"  # Controller
    NBFC_LICENSE = "nbfc_license"  # Financer
    CREDIT_RATING = "credit_rating"  # Financer
    BOARD_RESOLUTION = "board_resolution"  # Financer
    CHA_LICENSE = "cha_license"  # Shipping Agent
    SHIPPING_LINE_AGREEMENT = "shipping_line_agreement"  # Shipping Agent
    PORT_REGISTRATION = "port_registration"  # Shipping Agent


class AmendmentType(str, Enum):
    """Types of amendments"""
    ADD_LOCATION = "add_location"
    CHANGE_BANK = "change_bank"
    UPDATE_GST = "update_gst"
    INCREASE_CREDIT_LIMIT = "increase_credit_limit"
    ADD_EMPLOYEE = "add_employee"
    UPDATE_CONTACT = "update_contact"
    UPDATE_ADDRESS = "update_address"
    ADD_VEHICLE = "add_vehicle"
