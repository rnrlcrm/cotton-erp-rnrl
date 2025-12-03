# AI Implementation Plan - Enterprise-Grade AI Platform

**Date:** December 3, 2025  
**Objective:** Build world-class, multi-lingual, AI-driven platform for commodity trading  
**Current Status:** 🔴 Basic LLM calls only - needs complete rebuild

---

## Critical Gap Analysis

### What's Missing (Current System is NOT Robust)
- ❌ **No Conversation Persistence:** Chat history not saved in DB
- ❌ **No Multi-Language Support:** No Hindi/regional language support
- ❌ **No Streaming:** Responses come all at once (poor UX)
- ❌ **No Multi-Modal:** Can't process images, PDFs, audio
- ❌ **No AI Agents:** Just simple Q&A, no autonomous workflows
- ❌ **No Advanced RAG:** Basic search only, no reranking/citations
- ❌ **No Monitoring:** Zero visibility into AI performance/cost
- ❌ **No Production Features:** No caching, rate limits, circuit breakers

### Current State Assessment
- ✅ **Architecture:** Good abstraction layer (BaseAIOrchestrator)
- ✅ **Provider Support:** OpenAI/LangChain integrated
- 🔴 **Chat System:** NO conversation memory or persistence
- 🔴 **Language Support:** English only, no i18n
- 🔴 **Streaming:** Not implemented
- 🔴 **Multi-Modal:** Not implemented
- 🔴 **AI Agents:** Basic tools only, no LangGraph workflows
- 🔴 **RAG Pipeline:** Basic semantic search, needs enhancement
- ❌ **Monitoring:** No observability, cost tracking, or performance metrics
- ❌ **Testing:** No AI-specific tests

### Implementation Priority (Revised)
**Phase 1 (CRITICAL):** Conversation Persistence & Multi-Language - 2-3 Days  
**Phase 2 (CRITICAL):** Streaming & Real-time UX - 1-2 Days  
**Phase 3 (HIGH):** Multi-Modal AI (Vision, OCR, Audio) - 2-3 Days  
**Phase 4 (HIGH):** AI Agents & Workflows (LangGraph) - 3-4 Days  
**Phase 5 (HIGH):** Advanced RAG Pipeline - 2-3 Days  
**Phase 6 (MEDIUM):** Observability & Monitoring - 2 Days  
**Phase 7 (MEDIUM):** ML Models (Demand, Price, Quality) - 3-4 Days

**Total Timeline: 4-5 weeks to enterprise-grade AI platform**

---

## Phase 7: ML Models & Predictive Analytics (HIGH) - 4-5 Days

### 7.1 Tech Stack for ML Modules 🤖

**Core ML Frameworks:**
```python
# Production ML Stack
{
    # Classical ML
    "scikit-learn": "1.3.2",      # Random Forest, SVM, preprocessing
    "xgboost": "2.0.3",            # Gradient boosting (best for tabular)
    "lightgbm": "4.1.0",           # Fast gradient boosting
    
    # Time Series
    "prophet": "1.1.5",            # Facebook Prophet for demand forecasting
    "statsmodels": "0.14.1",       # ARIMA, SARIMA
    "pmdarima": "2.0.4",           # Auto-ARIMA
    
    # Deep Learning
    "torch": "2.1.2",              # PyTorch for neural networks
    "tensorflow": "2.15.0",        # TensorFlow (alternative)
    
    # Feature Engineering
    "category_encoders": "2.6.3",  # Categorical encoding
    "feature-engine": "1.6.2",     # Feature transformations
    
    # Model Management
    "mlflow": "2.9.2",             # Experiment tracking, model registry
    "optuna": "3.5.0",             # Hyperparameter optimization
    
    # Serving
    "onnx": "1.15.0",              # Model format conversion
    "onnxruntime": "1.16.3",       # Fast inference
    
    # Monitoring
    "evidently": "0.4.15",         # ML monitoring, drift detection
    "alibi-detect": "0.11.4",      # Outlier/drift detection
}
```

---

### 7.2 Price Prediction Model (XGBoost) 🟡 HIGH

**Use Case:** Predict fair market price for commodities

**Tech Spec:**
```python
# backend/ai/models/price_prediction/model.py
import xgboost as xgb
import numpy as np
import pandas as pd
from typing import Dict, List, Tuple
import mlflow
from datetime import datetime, timedelta

class CottonPricePredictor:
    """
    XGBoost-based price prediction model
    
    Features:
    - Historical prices (30/60/90 day moving averages)
    - Quality parameters (staple length, micronaire, strength)
    - Location (distance from ports, regional demand)
    - Seasonality (month, quarter, harvest season)
    - Market indicators (global cotton index, currency rates)
    - Supplier reputation (credit score, delivery history)
    
    Target: Price per unit (INR/quintal)
    
    Algorithm: XGBoost Regression
    - Handles non-linear relationships
    - Feature importance analysis
    - Fast training and inference
    - Robust to outliers
    """
    
    def __init__(self):
        self.model = None
        self.feature_names = []
        self.scaler = None
        self.model_version = None
    
    def prepare_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """Feature engineering pipeline"""
        features = pd.DataFrame()
        
        # 1. Price history features
        features['price_ma_7'] = df.groupby('commodity_id')['price'].transform(
            lambda x: x.rolling(7, min_periods=1).mean()
        )
        features['price_ma_30'] = df.groupby('commodity_id')['price'].transform(
            lambda x: x.rolling(30, min_periods=1).mean()
        )
        features['price_ma_90'] = df.groupby('commodity_id')['price'].transform(
            lambda x: x.rolling(90, min_periods=1).mean()
        )
        features['price_volatility'] = df.groupby('commodity_id')['price'].transform(
            lambda x: x.rolling(30, min_periods=1).std()
        )
        
        # 2. Quality parameters (cotton-specific)
        features['staple_length_mm'] = df['quality_params'].apply(
            lambda x: x.get('staple_length', 28.0)
        )
        features['micronaire'] = df['quality_params'].apply(
            lambda x: x.get('micronaire', 4.5)
        )
        features['fiber_strength'] = df['quality_params'].apply(
            lambda x: x.get('strength', 25.0)
        )
        features['color_grade'] = df['quality_params'].apply(
            lambda x: self._encode_color(x.get('color', 'white'))
        )
        
        # 3. Location features
        features['distance_from_port_km'] = df['location_distance_from_port']
        features['state_demand_index'] = df['location_state'].map(self.state_demand_map)
        features['is_major_cotton_region'] = df['location_state'].isin([
            'Gujarat', 'Maharashtra', 'Telangana', 'Punjab', 'Haryana'
        ]).astype(int)
        
        # 4. Temporal features
        features['month'] = df['date'].dt.month
        features['quarter'] = df['date'].dt.quarter
        features['is_harvest_season'] = df['date'].dt.month.isin([10, 11, 12, 1]).astype(int)
        features['day_of_year'] = df['date'].dt.dayofyear
        features['days_since_harvest_start'] = (
            df['date'] - pd.to_datetime(f"{df['date'].dt.year}-10-01")
        ).dt.days
        
        # 5. Market indicators
        features['cotton_index_global'] = df['market_cotton_index']
        features['usd_inr_rate'] = df['market_exchange_rate']
        features['crude_oil_price'] = df['market_crude_oil_price']  # Affects transport
        
        # 6. Supplier features
        features['supplier_credit_score'] = df['supplier_credit_score']
        features['supplier_avg_quality'] = df.groupby('supplier_id')['quality_score'].transform('mean')
        features['supplier_trade_count'] = df.groupby('supplier_id').cumcount()
        
        # 7. Quantity features
        features['quantity_log'] = np.log1p(df['quantity'])
        features['is_bulk_order'] = (df['quantity'] > df['quantity'].quantile(0.75)).astype(int)
        
        self.feature_names = features.columns.tolist()
        return features
    
    def train(
        self,
        train_data: pd.DataFrame,
        val_data: pd.DataFrame,
        hyperparams: Dict = None
    ) -> Dict:
        """
        Train XGBoost model with MLflow tracking
        """
        with mlflow.start_run(run_name=f"price_prediction_{datetime.now().strftime('%Y%m%d_%H%M')}"):
            # Prepare features
            X_train = self.prepare_features(train_data)
            y_train = train_data['price']
            
            X_val = self.prepare_features(val_data)
            y_val = val_data['price']
            
            # Default hyperparameters
            params = {
                'objective': 'reg:squarederror',
                'max_depth': 8,
                'learning_rate': 0.05,
                'n_estimators': 500,
                'min_child_weight': 3,
                'subsample': 0.8,
                'colsample_bytree': 0.8,
                'gamma': 0.1,
                'reg_alpha': 0.1,
                'reg_lambda': 1.0,
                'random_state': 42,
                'tree_method': 'hist',  # Fast training
                'device': 'cuda',  # GPU if available
            }
            
            if hyperparams:
                params.update(hyperparams)
            
            # Log parameters
            mlflow.log_params(params)
            
            # Train model
            self.model = xgb.XGBRegressor(**params)
            
            self.model.fit(
                X_train, y_train,
                eval_set=[(X_val, y_val)],
                early_stopping_rounds=50,
                verbose=50
            )
            
            # Evaluation
            train_preds = self.model.predict(X_train)
            val_preds = self.model.predict(X_val)
            
            from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
            
            metrics = {
                'train_mae': mean_absolute_error(y_train, train_preds),
                'train_rmse': np.sqrt(mean_squared_error(y_train, train_preds)),
                'train_r2': r2_score(y_train, train_preds),
                'val_mae': mean_absolute_error(y_val, val_preds),
                'val_rmse': np.sqrt(mean_squared_error(y_val, val_preds)),
                'val_r2': r2_score(y_val, val_preds),
            }
            
            # Log metrics
            mlflow.log_metrics(metrics)
            
            # Log feature importance
            feature_importance = pd.DataFrame({
                'feature': self.feature_names,
                'importance': self.model.feature_importances_
            }).sort_values('importance', ascending=False)
            
            mlflow.log_artifact(feature_importance.to_csv(index=False), 'feature_importance.csv')
            
            # Save model to MLflow
            mlflow.xgboost.log_model(self.model, "model")
            
            # Register model
            model_uri = f"runs:/{mlflow.active_run().info.run_id}/model"
            self.model_version = mlflow.register_model(model_uri, "cotton_price_predictor")
            
            return metrics
    
    def predict(
        self,
        commodity_id: str,
        quantity: float,
        quality_params: Dict,
        location: str,
        supplier_id: str
    ) -> Dict:
        """
        Predict price with confidence interval
        """
        # Prepare input features
        input_df = self._prepare_input(
            commodity_id, quantity, quality_params, location, supplier_id
        )
        
        X = self.prepare_features(input_df)
        
        # Prediction
        prediction = self.model.predict(X)[0]
        
        # Confidence interval using quantile regression
        # Train separate models for upper/lower bounds (or use prediction variance)
        std_error = self._estimate_prediction_std(X)
        
        lower_bound = prediction - 1.96 * std_error  # 95% CI
        upper_bound = prediction + 1.96 * std_error
        
        # Feature contributions (SHAP values)
        import shap
        explainer = shap.TreeExplainer(self.model)
        shap_values = explainer.shap_values(X)
        
        return {
            'predicted_price': float(prediction),
            'lower_bound_95': float(max(0, lower_bound)),
            'upper_bound_95': float(upper_bound),
            'confidence': 0.95,
            'feature_contributions': dict(zip(self.feature_names, shap_values[0])),
            'model_version': self.model_version.version
        }
    
    def hyperparameter_tuning(self, train_data: pd.DataFrame, val_data: pd.DataFrame):
        """Automated hyperparameter tuning with Optuna"""
        import optuna
        
        def objective(trial):
            params = {
                'max_depth': trial.suggest_int('max_depth', 3, 12),
                'learning_rate': trial.suggest_float('learning_rate', 0.01, 0.3, log=True),
                'n_estimators': trial.suggest_int('n_estimators', 100, 1000),
                'min_child_weight': trial.suggest_int('min_child_weight', 1, 10),
                'subsample': trial.suggest_float('subsample', 0.6, 1.0),
                'colsample_bytree': trial.suggest_float('colsample_bytree', 0.6, 1.0),
                'gamma': trial.suggest_float('gamma', 0.0, 1.0),
                'reg_alpha': trial.suggest_float('reg_alpha', 0.0, 1.0),
                'reg_lambda': trial.suggest_float('reg_lambda', 0.0, 2.0),
            }
            
            metrics = self.train(train_data, val_data, params)
            return metrics['val_mae']  # Minimize validation MAE
        
        study = optuna.create_study(direction='minimize')
        study.optimize(objective, n_trials=50)
        
        return study.best_params
```

---

### 7.3 Demand Forecasting Model (Prophet) 🟡 HIGH

**Use Case:** Forecast commodity demand for next 30/60/90 days

**Tech Spec:**
```python
# backend/ai/models/demand_forecasting/model.py
from prophet import Prophet
import pandas as pd
from typing import Dict, List

class DemandForecaster:
    """
    Facebook Prophet for time-series demand forecasting
    
    Features:
    - Handles seasonality (weekly, monthly, yearly)
    - Detects trend changes
    - Holiday effects (festivals, harvest seasons)
    - Multiple seasonality patterns
    
    Use Cases:
    - Predict demand for next 30 days
    - Inventory planning
    - Price optimization based on expected demand
    """
    
    def __init__(self):
        self.model = None
        self.commodity_models = {}  # Separate model per commodity
    
    def train(
        self,
        commodity_id: str,
        historical_data: pd.DataFrame,
        forecast_horizon: int = 90
    ):
        """
        Train Prophet model for specific commodity
        
        Args:
            historical_data: DataFrame with 'date' and 'demand' columns
        """
        # Prepare data for Prophet
        df = historical_data[['date', 'demand']].rename(
            columns={'date': 'ds', 'demand': 'y'}
        )
        
        # Initialize Prophet with custom parameters
        model = Prophet(
            growth='linear',
            changepoint_prior_scale=0.05,  # Flexibility in trend
            seasonality_prior_scale=10.0,   # Strength of seasonality
            yearly_seasonality=True,
            weekly_seasonality=True,
            daily_seasonality=False,
            interval_width=0.95  # 95% confidence interval
        )
        
        # Add custom seasonality
        model.add_seasonality(
            name='monthly',
            period=30.5,
            fourier_order=5
        )
        
        # Add harvest season (October-January for cotton)
        model.add_seasonality(
            name='harvest',
            period=365.25,
            fourier_order=10,
            condition_name='is_harvest'
        )
        
        df['is_harvest'] = df['ds'].dt.month.isin([10, 11, 12, 1])
        
        # Add Indian holidays/festivals
        indian_holidays = pd.DataFrame({
            'holiday': 'diwali',
            'ds': pd.to_datetime(['2023-11-12', '2024-11-01', '2025-10-20']),
            'lower_window': -10,
            'upper_window': 10,
        })
        model.add_country_holidays(country_name='IN')
        
        # Fit model
        model.fit(df)
        
        # Store model
        self.commodity_models[commodity_id] = model
        
        # Save to MLflow
        with mlflow.start_run():
            mlflow.prophet.log_model(model, f"demand_forecast_{commodity_id}")
    
    def forecast(
        self,
        commodity_id: str,
        forecast_days: int = 30,
        location: str = None
    ) -> pd.DataFrame:
        """
        Generate demand forecast
        
        Returns:
            DataFrame with columns: date, predicted_demand, lower_bound, upper_bound
        """
        model = self.commodity_models[commodity_id]
        
        # Create future dataframe
        future = model.make_future_dataframe(periods=forecast_days)
        future['is_harvest'] = future['ds'].dt.month.isin([10, 11, 12, 1])
        
        # Predict
        forecast = model.predict(future)
        
        return forecast[['ds', 'yhat', 'yhat_lower', 'yhat_upper']].rename(
            columns={
                'ds': 'date',
                'yhat': 'predicted_demand',
                'yhat_lower': 'lower_bound',
                'yhat_upper': 'upper_bound'
            }
        ).tail(forecast_days)
```

---

### 7.4 Quality Scoring Model (Random Forest) 🟡 HIGH

**Use Case:** AI-powered quality assessment and anomaly detection

**Tech Spec:**
```python
# backend/ai/models/quality_scoring/model.py
from sklearn.ensemble import RandomForestClassifier, IsolationForest
import numpy as np

class QualityScoringModel:
    """
    Random Forest for quality grading + Isolation Forest for anomaly detection
    
    Inputs:
    - Quality parameters (staple length, micronaire, strength, color)
    - Supplier history (average quality, variance)
    - Market standards for commodity type
    
    Outputs:
    - Quality grade: A/B/C/D
    - Quality score: 0-100
    - Anomaly flag: Is this unusual for this supplier?
    - Confidence: Model certainty
    """
    
    def __init__(self):
        self.classifier = RandomForestClassifier(
            n_estimators=200,
            max_depth=15,
            min_samples_split=10,
            class_weight='balanced',
            random_state=42
        )
        self.anomaly_detector = IsolationForest(
            contamination=0.1,  # 10% expected anomalies
            random_state=42
        )
    
    def train(self, X_train, y_train):
        """Train both classification and anomaly detection"""
        self.classifier.fit(X_train, y_train)
        self.anomaly_detector.fit(X_train)
    
    def predict(self, quality_params: Dict, supplier_history: List[Dict]) -> Dict:
        """
        Score quality with anomaly detection
        """
        # Extract features
        X = self._extract_features(quality_params, supplier_history)
        
        # Quality grade prediction
        grade_proba = self.classifier.predict_proba(X)[0]
        grade = self.classifier.classes_[np.argmax(grade_proba)]
        confidence = float(np.max(grade_proba))
        
        # Anomaly detection
        anomaly_score = self.anomaly_detector.score_samples(X)[0]
        is_anomaly = self.anomaly_detector.predict(X)[0] == -1
        
        # Overall quality score (0-100)
        grade_scores = {'A': 90, 'B': 75, 'C': 60, 'D': 40}
        quality_score = grade_scores.get(grade, 50)
        
        return {
            'quality_grade': grade,
            'quality_score': quality_score,
            'confidence': confidence,
            'is_anomaly': bool(is_anomaly),
            'anomaly_score': float(anomaly_score),
            'grade_probabilities': dict(zip(self.classifier.classes_, grade_proba))
        }
```

---

### 7.5 Fraud Detection Model (Autoencoder) 🟡 MEDIUM

**Use Case:** Detect fraudulent trades, fake documents, suspicious patterns

**Tech Spec:**
```python
# backend/ai/models/fraud_detection/model.py
import torch
import torch.nn as nn

class FraudDetectionAutoencoder(nn.Module):
    """
    Deep Autoencoder for fraud detection
    
    Approach:
    - Train on normal transactions (reconstruction)
    - High reconstruction error = anomaly/fraud
    
    Features:
    - Trade patterns (frequency, amounts, timing)
    - Partner behavior (sudden changes)
    - Document verification (OCR inconsistencies)
    - Payment patterns
    """
    
    def __init__(self, input_dim=50):
        super().__init__()
        
        # Encoder
        self.encoder = nn.Sequential(
            nn.Linear(input_dim, 32),
            nn.ReLU(),
            nn.Dropout(0.2),
            nn.Linear(32, 16),
            nn.ReLU(),
            nn.Linear(16, 8),  # Compressed representation
        )
        
        # Decoder
        self.decoder = nn.Sequential(
            nn.Linear(8, 16),
            nn.ReLU(),
            nn.Linear(16, 32),
            nn.ReLU(),
            nn.Dropout(0.2),
            nn.Linear(32, input_dim),
            nn.Sigmoid()
        )
    
    def forward(self, x):
        encoded = self.encoder(x)
        decoded = self.decoder(encoded)
        return decoded
    
    def detect_fraud(self, transaction_features: np.ndarray, threshold: float = 0.05):
        """
        Detect fraud based on reconstruction error
        """
        self.eval()
        with torch.no_grad():
            X = torch.tensor(transaction_features, dtype=torch.float32)
            reconstructed = self.forward(X)
            
            # Reconstruction error (MSE)
            error = torch.mean((X - reconstructed) ** 2, dim=1)
            
            is_fraud = error > threshold
            fraud_score = torch.clamp(error / threshold, 0, 1)
            
            return {
                'is_fraud': bool(is_fraud[0]),
                'fraud_score': float(fraud_score[0]),
                'reconstruction_error': float(error[0]),
                'risk_level': 'HIGH' if is_fraud else ('MEDIUM' if fraud_score > 0.5 else 'LOW')
            }
```

---

### 7.6 Trade Matching Engine (Neural Network) 🟡 HIGH

**Use Case:** AI-powered buyer-seller matching

**Tech Spec:**
```python
# backend/ai/models/matching_engine/model.py
import torch.nn as nn

class TradeMatchingNetwork(nn.Module):
    """
    Siamese Neural Network for availability-requirement matching
    
    Architecture:
    - Embedding network for availability
    - Embedding network for requirement
    - Cosine similarity + learned scoring head
    
    Features:
    - Commodity embeddings
    - Quality parameter embeddings
    - Location embeddings
    - Price compatibility
    - Supplier reputation
    """
    
    def __init__(self, embedding_dim=128):
        super().__init__()
        
        # Shared embedding network
        self.embedding_net = nn.Sequential(
            nn.Linear(100, 256),
            nn.ReLU(),
            nn.BatchNorm1d(256),
            nn.Dropout(0.3),
            nn.Linear(256, 128),
            nn.ReLU(),
            nn.Linear(128, embedding_dim)
        )
        
        # Scoring head
        self.scorer = nn.Sequential(
            nn.Linear(embedding_dim * 2 + 1, 64),  # concat + cosine sim
            nn.ReLU(),
            nn.Dropout(0.2),
            nn.Linear(64, 32),
            nn.ReLU(),
            nn.Linear(32, 1),
            nn.Sigmoid()  # Match score 0-1
        )
    
    def forward(self, availability_features, requirement_features):
        # Get embeddings
        avail_emb = self.embedding_net(availability_features)
        req_emb = self.embedding_net(requirement_features)
        
        # Cosine similarity
        cos_sim = torch.cosine_similarity(avail_emb, req_emb, dim=1, keepdim=True)
        
        # Concatenate embeddings + similarity
        combined = torch.cat([avail_emb, req_emb, cos_sim], dim=1)
        
        # Final match score
        match_score = self.scorer(combined)
        
        return match_score, avail_emb, req_emb
```

---

### 7.7 Model Management & Serving

**MLflow Model Registry:**
```python
# backend/ai/models/shared/model_registry.py
import mlflow
from mlflow.tracking import MlflowClient

class ModelRegistry:
    """Centralized model management"""
    
    def __init__(self, tracking_uri: str = "sqlite:///mlflow.db"):
        mlflow.set_tracking_uri(tracking_uri)
        self.client = MlflowClient()
    
    def register_model(self, model, model_name: str, metadata: Dict):
        """Register model with versioning"""
        with mlflow.start_run():
            # Log metadata
            mlflow.log_params(metadata)
            
            # Log model
            mlflow.sklearn.log_model(model, model_name)
            
            # Register to model registry
            model_uri = f"runs:/{mlflow.active_run().info.run_id}/{model_name}"
            mlflow.register_model(model_uri, model_name)
    
    def load_production_model(self, model_name: str):
        """Load production version of model"""
        model_uri = f"models:/{model_name}/production"
        return mlflow.sklearn.load_model(model_uri)
    
    def promote_to_production(self, model_name: str, version: int):
        """Promote model version to production"""
        self.client.transition_model_version_stage(
            name=model_name,
            version=version,
            stage="Production"
        )
```

**ONNX Model Serving (Fast Inference):**
```python
# backend/ai/models/shared/deployment.py
import onnxruntime as ort
import torch

class ONNXModelServer:
    """Serve models via ONNX for 10x faster inference"""
    
    def __init__(self, model_path: str):
        self.session = ort.InferenceSession(
            model_path,
            providers=['CUDAExecutionProvider', 'CPUExecutionProvider']
        )
    
    def predict(self, input_data: np.ndarray):
        """Fast inference"""
        input_name = self.session.get_inputs()[0].name
        output = self.session.run(None, {input_name: input_data})
        return output[0]
    
    @staticmethod
    def convert_pytorch_to_onnx(model: nn.Module, input_shape, output_path: str):
        """Convert PyTorch to ONNX"""
        dummy_input = torch.randn(input_shape)
        torch.onnx.export(
            model,
            dummy_input,
            output_path,
            export_params=True,
            opset_version=14,
            input_names=['input'],
            output_names=['output'],
            dynamic_axes={'input': {0: 'batch_size'}, 'output': {0: 'batch_size'}}
        )
```

---

### 7.8 Model Monitoring & Drift Detection

**Evidently AI for ML Monitoring:**
```python
# backend/ai/models/shared/monitoring.py
from evidently.report import Report
from evidently.metric_preset import DataDriftPreset, RegressionPreset

class ModelMonitor:
    """Monitor model performance and data drift"""
    
    def detect_drift(
        self,
        reference_data: pd.DataFrame,
        current_data: pd.DataFrame
    ) -> Dict:
        """Detect if input data distribution has changed"""
        report = Report(metrics=[DataDriftPreset()])
        report.run(reference_data=reference_data, current_data=current_data)
        
        result = report.as_dict()
        
        return {
            'drift_detected': result['metrics'][0]['result']['dataset_drift'],
            'drifted_features': [
                feat for feat, drift in result['metrics'][0]['result']['drift_by_columns'].items()
                if drift['drift_detected']
            ],
            'drift_score': result['metrics'][0]['result']['share_of_drifted_columns']
        }
    
    def monitor_regression_performance(
        self,
        predictions: np.ndarray,
        actuals: np.ndarray,
        reference_predictions: np.ndarray,
        reference_actuals: np.ndarray
    ):
        """Monitor model performance degradation"""
        report = Report(metrics=[RegressionPreset()])
        
        current = pd.DataFrame({'prediction': predictions, 'actual': actuals})
        reference = pd.DataFrame({'prediction': reference_predictions, 'actual': reference_actuals})
        
        report.run(reference_data=reference, current_data=current)
        return report.as_dict()
```

---

## ML Pipeline Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                     ML Pipeline Flow                         │
└─────────────────────────────────────────────────────────────┘

1. Data Collection (PostgreSQL)
   ↓
2. Feature Engineering (Pandas, Feature-engine)
   ↓
3. Model Training (XGBoost, Prophet, PyTorch)
   ↓
4. Experiment Tracking (MLflow)
   ↓
5. Hyperparameter Tuning (Optuna)
   ↓
6. Model Validation (Evidently)
   ↓
7. Model Registry (MLflow)
   ↓
8. Model Deployment (ONNX Runtime)
   ↓
9. Inference API (FastAPI)
   ↓
10. Monitoring & Drift Detection (Evidently)
```

---

## Phase 1: Conversation Persistence & Multi-Language (CRITICAL) - 2-3 Days

### 1.1 Conversation Memory System 🔴 CRITICAL

**Problem:** No chat history persistence - users lose context on refresh

**Implementation:**

```python
# backend/ai/conversation/models.py
from sqlalchemy import Column, String, JSON, DateTime, ForeignKey, Integer, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
import uuid
from datetime import datetime

class Conversation(Base):
    """Conversation session with persistent history"""
    __tablename__ = "ai_conversations"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    organization_id = Column(UUID(as_uuid=True), ForeignKey("organizations.id"))
    
    # Conversation metadata
    title = Column(String(200))  # Auto-generated from first message
    assistant_type = Column(String(50))  # trade, contract, quality, general
    language = Column(String(10), default="en")  # en, hi, ta, te, mr, gu
    
    # Session tracking
    session_id = Column(String(100), unique=True)
    is_active = Column(Boolean, default=True)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at = Column(DateTime(timezone=True), onupdate=datetime.utcnow)
    ended_at = Column(DateTime(timezone=True), nullable=True)
    
    # Relationships
    messages = relationship("ConversationMessage", back_populates="conversation")
    user = relationship("User")
    
    # Analytics
    total_messages = Column(Integer, default=0)
    total_cost_usd = Column(Numeric(10, 6), default=0.0)


class ConversationMessage(Base):
    """Individual message in conversation"""
    __tablename__ = "ai_conversation_messages"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    conversation_id = Column(UUID(as_uuid=True), ForeignKey("ai_conversations.id"))
    
    # Message content
    role = Column(String(20))  # user | assistant | system
    content = Column(Text)
    content_translated = Column(Text, nullable=True)  # Translation if needed
    
    # Metadata
    language = Column(String(10))  # Detected language
    tokens_used = Column(Integer, default=0)
    cost_usd = Column(Numeric(10, 6), default=0.0)
    latency_ms = Column(Integer, default=0)
    
    # RAG metadata
    sources = Column(JSON, default=list)  # Source documents used
    confidence_score = Column(Numeric(3, 2), nullable=True)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)
    
    # Relationships
    conversation = relationship("Conversation", back_populates="messages")


class ConversationContext(Base):
    """Persistent context for conversations (user preferences, entities)"""
    __tablename__ = "ai_conversation_context"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    conversation_id = Column(UUID(as_uuid=True), ForeignKey("ai_conversations.id"))
    
    # Context data
    context_type = Column(String(50))  # entities, preferences, facts
    key = Column(String(100))
    value = Column(JSON)
    
    # Metadata
    confidence = Column(Numeric(3, 2))
    source = Column(String(100))  # extracted_from_message, user_profile, system
    
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at = Column(DateTime(timezone=True), onupdate=datetime.utcnow)
```

**Conversation Manager:**

```python
# backend/ai/conversation/manager.py
from typing import List, Dict, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from uuid import UUID
import hashlib

class ConversationManager:
    """Manage conversation lifecycle and memory"""
    
    def __init__(self, db: AsyncSession, redis: Optional[Redis] = None):
        self.db = db
        self.redis = redis
    
    async def create_conversation(
        self,
        user_id: UUID,
        assistant_type: str = "general",
        language: str = "en"
    ) -> Conversation:
        """Create new conversation session"""
        conversation = Conversation(
            user_id=user_id,
            assistant_type=assistant_type,
            language=language,
            session_id=self._generate_session_id(user_id)
        )
        self.db.add(conversation)
        await self.db.commit()
        await self.db.refresh(conversation)
        
        # Cache in Redis for fast access
        if self.redis:
            await self._cache_conversation(conversation)
        
        return conversation
    
    async def add_message(
        self,
        conversation_id: UUID,
        role: str,
        content: str,
        **metadata
    ) -> ConversationMessage:
        """Add message to conversation"""
        message = ConversationMessage(
            conversation_id=conversation_id,
            role=role,
            content=content,
            **metadata
        )
        self.db.add(message)
        
        # Update conversation
        conversation = await self.db.get(Conversation, conversation_id)
        conversation.total_messages += 1
        conversation.total_cost_usd += metadata.get("cost_usd", 0.0)
        conversation.updated_at = datetime.utcnow()
        
        # Auto-generate title from first user message
        if conversation.total_messages == 1 and role == "user":
            conversation.title = await self._generate_title(content)
        
        await self.db.commit()
        await self.db.refresh(message)
        
        # Update Redis cache
        if self.redis:
            await self._update_cache(conversation_id, message)
        
        return message
    
    async def get_conversation_history(
        self,
        conversation_id: UUID,
        limit: int = 50
    ) -> List[ConversationMessage]:
        """Get conversation history (with caching)"""
        # Try Redis first
        if self.redis:
            cached = await self._get_cached_history(conversation_id)
            if cached:
                return cached
        
        # Fallback to DB
        query = (
            select(ConversationMessage)
            .where(ConversationMessage.conversation_id == conversation_id)
            .order_by(ConversationMessage.created_at.desc())
            .limit(limit)
        )
        result = await self.db.execute(query)
        messages = result.scalars().all()
        
        # Cache for next time
        if self.redis:
            await self._cache_history(conversation_id, messages)
        
        return list(reversed(messages))
    
    async def get_langchain_memory(
        self,
        conversation_id: UUID
    ) -> ConversationBufferMemory:
        """Convert DB history to LangChain memory"""
        from langchain.memory import ConversationBufferMemory
        from langchain.schema import HumanMessage, AIMessage
        
        messages = await self.get_conversation_history(conversation_id)
        
        memory = ConversationBufferMemory(
            memory_key="chat_history",
            return_messages=True
        )
        
        for msg in messages:
            if msg.role == "user":
                memory.chat_memory.add_user_message(msg.content)
            elif msg.role == "assistant":
                memory.chat_memory.add_ai_message(msg.content)
        
        return memory
    
    async def _generate_title(self, first_message: str) -> str:
        """Generate conversation title from first message"""
        # Use LLM to generate concise title
        from backend.ai.orchestrators.factory import get_orchestrator
        
        orchestrator = get_orchestrator()
        response = await orchestrator.execute(
            AIRequest(
                task_type=AITaskType.TEXT_GENERATION,
                prompt=f"Generate a short 3-5 word title for this conversation:\n\n{first_message}",
                max_tokens=20,
                temperature=0.3
            )
        )
        return response.result.strip().replace('"', '')
```

**Files to Create:**
- `backend/ai/conversation/__init__.py`
- `backend/ai/conversation/models.py`
- `backend/ai/conversation/manager.py`
- `backend/ai/conversation/cache.py` (Redis caching layer)
- `backend/db/migrations/versions/add_ai_conversations.py`

---

### 1.2 Multi-Language Support (i18n) 🔴 CRITICAL

**Problem:** Platform only works in English - need Hindi/regional language support

**Implementation:**

```python
# backend/ai/i18n/translator.py
from typing import Optional, Dict
from enum import Enum
import httpx

class Language(str, Enum):
    """Supported languages"""
    ENGLISH = "en"
    HINDI = "hi"
    TAMIL = "ta"
    TELUGU = "te"
    MARATHI = "mr"
    GUJARATI = "gu"
    KANNADA = "kn"
    MALAYALAM = "ml"
    PUNJABI = "pa"
    BENGALI = "bn"


class AITranslator:
    """Multi-language translation for AI responses"""
    
    def __init__(self, orchestrator: BaseAIOrchestrator):
        self.orchestrator = orchestrator
        
        # Language detection cache (Redis)
        self.detection_cache = {}
    
    async def detect_language(self, text: str) -> Language:
        """Detect language of input text"""
        # Use OpenAI for language detection (more accurate than libraries)
        response = await self.orchestrator.execute(
            AIRequest(
                task_type=AITaskType.CLASSIFICATION,
                prompt=f"""Detect the language of this text. Respond with ONLY the language code.
                
Supported: en (English), hi (Hindi), ta (Tamil), te (Telugu), mr (Marathi), gu (Gujarati), kn (Kannada), ml (Malayalam), pa (Punjabi), bn (Bengali)

Text: {text}

Language code:""",
                temperature=0.0,
                max_tokens=5
            )
        )
        
        lang_code = response.result.strip().lower()
        return Language(lang_code) if lang_code in Language.__members__.values() else Language.ENGLISH
    
    async def translate(
        self,
        text: str,
        target_language: Language,
        source_language: Optional[Language] = None
    ) -> str:
        """Translate text to target language"""
        # Auto-detect source if not provided
        if source_language is None:
            source_language = await self.detect_language(text)
        
        # Skip if same language
        if source_language == target_language:
            return text
        
        # Use GPT-4 for high-quality translation
        response = await self.orchestrator.execute(
            AIRequest(
                task_type=AITaskType.TEXT_GENERATION,
                prompt=f"""Translate the following text from {source_language.value} to {target_language.value}.
                
IMPORTANT:
- Maintain professional tone
- Use domain-specific terminology (commodity trading, ERP)
- Keep formatting (markdown, numbers, units)
- Preserve named entities (company names, locations)

Text to translate:
{text}

Translation:""",
                temperature=0.3,
                max_tokens=len(text) * 3  # Allow for language expansion
            )
        )
        
        return response.result.strip()
    
    async def get_localized_prompt(
        self,
        prompt_key: str,
        language: Language,
        **variables
    ) -> str:
        """Get localized system prompt"""
        prompts = LOCALIZED_PROMPTS.get(prompt_key, {})
        template = prompts.get(language, prompts.get(Language.ENGLISH, ""))
        
        return template.format(**variables)


# Localized prompts for different languages
LOCALIZED_PROMPTS = {
    "system_trade_assistant": {
        Language.ENGLISH: """You are an AI assistant for commodity trading.
Help the user with trade management, pricing, and market insights.
Be professional and provide accurate information.""",
        
        Language.HINDI: """आप कमोडिटी ट्रेडिंग के लिए एक AI सहायक हैं।
उपयोगकर्ता को व्यापार प्रबंधन, मूल्य निर्धारण और बाजार अंतर्दृष्टि में मदद करें।
पेशेवर बनें और सटीक जानकारी प्रदान करें।""",
        
        Language.TAMIL: """நீங்கள் பண்டச் சந்தைக்கான AI உதவியாளர்.
வர்த்தக மேலாண்மை, விலை நிர்ணயம் மற்றும் சந்தை நுண்ணறிவுகளில் பயனருக்கு உதவுங்கள்.
தொழில்முறையாக இருங்கள் மற்றும் துல்லியமான தகவல்களை வழங்குங்கள்.""",
    },
    
    "greeting": {
        Language.ENGLISH: "Hello! How can I help you today?",
        Language.HINDI: "नमस्ते! आज मैं आपकी कैसे मदद कर सकता हूं?",
        Language.TAMIL: "வணக்கம்! இன்று நான் உங்களுக்கு எப்படி உதவ முடியும்?",
    },
    
    # Add more localized prompts...
}
```

**Multi-Language Chat Handler:**

```python
# backend/ai/conversation/multilingual_chat.py
class MultilingualChatHandler:
    """Handle multi-language conversations with auto-translation"""
    
    def __init__(
        self,
        orchestrator: BaseAIOrchestrator,
        translator: AITranslator,
        conversation_manager: ConversationManager
    ):
        self.orchestrator = orchestrator
        self.translator = translator
        self.conversation_manager = conversation_manager
    
    async def chat(
        self,
        conversation_id: UUID,
        user_message: str,
        user_language: Optional[Language] = None
    ) -> Dict:
        """
        Process chat message with multi-language support
        
        Workflow:
        1. Detect user's language
        2. Translate to English (for processing)
        3. Process with LLM
        4. Translate response back to user's language
        5. Save both original and translated in DB
        """
        start_time = time.time()
        
        # 1. Detect language if not provided
        if user_language is None:
            user_language = await self.translator.detect_language(user_message)
        
        # 2. Translate to English for processing (if needed)
        message_en = user_message
        if user_language != Language.ENGLISH:
            message_en = await self.translator.translate(
                user_message,
                Language.ENGLISH,
                user_language
            )
        
        # 3. Get conversation history (in English)
        memory = await self.conversation_manager.get_langchain_memory(conversation_id)
        
        # 4. Get localized system prompt
        conversation = await self.db.get(Conversation, conversation_id)
        system_prompt = await self.translator.get_localized_prompt(
            f"system_{conversation.assistant_type}",
            user_language
        )
        
        # 5. Process with LLM (in English)
        response = await self.orchestrator.execute(
            AIRequest(
                task_type=AITaskType.CHAT,
                prompt=message_en,
                context={
                    "system_message": system_prompt,
                    "chat_history": memory.chat_memory.messages
                },
                temperature=0.7
            )
        )
        
        response_en = response.result
        
        # 6. Translate response back to user's language
        response_localized = response_en
        if user_language != Language.ENGLISH:
            response_localized = await self.translator.translate(
                response_en,
                user_language,
                Language.ENGLISH
            )
        
        # 7. Save messages to DB (both versions)
        latency_ms = (time.time() - start_time) * 1000
        
        await self.conversation_manager.add_message(
            conversation_id=conversation_id,
            role="user",
            content=user_message,
            content_translated=message_en if user_language != Language.ENGLISH else None,
            language=user_language.value,
            tokens_used=response.tokens_used or 0,
            latency_ms=int(latency_ms)
        )
        
        await self.conversation_manager.add_message(
            conversation_id=conversation_id,
            role="assistant",
            content=response_localized,
            content_translated=response_en if user_language != Language.ENGLISH else None,
            language=user_language.value,
            tokens_used=response.tokens_used or 0,
            cost_usd=float(response.metadata.get("cost_usd", 0.0)) if response.metadata else 0.0,
            latency_ms=int(latency_ms)
        )
        
        return {
            "message": response_localized,
            "language": user_language.value,
            "detected_language": user_language.value,
            "latency_ms": latency_ms
        }
```

**Files to Create:**
- `backend/ai/i18n/__init__.py`
- `backend/ai/i18n/translator.py`
- `backend/ai/i18n/prompts.py` (localized prompt templates)
- `backend/ai/i18n/language_detector.py`
- `backend/ai/conversation/multilingual_chat.py`

---

## Phase 2: Streaming & Real-Time UX (CRITICAL) - 1-2 Days

### 2.1 Token Streaming 🔴 CRITICAL

**Problem:** Responses come all at once - poor UX for long responses

**Implementation:**

```python
# backend/ai/streaming/streamer.py
from typing import AsyncGenerator
import asyncio
from fastapi.responses import StreamingResponse

class AIStreamingHandler:
    """Handle streaming AI responses"""
    
    def __init__(self, orchestrator: BaseAIOrchestrator):
        self.orchestrator = orchestrator
    
    async def stream_chat(
        self,
        conversation_id: UUID,
        user_message: str,
        language: Language = Language.ENGLISH
    ) -> AsyncGenerator[str, None]:
        """
        Stream AI response token-by-token
        
        Yields:
            Server-Sent Events (SSE) format:
            data: {"type": "token", "content": "Hello"}
            data: {"type": "token", "content": " world"}
            data: {"type": "done", "metadata": {...}}
        """
        # Get conversation memory
        memory = await self.conversation_manager.get_langchain_memory(conversation_id)
        
        # Streaming LLM call
        full_response = ""
        async for token in self._stream_tokens(user_message, memory):
            full_response += token
            
            # Yield SSE format
            yield f"data: {json.dumps({'type': 'token', 'content': token})}\n\n"
        
        # Save to database after streaming complete
        await self.conversation_manager.add_message(
            conversation_id=conversation_id,
            role="user",
            content=user_message,
            language=language.value
        )
        
        await self.conversation_manager.add_message(
            conversation_id=conversation_id,
            role="assistant",
            content=full_response,
            language=language.value
        )
        
        # Send completion event
        yield f"data: {json.dumps({'type': 'done', 'metadata': {'tokens': len(full_response.split())}})}\n\n"
    
    async def _stream_tokens(
        self,
        message: str,
        memory: ConversationBufferMemory
    ) -> AsyncGenerator[str, None]:
        """Stream tokens from OpenAI"""
        from langchain_openai import ChatOpenAI
        
        llm = ChatOpenAI(
            model="gpt-4-turbo-preview",
            streaming=True,
            temperature=0.7
        )
        
        messages = memory.chat_memory.messages + [HumanMessage(content=message)]
        
        async for chunk in llm.astream(messages):
            if chunk.content:
                yield chunk.content


# FastAPI endpoint
@router.post("/chat/stream")
async def stream_chat(
    request: ChatStreamRequest,
    current_user: User = Depends(get_current_user),
    conversation_manager: ConversationManager = Depends(get_conversation_manager),
    streaming_handler: AIStreamingHandler = Depends(get_streaming_handler)
):
    """Stream chat response token-by-token"""
    
    return StreamingResponse(
        streaming_handler.stream_chat(
            conversation_id=request.conversation_id,
            user_message=request.message,
            language=Language(request.language or "en")
        ),
        media_type="text/event-stream"
    )
```

**Frontend Integration:**

```typescript
// frontend/src/services/ai/streamingChat.ts
export async function* streamChat(
  conversationId: string,
  message: string,
  language: string = "en"
): AsyncGenerator<string> {
  const response = await fetch("/api/v1/ai/chat/stream", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      "Authorization": `Bearer ${getToken()}`
    },
    body: JSON.stringify({
      conversation_id: conversationId,
      message,
      language
    })
  });

  const reader = response.body?.getReader();
  const decoder = new TextDecoder();

  while (true) {
    const { done, value } = await reader!.read();
    if (done) break;

    const chunk = decoder.decode(value);
    const lines = chunk.split("\n\n");

    for (const line of lines) {
      if (line.startsWith("data: ")) {
        const data = JSON.parse(line.slice(6));
        
        if (data.type === "token") {
          yield data.content;
        } else if (data.type === "done") {
          return;
        }
      }
    }
  }
}

// Usage in React component
function ChatInterface() {
  const [response, setResponse] = useState("");

  async function handleSend(message: string) {
    setResponse("");
    
    for await (const token of streamChat(conversationId, message)) {
      setResponse(prev => prev + token);
    }
  }

  return <div>{response}</div>;
}
```

**Files to Create:**
- `backend/ai/streaming/__init__.py`
- `backend/ai/streaming/streamer.py`
- `backend/ai/streaming/sse_handler.py`
- `backend/api/v1/endpoints/ai_streaming.py`

---

## Phase 3: Multi-Modal AI (HIGH) - 2-3 Days

### 3.1 Vision AI (GPT-4V) 🟡 HIGH

**Problem:** Can't analyze quality inspection photos, documents, invoices

**Implementation:**

```python
# backend/ai/multimodal/vision.py
from typing import List, Dict
import base64
from pathlib import Path

class VisionAI:
    """Multi-modal AI for image analysis"""
    
    def __init__(self, orchestrator: BaseAIOrchestrator):
        self.orchestrator = orchestrator
    
    async def analyze_quality_inspection_photo(
        self,
        image_url: str,
        commodity_type: str
    ) -> Dict:
        """
        Analyze quality inspection photo
        
        Use cases:
        - Cotton fiber quality assessment
        - Packaging condition inspection
        - Damage detection
        - Compliance verification
        """
        response = await self.orchestrator.execute(
            AIRequest(
                task_type=AITaskType.IMAGE_ANALYSIS,
                prompt=f"""Analyze this {commodity_type} quality inspection photo.

Provide detailed assessment of:
1. Visual quality grade (A/B/C/D)
2. Fiber length and uniformity (for cotton)
3. Color and brightness
4. Contamination/foreign matter
5. Packaging condition
6. Compliance with standards

Format response as JSON:
{{
    "quality_grade": "A",
    "fiber_assessment": {{}},
    "color_score": 8.5,
    "contamination": "none",
    "packaging_condition": "excellent",
    "compliance": true,
    "confidence": 0.92,
    "recommendations": []
}}""",
                context={"image_url": image_url},
                model="gpt-4-vision-preview"
            )
        )
        
        return json.loads(response.result)
    
    async def extract_invoice_data(
        self,
        invoice_image_url: str
    ) -> Dict:
        """Extract structured data from invoice image (OCR + Understanding)"""
        response = await self.orchestrator.execute(
            AIRequest(
                task_type=AITaskType.IMAGE_ANALYSIS,
                prompt="""Extract all data from this invoice image.

Return JSON:
{
    "invoice_number": "",
    "date": "",
    "seller": {},
    "buyer": {},
    "items": [],
    "amounts": {},
    "payment_terms": "",
    "confidence": 0.0
}""",
                context={"image_url": invoice_image_url},
                model="gpt-4-vision-preview"
            )
        )
        
        return json.loads(response.result)
    
    async def verify_document_authenticity(
        self,
        document_image_url: str,
        document_type: str
    ) -> Dict:
        """Detect forged/tampered documents"""
        response = await self.orchestrator.execute(
            AIRequest(
                task_type=AITaskType.IMAGE_ANALYSIS,
                prompt=f"""Analyze this {document_type} for authenticity.

Check for:
1. Watermarks and security features
2. Signature consistency
3. Stamp/seal authenticity
4. Text alignment anomalies
5. Digital manipulation signs

Risk assessment:
- Low: Document appears authentic
- Medium: Some inconsistencies found
- High: Likely forged/tampered

Return JSON with risk level and findings.""",
                context={"image_url": document_image_url},
                model="gpt-4-vision-preview"
            )
        )
        
        return json.loads(response.result)
```

### 3.2 Document Processing (OCR + Understanding)

```python
# backend/ai/multimodal/document_processor.py
from typing import BinaryIO
import pytesseract
from pdf2image import convert_from_path
from PIL import Image

class DocumentProcessor:
    """Advanced document processing with OCR and AI understanding"""
    
    def __init__(self, vision_ai: VisionAI, orchestrator: BaseAIOrchestrator):
        self.vision_ai = vision_ai
        self.orchestrator = orchestrator
    
    async def process_contract_pdf(
        self,
        pdf_path: str
    ) -> Dict:
        """
        Process contract PDF:
        1. OCR extraction
        2. AI understanding
        3. Clause extraction
        4. Risk analysis
        """
        # Convert PDF to images
        images = convert_from_path(pdf_path)
        
        # OCR each page
        full_text = ""
        for page_num, image in enumerate(images, 1):
            page_text = pytesseract.image_to_string(image)
            full_text += f"\n--- Page {page_num} ---\n{page_text}"
        
        # AI analysis
        analysis = await self.orchestrator.execute(
            AIRequest(
                task_type=AITaskType.DOCUMENT_ANALYSIS,
                prompt=f"""Analyze this contract and extract:

1. Parties (buyer/seller)
2. Commodity details
3. Quantity and pricing
4. Delivery terms
5. Payment terms
6. Force majeure clause
7. Dispute resolution
8. Key risks

Contract text:
{full_text}

Return structured JSON.""",
                temperature=0.1
            )
        )
        
        return {
            "full_text": full_text,
            "analysis": json.loads(analysis.result),
            "page_count": len(images)
        }
```

**Files to Create:**
- `backend/ai/multimodal/__init__.py`
- `backend/ai/multimodal/vision.py`
- `backend/ai/multimodal/document_processor.py`
- `backend/ai/multimodal/audio.py` (voice commands - future)

---

## Phase 4: AI Agents & Workflows (HIGH) - 3-4 Days

### 4.1 LangGraph Autonomous Agents 🟡 HIGH

**Problem:** Current system only does Q&A - need autonomous task execution

**Implementation:**

```python
# backend/ai/agents/trade_matching_agent.py
from langgraph.graph import StateGraph, END
from typing import TypedDict, List, Dict, Annotated
import operator

class TradeMatchState(TypedDict):
    """State for trade matching workflow"""
    availability_id: str
    requirements: List[Dict]
    matches: Annotated[List[Dict], operator.add]
    scores: Annotated[List[float], operator.add]
    current_step: str
    analysis: Dict


class TradeMatchingAgent:
    """
    Autonomous agent for intelligent trade matching
    
    Workflow:
    1. Fetch availability details
    2. Search similar requirements
    3. Score each match (quality, price, location)
    4. Analyze counterparty risk
    5. Rank matches by composite score
    6. Generate negotiation suggestions
    """
    
    def __init__(
        self,
        orchestrator: BaseAIOrchestrator,
        db: AsyncSession,
        vector_store: ChromaDBStore
    ):
        self.orchestrator = orchestrator
        self.db = db
        self.vector_store = vector_store
        
        # Build LangGraph workflow
        self.workflow = self._build_workflow()
    
    def _build_workflow(self) -> StateGraph:
        """Build autonomous workflow graph"""
        workflow = StateGraph(TradeMatchState)
        
        # Add nodes (steps)
        workflow.add_node("fetch_availability", self.fetch_availability)
        workflow.add_node("search_requirements", self.search_requirements)
        workflow.add_node("score_matches", self.score_matches)
        workflow.add_node("risk_analysis", self.risk_analysis)
        workflow.add_node("generate_recommendations", self.generate_recommendations)
        
        # Define edges (flow)
        workflow.set_entry_point("fetch_availability")
        workflow.add_edge("fetch_availability", "search_requirements")
        workflow.add_edge("search_requirements", "score_matches")
        workflow.add_edge("score_matches", "risk_analysis")
        workflow.add_edge("risk_analysis", "generate_recommendations")
        workflow.add_edge("generate_recommendations", END)
        
        return workflow.compile()
    
    async def fetch_availability(self, state: TradeMatchState) -> TradeMatchState:
        """Step 1: Fetch availability details from DB"""
        availability = await self.db.get(Availability, state["availability_id"])
        
        state["availability"] = {
            "commodity": availability.commodity.name,
            "quantity": availability.quantity,
            "price": availability.price_per_unit,
            "quality": availability.quality_params,
            "location": availability.location.city,
            "seller_id": str(availability.seller_partner_id)
        }
        state["current_step"] = "fetch_availability"
        return state
    
    async def search_requirements(self, state: TradeMatchState) -> TradeMatchState:
        """Step 2: Search for matching requirements using vector search"""
        availability = state["availability"]
        
        # Create search query
        query = f"""
        Looking for: {availability['commodity']}
        Quantity needed: {availability['quantity']} units
        Quality: {availability['quality']}
        Location: {availability['location']}
        """
        
        # Semantic search in requirements
        results = await self.vector_store.search(
            collection_name="requirements",
            query_embedding=await self._embed_text(query),
            k=20,
            filter={"commodity": availability["commodity"]}
        )
        
        state["requirements"] = [r["metadata"] for r in results]
        state["current_step"] = "search_requirements"
        return state
    
    async def score_matches(self, state: TradeMatchState) -> TradeMatchState:
        """Step 3: AI-powered scoring of matches"""
        availability = state["availability"]
        
        for requirement in state["requirements"]:
            # Use AI to score match comprehensively
            score_response = await self.orchestrator.execute(
                AIRequest(
                    task_type=AITaskType.SCORING,
                    prompt=f"""Score this trade match on scale 0-100:

AVAILABILITY:
- Commodity: {availability['commodity']}
- Quantity: {availability['quantity']}
- Price: ${availability['price']}/unit
- Quality: {availability['quality']}
- Location: {availability['location']}

REQUIREMENT:
- Commodity: {requirement['commodity']}
- Quantity: {requirement['quantity_needed']}
- Max Price: ${requirement['max_price']}/unit
- Quality: {requirement['quality_requirements']}
- Location: {requirement['delivery_location']}

Consider:
1. Quantity match (30%)
2. Price competitiveness (25%)
3. Quality alignment (25%)
4. Location proximity (10%)
5. Delivery timeline (10%)

Return JSON:
{{
    "total_score": 85,
    "breakdown": {{}},
    "reasoning": ""
}}""",
                    temperature=0.1
                )
            )
            
            score_data = json.loads(score_response.result)
            state["matches"].append({
                "requirement_id": requirement["id"],
                "score": score_data["total_score"],
                "breakdown": score_data["breakdown"],
                "reasoning": score_data["reasoning"]
            })
            state["scores"].append(score_data["total_score"])
        
        state["current_step"] = "score_matches"
        return state
    
    async def risk_analysis(self, state: TradeMatchState) -> TradeMatchState:
        """Step 4: Analyze counterparty risk for top matches"""
        top_matches = sorted(state["matches"], key=lambda x: x["score"], reverse=True)[:5]
        
        for match in top_matches:
            requirement = next(r for r in state["requirements"] if r["id"] == match["requirement_id"])
            buyer_id = requirement["buyer_id"]
            
            # Fetch buyer history
            buyer_trades = await self._get_buyer_history(buyer_id)
            
            # AI risk assessment
            risk_response = await self.orchestrator.execute(
                AIRequest(
                    task_type=AITaskType.CLASSIFICATION,
                    prompt=f"""Assess counterparty risk for this buyer:

BUYER HISTORY:
- Total Trades: {len(buyer_trades)}
- Completed: {sum(1 for t in buyer_trades if t.status == 'completed')}
- Disputed: {sum(1 for t in buyer_trades if t.status == 'disputed')}
- Payment Delays: {sum(1 for t in buyer_trades if t.payment_delayed)}
- Average Payment Days: {sum(t.payment_days for t in buyer_trades) / len(buyer_trades) if buyer_trades else 0}

Risk Level: LOW | MEDIUM | HIGH
Explanation:""",
                    temperature=0.0
                )
            )
            
            match["risk_assessment"] = risk_response.result
        
        state["current_step"] = "risk_analysis"
        return state
    
    async def generate_recommendations(self, state: TradeMatchState) -> TradeMatchState:
        """Step 5: Generate actionable recommendations"""
        top_matches = sorted(state["matches"], key=lambda x: x["score"], reverse=True)[:3]
        
        recommendations_response = await self.orchestrator.execute(
            AIRequest(
                task_type=AITaskType.TEXT_GENERATION,
                prompt=f"""Generate trade recommendations based on these top matches:

{json.dumps(top_matches, indent=2)}

Provide:
1. Top 3 recommended matches with reasoning
2. Suggested negotiation strategy for each
3. Pricing recommendations
4. Risk mitigation steps
5. Next actions

Format as actionable business advice.""",
                temperature=0.7
            )
        )
        
        state["recommendations"] = recommendations_response.result
        state["current_step"] = "complete"
        return state
    
    async def execute(self, availability_id: str) -> Dict:
        """Execute full matching workflow"""
        initial_state = TradeMatchState(
            availability_id=availability_id,
            requirements=[],
            matches=[],
            scores=[],
            current_step="init",
            analysis={}
        )
        
        final_state = await self.workflow.ainvoke(initial_state)
        
        return {
            "matches": final_state["matches"],
            "recommendations": final_state["recommendations"],
            "workflow_steps": final_state["current_step"]
        }
```

**Contract Analysis Agent:**

```python
# backend/ai/agents/contract_analysis_agent.py
class ContractAnalysisAgent:
    """
    Autonomous agent for contract analysis
    
    Workflow:
    1. Extract contract clauses
    2. Identify risks (force majeure, payment terms, penalties)
    3. Compare with standard templates
    4. Check compliance with regulations
    5. Generate negotiation points
    """
    
    async def analyze_contract(self, contract_id: UUID) -> Dict:
        """Full contract analysis workflow"""
        workflow = StateGraph(ContractAnalysisState)
        
        workflow.add_node("extract_clauses", self.extract_clauses)
        workflow.add_node("identify_risks", self.identify_risks)
        workflow.add_node("compliance_check", self.compliance_check)
        workflow.add_node("generate_negotiation_points", self.generate_negotiation_points)
        
        # ... workflow execution
```

**Files to Create:**
- `backend/ai/agents/__init__.py`
- `backend/ai/agents/trade_matching_agent.py`
- `backend/ai/agents/contract_analysis_agent.py`
- `backend/ai/agents/fraud_detection_agent.py`
- `backend/ai/agents/base_agent.py` (shared workflow utilities)

---

## Phase 5: Advanced RAG Pipeline (HIGH) - 2-3 Days

### 5.1 Advanced Retrieval-Augmented Generation 🟡 HIGH

**Problem:** Basic semantic search - needs query rewriting, hybrid search, reranking

**Implementation:**

```python
# backend/ai/rag/advanced_retrieval.py
from typing import List, Dict, Optional
from rank_bm25 import BM25Okapi
import numpy as np

class AdvancedRAGPipeline:
    """
    Production-grade RAG with:
    - Query rewriting
    - Hybrid search (semantic + keyword)
    - Reranking
    - Citation tracking
    - Confidence scoring
    """
    
    def __init__(
        self,
        orchestrator: BaseAIOrchestrator,
        vector_store: ChromaDBStore,
        db: AsyncSession
    ):
        self.orchestrator = orchestrator
        self.vector_store = vector_store
        self.db = db
    
    async def retrieve_and_answer(
        self,
        query: str,
        collection: str,
        k: int = 5,
        use_reranking: bool = True
    ) -> Dict:
        """
        Advanced RAG workflow:
        1. Query rewriting (expand query)
        2. Hybrid search (semantic + BM25)
        3. Reranking (cross-encoder)
        4. Answer generation with citations
        5. Confidence scoring
        """
        # Step 1: Query rewriting
        rewritten_queries = await self._rewrite_query(query)
        
        # Step 2: Hybrid retrieval
        all_results = []
        for q in rewritten_queries:
            semantic_results = await self._semantic_search(q, collection, k=20)
            keyword_results = await self._keyword_search(q, collection, k=20)
            
            # Merge with reciprocal rank fusion
            merged = self._reciprocal_rank_fusion(semantic_results, keyword_results)
            all_results.extend(merged)
        
        # Deduplicate
        unique_results = self._deduplicate(all_results)
        
        # Step 3: Reranking
        if use_reranking:
            reranked = await self._rerank(query, unique_results[:50])
        else:
            reranked = unique_results[:k]
        
        # Step 4: Generate answer with citations
        answer = await self._generate_answer_with_citations(query, reranked[:k])
        
        # Step 5: Confidence scoring
        confidence = await self._calculate_confidence(query, answer, reranked[:k])
        
        return {
            "answer": answer["text"],
            "sources": answer["sources"],
            "confidence": confidence,
            "retrieved_chunks": len(reranked),
            "query_rewrites": rewritten_queries
        }
    
    async def _rewrite_query(self, query: str) -> List[str]:
        """Expand query to improve retrieval"""
        response = await self.orchestrator.execute(
            AIRequest(
                task_type=AITaskType.TEXT_GENERATION,
                prompt=f"""Given this user query, generate 3 alternative phrasings to improve search recall.

Original query: {query}

Generate queries that:
1. Use synonyms and related terms
2. Expand abbreviations
3. Add domain context

Return JSON array:
["query1", "query2", "query3"]""",
                temperature=0.3,
                max_tokens=200
            )
        )
        
        rewrites = json.loads(response.result)
        return [query] + rewrites  # Include original
    
    async def _semantic_search(
        self,
        query: str,
        collection: str,
        k: int = 20
    ) -> List[Dict]:
        """Semantic vector search"""
        query_embedding = await self._embed_text(query)
        
        results = await self.vector_store.search(
            collection_name=collection,
            query_embedding=query_embedding,
            k=k
        )
        
        return [{
            "document": r["document"],
            "metadata": r["metadata"],
            "score": r["distance"],
            "source": "semantic"
        } for r in results]
    
    async def _keyword_search(
        self,
        query: str,
        collection: str,
        k: int = 20
    ) -> List[Dict]:
        """BM25 keyword search"""
        # Fetch all documents from collection (cache this in production)
        all_docs = await self._get_collection_documents(collection)
        
        # Tokenize
        tokenized_docs = [doc["text"].lower().split() for doc in all_docs]
        bm25 = BM25Okapi(tokenized_docs)
        
        # Search
        tokenized_query = query.lower().split()
        scores = bm25.get_scores(tokenized_query)
        
        # Get top k
        top_indices = np.argsort(scores)[-k:][::-1]
        
        return [{
            "document": all_docs[i]["text"],
            "metadata": all_docs[i]["metadata"],
            "score": scores[i],
            "source": "keyword"
        } for i in top_indices]
    
    def _reciprocal_rank_fusion(
        self,
        semantic_results: List[Dict],
        keyword_results: List[Dict],
        k: int = 60
    ) -> List[Dict]:
        """Merge two result lists using RRF"""
        doc_scores = {}
        
        # Score semantic results
        for rank, result in enumerate(semantic_results, 1):
            doc_id = result["metadata"].get("id", result["document"][:50])
            doc_scores[doc_id] = doc_scores.get(doc_id, 0) + 1 / (k + rank)
        
        # Score keyword results
        for rank, result in enumerate(keyword_results, 1):
            doc_id = result["metadata"].get("id", result["document"][:50])
            doc_scores[doc_id] = doc_scores.get(doc_id, 0) + 1 / (k + rank)
        
        # Sort by fused score
        sorted_docs = sorted(doc_scores.items(), key=lambda x: x[1], reverse=True)
        
        # Return full documents
        doc_map = {r["metadata"].get("id", r["document"][:50]): r for r in semantic_results + keyword_results}
        return [doc_map[doc_id] for doc_id, _ in sorted_docs if doc_id in doc_map]
    
    async def _rerank(
        self,
        query: str,
        results: List[Dict],
        top_k: int = 10
    ) -> List[Dict]:
        """Rerank using cross-encoder or LLM"""
        # Use LLM as reranker
        rerank_response = await self.orchestrator.execute(
            AIRequest(
                task_type=AITaskType.SCORING,
                prompt=f"""Rerank these documents by relevance to the query.

Query: {query}

Documents:
{json.dumps([{"id": i, "text": r["document"][:500]} for i, r in enumerate(results)], indent=2)}

Return JSON array of document IDs sorted by relevance (most relevant first):
[2, 5, 1, 8, ...]""",
                temperature=0.0
            )
        )
        
        reranked_ids = json.loads(rerank_response.result)
        return [results[i] for i in reranked_ids[:top_k] if i < len(results)]
    
    async def _generate_answer_with_citations(
        self,
        query: str,
        sources: List[Dict]
    ) -> Dict:
        """Generate answer with inline citations"""
        context = "\n\n".join([
            f"[{i+1}] {s['document']}"
            for i, s in enumerate(sources)
        ])
        
        response = await self.orchestrator.execute(
            AIRequest(
                task_type=AITaskType.TEXT_GENERATION,
                prompt=f"""Answer the question using the provided sources. 

IMPORTANT:
- Cite sources using [1], [2], etc.
- Only use information from sources
- If sources don't contain answer, say so
- Be concise and accurate

Question: {query}

Sources:
{context}

Answer with citations:""",
                temperature=0.3
            )
        )
        
        return {
            "text": response.result,
            "sources": [{
                "id": i + 1,
                "text": s["document"],
                "metadata": s["metadata"]
            } for i, s in enumerate(sources)]
        }
    
    async def _calculate_confidence(
        self,
        query: str,
        answer: Dict,
        sources: List[Dict]
    ) -> float:
        """Calculate confidence score for answer"""
        # Factors:
        # 1. Number of supporting sources
        # 2. Source similarity scores
        # 3. Answer completeness
        
        source_count_score = min(len(sources) / 5.0, 1.0)
        avg_source_score = np.mean([s.get("score", 0.5) for s in sources])
        
        # Ask LLM to self-assess
        confidence_response = await self.orchestrator.execute(
            AIRequest(
                task_type=AITaskType.SCORING,
                prompt=f"""Rate your confidence in this answer on scale 0.0 to 1.0.

Question: {query}
Answer: {answer['text']}
Number of sources: {len(sources)}

Confidence (0.0-1.0):""",
                temperature=0.0,
                max_tokens=10
            )
        )
        
        try:
            llm_confidence = float(confidence_response.result.strip())
        except:
            llm_confidence = 0.5
        
        # Weighted average
        confidence = (
            0.3 * source_count_score +
            0.3 * avg_source_score +
            0.4 * llm_confidence
        )
        
        return round(confidence, 2)
```

**Files to Create:**
- `backend/ai/rag/__init__.py`
- `backend/ai/rag/advanced_retrieval.py`
- `backend/ai/rag/query_rewriter.py`
- `backend/ai/rag/hybrid_search.py`
- `backend/ai/rag/reranker.py`
- `backend/ai/rag/citation_tracker.py`

---

## Phase 6: Observability & Monitoring (MEDIUM) - 2 Days

### 6.1 AI Observability & Monitoring 🟡 MEDIUM

**Problem:** No visibility into AI usage, costs, errors, or performance

**Implementation:**

```python
# backend/ai/observability/tracker.py
from dataclasses import dataclass
from datetime import datetime
from typing import Optional
import time

@dataclass
class AICallMetrics:
    """Track every AI call for observability"""
    request_id: str
    provider: str
    model: str
    task_type: str
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int
    cost_usd: float
    latency_ms: float
    status: str  # success | error | timeout
    error_message: Optional[str]
    user_id: Optional[str]
    organization_id: Optional[str]
    timestamp: datetime


class AIMetricsTracker:
    """
    Track all AI calls for:
    - Cost monitoring (prevent runaway costs)
    - Performance analysis
    - Error tracking
    - Usage analytics
    - Compliance/audit trail
    """
    
    def __init__(self, db: AsyncSession, redis: Optional[Redis] = None):
        self.db = db
        self.redis = redis
    
    async def track_call(self, metrics: AICallMetrics):
        """Log AI call to database + real-time cache"""
        # 1. Store in PostgreSQL (permanent audit trail)
        await self._store_to_db(metrics)
        
        # 2. Update Redis counters (real-time dashboard)
        await self._update_redis_metrics(metrics)
        
        # 3. Check cost thresholds (prevent budget overruns)
        await self._check_cost_alerts(metrics)
    
    async def get_daily_cost(self, org_id: str) -> float:
        """Get today's AI spend for organization"""
        pass
    
    async def get_usage_stats(self, org_id: str, days: int = 7):
        """Get AI usage statistics"""
        pass
```

**Database Schema:**
```sql
CREATE TABLE ai_metrics (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    request_id UUID NOT NULL,
    provider VARCHAR(50) NOT NULL,
    model VARCHAR(100) NOT NULL,
    task_type VARCHAR(50) NOT NULL,
    prompt_tokens INTEGER NOT NULL,
    completion_tokens INTEGER NOT NULL,
    total_tokens INTEGER NOT NULL,
    cost_usd DECIMAL(10, 6) NOT NULL,
    latency_ms INTEGER NOT NULL,
    status VARCHAR(20) NOT NULL,
    error_message TEXT,
    user_id UUID,
    organization_id UUID,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX idx_ai_metrics_org_date ON ai_metrics(organization_id, created_at);
CREATE INDEX idx_ai_metrics_provider ON ai_metrics(provider, created_at);
```

**Cost Tracking:**
```python
# backend/ai/observability/cost_calculator.py
class CostCalculator:
    """Calculate AI costs across providers"""
    
    PRICING = {
        "gpt-4-turbo-preview": {
            "input": 0.01,   # per 1K tokens
            "output": 0.03,  # per 1K tokens
        },
        "gpt-3.5-turbo": {
            "input": 0.0005,
            "output": 0.0015,
        },
        "text-embedding-3-small": {
            "input": 0.00002,
            "output": 0.0,
        },
    }
    
    @classmethod
    def calculate(cls, model: str, input_tokens: int, output_tokens: int) -> float:
        """Calculate cost in USD"""
        pricing = cls.PRICING.get(model, {"input": 0, "output": 0})
        input_cost = (input_tokens / 1000) * pricing["input"]
        output_cost = (output_tokens / 1000) * pricing["output"]
        return input_cost + output_cost
```

**Files to Create:**
- `backend/ai/observability/__init__.py`
- `backend/ai/observability/tracker.py`
- `backend/ai/observability/cost_calculator.py`
- `backend/ai/observability/models.py` (SQLAlchemy model)
- `backend/db/migrations/versions/add_ai_metrics.py`

---

### 1.2 Error Handling & Retry Logic 🔴 CRITICAL

**Problem:** No graceful handling of API failures, rate limits, timeouts

**Implementation:**

```python
# backend/ai/resilience/retry.py
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
)
import openai

class AIResilient:
    """Robust AI calls with retry logic"""
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type((
            openai.error.RateLimitError,
            openai.error.APIError,
            openai.error.Timeout,
        ))
    )
    async def call_with_retry(self, func, *args, **kwargs):
        """Execute AI call with exponential backoff"""
        try:
            return await func(*args, **kwargs)
        except openai.error.RateLimitError as e:
            logger.warning(f"Rate limit hit: {e}")
            raise
        except openai.error.APIError as e:
            logger.error(f"API error: {e}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error: {e}", exc_info=True)
            raise AIOrchestrationError(f"AI call failed: {e}")
```

**Circuit Breaker:**
```python
# backend/ai/resilience/circuit_breaker.py
from enum import Enum
from datetime import datetime, timedelta

class CircuitState(Enum):
    CLOSED = "closed"    # Normal operation
    OPEN = "open"        # Failing, stop calling
    HALF_OPEN = "half_open"  # Testing recovery

class CircuitBreaker:
    """Prevent cascading failures from AI provider outages"""
    
    def __init__(
        self,
        failure_threshold: int = 5,
        timeout: int = 60,
        redis: Optional[Redis] = None
    ):
        self.failure_threshold = failure_threshold
        self.timeout = timeout
        self.redis = redis
    
    async def call(self, func, *args, **kwargs):
        """Execute function with circuit breaker protection"""
        state = await self._get_state()
        
        if state == CircuitState.OPEN:
            if await self._should_attempt_reset():
                await self._set_state(CircuitState.HALF_OPEN)
            else:
                raise AIProviderUnavailableError("Circuit breaker OPEN")
        
        try:
            result = await func(*args, **kwargs)
            await self._on_success()
            return result
        except Exception as e:
            await self._on_failure()
            raise
```

**Files to Create:**
- `backend/ai/resilience/__init__.py`
- `backend/ai/resilience/retry.py`
- `backend/ai/resilience/circuit_breaker.py`
- `backend/ai/resilience/fallback.py`

---

### 1.3 Caching Layer 🟡 HIGH

**Problem:** Repeated identical queries waste money and time

**Implementation:**

```python
# backend/ai/caching/semantic_cache.py
import hashlib
from typing import Optional

class SemanticCache:
    """Cache AI responses with semantic similarity"""
    
    def __init__(self, redis: Redis, ttl: int = 3600):
        self.redis = redis
        self.ttl = ttl
    
    def _generate_cache_key(self, request: AIRequest) -> str:
        """Generate deterministic cache key"""
        key_data = f"{request.task_type}:{request.prompt}:{request.model}:{request.temperature}"
        return f"ai:cache:{hashlib.sha256(key_data.encode()).hexdigest()}"
    
    async def get(self, request: AIRequest) -> Optional[AIResponse]:
        """Get cached response if exists"""
        key = self._generate_cache_key(request)
        cached = await self.redis.get(key)
        if cached:
            return AIResponse.parse_raw(cached)
        return None
    
    async def set(self, request: AIRequest, response: AIResponse):
        """Cache AI response"""
        key = self._generate_cache_key(request)
        await self.redis.setex(
            key,
            self.ttl,
            response.json()
        )
    
    async def invalidate(self, pattern: str):
        """Invalidate cache by pattern"""
        keys = await self.redis.keys(f"ai:cache:{pattern}*")
        if keys:
            await self.redis.delete(*keys)
```

**Smart Caching Strategy:**
- ✅ Cache: Classification, scoring, summarization (deterministic)
- ❌ Don't Cache: Chat, generation (conversational context)
- 🔄 Partial Cache: Embeddings (cache at document level)

**Files to Create:**
- `backend/ai/caching/__init__.py`
- `backend/ai/caching/semantic_cache.py`
- `backend/ai/caching/embedding_cache.py`

---

### 1.4 Rate Limiting & Quotas 🟡 HIGH

**Problem:** No protection against abuse or runaway costs

**Implementation:**

```python
# backend/ai/quota/rate_limiter.py
from datetime import datetime, timedelta

class AIRateLimiter:
    """Prevent AI abuse and budget overruns"""
    
    LIMITS = {
        "free": {
            "calls_per_hour": 100,
            "tokens_per_day": 50000,
            "cost_per_day": 5.0,
        },
        "pro": {
            "calls_per_hour": 1000,
            "tokens_per_day": 500000,
            "cost_per_day": 50.0,
        },
        "enterprise": {
            "calls_per_hour": 10000,
            "tokens_per_day": 5000000,
            "cost_per_day": 500.0,
        },
    }
    
    def __init__(self, redis: Redis):
        self.redis = redis
    
    async def check_limit(
        self,
        org_id: str,
        tier: str,
        tokens: int
    ) -> bool:
        """Check if organization is within limits"""
        limits = self.LIMITS[tier]
        
        # Check hourly calls
        calls_key = f"ai:rate:{org_id}:calls:{datetime.utcnow().hour}"
        calls = await self.redis.incr(calls_key)
        await self.redis.expire(calls_key, 3600)
        
        if calls > limits["calls_per_hour"]:
            raise AIQuotaExceededError("Hourly call limit exceeded")
        
        # Check daily tokens
        tokens_key = f"ai:quota:{org_id}:tokens:{datetime.utcnow().date()}"
        total_tokens = await self.redis.incrby(tokens_key, tokens)
        await self.redis.expire(tokens_key, 86400)
        
        if total_tokens > limits["tokens_per_day"]:
            raise AIQuotaExceededError("Daily token limit exceeded")
        
        return True
```

**Files to Create:**
- `backend/ai/quota/__init__.py`
- `backend/ai/quota/rate_limiter.py`
- `backend/ai/quota/models.py`

---

## Phase 2: Embeddings & Vector Search (HIGH) - 2-3 Days

### 2.1 Production ChromaDB Setup 🟡 HIGH

**Current:** Basic ChromaDB exists but not production-ready

**Improvements Needed:**

```python
# backend/ai/embeddings/chromadb/store.py (ENHANCE)
class ChromaDBStore:
    """Production-ready vector store"""
    
    def __init__(self, persist_directory: str = "./chroma_db"):
        # ✅ Add: Persistent storage
        # ✅ Add: Collection versioning
        # ✅ Add: Backup/restore
        # ✅ Add: Migration support
        pass
    
    async def add_documents_batch(
        self,
        collection_name: str,
        documents: List[str],
        metadatas: List[Dict],
        ids: List[str],
        batch_size: int = 100
    ):
        """Add documents in batches to prevent memory issues"""
        for i in range(0, len(documents), batch_size):
            batch_docs = documents[i:i+batch_size]
            batch_meta = metadatas[i:i+batch_size]
            batch_ids = ids[i:i+batch_size]
            await self.add_documents(collection_name, batch_docs, batch_meta, batch_ids)
    
    async def backup_collection(self, collection_name: str, backup_path: str):
        """Backup collection for disaster recovery"""
        pass
    
    async def migrate_collection(
        self,
        old_name: str,
        new_name: str,
        transform_fn: Optional[callable] = None
    ):
        """Migrate collection with optional transformation"""
        pass
```

**Files to Enhance:**
- `backend/ai/embeddings/chromadb/store.py` (add production features)
- `backend/ai/embeddings/chromadb/backup.py` (NEW)
- `backend/ai/embeddings/chromadb/migration.py` (NEW)

---

### 2.2 Embedding Generation Pipeline 🟡 HIGH

**Problem:** No systematic document embedding pipeline

**Implementation:**

```python
# backend/ai/embeddings/pipeline/embedder.py
from typing import List, Dict, Any
from uuid import UUID

class DocumentEmbeddingPipeline:
    """Systematic document embedding workflow"""
    
    def __init__(
        self,
        orchestrator: BaseAIOrchestrator,
        vector_store: ChromaDBStore,
        db: AsyncSession
    ):
        self.orchestrator = orchestrator
        self.vector_store = vector_store
        self.db = db
    
    async def embed_contract(self, contract_id: UUID):
        """Embed contract for semantic search"""
        # 1. Fetch contract from database
        contract = await self.db.get(Contract, contract_id)
        
        # 2. Extract text (OCR if needed)
        text = contract.full_text or await self._ocr_document(contract.file_url)
        
        # 3. Chunk text (max 8000 tokens per chunk)
        chunks = self._chunk_text(text, max_tokens=8000)
        
        # 4. Generate embeddings
        embeddings = []
        for chunk in chunks:
            response = await self.orchestrator.execute(
                AIRequest(
                    task_type=AITaskType.EMBEDDING,
                    prompt=chunk
                )
            )
            embeddings.append(response.result)
        
        # 5. Store in vector database
        await self.vector_store.add_documents(
            collection_name="contracts",
            documents=chunks,
            metadatas=[{
                "contract_id": str(contract_id),
                "chunk_index": i,
                "party_a": contract.party_a,
                "party_b": contract.party_b,
                "start_date": contract.start_date.isoformat(),
            } for i in range(len(chunks))],
            embeddings=embeddings
        )
    
    async def embed_availability(self, availability_id: UUID):
        """Embed availability for semantic matching"""
        availability = await self.db.get(Availability, availability_id)
        
        # Create rich text representation
        text = f"""
        Commodity: {availability.commodity.name}
        Seller: {availability.seller_partner.legal_name}
        Location: {availability.location.city}, {availability.location.state}
        Quantity: {availability.quantity} {availability.unit}
        Price: {availability.price_per_unit} {availability.currency}
        Quality: {availability.quality_params}
        """
        
        # Generate embedding
        response = await self.orchestrator.execute(
            AIRequest(task_type=AITaskType.EMBEDDING, prompt=text)
        )
        
        # Update availability record
        availability.market_context_embedding = response.result
        await self.db.commit()
```

**Files to Create:**
- `backend/ai/embeddings/pipeline/__init__.py`
- `backend/ai/embeddings/pipeline/embedder.py`
- `backend/ai/embeddings/pipeline/chunker.py`
- `backend/ai/embeddings/pipeline/scheduler.py` (batch embedding jobs)

---

### 2.3 Semantic Search Enhancement 🟡 HIGH

**Current:** Basic search exists, needs advanced features

**Enhancements:**

```python
# backend/ai/embeddings/chromadb/search.py (ENHANCE)
class SemanticSearch:
    """Advanced semantic search"""
    
    async def hybrid_search(
        self,
        query: str,
        collection: str,
        k: int = 10,
        filters: Optional[Dict] = None,
        rerank: bool = True
    ) -> List[Dict]:
        """
        Hybrid search: Semantic + Keyword + Reranking
        
        Steps:
        1. Semantic vector search (get top 50)
        2. Keyword BM25 search (get top 50)
        3. Merge and deduplicate
        4. Rerank with cross-encoder
        5. Return top K
        """
        # Semantic search
        semantic_results = await self.vector_search(query, collection, k=50, filters=filters)
        
        # Keyword search
        keyword_results = await self.keyword_search(query, collection, k=50, filters=filters)
        
        # Merge results
        merged = self._merge_results(semantic_results, keyword_results)
        
        # Rerank if requested
        if rerank:
            merged = await self._rerank(query, merged)
        
        return merged[:k]
    
    async def _rerank(self, query: str, results: List[Dict]) -> List[Dict]:
        """Rerank results using cross-encoder for better relevance"""
        # Use OpenAI or local cross-encoder model
        pass
```

---

## Phase 3: ML Models & Analytics (MEDIUM) - 4-5 Days

### 3.1 Price Prediction Model 🟡 MEDIUM

**Current:** Empty placeholder

**Implementation:**

```python
# backend/ai/models/price_prediction/predictor.py
from sklearn.ensemble import RandomForestRegressor
import numpy as np

class PricePredictor:
    """Predict fair market price for commodities"""
    
    def __init__(self, db: AsyncSession):
        self.db = db
        self.model = None
    
    async def train(self, commodity_id: UUID, historical_days: int = 90):
        """Train price prediction model"""
        # 1. Fetch historical data
        trades = await self._fetch_historical_trades(commodity_id, historical_days)
        
        # 2. Feature engineering
        X = self._extract_features(trades)
        y = np.array([t.price_per_unit for t in trades])
        
        # 3. Train model
        self.model = RandomForestRegressor(n_estimators=100)
        self.model.fit(X, y)
        
        # 4. Save model
        await self._save_model(commodity_id)
    
    def _extract_features(self, trades):
        """Extract features from trades"""
        features = []
        for trade in trades:
            features.append([
                trade.quantity,
                trade.quality_params.get("staple_length", 0),
                trade.quality_params.get("micronaire", 0),
                trade.seller_partner.credit_score,
                trade.location.distance_from_major_port,
                trade.created_at.month,  # Seasonality
                trade.created_at.day_of_week,
            ])
        return np.array(features)
    
    async def predict(
        self,
        commodity_id: UUID,
        quantity: float,
        quality_params: Dict,
        location: str
    ) -> Dict[str, float]:
        """Predict price with confidence interval"""
        # Load model
        model = await self._load_model(commodity_id)
        
        # Predict
        X = self._extract_features_single(quantity, quality_params, location)
        prediction = model.predict([X])[0]
        
        # Calculate confidence interval
        predictions = [tree.predict([X])[0] for tree in model.estimators_]
        std = np.std(predictions)
        
        return {
            "predicted_price": float(prediction),
            "lower_bound": float(prediction - 1.96 * std),
            "upper_bound": float(prediction + 1.96 * std),
            "confidence": 0.95
        }
```

**Files to Create:**
- `backend/ai/models/price_prediction/predictor.py`
- `backend/ai/models/price_prediction/trainer.py`
- `backend/ai/models/price_prediction/evaluator.py`
- `backend/ai/models/price_prediction/features.py`

---

### 3.2 Demand Forecasting 🟡 MEDIUM

```python
# backend/ai/models/demand_forecasting/forecaster.py
from statsmodels.tsa.arima.model import ARIMA

class DemandForecaster:
    """Forecast commodity demand using time series analysis"""
    
    async def forecast(
        self,
        commodity_id: UUID,
        location: str,
        forecast_days: int = 30
    ) -> List[Dict]:
        """Predict demand for next N days"""
        # 1. Fetch historical demand
        history = await self._fetch_demand_history(commodity_id, location)
        
        # 2. Fit ARIMA model
        model = ARIMA(history, order=(7, 1, 7))
        fitted = model.fit()
        
        # 3. Generate forecast
        forecast = fitted.forecast(steps=forecast_days)
        
        return [{
            "date": (datetime.utcnow() + timedelta(days=i)).date(),
            "predicted_demand": float(forecast[i]),
        } for i in range(forecast_days)]
```

---

### 3.3 Quality Scoring AI 🟡 MEDIUM

```python
# backend/ai/models/quality_scoring/scorer.py
class QualityScorer:
    """AI-powered quality parameter validation and scoring"""
    
    async def score_quality_report(
        self,
        commodity_id: UUID,
        quality_params: Dict[str, Any],
        supplier_id: UUID
    ) -> Dict:
        """
        Score quality report for:
        - Consistency with supplier history
        - Parameter validity
        - Anomaly detection
        """
        # 1. Fetch supplier history
        history = await self._fetch_supplier_quality_history(supplier_id)
        
        # 2. Anomaly detection
        anomalies = self._detect_anomalies(quality_params, history)
        
        # 3. Consistency score
        consistency_score = self._calculate_consistency(quality_params, history)
        
        # 4. Overall quality score
        overall_score = self._calculate_overall_score(quality_params, commodity_id)
        
        return {
            "overall_score": overall_score,
            "consistency_score": consistency_score,
            "anomalies": anomalies,
            "confidence": 0.9
        }
```

---

## Phase 4: Testing & Documentation (CRITICAL) - 2 Days

### 4.1 Unit Tests

```python
# backend/tests/ai/test_orchestrator.py
import pytest
from backend.ai.orchestrators.base import AIRequest, AITaskType
from backend.ai.orchestrators.factory import get_orchestrator

@pytest.mark.asyncio
async def test_text_generation():
    """Test basic text generation"""
    orchestrator = get_orchestrator()
    
    response = await orchestrator.execute(
        AIRequest(
            task_type=AITaskType.TEXT_GENERATION,
            prompt="Explain cotton trading in 2 sentences",
            max_tokens=100
        )
    )
    
    assert response.result
    assert len(response.result) > 10
    assert response.provider == AIProvider.OPENAI


@pytest.mark.asyncio
async def test_cost_tracking():
    """Test AI cost tracking"""
    tracker = AIMetricsTracker(db, redis)
    
    metrics = AICallMetrics(
        request_id=str(uuid4()),
        provider="openai",
        model="gpt-4-turbo-preview",
        prompt_tokens=100,
        completion_tokens=50,
        cost_usd=0.002,
        ...
    )
    
    await tracker.track_call(metrics)
    
    daily_cost = await tracker.get_daily_cost(org_id)
    assert daily_cost >= 0.002
```

**Test Files to Create:**
- `backend/tests/ai/test_orchestrator.py`
- `backend/tests/ai/test_caching.py`
- `backend/tests/ai/test_retry.py`
- `backend/tests/ai/test_embeddings.py`
- `backend/tests/ai/test_price_prediction.py`

---

### 4.2 Integration Tests

```python
# backend/tests/ai/test_e2e_embedding.py
@pytest.mark.asyncio
async def test_contract_embedding_pipeline():
    """Test full contract embedding workflow"""
    # 1. Create test contract
    contract = await create_test_contract()
    
    # 2. Run embedding pipeline
    pipeline = DocumentEmbeddingPipeline(orchestrator, vector_store, db)
    await pipeline.embed_contract(contract.id)
    
    # 3. Verify search works
    search = SemanticSearch(vector_store)
    results = await search.search_contracts(
        query="cotton supply agreement",
        k=5
    )
    
    assert len(results) > 0
    assert any(r["metadata"]["contract_id"] == str(contract.id) for r in results)
```

---

### 4.3 Documentation

```markdown
# AI/README.md

## Architecture

- **Orchestrators:** Abstract provider interface
- **Embeddings:** Vector search via ChromaDB
- **ML Models:** Scikit-learn/statsmodels
- **Observability:** Full tracking of all AI calls

## Usage

### Basic AI Call
```python
from backend.ai.orchestrators.factory import get_orchestrator
from backend.ai.orchestrators.base import AIRequest, AITaskType

orchestrator = get_orchestrator()
response = await orchestrator.execute(
    AIRequest(
        task_type=AITaskType.SCORING,
        prompt="Score this trade match: ...",
        temperature=0.0
    )
)
score = response.result["score"]
```

### Semantic Search
```python
from backend.ai.embeddings.chromadb import SemanticSearch

search = SemanticSearch(vector_store)
results = await search.search_contracts(
    query="force majeure clause",
    k=5
)
```

## Cost Management

- Daily budgets per organization
- Rate limiting per tier
- Automatic alerts at 80% quota

## Monitoring

Dashboard: `/admin/ai-metrics`
- Real-time cost tracking
- Usage analytics
- Error rates
- Performance metrics
```

---

---

## Enhanced API Endpoints

### Current vs New API Design

**CURRENT (Basic):**
```python
POST /api/v1/ai/chat
{
  "message": "What is the cotton price?",
  "assistant_type": "trade"
}

Response:
{
  "response": "The current cotton price is..."
}
```

**NEW (Enterprise):**
```python
# 1. Create conversation
POST /api/v1/ai/conversations
{
  "assistant_type": "trade",
  "language": "hi"  # Hindi
}

Response:
{
  "conversation_id": "uuid",
  "session_id": "sess_xyz",
  "language": "hi"
}

# 2. Stream chat
POST /api/v1/ai/conversations/{id}/chat/stream
{
  "message": "कपास की कीमत क्या है?",  # Hindi: What is cotton price?
  "language": "hi"
}

Response (SSE):
data: {"type": "token", "content": "वर्तमान"}
data: {"type": "token", "content": " कपास"}
data: {"type": "token", "content": " की"}
data: {"type": "token", "content": " कीमत"}
...
data: {"type": "done", "metadata": {"tokens": 150, "cost_usd": 0.003, "latency_ms": 2100}}

# 3. Advanced RAG search
POST /api/v1/ai/rag/search
{
  "query": "contracts with force majeure clause",
  "collection": "contracts",
  "use_reranking": true,
  "k": 5
}

Response:
{
  "answer": "Based on the contracts, force majeure clauses [1][2]...",
  "sources": [{
    "id": 1,
    "text": "...",
    "metadata": {"contract_id": "..."}
  }],
  "confidence": 0.87,
  "retrieved_chunks": 15
}

# 4. Multi-modal: Analyze quality photo
POST /api/v1/ai/multimodal/analyze-image
Content-Type: multipart/form-data

{
  "image": <file>,
  "analysis_type": "quality_inspection",
  "commodity_type": "cotton"
}

Response:
{
  "quality_grade": "A",
  "fiber_assessment": {...},
  "confidence": 0.92,
  "recommendations": [...]
}

# 5. AI Agent: Autonomous trade matching
POST /api/v1/ai/agents/trade-matching
{
  "availability_id": "uuid"
}

Response:
{
  "matches": [{
    "requirement_id": "uuid",
    "score": 85,
    "reasoning": "...",
    "risk_assessment": "LOW"
  }],
  "recommendations": "Top match is Buyer ABC. Suggest negotiating price...",
  "workflow_steps": ["fetch", "search", "score", "risk", "recommend"]
}

# 6. Get conversation history
GET /api/v1/ai/conversations/{id}/history?limit=50

Response:
{
  "conversation_id": "uuid",
  "messages": [{
    "role": "user",
    "content": "...",
    "language": "hi",
    "timestamp": "..."
  }],
  "total_messages": 42,
  "total_cost_usd": 0.15
}

# 7. AI Analytics Dashboard
GET /api/v1/ai/analytics/usage?days=7

Response:
{
  "total_calls": 1523,
  "total_cost_usd": 45.67,
  "average_latency_ms": 1850,
  "error_rate": 0.02,
  "by_assistant": {
    "trade": {"calls": 800, "cost": 25.00},
    "contract": {"calls": 500, "cost": 15.00}
  },
  "by_language": {
    "en": 60%,
    "hi": 30%,
    "ta": 10%
  }
}
```

---

## Implementation Timeline (Revised)

### Week 1: Conversation & Multi-Language (CRITICAL)
- **Day 1:** Database models for conversations, migrations
- **Day 2:** Conversation manager, persistence layer, Redis caching
- **Day 3:** Multi-language support, translator, language detection
- **Day 4:** Multi-lingual chat handler, API endpoints
- **Day 5:** Testing & validation

### Week 2: Streaming & Multi-Modal (CRITICAL/HIGH)
- **Day 6:** Streaming infrastructure, SSE handler
- **Day 7:** Frontend integration, React streaming components
- **Day 8:** Vision AI (GPT-4V), quality inspection analysis
- **Day 9:** Document processor (OCR + understanding)
- **Day 10:** Multi-modal API endpoints

### Week 3: AI Agents & Advanced RAG (HIGH)
- **Day 11-12:** LangGraph workflows, trade matching agent
- **Day 13:** Contract analysis agent, fraud detection agent
- **Day 14-15:** Advanced RAG pipeline (hybrid search, reranking)
- **Day 16:** Query rewriting, citation tracking

### Week 4: Observability & ML Models (HIGH)
- **Day 17-18:** AI metrics tracking, cost monitoring
- **Day 19:** Error handling, circuit breakers, retry logic
- **Day 20:** Price prediction model (XGBoost)
- **Day 21:** Demand forecasting model (Prophet)

### Week 5: ML Models & Deployment (MEDIUM)
- **Day 22:** Quality scoring model (Random Forest)
- **Day 23:** Fraud detection model (Autoencoder)
- **Day 24:** Trade matching engine (Neural Network)
- **Day 25:** MLflow setup, model registry, ONNX conversion
- **Day 26:** Model monitoring, drift detection (Evidently)
- **Day 27:** Comprehensive testing suite
- **Day 28:** Documentation, API reference, deployment

**Total: 4-5 weeks for enterprise-grade AI + ML platform**

---

---

## Success Criteria (Revised)

### Core Features ✅
- ✅ **Conversation Persistence:** All chats saved in PostgreSQL + Redis cache
- ✅ **Multi-Language:** Hindi, Tamil, Telugu, Marathi, Gujarati + auto-detection
- ✅ **Streaming:** Real-time token streaming via SSE
- ✅ **Multi-Modal:** Vision AI for quality photos, document OCR
- ✅ **AI Agents:** LangGraph autonomous workflows for trade matching, contract analysis
- ✅ **Advanced RAG:** Hybrid search, reranking, citations, confidence scoring
- ✅ **ML Models:** 5 production models (price, demand, quality, fraud, matching)

### AI Performance 📊
- ✅ AI response time < 2 seconds (p95)
- ✅ Streaming first token < 500ms
- ✅ Translation accuracy > 90% (human eval)
- ✅ RAG answer confidence > 0.75 for 80% of queries
- ✅ Vision AI quality grading accuracy > 85%

### ML Model Performance 🤖
- ✅ **Price Prediction:** MAE < ₹50/quintal, R² > 0.85
- ✅ **Demand Forecasting:** MAPE < 15% (30-day forecast)
- ✅ **Quality Scoring:** F1-score > 0.90 (multi-class)
- ✅ **Fraud Detection:** Precision > 0.85, Recall > 0.80
- ✅ **Trade Matching:** Top-5 accuracy > 0.75 (relevant match in top 5)
- ✅ **Model Inference Time:** < 100ms per prediction (p95)
- ✅ **Drift Detection:** Alert when data drift > 30%

### Reliability 🛡️
- ✅ 99.9% uptime for AI services
- ✅ Circuit breaker prevents cascading failures
- ✅ Graceful degradation when AI unavailable
- ✅ Conversation recovery on connection loss
- ✅ Automatic retry with exponential backoff

### Observability 👁️
- ✅ All AI calls logged with full metadata
- ✅ Real-time cost dashboard per organization
- ✅ Language usage analytics
- ✅ Conversation quality metrics (rating, sentiment)
- ✅ Automated alerts for cost/error thresholds

### Security 🔒
- ✅ API keys in environment variables (no hardcoding)
- ✅ Rate limiting per organization tier
- ✅ PII detection and redaction in logs
- ✅ Audit trail for all AI decisions
- ✅ GDPR compliance (conversation deletion)

### Cost Management 💰
- ✅ Cost per request < $0.05 (average)
- ✅ 40%+ cache hit rate
- ✅ Automatic cost alerts at 80% quota
- ✅ Organization-level budget enforcement

---

## Files to Create (Complete List)

### Phase 1: Conversation & Multi-Language (20 files)
```
backend/ai/conversation/
  __init__.py
  models.py                    # DB models for conversations
  manager.py                   # Conversation lifecycle management
  cache.py                     # Redis caching layer
  multilingual_chat.py         # Multi-language chat handler
  
backend/ai/i18n/
  __init__.py
  translator.py                # Translation engine
  prompts.py                   # Localized prompt templates
  language_detector.py         # Language detection
  
backend/db/migrations/versions/
  add_ai_conversations.py      # Alembic migration
  add_conversation_context.py
  
backend/api/v1/endpoints/
  ai_conversations.py          # Conversation CRUD endpoints
  
backend/tests/ai/
  test_conversation.py
  test_translation.py
  test_language_detection.py
```

### Phase 2: Streaming & Multi-Modal (15 files)
```
backend/ai/streaming/
  __init__.py
  streamer.py                  # Token streaming handler
  sse_handler.py               # Server-Sent Events
  
backend/ai/multimodal/
  __init__.py
  vision.py                    # GPT-4V integration
  document_processor.py        # OCR + understanding
  image_utils.py               # Image preprocessing
  
backend/api/v1/endpoints/
  ai_streaming.py
  ai_multimodal.py
  
backend/tests/ai/
  test_streaming.py
  test_vision_ai.py
  test_document_processor.py
```

### Phase 3: AI Agents & RAG (18 files)
```
backend/ai/agents/
  __init__.py
  base_agent.py                # Shared workflow utilities
  trade_matching_agent.py      # LangGraph trade matcher
  contract_analysis_agent.py   # Contract analyzer
  fraud_detection_agent.py     # Fraud detector
  
backend/ai/rag/
  __init__.py
  advanced_retrieval.py        # Main RAG pipeline
  query_rewriter.py            # Query expansion
  hybrid_search.py             # Semantic + BM25
  reranker.py                  # Cross-encoder reranking
  citation_tracker.py          # Source citations
  
backend/api/v1/endpoints/
  ai_agents.py
  ai_rag.py
  
backend/tests/ai/
  test_trade_matching_agent.py
  test_rag_pipeline.py
  test_hybrid_search.py
```

### Phase 4: Observability (12 files)
```
backend/ai/observability/
  __init__.py
  tracker.py                   # Metrics tracking
  cost_calculator.py           # Cost computation
  models.py                    # SQLAlchemy metrics model
  dashboard.py                 # Analytics queries
  
backend/ai/resilience/
  __init__.py
  retry.py                     # Retry logic
  circuit_breaker.py           # Circuit breaker
  fallback.py                  # Fallback strategies
  
backend/db/migrations/versions/
  add_ai_metrics.py
  
backend/api/v1/endpoints/
  ai_analytics.py
```

### Phase 5: ML Models (25 files)
```
backend/ai/models/price_prediction/
  __init__.py
  model.py                     # XGBoost price predictor
  trainer.py                   # Training pipeline
  features.py                  # Feature engineering
  evaluator.py                 # Model evaluation
  
backend/ai/models/demand_forecasting/
  __init__.py
  model.py                     # Prophet time-series forecaster
  trainer.py                   # Training pipeline
  seasonality.py               # Seasonal patterns
  
backend/ai/models/quality_scoring/
  __init__.py
  model.py                     # Random Forest quality scorer
  trainer.py                   # Training pipeline
  anomaly_detector.py          # Isolation Forest
  
backend/ai/models/fraud_detection/
  __init__.py
  model.py                     # Autoencoder anomaly detector
  trainer.py                   # Neural network training
  feature_extractor.py         # Graph features
  
backend/ai/models/matching_engine/
  __init__.py
  model.py                     # Neural matching model
  embedding_model.py           # Siamese network
  scorer.py                    # Similarity scoring
  
backend/ai/models/shared/
  __init__.py
  base_model.py                # Base ML model class
  model_registry.py            # MLflow registry
  versioning.py                # Model versioning
  deployment.py                # Model serving
```

**Total: ~90 new files + enhancements to 10 existing files**

---

## Migration Path from Current System

### What to Keep ✅
- `backend/ai/orchestrators/base.py` - Excellent abstraction
- `backend/ai/orchestrators/factory.py` - Factory pattern
- `backend/ai/embeddings/chromadb/` - Vector store foundation
- `backend/ai/orchestrators/langchain/` - LangChain integration

### What to Enhance 🔄
- `backend/api/v1/ai.py` → Add streaming, multi-language endpoints
- `backend/ai/orchestrators/langchain/chains.py` → Add conversation persistence
- `backend/ai/embeddings/chromadb/search.py` → Add hybrid search, reranking

### What to Replace ❌
- Current chat endpoints (no persistence)
- Basic semantic search (add RAG pipeline)
- Assistants without conversation memory

### Migration Steps
1. **Phase 1:** Add new tables alongside existing (no breaking changes)
2. **Phase 2:** Deploy new endpoints with `/v2/` prefix
3. **Phase 3:** Migrate existing conversations to new schema
4. **Phase 4:** Deprecate old endpoints after 2 weeks
5. **Phase 5:** Remove old code after migration complete

---

## Risk Mitigation

### Technical Risks 🚨
| Risk | Impact | Mitigation |
|------|--------|------------|
| OpenAI API downtime | HIGH | Circuit breaker, fallback to cached responses |
| High translation costs | MEDIUM | Cache translations, use smaller models for detection |
| Streaming failures | MEDIUM | Fallback to non-streaming mode |
| RAG answer hallucination | HIGH | Confidence scoring, citation verification |
| Agent workflow errors | HIGH | Try/catch at each step, save partial results |

### Business Risks 💼
| Risk | Impact | Mitigation |
|------|--------|------------|
| Runaway AI costs | HIGH | Per-org budgets, auto-shutoff at limits |
| Poor translation quality | MEDIUM | Human validation for critical messages |
| User confusion (new features) | LOW | Gradual rollout, user education |

---

## Next Steps (Action Plan)

### Immediate (This Week)
1. ✅ **Review & approve** this comprehensive plan
2. 🔄 **Create Git branch:** `feature/enterprise-ai-platform`
3. 🔄 **Set up project board:** Track 8 phases, 65 files
4. 🔄 **Start Phase 1:** Conversation persistence + multi-language

### Week 1 Deliverables
- Database schema for conversations
- Conversation manager with Redis caching
- Multi-language translator (Hindi, Tamil, English)
- New API endpoints for conversation CRUD
- Unit tests for conversation persistence

### Weekly Check-ins
- **Monday:** Review progress, unblock issues
- **Wednesday:** Demo working features
- **Friday:** Retrospective, plan next week

### Definition of Done (Each Phase)
## Technology Stack (Updated)

### Core AI & LLM
- **LLM:** OpenAI GPT-4 Turbo, GPT-4V (vision)
- **Embeddings:** text-embedding-3-small
- **Translation:** GPT-4 (high quality)
- **Orchestration:** LangChain 0.1.x
- **Agents:** LangGraph (autonomous workflows)

### Machine Learning (Classical + Deep Learning)
- **Classical ML:** scikit-learn 1.3.2, XGBoost 2.0.3, LightGBM 4.1.0
- **Time Series:** Prophet 1.1.5, statsmodels 0.14.1, pmdarima 2.0.4
- **Deep Learning:** PyTorch 2.1.2, TensorFlow 2.15.0
- **Feature Engineering:** category_encoders 2.6.3, feature-engine 1.6.2
- **Explainability:** SHAP 0.44.0 (feature importance, model interpretability)

### ML Operations (MLOps)
- **Experiment Tracking:** MLflow 2.9.2 (track experiments, log metrics, compare models)
- **Model Registry:** MLflow Registry (version control, staging, production)
- **Hyperparameter Tuning:** Optuna 3.5.0 (automated optimization)
- **Model Serving:** ONNX Runtime 1.16.3 (10x faster inference)
- **Model Format:** ONNX 1.15.0 (cross-platform deployment)

### Model Monitoring & Quality
- **Drift Detection:** Evidently 0.4.15 (data drift, concept drift)
- **Outlier Detection:** Alibi-Detect 0.11.4 (anomaly detection)
- **Performance Monitoring:** Custom metrics (MAE, RMSE, R², Precision, Recall)
- **A/B Testing:** MLflow + custom framework

### Vector & Search
- **Vector DB:** ChromaDB (persistent mode)
- **Keyword Search:** BM25 (rank-bm25)
- **Reranking:** LLM-based cross-encoder
- **Hybrid Search:** Semantic + BM25 with reciprocal rank fusion

### Infrastructure
- **Database:** PostgreSQL (conversations, metrics, ML features)
- **Cache:** Redis (conversation history, translations, model predictions)
- **Streaming:** FastAPI StreamingResponse (SSE)
- **Background Jobs:** Celery (batch embedding, model training, batch predictions)
- **GPU Support:** CUDA 12.1 (for deep learning models)

### Monitoring & Observability
- **AI Metrics:** Custom tables (tokens, cost, latency, errors)
- **ML Metrics:** MLflow tracking (accuracy, loss, drift scores)
- **Logging:** Structured JSON logs
- **Alerts:** Threshold-based (cost, errors, drift, performance degradation)
- **Dashboards:** Real-time AI/ML analytics

### Multi-Modal
- **Vision:** GPT-4 Vision API
- **OCR:** Tesseract 5.x + pytesseract
- **PDF:** pdf2image, PyPDF2
- **Image Processing:** Pillow 10.x, OpenCV 4.x
### Monitoring
- **Metrics:** Custom AI metrics tables
- **Logging:** Structured JSON logs
- **Alerts:** Threshold-based (cost, errors)

### Multi-Modal
- **Vision:** GPT-4 Vision API
- **OCR:** Tesseract + pytesseract
- **PDF:** pdf2image, PyPDF2

---

## Conclusion

This plan transforms the current basic AI system into an **enterprise-grade, multi-lingual, AI-driven platform with production ML models**:

### LLM & Generative AI
1. ✅ **Persistent Conversations** - Never lose context
2. ✅ **Multi-Language Support** - Hindi, regional languages
3. ✅ **Real-Time Streaming** - Better UX
4. ✅ **Multi-Modal AI** - Vision, OCR, documents
5. ✅ **Autonomous Agents** - Complex workflows
6. ✅ **Advanced RAG** - High-quality answers with citations

### Machine Learning Models
7. ✅ **Price Prediction** - XGBoost regression (±₹50/quintal accuracy)
8. ✅ **Demand Forecasting** - Prophet time-series (15% MAPE)
9. ✅ **Quality Scoring** - Random Forest + Isolation Forest (90% F1)
10. ✅ **Fraud Detection** - Autoencoder anomaly detection (85% precision)
11. ✅ **Trade Matching** - Neural network matching engine (75% top-5 accuracy)

### MLOps & Production
12. ✅ **Experiment Tracking** - MLflow for all experiments
13. ✅ **Model Registry** - Versioning, staging, production
14. ✅ **Fast Inference** - ONNX Runtime (10x speedup)
15. ✅ **Drift Detection** - Evidently AI monitoring
16. ✅ **Observability** - Full monitoring, costs, reliability

---

## Complete Tech Stack Summary

```python
# AI & LLM Layer
GENERATIVE_AI = {
    "llm": "OpenAI GPT-4 Turbo",
    "vision": "GPT-4V",
    "embeddings": "text-embedding-3-small",
    "orchestration": "LangChain + LangGraph",
    "rag": "ChromaDB + BM25 + Reranking"
}

# Machine Learning Layer
CLASSICAL_ML = {
    "regression": "XGBoost 2.0.3",
    "time_series": "Prophet 1.1.5",
    "classification": "Random Forest (scikit-learn)",
    "anomaly": "Isolation Forest + Autoencoder"
}

DEEP_LEARNING = {
    "framework": "PyTorch 2.1.2",
    "matching": "Siamese Networks",
    "fraud": "Autoencoder (Neural Network)"
}

# MLOps Layer
MLOPS = {
    "tracking": "MLflow 2.9.2",
    "tuning": "Optuna 3.5.0",
    "serving": "ONNX Runtime 1.16.3",
    "monitoring": "Evidently 0.4.15",
    "explainability": "SHAP 0.44.0"
}

# Infrastructure
INFRASTRUCTURE = {
    "database": "PostgreSQL + Redis",
    "vectors": "ChromaDB",
    "streaming": "FastAPI SSE",
    "jobs": "Celery",
    "gpu": "CUDA 12.1"
}
```

---

## Key Differentiators

| Feature | Current System | New System |
|---------|---------------|------------|
| **Conversations** | Lost on refresh | Persistent in DB |
| **Languages** | English only | 10 Indian languages |
| **Streaming** | ❌ No | ✅ Real-time SSE |
| **Multi-Modal** | ❌ No | ✅ Vision + OCR |
| **AI Agents** | ❌ No | ✅ LangGraph workflows |
| **RAG** | Basic search | Hybrid + Reranking |
| **ML Models** | ❌ Empty placeholders | ✅ 5 production models |
| **Price Prediction** | ❌ No | ✅ XGBoost (R²>0.85) |
| **Demand Forecast** | ❌ No | ✅ Prophet (MAPE<15%) |
| **Quality AI** | ❌ No | ✅ Random Forest (F1>0.90) |
| **Fraud Detection** | ❌ No | ✅ Autoencoder (P>0.85) |
| **Model Versioning** | ❌ No | ✅ MLflow Registry |
| **Drift Detection** | ❌ No | ✅ Evidently AI |
| **Observability** | ❌ No | ✅ Full metrics |

---

## Expected Business Impact

### Cost Efficiency 💰
- **AI Cost Reduction:** 40% savings via caching
- **Automation:** 60% reduction in manual quality checks (AI scoring)
- **Fraud Prevention:** ₹10L+ saved annually (fraud detection)

### Revenue Growth 📈
- **Better Matching:** 25% increase in successful trades (ML matching)
- **Price Optimization:** 5-8% better pricing (ML predictions)
- **Demand Planning:** 30% reduction in stockouts (forecasting)

### User Experience ⚡
- **Response Time:** < 2s (streaming feels instant)
- **Accuracy:** 85%+ for all ML models
- **Multi-Language:** Accessible to 95% of Indian market

### Operational Excellence 🎯
- **Quality Assurance:** Automated with 90% accuracy
- **Risk Management:** Real-time fraud detection
- **Market Intelligence:** Demand forecasting + price predictions

---

**Ready to build a world-class AI + ML platform? Let's start! 🚀**

**Next Step:** Start Phase 1 (Conversation Persistence + Multi-Language) this week!
