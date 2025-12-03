"""
Risk Engine API - ML-Powered Risk Assessment

Endpoints:
1. POST /risk/ml/train/payment-default - Train payment default predictor
2. POST /risk/ml/train/xgboost - Train XGBoost advanced model
3. POST /risk/ml/train/credit-limit - Train credit limit optimizer
4. POST /risk/ml/train/fraud-detector - Train anomaly detection
5. POST /risk/ml/train/all - Train all models in one go
6. POST /risk/ml/predict/payment-default - Predict payment default risk
7. POST /risk/ml/predict/fraud - Detect fraud anomalies
8. GET /risk/ml/models/status - Get model training status
"""

from fastapi import APIRouter, HTTPException, BackgroundTasks, Depends
from pydantic import BaseModel, Field
from typing import Dict, Any, Optional, List
from datetime import datetime
from decimal import Decimal

from backend.modules.risk.ml_risk_model import MLRiskModel


router = APIRouter(prefix="/risk", tags=["Risk Engine", "Machine Learning"])


# ============================================================================
# REQUEST/RESPONSE SCHEMAS
# ============================================================================

class PaymentDefaultPredictRequest(BaseModel):
    """Request to predict payment default risk."""
    partner_id: Optional[str] = None
    credit_utilization: float = Field(..., ge=0.0, le=2.0, description="Credit utilization ratio (0-2)")
    rating: float = Field(..., ge=1.0, le=5.0, description="Partner rating (1-5)")
    payment_performance: int = Field(..., ge=0, le=100, description="Payment performance score (0-100)")
    trade_history_count: int = Field(..., ge=0, description="Number of trades")
    dispute_rate: float = Field(..., ge=0.0, le=1.0, description="Dispute rate (0-1)")
    payment_delay_days: float = Field(..., ge=0.0, description="Average payment delay in days")
    avg_trade_value: float = Field(..., gt=0, description="Average trade value (₹)")


class FraudDetectionRequest(BaseModel):
    """Request to detect fraud anomalies."""
    partner_id: Optional[str] = None
    credit_utilization: float = Field(..., ge=0.0, le=2.0)
    rating: float = Field(..., ge=1.0, le=5.0)
    payment_performance: int = Field(..., ge=0, le=100)
    trade_history_count: int = Field(..., ge=0)
    dispute_rate: float = Field(..., ge=0.0, le=1.0)
    payment_delay_days: float = Field(..., ge=0.0)
    avg_trade_value: float = Field(..., gt=0)


class TrainModelRequest(BaseModel):
    """Request to train ML models."""
    num_samples: int = Field(default=10000, ge=1000, le=100000, description="Number of synthetic training samples")
    test_size: float = Field(default=0.2, ge=0.1, le=0.5, description="Fraction for test set")


class ModelStatusResponse(BaseModel):
    """Model training status."""
    models: Dict[str, Any]
    last_trained: Optional[str] = None
    total_models: int
    trained_models: int


# ============================================================================
# SINGLETON ML MODEL INSTANCE
# ============================================================================

_ml_model_instance: Optional[MLRiskModel] = None


def get_ml_model() -> MLRiskModel:
    """Dependency injection for ML model."""
    global _ml_model_instance
    if _ml_model_instance is None:
        _ml_model_instance = MLRiskModel()
    return _ml_model_instance


# ============================================================================
# TRAINING ENDPOINTS
# ============================================================================

@router.post("/ml/train/payment-default", response_model=Dict[str, Any])
async def train_payment_default_model(
    request: TrainModelRequest = TrainModelRequest(),
    ml_model: MLRiskModel = Depends(get_ml_model)
):
    """
    Train Payment Default Predictor (RandomForest).
    
    Trains a machine learning model to predict payment default probability.
    Uses synthetic data for training if no real historical data available.
    
    **Training Time**: ~30 seconds for 10,000 samples
    
    Returns:
        Training metrics including ROC-AUC score and feature importance
    """
    try:
        # Generate synthetic training data
        df = ml_model.generate_synthetic_training_data(num_samples=request.num_samples)
        
        # Train model
        metrics = ml_model.train_payment_default_model(df=df, test_size=request.test_size)
        
        return {
            "status": "success",
            "message": "Payment default model trained successfully",
            "metrics": metrics,
            "training_samples": request.num_samples,
            "trained_at": datetime.utcnow().isoformat()
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Training failed: {str(e)}")


@router.post("/ml/train/xgboost", response_model=Dict[str, Any])
async def train_xgboost_model(
    request: TrainModelRequest = TrainModelRequest(),
    ml_model: MLRiskModel = Depends(get_ml_model)
):
    """
    Train XGBoost Advanced Risk Predictor.
    
    More accurate than RandomForest, better for imbalanced data.
    
    **Training Time**: ~45 seconds for 10,000 samples
    
    Returns:
        Training metrics including ROC-AUC score and feature importance
    """
    try:
        # Generate synthetic training data
        df = ml_model.generate_synthetic_training_data(num_samples=request.num_samples)
        
        # Train XGBoost model
        metrics = ml_model.train_xgboost_risk_model(df=df, test_size=request.test_size)
        
        return {
            "status": "success",
            "message": "XGBoost model trained successfully",
            "metrics": metrics,
            "training_samples": request.num_samples,
            "trained_at": datetime.utcnow().isoformat()
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Training failed: {str(e)}")


@router.post("/ml/train/credit-limit", response_model=Dict[str, Any])
async def train_credit_limit_model(
    request: TrainModelRequest = TrainModelRequest(),
    ml_model: MLRiskModel = Depends(get_ml_model)
):
    """
    Train Credit Limit Optimizer (Regression).
    
    Predicts optimal credit limit for partners based on their profile.
    
    **Training Time**: ~20 seconds for 10,000 samples
    
    Returns:
        Training metrics including Mean Absolute Error (MAE)
    """
    try:
        # Generate synthetic training data
        df = ml_model.generate_synthetic_training_data(num_samples=request.num_samples)
        
        # Train credit limit model
        metrics = ml_model.train_credit_limit_model(df=df, test_size=request.test_size)
        
        return {
            "status": "success",
            "message": "Credit limit optimizer trained successfully",
            "metrics": metrics,
            "training_samples": request.num_samples,
            "trained_at": datetime.utcnow().isoformat()
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Training failed: {str(e)}")


@router.post("/ml/train/fraud-detector", response_model=Dict[str, Any])
async def train_fraud_detector(
    request: TrainModelRequest = TrainModelRequest(),
    ml_model: MLRiskModel = Depends(get_ml_model)
):
    """
    Train Fraud Detector (Anomaly Detection).
    
    Uses IsolationForest to detect unusual partner behavior patterns.
    
    **Training Time**: ~15 seconds for 10,000 samples
    
    Returns:
        Training metrics including anomaly detection rate
    """
    try:
        # Generate synthetic training data
        df = ml_model.generate_synthetic_training_data(num_samples=request.num_samples)
        
        # Train fraud detector
        metrics = ml_model.train_fraud_detector(df=df)
        
        return {
            "status": "success",
            "message": "Fraud detector trained successfully",
            "metrics": metrics,
            "training_samples": request.num_samples,
            "trained_at": datetime.utcnow().isoformat()
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Training failed: {str(e)}")


@router.post("/ml/train/all", response_model=Dict[str, Any])
async def train_all_models(
    background_tasks: BackgroundTasks,
    request: TrainModelRequest = TrainModelRequest(),
    ml_model: MLRiskModel = Depends(get_ml_model)
):
    """
    Train ALL ML Models in One Go.
    
    Trains all 4 models:
    1. Payment Default Predictor (RandomForest)
    2. XGBoost Advanced Predictor
    3. Credit Limit Optimizer
    4. Fraud Detector
    
    **Training Time**: ~2 minutes for 10,000 samples
    
    Returns:
        Training metrics for all models
    """
    try:
        # Generate synthetic training data once
        df = ml_model.generate_synthetic_training_data(num_samples=request.num_samples)
        
        results = {}
        
        # Train all models
        print("Training Model 1/4: Payment Default Predictor...")
        results['payment_default'] = ml_model.train_payment_default_model(df=df, test_size=request.test_size)
        
        print("Training Model 2/4: XGBoost Advanced Predictor...")
        results['xgboost'] = ml_model.train_xgboost_risk_model(df=df, test_size=request.test_size)
        
        print("Training Model 3/4: Credit Limit Optimizer...")
        results['credit_limit'] = ml_model.train_credit_limit_model(df=df, test_size=request.test_size)
        
        print("Training Model 4/4: Fraud Detector...")
        results['fraud_detector'] = ml_model.train_fraud_detector(df=df)
        
        return {
            "status": "success",
            "message": "All ML models trained successfully",
            "models_trained": 4,
            "metrics": results,
            "training_samples": request.num_samples,
            "trained_at": datetime.utcnow().isoformat()
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Training failed: {str(e)}")


# ============================================================================
# PREDICTION ENDPOINTS
# ============================================================================

@router.post("/ml/predict/payment-default", response_model=Dict[str, Any])
async def predict_payment_default(
    request: PaymentDefaultPredictRequest,
    ml_model: MLRiskModel = Depends(get_ml_model)
):
    """
    Predict Payment Default Risk.
    
    Uses trained ML model (RandomForest or XGBoost) to predict default probability.
    Falls back to rule-based scoring if ML models not trained.
    
    **Response Time**: <50ms
    
    Returns:
        {
            "default_probability": 0.15,  # 15% chance of default
            "risk_level": "LOW",  # LOW, MODERATE, HIGH, CRITICAL
            "confidence": 0.92,
            "recommendation": "APPROVE",
            "model_used": "xgboost"
        }
    """
    try:
        # Call prediction method
        prediction = await ml_model.predict_payment_default_risk(
            credit_utilization=request.credit_utilization,
            rating=request.rating,
            payment_performance=request.payment_performance,
            trade_history_count=request.trade_history_count,
            dispute_rate=request.dispute_rate,
            payment_delay_days=request.payment_delay_days,
            avg_trade_value=request.avg_trade_value
        )
        
        # Add partner ID if provided
        if request.partner_id:
            prediction['partner_id'] = request.partner_id
        
        return {
            "status": "success",
            "prediction": prediction,
            "predicted_at": datetime.utcnow().isoformat()
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Prediction failed: {str(e)}")


@router.post("/ml/predict/fraud", response_model=Dict[str, Any])
async def detect_fraud_anomaly(
    request: FraudDetectionRequest,
    ml_model: MLRiskModel = Depends(get_ml_model)
):
    """
    Detect Fraud Anomalies.
    
    Uses IsolationForest to detect unusual partner behavior patterns.
    
    **Response Time**: <30ms
    
    Returns:
        {
            "is_anomaly": false,
            "anomaly_score": -0.15,  # Lower = more anomalous
            "risk_level": "NORMAL",
            "recommendation": "PASS"
        }
    """
    try:
        # Call fraud detection
        detection = await ml_model.detect_fraud_anomaly(
            credit_utilization=request.credit_utilization,
            rating=request.rating,
            payment_performance=request.payment_performance,
            trade_history_count=request.trade_history_count,
            dispute_rate=request.dispute_rate,
            payment_delay_days=request.payment_delay_days,
            avg_trade_value=request.avg_trade_value
        )
        
        # Add partner ID if provided
        if request.partner_id:
            detection['partner_id'] = request.partner_id
        
        return {
            "status": "success",
            "detection": detection,
            "detected_at": datetime.utcnow().isoformat()
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Fraud detection failed: {str(e)}")


# ============================================================================
# STATUS ENDPOINTS
# ============================================================================

@router.get("/ml/models/status", response_model=ModelStatusResponse)
async def get_models_status(ml_model: MLRiskModel = Depends(get_ml_model)):
    """
    Get ML Models Training Status.
    
    Returns which models are trained and ready for predictions.
    
    Returns:
        {
            "models": {
                "payment_default": {"trained": true, "type": "RandomForestClassifier"},
                "xgboost": {"trained": false},
                "credit_limit": {"trained": true, "type": "GradientBoostingRegressor"},
                "fraud_detector": {"trained": false}
            },
            "total_models": 4,
            "trained_models": 2
        }
    """
    models_info = {
        "payment_default": {
            "trained": ml_model.payment_default_model is not None,
            "type": "RandomForestClassifier" if ml_model.payment_default_model else None
        },
        "xgboost": {
            "trained": ml_model.xgboost_model is not None,
            "type": "XGBoost Booster" if ml_model.xgboost_model else None
        },
        "credit_limit": {
            "trained": ml_model.credit_limit_model is not None,
            "type": "GradientBoostingRegressor" if ml_model.credit_limit_model else None
        },
        "fraud_detector": {
            "trained": ml_model.fraud_detector is not None,
            "type": "IsolationForest" if ml_model.fraud_detector else None
        }
    }
    
    trained_count = sum(1 for m in models_info.values() if m['trained'])
    
    return ModelStatusResponse(
        models=models_info,
        total_models=4,
        trained_models=trained_count
    )
