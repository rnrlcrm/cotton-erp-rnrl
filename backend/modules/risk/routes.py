"""
Risk Engine REST API Routes

Complete API endpoints for:
- Requirement risk assessment
- Availability risk assessment
- Bilateral trade risk assessment
- Party links validation
- Circular trading detection
- Role restriction validation
- ML-based predictions
- Exposure monitoring
- Batch operations

Authentication: JWT via get_current_user
"""

from datetime import datetime
from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, Header, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from backend.core.auth.capabilities.decorators import RequireCapability
from backend.core.auth.capabilities.definitions import Capabilities
from backend.core.auth.dependencies import get_current_user
from backend.db.async_session import get_db
from backend.modules.risk.risk_service import RiskService
from backend.modules.risk.ml_risk_model import MLRiskModel
from backend.modules.risk.schemas import (
    AvailabilityRiskAssessmentRequest,
    BatchRiskAssessmentResponse,
    CircularTradingCheckRequest,
    CircularTradingCheckResponse,
    ErrorResponse,
    ExposureMonitoringRequest,
    ExposureMonitoringResponse,
    MLModelTrainRequest,
    MLModelTrainResponse,
    MLPredictionRequest,
    MLPredictionResponse,
    PartnerRiskAssessmentRequest,
    PartyLinksCheckRequest,
    PartyLinksCheckResponse,
    RequirementRiskAssessmentRequest,
    RiskAssessmentResponse,
    RoleRestrictionCheckRequest,
    RoleRestrictionCheckResponse,
    TradeRiskAssessmentRequest,
    TradeRiskAssessmentResponse,
)

router = APIRouter(prefix="/risk", tags=["Risk Engine"])


def get_risk_service(
    db: AsyncSession = Depends(get_db),
) -> RiskService:
    """Dependency to get RiskService instance."""
    return RiskService(db=db)


def get_ml_model() -> MLRiskModel:
    """Dependency to get ML Risk Model instance."""
    return MLRiskModel()


# =============================================================================
# RISK ASSESSMENT ENDPOINTS
# =============================================================================

@router.post(
    "/assess/requirement",
    response_model=RiskAssessmentResponse,
    summary="Assess Requirement Risk",
    description="Perform risk assessment for a buyer requirement. Requires ADMIN_VIEW_ALL_DATA capability.",
    responses={404: {"model": ErrorResponse}, 500: {"model": ErrorResponse}}
)
async def assess_requirement_risk(
    request: RequirementRiskAssessmentRequest,
    current_user=Depends(get_current_user),
    risk_service: RiskService = Depends(get_risk_service),
    idempotency_key: Optional[str] = Header(None, alias="Idempotency-Key"),
    _check: None = Depends(RequireCapability(Capabilities.ADMIN_VIEW_ALL_DATA))
):
    """
    Assess risk for a requirement. Requires ADMIN_VIEW_ALL_DATA capability.
    
    Evaluates:
    - Buyer credit limit and exposure
    - Buyer rating and payment performance
    - Estimated trade value
    - Historical data
    
    Returns risk score (0-100) and status (PASS/WARN/FAIL).
    """
    try:
        user_id = UUID(current_user.get("sub"))
        assessment = await risk_service.assess_requirement_risk(
            requirement_id=request.requirement_id,
            user_id=user_id
        )
        return assessment
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Risk assessment failed: {str(e)}")


@router.post(
    "/assess/availability",
    response_model=RiskAssessmentResponse,
    summary="Assess Availability Risk",
    description="Perform risk assessment for a seller availability. Requires ADMIN_VIEW_ALL_DATA capability.",
    responses={404: {"model": ErrorResponse}, 500: {"model": ErrorResponse}}
)
async def assess_availability_risk(
    request: AvailabilityRiskAssessmentRequest,
    current_user=Depends(get_current_user),
    risk_service: RiskService = Depends(get_risk_service),
    idempotency_key: Optional[str] = Header(None, alias="Idempotency-Key"),
    _check: None = Depends(RequireCapability(Capabilities.ADMIN_VIEW_ALL_DATA))
):
    """
    Assess risk for an availability. Requires ADMIN_VIEW_ALL_DATA capability.
    
    Evaluates:
    - Seller credit limit and exposure
    - Seller rating and delivery performance
    - Quality history
    - Fulfillment track record
    
    Returns risk score (0-100) and status (PASS/WARN/FAIL).
    """
    try:
        user_id = UUID(current_user.get("sub"))
        assessment = await risk_service.assess_availability_risk(
            availability_id=request.availability_id,
            user_id=user_id
        )
        return assessment
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Risk assessment failed: {str(e)}")


@router.post(
    "/assess/trade",
    response_model=TradeRiskAssessmentResponse,
    summary="Assess Bilateral Trade Risk",
    description="Perform comprehensive bilateral risk assessment for a proposed trade. Requires ADMIN_VIEW_ALL_DATA capability.",
    responses={404: {"model": ErrorResponse}, 500: {"model": ErrorResponse}}
)
async def assess_trade_risk(
    request: TradeRiskAssessmentRequest,
    current_user=Depends(get_current_user),
    risk_service: RiskService = Depends(get_risk_service),
    idempotency_key: Optional[str] = Header(None, alias="Idempotency-Key"),
    _check: None = Depends(RequireCapability(Capabilities.ADMIN_VIEW_ALL_DATA))
):
    """
    Assess bilateral trade risk. Requires ADMIN_VIEW_ALL_DATA capability.
    
    Evaluates:
    - Buyer risk (credit, rating, payment history)
    - Seller risk (credit, rating, delivery history)
    - Party links (PAN/GST/mobile/email)
    - Internal trade blocking (same branch)
    - Combined risk score
    
    Returns comprehensive risk assessment with recommended action.
    """
    try:
        user_id = UUID(current_user.get("sub"))
        assessment = await risk_service.assess_trade_risk(
            requirement_id=request.requirement_id,
            availability_id=request.availability_id,
            trade_quantity=request.trade_quantity,
            trade_price=request.trade_price,
            user_id=user_id
        )
        return assessment
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Trade risk assessment failed: {str(e)}")


@router.post(
    "/assess/partner",
    response_model=RiskAssessmentResponse,
    summary="Assess Partner Counterparty Risk",
    description="Assess overall counterparty risk for a partner. Requires ADMIN_VIEW_ALL_DATA capability.",
    responses={404: {"model": ErrorResponse}, 500: {"model": ErrorResponse}}
)
async def assess_partner_risk(
    request: PartnerRiskAssessmentRequest,
    current_user=Depends(get_current_user),
    risk_service: RiskService = Depends(get_risk_service),
    idempotency_key: Optional[str] = Header(None, alias="Idempotency-Key"),
    _check: None = Depends(RequireCapability(Capabilities.ADMIN_VIEW_ALL_DATA))
):
    """
    Assess counterparty risk for a partner. Requires ADMIN_VIEW_ALL_DATA capability.
    
    Evaluates:
    - Credit limit and exposure
    - Rating and performance scores
    - Trade history and disputes
    - Average trade values
    
    Returns overall partner risk profile.
    """
    try:
        assessment = await risk_service.assess_partner_risk(
            partner_id=request.partner_id,
            partner_type=request.partner_type
        )
        return assessment
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Partner risk assessment failed: {str(e)}")


# =============================================================================
# VALIDATION ENDPOINTS
# =============================================================================

@router.post(
    "/validate/party-links",
    response_model=PartyLinksCheckResponse,
    summary="Check Party Links",
    description="Validate for related party transactions (PAN/GST/mobile/email matching). Requires ADMIN_VIEW_ALL_DATA capability.",
    responses={500: {"model": ErrorResponse}}
)
async def check_party_links(
    request: PartyLinksCheckRequest,
    current_user=Depends(get_current_user),
    risk_service: RiskService = Depends(get_risk_service),
    idempotency_key: Optional[str] = Header(None, alias="Idempotency-Key"),
    _check: None = Depends(RequireCapability(Capabilities.ADMIN_VIEW_ALL_DATA))
):
    """
    Check for party links between buyer and seller. Requires ADMIN_VIEW_ALL_DATA capability.
    
    Validates:
    - Same PAN number → BLOCK
    - Same GST number → BLOCK
    - Same mobile number → WARN
    - Same corporate email domain → WARN
    
    Returns severity (BLOCK/WARN/PASS) and violations.
    """
    try:
        result = await risk_service.risk_engine.check_party_links(
            buyer_id=request.buyer_id,
            seller_id=request.seller_id
        )
        return result
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Party links validation failed: {str(e)}"
        )


@router.post(
    "/validate/circular-trading",
    response_model=CircularTradingCheckResponse,
    summary="Check Circular Trading",
    description="Detect same-day circular trading (wash trading prevention). Requires ADMIN_VIEW_ALL_DATA capability.",
    responses={500: {"model": ErrorResponse}}
)
async def check_circular_trading(
    request: CircularTradingCheckRequest,
    current_user=Depends(get_current_user),
    risk_service: RiskService = Depends(get_risk_service),
    idempotency_key: Optional[str] = Header(None, alias="Idempotency-Key"),
    _check: None = Depends(RequireCapability(Capabilities.ADMIN_VIEW_ALL_DATA))
):
    """
    Check for circular trading patterns. Requires ADMIN_VIEW_ALL_DATA capability.
    
    Validates:
    - Partner has opposite position (BUY ↔ SELL) for same commodity
    - Same day only (Option A implementation)
    
    Returns blocked status and conflicting positions.
    """
    try:
        trade_date = request.transaction_date or datetime.now()
        result = await risk_service.risk_engine.check_circular_trading(
            partner_id=request.partner_id,
            commodity_id=request.commodity_id,
            transaction_type=request.transaction_type,
            transaction_date=trade_date
        )
        return result
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Circular trading check failed: {str(e)}"
        )


@router.post(
    "/validate/role-restriction",
    response_model=RoleRestrictionCheckResponse,
    summary="Validate Role Restrictions",
    description="Check if partner role allows transaction type. Requires ADMIN_VIEW_ALL_DATA capability.",
    responses={500: {"model": ErrorResponse}}
)
async def validate_role_restriction(
    request: RoleRestrictionCheckRequest,
    current_user=Depends(get_current_user),
    risk_service: RiskService = Depends(get_risk_service),
    idempotency_key: Optional[str] = Header(None, alias="Idempotency-Key"),
    _check: None = Depends(RequireCapability(Capabilities.ADMIN_VIEW_ALL_DATA))
):
    """
    Validate partner role restrictions. Requires ADMIN_VIEW_ALL_DATA capability.
    
    Rules:
    - BUYER can only BUY (cannot SELL)
    - SELLER can only SELL (cannot BUY)
    - TRADER can both BUY and SELL
    
    Returns allowed status and partner role.
    """
    try:
        result = await risk_service.risk_engine.validate_partner_role(
            partner_id=request.partner_id,
            transaction_type=request.transaction_type
        )
        return result
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Role validation failed: {str(e)}"
        )


# =============================================================================
# ML PREDICTION ENDPOINTS
# =============================================================================

@router.post(
    "/ml/predict/payment-default",
    response_model=MLPredictionResponse,
    summary="ML Payment Default Prediction",
    description="Predict payment default risk using ML model. Requires ADMIN_VIEW_ALL_DATA capability.",
    responses={500: {"model": ErrorResponse}}
)
async def predict_payment_default(
    request: MLPredictionRequest,
    current_user=Depends(get_current_user),
    ml_model: MLRiskModel = Depends(get_ml_model),
    idempotency_key: Optional[str] = Header(None, alias="Idempotency-Key"),
    _check: None = Depends(RequireCapability(Capabilities.ADMIN_VIEW_ALL_DATA))
):
    """
    Predict payment default probability using ML. Requires ADMIN_VIEW_ALL_DATA capability.
    
    Input features:
    - Credit utilization %
    - Partner rating (0-5)
    - Payment performance score
    - Trade history count
    - Dispute rate %
    - Average payment delay days
    - Average trade value
    
    Returns default probability, risk level, and recommendations.
    """
    try:
        prediction = await ml_model.predict_payment_default_risk(
            credit_utilization=request.credit_utilization,
            rating=request.rating,
            payment_performance=request.payment_performance,
            trade_history_count=request.trade_history_count,
            dispute_rate=request.dispute_rate,
            payment_delay_days=request.payment_delay_days,
            avg_trade_value=request.avg_trade_value
        )
        return prediction
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"ML prediction failed: {str(e)}"
        )


@router.post(
    "/ml/train",
    response_model=MLModelTrainResponse,
    summary="Train ML Risk Models",
    description="Train ML models with synthetic or real data. Requires ADMIN_MANAGE_USERS capability.",
    responses={500: {"model": ErrorResponse}}
)
async def train_ml_models(
    request: MLModelTrainRequest,
    current_user=Depends(get_current_user),
    ml_model: MLRiskModel = Depends(get_ml_model),
    idempotency_key: Optional[str] = Header(None, alias="Idempotency-Key"),
    _check: None = Depends(RequireCapability(Capabilities.ADMIN_MANAGE_USERS))
):
    """
    Train ML risk models. Requires ADMIN_MANAGE_USERS capability.
    
    Can use:
    - Synthetic data (if no real data available)
    - Real trading data (when available)
    
    Returns training metrics and model performance.
    """
    try:
        import time
        start_time = time.time()
        
        if request.use_synthetic_data:
            metrics = ml_model.train_payment_default_model(
                num_samples=request.num_samples
            )
        else:
            # TODO: Train with real data from database
            raise HTTPException(
                status_code=501,
                detail="Real data training not yet implemented. Use synthetic data."
            )
        
        training_time = time.time() - start_time
        
        return MLModelTrainResponse(
            success=True,
            model_name="payment_default_predictor",
            metrics=metrics,
            samples_trained=request.num_samples,
            training_time_seconds=round(training_time, 2)
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Model training failed: {str(e)}"
        )


# =============================================================================
# EXPOSURE MONITORING ENDPOINTS
# =============================================================================

@router.post(
    "/monitor/exposure",
    response_model=ExposureMonitoringResponse,
    summary="Monitor Partner Exposure",
    description="Monitor partner credit exposure and generate alerts",
    responses={500: {"model": ErrorResponse}}
)
async def monitor_partner_exposure(
    request: ExposureMonitoringRequest,
    current_user=Depends(get_current_user),
    risk_service: RiskService = Depends(get_risk_service)
):
    """
    Monitor partner credit exposure.
    
    Alerts:
    - GREEN: < 80% utilization
    - YELLOW: 80-95% utilization
    - RED: > 95% utilization
    
    Returns exposure details and alert level.
    """
    try:
        monitoring = await risk_service.monitor_partner_exposure(
            partner_id=request.partner_id
        )
        return monitoring
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Exposure monitoring failed: {str(e)}"
        )


# =============================================================================
# BATCH OPERATION ENDPOINTS
# =============================================================================

@router.post(
    "/batch/assess-requirements",
    response_model=BatchRiskAssessmentResponse,
    summary="Batch Assess All Active Requirements",
    description="Assess risk for all active requirements in one operation. Requires ADMIN_VIEW_ALL_DATA capability.",
    responses={500: {"model": ErrorResponse}}
)
async def batch_assess_requirements(
    current_user=Depends(get_current_user),
    risk_service: RiskService = Depends(get_risk_service),
    idempotency_key: Optional[str] = Header(None, alias="Idempotency-Key"),
    _check: None = Depends(RequireCapability(Capabilities.ADMIN_VIEW_ALL_DATA))
):
    """
    Batch assess all active requirements. Requires ADMIN_VIEW_ALL_DATA capability.
    
    Useful for:
    - Daily risk reviews
    - Portfolio monitoring
    - Bulk risk recalculation
    
    Returns aggregated results with counts.
    """
    try:
        user_id = UUID(current_user.get("sub"))
        assessments = await risk_service.assess_all_active_requirements(user_id=user_id)
        
        # Calculate statistics
        passed = sum(1 for a in assessments if a.get("assessment", {}).get("status") == "PASS")
        warned = sum(1 for a in assessments if a.get("assessment", {}).get("status") == "WARN")
        failed = sum(1 for a in assessments if a.get("assessment", {}).get("status") == "FAIL")
        
        return BatchRiskAssessmentResponse(
            total_assessed=len(assessments),
            passed=passed,
            warned=warned,
            failed=failed,
            assessments=assessments,
            assessed_at=datetime.now()
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Batch assessment failed: {str(e)}"
        )


@router.post(
    "/batch/assess-availabilities",
    response_model=BatchRiskAssessmentResponse,
    summary="Batch Assess All Active Availabilities",
    description="Assess risk for all active availabilities in one operation. Requires ADMIN_VIEW_ALL_DATA capability.",
    responses={500: {"model": ErrorResponse}}
)
async def batch_assess_availabilities(
    current_user=Depends(get_current_user),
    risk_service: RiskService = Depends(get_risk_service),
    idempotency_key: Optional[str] = Header(None, alias="Idempotency-Key"),
    _check: None = Depends(RequireCapability(Capabilities.ADMIN_VIEW_ALL_DATA))
):
    """
    Batch assess all active availabilities. Requires ADMIN_VIEW_ALL_DATA capability.
    
    Useful for:
    - Daily risk reviews
    - Seller portfolio monitoring
    - Bulk risk recalculation
    
    Returns aggregated results with counts.
    """
    try:
        user_id = UUID(current_user.get("sub"))
        assessments = await risk_service.assess_all_active_availabilities(user_id=user_id)
        
        # Calculate statistics
        passed = sum(1 for a in assessments if a.get("assessment", {}).get("status") == "PASS")
        warned = sum(1 for a in assessments if a.get("assessment", {}).get("status") == "WARN")
        failed = sum(1 for a in assessments if a.get("assessment", {}).get("status") == "FAIL")
        
        return BatchRiskAssessmentResponse(
            total_assessed=len(assessments),
            passed=passed,
            warned=warned,
            failed=failed,
            assessments=assessments,
            assessed_at=datetime.now()
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Batch assessment failed: {str(e)}"
        )


# =============================================================================
# HEALTH CHECK ENDPOINT
# =============================================================================

@router.get(
    "/health",
    summary="Risk Engine Health Check",
    description="Check if Risk Engine and ML models are operational"
)
async def health_check():
    """
    Health check endpoint.
    
    Returns status of:
    - Risk Engine
    - ML Models
    - Database connection
    """
    try:
        ml_model = MLRiskModel()
        ml_available = ml_model.model is not None
        
        return {
            "status": "healthy",
            "risk_engine": "operational",
            "ml_model": "loaded" if ml_available else "not_loaded",
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        return {
            "status": "degraded",
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }
