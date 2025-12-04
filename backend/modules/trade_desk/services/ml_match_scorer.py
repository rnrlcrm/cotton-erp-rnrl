"""
ML Match Scoring Service - Machine Learning based match prediction

Uses RandomForest classifier to predict match success probability
based on historical match outcomes.

Features:
- Train on real match outcome data
- Predict success probability (0-1)
- Feature importance analysis
- Model versioning and persistence
- Fallback to rule-based scoring
"""

import logging
import pickle
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple
from uuid import UUID
from decimal import Decimal

import numpy as np
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score

from backend.modules.trade_desk.models.match_outcome import MatchOutcome
from backend.modules.trade_desk.models.requirement import Requirement
from backend.modules.trade_desk.models.availability import Availability

logger = logging.getLogger(__name__)


class MLMatchScorer:
    """
    ML-based match scoring using RandomForest classifier.
    
    Predicts probability of match success based on:
    - Quality score
    - Price score
    - Delivery score
    - Risk score
    - Distance
    - Price difference
    """
    
    MODEL_PATH = Path(__file__).parent.parent.parent.parent / "ai" / "models" / "match_predictor.pkl"
    MIN_TRAINING_SAMPLES = 100  # Minimum samples needed to train
    
    def __init__(self, db: AsyncSession):
        self.db = db
        self.model: Optional[RandomForestClassifier] = None
        self.feature_names = [
            "quality_score",
            "price_score", 
            "delivery_score",
            "risk_score",
            "distance_km",
            "price_difference_pct"
        ]
        self.is_trained = False
        self._load_model()
    
    def _load_model(self) -> bool:
        """Load trained model from disk if exists."""
        if self.MODEL_PATH.exists():
            try:
                with open(self.MODEL_PATH, 'rb') as f:
                    self.model = pickle.load(f)
                self.is_trained = True
                logger.info("✅ Loaded ML match predictor model")
                return True
            except Exception as e:
                logger.error(f"Failed to load model: {e}")
                return False
        else:
            logger.warning("⚠️ No trained model found - will use rule-based scoring")
            return False
    
    def _save_model(self) -> bool:
        """Save trained model to disk."""
        try:
            self.MODEL_PATH.parent.mkdir(parents=True, exist_ok=True)
            with open(self.MODEL_PATH, 'wb') as f:
                pickle.dump(self.model, f)
            logger.info(f"✅ Saved ML model to {self.MODEL_PATH}")
            return True
        except Exception as e:
            logger.error(f"Failed to save model: {e}")
            return False
    
    async def train_model(self, test_size: float = 0.2, random_state: int = 42) -> Dict[str, Any]:
        """
        Train RandomForest model on match outcomes.
        
        Args:
            test_size: Fraction of data for testing
            random_state: Random seed for reproducibility
            
        Returns:
            Dict with training metrics
        """
        # Fetch all match outcomes
        result = await self.db.execute(
            select(MatchOutcome).order_by(MatchOutcome.matched_at)
        )
        outcomes = result.scalars().all()
        
        if len(outcomes) < self.MIN_TRAINING_SAMPLES:
            return {
                "success": False,
                "error": f"Need at least {self.MIN_TRAINING_SAMPLES} samples, got {len(outcomes)}",
                "samples": len(outcomes)
            }
        
        # Prepare features and labels
        X = []
        y = []
        
        for outcome in outcomes:
            features = [
                float(outcome.quality_score),
                float(outcome.price_score),
                float(outcome.delivery_score),
                float(outcome.risk_score),
                float(outcome.distance_km) if outcome.distance_km else 0.0,
                float(outcome.price_difference_pct) if outcome.price_difference_pct else 0.0
            ]
            X.append(features)
            y.append(1 if outcome.trade_completed else 0)
        
        X = np.array(X)
        y = np.array(y)
        
        # Split data
        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=test_size, random_state=random_state, stratify=y
        )
        
        # Train RandomForest
        self.model = RandomForestClassifier(
            n_estimators=100,
            max_depth=10,
            min_samples_split=5,
            min_samples_leaf=2,
            random_state=random_state,
            class_weight='balanced'  # Handle imbalanced data
        )
        
        self.model.fit(X_train, y_train)
        self.is_trained = True
        
        # Evaluate
        y_pred = self.model.predict(X_test)
        y_pred_proba = self.model.predict_proba(X_test)[:, 1]
        
        metrics = {
            "success": True,
            "total_samples": len(outcomes),
            "train_samples": len(X_train),
            "test_samples": len(X_test),
            "accuracy": float(accuracy_score(y_test, y_pred)),
            "precision": float(precision_score(y_test, y_pred, zero_division=0)),
            "recall": float(recall_score(y_test, y_pred, zero_division=0)),
            "f1_score": float(f1_score(y_test, y_pred, zero_division=0)),
            "feature_importance": {
                name: float(importance) 
                for name, importance in zip(self.feature_names, self.model.feature_importances_)
            },
            "positive_rate": float(np.mean(y)),
            "model_path": str(self.MODEL_PATH)
        }
        
        # Save model
        self._save_model()
        
        logger.info(f"✅ Model trained - Accuracy: {metrics['accuracy']:.1%}, F1: {metrics['f1_score']:.1%}")
        return metrics
    
    async def predict_match_success(
        self,
        quality_score: float,
        price_score: float,
        delivery_score: float,
        risk_score: float,
        distance_km: float = 0.0,
        price_difference_pct: float = 0.0
    ) -> Dict[str, Any]:
        """
        Predict match success probability using ML model.
        
        Args:
            quality_score: Quality compatibility (0-1)
            price_score: Price competitiveness (0-1)
            delivery_score: Delivery logistics (0-1)
            risk_score: Risk assessment (0-1)
            distance_km: Distance in km
            price_difference_pct: Price difference percentage
            
        Returns:
            Dict with prediction results
        """
        if not self.is_trained:
            # Fallback to rule-based scoring
            rule_based_score = (
                quality_score * 0.4 +
                price_score * 0.3 +
                delivery_score * 0.15 +
                risk_score * 0.15
            )
            return {
                "success_probability": rule_based_score,
                "method": "rule_based",
                "model_available": False
            }
        
        # Prepare features
        features = np.array([[
            quality_score,
            price_score,
            delivery_score,
            risk_score,
            distance_km,
            price_difference_pct
        ]])
        
        # Predict
        probability = self.model.predict_proba(features)[0][1]  # Probability of success (class 1)
        prediction = self.model.predict(features)[0]
        
        return {
            "success_probability": float(probability),
            "predicted_success": bool(prediction),
            "method": "ml_random_forest",
            "model_available": True,
            "confidence": float(max(self.model.predict_proba(features)[0]))
        }
    
    async def predict_requirement_availability_match(
        self,
        requirement: Requirement,
        availability: Availability,
        quality_score: float,
        price_score: float,
        delivery_score: float,
        risk_score: float
    ) -> Dict[str, Any]:
        """
        Predict match success for a specific requirement-availability pair.
        
        Convenience method that calculates distance and price diff.
        """
        # Calculate distance (placeholder - would use actual lat/lon)
        distance_km = 0.0  # TODO: Calculate from locations
        
        # Calculate price difference
        if requirement.max_budget_per_unit and availability.base_price:
            price_diff_pct = (
                (float(availability.base_price) - float(requirement.max_budget_per_unit)) 
                / float(requirement.max_budget_per_unit) * 100
            )
        else:
            price_diff_pct = 0.0
        
        return await self.predict_match_success(
            quality_score=quality_score,
            price_score=price_score,
            delivery_score=delivery_score,
            risk_score=risk_score,
            distance_km=distance_km,
            price_difference_pct=price_diff_pct
        )
    
    async def get_model_info(self) -> Dict[str, Any]:
        """Get information about the current model."""
        if not self.is_trained:
            return {
                "trained": False,
                "model_path": str(self.MODEL_PATH),
                "model_exists": self.MODEL_PATH.exists()
            }
        
        return {
            "trained": True,
            "model_type": "RandomForestClassifier",
            "n_estimators": self.model.n_estimators,
            "max_depth": self.model.max_depth,
            "feature_names": self.feature_names,
            "feature_importances": {
                name: float(importance)
                for name, importance in zip(self.feature_names, self.model.feature_importances_)
            },
            "model_path": str(self.MODEL_PATH)
        }
