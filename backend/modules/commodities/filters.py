"""
Advanced Filtering for Commodities

Provides complex filtering, search, and caching capabilities.
"""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional
from uuid import UUID

from sqlalchemy import and_, or_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from backend.modules.commodities.models import Commodity


class CommodityFilter:
    """Advanced filtering for commodities"""
    
    def __init__(self, db: AsyncSession):
        self.db = db
        self._cache: Dict[str, tuple[Any, datetime]] = {}
        self._cache_ttl = timedelta(minutes=5)
    
    async def search_commodities(
        self,
        query: str,
        category: Optional[str] = None,
        is_active: Optional[bool] = None,
        min_gst_rate: Optional[float] = None,
        max_gst_rate: Optional[float] = None,
        hsn_codes: Optional[List[str]] = None,
        skip: int = 0,
        limit: int = 100,
        use_cache: bool = True,
    ) -> tuple[List[Commodity], int]:
        """
        Advanced search with multiple filters.
        
        Args:
            query: Search text (searches name, description)
            category: Filter by category
            is_active: Filter by active status
            min_gst_rate: Minimum GST rate
            max_gst_rate: Maximum GST rate
            hsn_codes: List of HSN codes to filter
            skip: Pagination offset
            limit: Results per page
            use_cache: Enable caching
        
        Returns:
            (results, total_count)
        """
        # Generate cache key
        cache_key = self._generate_cache_key({
            "query": query,
            "category": category,
            "is_active": is_active,
            "min_gst": min_gst_rate,
            "max_gst": max_gst_rate,
            "hsn": hsn_codes,
            "skip": skip,
            "limit": limit,
        })
        
        # Check cache
        if use_cache and cache_key in self._cache:
            cached_data, cached_time = self._cache[cache_key]
            if datetime.utcnow() - cached_time < self._cache_ttl:
                return cached_data
        
        # Build query
        conditions = []
        
        # Text search
        if query:
            search_filter = or_(
                Commodity.name.ilike(f"%{query}%"),
                Commodity.description.ilike(f"%{query}%"),
            )
            conditions.append(search_filter)
        
        # Category filter
        if category:
            conditions.append(Commodity.category == category)
        
        # Active status filter
        if is_active is not None:
            conditions.append(Commodity.is_active == is_active)
        
        # GST rate range
        if min_gst_rate is not None:
            conditions.append(Commodity.gst_rate >= min_gst_rate)
        if max_gst_rate is not None:
            conditions.append(Commodity.gst_rate <= max_gst_rate)
        
        # HSN codes filter
        if hsn_codes:
            conditions.append(Commodity.hsn_code.in_(hsn_codes))
        
        # Combine all conditions
        where_clause = and_(*conditions) if conditions else True
        
        # Count total
        count_query = select(Commodity).where(where_clause)
        count_result = await self.db.execute(count_query)
        total_count = len(count_result.scalars().all())
        
        # Get paginated results
        query_stmt = (
            select(Commodity)
            .where(where_clause)
            .offset(skip)
            .limit(limit)
            .order_by(Commodity.name)
        )
        
        result = await self.db.execute(query_stmt)
        commodities = result.scalars().all()
        
        # Cache results
        if use_cache:
            self._cache[cache_key] = ((list(commodities), total_count), datetime.utcnow())
        
        return list(commodities), total_count
    
    async def get_categories(self, use_cache: bool = True) -> List[str]:
        """Get all unique categories"""
        cache_key = "categories"
        
        if use_cache and cache_key in self._cache:
            cached_data, cached_time = self._cache[cache_key]
            if datetime.utcnow() - cached_time < self._cache_ttl:
                return cached_data
        
        query = select(Commodity.category).distinct()
        result = await self.db.execute(query)
        categories = [row[0] for row in result if row[0]]
        
        if use_cache:
            self._cache[cache_key] = (categories, datetime.utcnow())
        
        return categories
    
    async def get_hsn_codes(self, use_cache: bool = True) -> List[str]:
        """Get all unique HSN codes"""
        cache_key = "hsn_codes"
        
        if use_cache and cache_key in self._cache:
            cached_data, cached_time = self._cache[cache_key]
            if datetime.utcnow() - cached_time < self._cache_ttl:
                return cached_data
        
        query = select(Commodity.hsn_code).distinct()
        result = await self.db.execute(query)
        hsn_codes = [row[0] for row in result if row[0]]
        
        if use_cache:
            self._cache[cache_key] = (hsn_codes, datetime.utcnow())
        
        return hsn_codes
    
    async def get_facets(self) -> Dict[str, Any]:
        """
        Get faceted search data.
        
        Returns counts and options for filtering.
        """
        categories = await self.get_categories()
        hsn_codes = await self.get_hsn_codes()
        
        # Get active/inactive counts
        active_query = select(Commodity).where(Commodity.is_active == True)
        active_result = await self.db.execute(active_query)
        active_count = len(active_result.scalars().all())
        
        inactive_query = select(Commodity).where(Commodity.is_active == False)
        inactive_result = await self.db.execute(inactive_query)
        inactive_count = len(inactive_result.scalars().all())
        
        return {
            "categories": {
                "options": categories,
                "count": len(categories),
            },
            "hsn_codes": {
                "options": hsn_codes,
                "count": len(hsn_codes),
            },
            "status": {
                "active": active_count,
                "inactive": inactive_count,
            },
        }
    
    def clear_cache(self):
        """Clear all cached data"""
        self._cache.clear()
    
    def _generate_cache_key(self, params: Dict[str, Any]) -> str:
        """Generate cache key from parameters"""
        # Sort and serialize parameters
        sorted_params = json.dumps(params, sort_keys=True, default=str)
        return hashlib.md5(sorted_params.encode()).hexdigest()


class SimpleCache:
    """Simple in-memory cache with TTL"""
    
    def __init__(self, ttl_seconds: int = 300):
        self._cache: Dict[str, tuple[Any, datetime]] = {}
        self._ttl = timedelta(seconds=ttl_seconds)
    
    def get(self, key: str) -> Optional[Any]:
        """Get value from cache"""
        if key in self._cache:
            value, cached_time = self._cache[key]
            if datetime.utcnow() - cached_time < self._ttl:
                return value
            else:
                # Expired, remove
                del self._cache[key]
        return None
    
    def set(self, key: str, value: Any):
        """Set value in cache"""
        self._cache[key] = (value, datetime.utcnow())
    
    def delete(self, key: str):
        """Delete value from cache"""
        if key in self._cache:
            del self._cache[key]
    
    def clear(self):
        """Clear all cache"""
        self._cache.clear()
    
    def cleanup_expired(self):
        """Remove expired entries"""
        now = datetime.utcnow()
        expired_keys = [
            key for key, (_, cached_time) in self._cache.items()
            if now - cached_time >= self._ttl
        ]
        for key in expired_keys:
            del self._cache[key]


# Global cache instance
commodity_cache = SimpleCache(ttl_seconds=300)  # 5 minutes
