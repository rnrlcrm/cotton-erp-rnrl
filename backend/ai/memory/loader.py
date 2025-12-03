"""
AI Memory Loader

Loads conversation history, user context, and preferences for AI interactions.
"""

from __future__ import annotations

import logging
from typing import List, Dict, Any, Optional
from uuid import UUID
from datetime import datetime, timedelta

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc
from redis.asyncio import Redis

logger = logging.getLogger(__name__)


class AIMemoryLoader:
    """
    Load AI memory and context for personalized interactions.
    
    Features:
    - Conversation history (last N messages)
    - User preferences and patterns
    - Recent trades and interactions
    - Cached summaries for performance
    
    Usage:
        loader = AIMemoryLoader(db, redis)
        context = await loader.load_context(user_id)
        
        # Use context in AI prompt
        prompt = f"User context: {context['summary']}\\n\\nUser: {message}"
    """
    
    def __init__(self, db: AsyncSession, redis: Optional[Redis] = None):
        self.db = db
        self.redis = redis
        self._cache_ttl = 300  # 5 minutes
    
    async def load_conversation_history(
        self,
        user_id: UUID,
        conversation_id: Optional[UUID] = None,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Load recent conversation messages.
        
        Args:
            user_id: User UUID
            conversation_id: Specific conversation (or latest if None)
            limit: Number of messages to load
            
        Returns:
            List of messages with role and content
        """
        try:
            # TODO: Implement when conversation tables are created in Phase 1
            # For now, return empty list
            logger.debug(f"Loading conversation history for user {user_id}")
            return []
        
        except Exception as e:
            logger.error(f"Failed to load conversation history: {e}")
            return []
    
    async def load_user_preferences(self, user_id: UUID) -> Dict[str, Any]:
        """
        Load user preferences and patterns.
        
        Args:
            user_id: User UUID
            
        Returns:
            Dictionary of user preferences
        """
        try:
            # Check cache first
            if self.redis:
                cache_key = f"ai:user_prefs:{user_id}"
                cached = await self.redis.get(cache_key)
                if cached:
                    import json
                    return json.loads(cached)
            
            # Load from database
            from backend.modules.user_onboarding.models import User
            
            result = await self.db.execute(
                select(User).where(User.id == user_id)
            )
            user = result.scalar_one_or_none()
            
            if not user:
                return {}
            
            preferences = {
                "user_id": str(user.id),
                "name": user.name,
                "email": user.email,
                "mobile": user.mobile_number,
                "language": user.preferred_language or "en",
                "partner_type": user.partner_type.value if user.partner_type else None,
                "created_at": user.created_at.isoformat() if user.created_at else None,
            }
            
            # Cache for 5 minutes
            if self.redis:
                import json
                await self.redis.setex(
                    cache_key,
                    self._cache_ttl,
                    json.dumps(preferences)
                )
            
            return preferences
        
        except Exception as e:
            logger.error(f"Failed to load user preferences: {e}")
            return {}
    
    async def load_recent_trades(
        self,
        user_id: UUID,
        limit: int = 5
    ) -> List[Dict[str, Any]]:
        """
        Load user's recent trade activity.
        
        Args:
            user_id: User UUID
            limit: Number of trades to load
            
        Returns:
            List of recent trades/requirements/availabilities
        """
        try:
            from backend.modules.trade_desk.models.requirement import Requirement
            from backend.modules.trade_desk.models.availability import Availability
            
            recent_activity = []
            
            # Load recent requirements
            req_result = await self.db.execute(
                select(Requirement)
                .where(Requirement.created_by_id == user_id)
                .order_by(desc(Requirement.created_at))
                .limit(limit)
            )
            requirements = req_result.scalars().all()
            
            for req in requirements:
                recent_activity.append({
                    "type": "requirement",
                    "id": str(req.id),
                    "commodity": req.commodity.name if req.commodity else None,
                    "variety": req.variety.name if req.variety else None,
                    "quantity": req.quantity,
                    "status": req.status.value if req.status else None,
                    "created_at": req.created_at.isoformat() if req.created_at else None,
                })
            
            # Load recent availabilities
            avail_result = await self.db.execute(
                select(Availability)
                .where(Availability.created_by_id == user_id)
                .order_by(desc(Availability.created_at))
                .limit(limit)
            )
            availabilities = avail_result.scalars().all()
            
            for avail in availabilities:
                recent_activity.append({
                    "type": "availability",
                    "id": str(avail.id),
                    "commodity": avail.commodity.name if avail.commodity else None,
                    "variety": avail.variety.name if avail.variety else None,
                    "quantity": avail.quantity,
                    "status": avail.status.value if avail.status else None,
                    "created_at": avail.created_at.isoformat() if avail.created_at else None,
                })
            
            # Sort by date
            recent_activity.sort(
                key=lambda x: x.get("created_at", ""),
                reverse=True
            )
            
            return recent_activity[:limit]
        
        except Exception as e:
            logger.error(f"Failed to load recent trades: {e}")
            return []
    
    async def load_context(
        self,
        user_id: UUID,
        conversation_id: Optional[UUID] = None,
        include_history: bool = True,
        include_trades: bool = True
    ) -> Dict[str, Any]:
        """
        Load complete AI context for user.
        
        Args:
            user_id: User UUID
            conversation_id: Specific conversation
            include_history: Include conversation history
            include_trades: Include recent trade activity
            
        Returns:
            Complete context dictionary
        """
        context = {
            "user_id": str(user_id),
            "loaded_at": datetime.utcnow().isoformat(),
        }
        
        # Load preferences
        context["preferences"] = await self.load_user_preferences(user_id)
        
        # Load conversation history
        if include_history:
            context["conversation_history"] = await self.load_conversation_history(
                user_id,
                conversation_id
            )
        
        # Load recent trades
        if include_trades:
            context["recent_trades"] = await self.load_recent_trades(user_id)
        
        # Generate summary
        context["summary"] = self._generate_summary(context)
        
        return context
    
    def _generate_summary(self, context: Dict[str, Any]) -> str:
        """
        Generate human-readable summary of context.
        
        Args:
            context: Full context dictionary
            
        Returns:
            Summary string for AI prompt
        """
        summary_parts = []
        
        # User info
        prefs = context.get("preferences", {})
        if prefs.get("name"):
            summary_parts.append(f"User: {prefs['name']}")
        if prefs.get("partner_type"):
            summary_parts.append(f"Role: {prefs['partner_type']}")
        if prefs.get("language"):
            summary_parts.append(f"Language: {prefs['language']}")
        
        # Recent activity
        trades = context.get("recent_trades", [])
        if trades:
            summary_parts.append(f"Recent activity: {len(trades)} trades")
            
            # Summarize commodities
            commodities = set()
            for trade in trades:
                if trade.get("commodity"):
                    commodities.add(trade["commodity"])
            
            if commodities:
                summary_parts.append(f"Interested in: {', '.join(commodities)}")
        
        return " | ".join(summary_parts)
    
    async def get_cached_context(self, user_id: UUID) -> Optional[Dict[str, Any]]:
        """
        Get cached context (faster than full load).
        
        Args:
            user_id: User UUID
            
        Returns:
            Cached context or None
        """
        if not self.redis:
            return None
        
        try:
            cache_key = f"ai:context:{user_id}"
            cached = await self.redis.get(cache_key)
            
            if cached:
                import json
                return json.loads(cached)
            
            return None
        
        except Exception as e:
            logger.error(f"Failed to get cached context: {e}")
            return None
    
    async def cache_context(self, user_id: UUID, context: Dict[str, Any]) -> None:
        """
        Cache context for faster loading.
        
        Args:
            user_id: User UUID
            context: Context to cache
        """
        if not self.redis:
            return
        
        try:
            import json
            cache_key = f"ai:context:{user_id}"
            await self.redis.setex(
                cache_key,
                self._cache_ttl,
                json.dumps(context)
            )
        
        except Exception as e:
            logger.error(f"Failed to cache context: {e}")


# Singleton
_memory_loader: Optional[AIMemoryLoader] = None


def get_memory_loader(db: AsyncSession, redis: Optional[Redis] = None) -> AIMemoryLoader:
    """
    Get memory loader instance.
    
    Args:
        db: Database session
        redis: Redis client (optional)
        
    Returns:
        AIMemoryLoader instance
    """
    global _memory_loader
    if _memory_loader is None:
        _memory_loader = AIMemoryLoader(db, redis)
    return _memory_loader
