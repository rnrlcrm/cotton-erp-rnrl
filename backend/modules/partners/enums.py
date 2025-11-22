"""
Business Partner Enums

All partner type enumerations for type safety
"""

from enum import Enum


class PartnerType(str, Enum):
    """Main partner classification"""
    SELLER = "seller"
    BUYER = "buyer"
    TRADER = "trader"
    BROKER = "broker"
    SUB_BROKER = "sub_broker"
    TRANSPORTER = "transporter"
    CONTROLLER = "controller"
    FINANCER = "financer"
    SHIPPING_AGENT = "shipping_agent"
    IMPORTER = "importer"
    EXPORTER = "exporter"


class ServiceProviderType(str, Enum):
    """Service provider sub-types"""
    BROKER = "broker"
    SUB_BROKER = "sub_broker"
    TRANSPORTER = "transporter"
    CONTROLLER = "controller"
    FINANCER = "financer"
    SHIPPING_AGENT = "shipping_agent"


class TradeClassification(str, Enum):
    """For import/export classification"""
    DOMESTIC = "domestic"
    EXPORTER = "exporter"  # Foreign entity selling TO India
    IMPORTER = "importer"  # Foreign entity buying FROM India


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
    """Legal entity types"""
    PROPRIETORSHIP = "proprietorship"
    PARTNERSHIP = "partnership"
    LLP = "llp"
    PRIVATE_LIMITED = "private_limited"
    PUBLIC_LIMITED = "public_limited"
    LLC = "llc"
    CORPORATION = "corporation"
    TRUST = "trust"
    SOCIETY = "society"


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
    GST_CERTIFICATE = "gst_certificate"
    PAN_CARD = "pan_card"
    BANK_PROOF = "bank_proof"
    TRANSPORT_LICENSE = "transport_license"
    VEHICLE_RC = "vehicle_rc"
    INSURANCE_CERTIFICATE = "insurance_certificate"
    PERMIT = "permit"
    TRADE_LICENSE = "trade_license"
    INCORPORATION_CERT = "incorporation_cert"
    NO_GST_DECLARATION = "no_gst_declaration"
    FINANCIAL_STATEMENT = "financial_statement"
    ITR = "itr"
    BROKER_LICENSE = "broker_license"
    QUALITY_CERT = "quality_cert"


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
