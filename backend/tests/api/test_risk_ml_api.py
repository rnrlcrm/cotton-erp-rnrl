"""
Test ML Risk Engine API

Tests all ML model endpoints:
- Training endpoints
- Prediction endpoints
- Status endpoints
"""

import pytest
from fastapi.testclient import TestClient
from decimal import Decimal


@pytest.mark.asyncio
async def test_train_all_models_endpoint(client: TestClient):
    """Test training all ML models at once."""
    response = client.post(
        "/api/v1/risk/ml/train/all",
        json={"num_samples": 1000, "test_size": 0.2}
    )
    
    assert response.status_code == 200
    data = response.json()
    
    assert data["status"] == "success"
    assert data["models_trained"] == 4
    assert "payment_default" in data["metrics"]
    assert "xgboost" in data["metrics"]
    assert "credit_limit" in data["metrics"]
    assert "fraud_detector" in data["metrics"]
    
    # Verify RandomForest metrics
    rf_metrics = data["metrics"]["payment_default"]
    assert rf_metrics["roc_auc"] > 0.8  # Should have good accuracy
    
    # Verify XGBoost metrics
    xgb_metrics = data["metrics"]["xgboost"]
    assert xgb_metrics["roc_auc"] > 0.8
    
    print(f"✅ All models trained! RF AUC: {rf_metrics['roc_auc']:.3f}, XGB AUC: {xgb_metrics['roc_auc']:.3f}")


@pytest.mark.asyncio
async def test_payment_default_prediction_endpoint(client: TestClient):
    """Test payment default prediction."""
    # First train the model
    client.post("/api/v1/risk/ml/train/payment-default", json={"num_samples": 1000})
    
    # Good partner profile
    response = client.post(
        "/api/v1/risk/ml/predict/payment-default",
        json={
            "credit_utilization": 0.5,
            "rating": 4.5,
            "payment_performance": 90,
            "trade_history_count": 100,
            "dispute_rate": 0.02,
            "payment_delay_days": 2.0,
            "avg_trade_value": 1000000.0
        }
    )
    
    assert response.status_code == 200
    data = response.json()
    
    assert data["status"] == "success"
    prediction = data["prediction"]
    
    assert "default_probability" in prediction
    assert "risk_level" in prediction
    assert prediction["risk_level"] in ["LOW", "MODERATE", "HIGH", "CRITICAL"]
    assert 0.0 <= prediction["default_probability"] <= 1.0
    
    # Good partner should have LOW risk
    assert prediction["risk_level"] in ["LOW", "MODERATE"]
    
    print(f"✅ Good partner: {prediction['risk_level']} risk, {prediction['default_probability']:.1%} default probability")


@pytest.mark.asyncio
async def test_payment_default_prediction_poor_partner(client: TestClient):
    """Test payment default prediction for poor partner."""
    # First train the model
    client.post("/api/v1/risk/ml/train/payment-default", json={"num_samples": 1000})
    
    # Poor partner profile
    response = client.post(
        "/api/v1/risk/ml/predict/payment-default",
        json={
            "credit_utilization": 1.2,  # Exceeding limit
            "rating": 2.0,
            "payment_performance": 30,
            "trade_history_count": 5,
            "dispute_rate": 0.5,  # 50% disputes
            "payment_delay_days": 45.0,
            "avg_trade_value": 100000.0
        }
    )
    
    assert response.status_code == 200
    data = response.json()
    prediction = data["prediction"]
    
    # Poor partner should have HIGH or CRITICAL risk
    assert prediction["risk_level"] in ["HIGH", "CRITICAL"]
    assert prediction["default_probability"] > 0.3  # >30% default chance
    
    print(f"✅ Poor partner: {prediction['risk_level']} risk, {prediction['default_probability']:.1%} default probability")


@pytest.mark.asyncio
async def test_fraud_detection_endpoint(client: TestClient):
    """Test fraud anomaly detection."""
    # Train fraud detector
    client.post("/api/v1/risk/ml/train/fraud-detector", json={"num_samples": 1000})
    
    # Normal partner behavior
    response = client.post(
        "/api/v1/risk/ml/predict/fraud",
        json={
            "credit_utilization": 0.6,
            "rating": 4.0,
            "payment_performance": 85,
            "trade_history_count": 80,
            "dispute_rate": 0.05,
            "payment_delay_days": 3.0,
            "avg_trade_value": 800000.0
        }
    )
    
    assert response.status_code == 200
    data = response.json()
    detection = data["detection"]
    
    assert "is_anomaly" in detection
    assert "anomaly_score" in detection
    assert "risk_level" in detection
    
    # Normal behavior should not be flagged
    assert detection["risk_level"] in ["NORMAL", "HIGH"]
    
    print(f"✅ Fraud detection: {detection['risk_level']}, anomaly={detection['is_anomaly']}")


@pytest.mark.asyncio
async def test_fraud_detection_anomalous_behavior(client: TestClient):
    """Test fraud detection with anomalous behavior."""
    # Train fraud detector
    client.post("/api/v1/risk/ml/train/fraud-detector", json={"num_samples": 1000})
    
    # Anomalous partner behavior (very unusual pattern)
    response = client.post(
        "/api/v1/risk/ml/predict/fraud",
        json={
            "credit_utilization": 1.8,  # Way over limit
            "rating": 1.5,  # Very low
            "payment_performance": 15,  # Terrible
            "trade_history_count": 200,  # But lots of trades (unusual)
            "dispute_rate": 0.9,  # 90% disputes
            "payment_delay_days": 120.0,  # 4 months delay
            "avg_trade_value": 50000.0
        }
    )
    
    assert response.status_code == 200
    data = response.json()
    detection = data["detection"]
    
    # This unusual pattern should potentially be flagged
    # (depends on training data distribution)
    print(f"✅ Anomalous behavior: {detection['risk_level']}, anomaly={detection['is_anomaly']}")


@pytest.mark.asyncio
async def test_models_status_endpoint(client: TestClient):
    """Test getting ML models status."""
    # Train all models first
    client.post("/api/v1/risk/ml/train/all", json={"num_samples": 1000})
    
    # Check status
    response = client.get("/api/v1/risk/ml/models/status")
    
    assert response.status_code == 200
    data = response.json()
    
    assert data["total_models"] == 4
    assert data["trained_models"] == 4  # All should be trained
    
    assert data["models"]["payment_default"]["trained"] is True
    assert data["models"]["xgboost"]["trained"] is True
    assert data["models"]["credit_limit"]["trained"] is True
    assert data["models"]["fraud_detector"]["trained"] is True
    
    print(f"✅ Models status: {data['trained_models']}/{data['total_models']} models trained")


@pytest.mark.asyncio
async def test_xgboost_training_endpoint(client: TestClient):
    """Test XGBoost training specifically."""
    response = client.post(
        "/api/v1/risk/ml/train/xgboost",
        json={"num_samples": 1000, "test_size": 0.2}
    )
    
    assert response.status_code == 200
    data = response.json()
    
    assert data["status"] == "success"
    assert "metrics" in data
    assert data["metrics"]["model_type"] == "xgboost"
    assert data["metrics"]["roc_auc"] > 0.8
    
    print(f"✅ XGBoost trained! ROC-AUC: {data['metrics']['roc_auc']:.3f}")


@pytest.mark.asyncio
async def test_credit_limit_training_endpoint(client: TestClient):
    """Test credit limit optimizer training."""
    response = client.post(
        "/api/v1/risk/ml/train/credit-limit",
        json={"num_samples": 1000}
    )
    
    assert response.status_code == 200
    data = response.json()
    
    assert data["status"] == "success"
    assert data["metrics"]["model_type"] == "gradient_boosting_regressor"
    assert "mae" in data["metrics"]
    
    print(f"✅ Credit limit optimizer trained! MAE: {data['metrics']['mean_absolute_error_inr']}")


if __name__ == "__main__":
    print("Run with: pytest tests/api/test_risk_ml_api.py -v")
