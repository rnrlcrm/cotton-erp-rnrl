"""
Base Repository with Automatic Data Isolation

All module repositories should extend this to get automatic business partner filtering.
Uses security context to apply isolation rules based on user type.

Pattern:
- SUPER_ADMIN: See all data (no filter)
- INTERNAL: See all business partners (no filter)
- EXTERNAL: See only their business_partner_id data (auto-filtered)

Compliance:
- GDPR Article 32: Security of Processing
- IT Act 2000 Section 43A: Data Protection
- Income Tax Act 1961: 7-year retention (soft delete)

Author: Commodity ERP Security Team
Date: November 22, 2025
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Generic, List, Optional, TypeVar
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.core.security.context import (
    SecurityError,
    get_current_business_partner_id,
    get_current_user_id,
    get_current_user_type,
    is_external_user,
    is_internal_user,
    is_super_admin,
)

# Generic type for model
ModelType = TypeVar("ModelType")


class BaseRepository(Generic[ModelType]):
    """
    Base repository with automatic business partner isolation.
    
    All module repositories should extend this class to get:
    - Automatic data filtering by business_partner_id
    - Soft delete support (GDPR compliance)
    - CRUD operations with isolation built-in
    - Type safety via Generic[ModelType]
    
    Usage:
        class ContractRepository(BaseRepository[Contract]):
            def __init__(self, db: Session):
                super().__init__(db, Contract)
            
            # Custom methods here...
        
        # In service:
        repo = ContractRepository(db)
        contracts = repo.get_all()  # Automatically filtered!
    """
    
    def __init__(self, db: Session, model: type[ModelType]):
        """
        Initialize repository.
        
        Args:
            db: SQLAlchemy session
            model: SQLAlchemy model class
        """
        self.db = db
        self.model = model
    
    # === Private Helper Methods ===
    
    def _has_business_partner_column(self) -> bool:
        """
        Check if model has business_partner_id column for isolation.
        
        Returns:
            bool: True if model has business_partner_id attribute
        """
        return hasattr(self.model, 'business_partner_id')
    
    def _apply_isolation_filter(self, query):
        """
        Apply business partner isolation filter to query.
        
        Isolation Rules:
        - SUPER_ADMIN: No filter (see all)
        - INTERNAL: No filter (see all business partners)
        - EXTERNAL: Filter by business_partner_id
        
        Args:
            query: SQLAlchemy select query
        
        Returns:
            Query with isolation filter applied
        
        Raises:
            SecurityError: If EXTERNAL user context missing
        """
        # Super admin and internal users - no filter
        if is_super_admin() or is_internal_user():
            return query
        
        # External users - apply business partner filter
        if is_external_user():
            if not self._has_business_partner_column():
                # Table doesn't have BP isolation (e.g., settings tables)
                # This is OK - settings are shared
                return query
            
            bp_id = get_current_business_partner_id()
            if not bp_id:
                raise SecurityError(
                    "Business partner context missing for external user. "
                    "This is a security violation - user must have business_partner_id."
                )
            
            # Apply filter
            return query.where(self.model.business_partner_id == bp_id)
        
        # Unknown user type - deny access
        user_type = get_current_user_type()
        raise SecurityError(f"Unknown user type: {user_type}")
    
    def _apply_soft_delete_filter(self, query):
        """
        Filter out soft-deleted records (GDPR 7-year retention).
        
        Args:
            query: SQLAlchemy select query
        
        Returns:
            Query with soft delete filter applied
        """
        if hasattr(self.model, 'is_deleted'):
            return query.where(self.model.is_deleted == False)  # noqa: E712
        return query
    
    def _base_query(self):
        """
        Base query with all standard filters applied.
        
        Returns:
            SQLAlchemy select query with isolation and soft delete filters
        """
        query = select(self.model)
        query = self._apply_isolation_filter(query)
        query = self._apply_soft_delete_filter(query)
        return query
    
    # === CRUD Operations ===
    
    def get_by_id(self, id: UUID) -> Optional[ModelType]:
        """
        Get single record by ID (with automatic isolation).
        
        Args:
            id: Record UUID
        
        Returns:
            Model instance if found and user has access, None otherwise
        """
        stmt = self._base_query().where(self.model.id == id)
        return self.db.execute(stmt).scalar_one_or_none()
    
    def get_all(
        self,
        skip: int = 0,
        limit: int = 100,
        filters: Optional[dict[str, Any]] = None,
        order_by: Optional[Any] = None,
    ) -> List[ModelType]:
        """
        Get all records (with automatic isolation and pagination).
        
        Args:
            skip: Number of records to skip (for pagination)
            limit: Maximum number of records to return
            filters: Additional filters as dict {column_name: value}
            order_by: SQLAlchemy order_by expression
        
        Returns:
            List of model instances
        """
        stmt = self._base_query()
        
        # Apply additional filters
        if filters:
            for key, value in filters.items():
                if hasattr(self.model, key) and value is not None:
                    stmt = stmt.where(getattr(self.model, key) == value)
        
        # Apply ordering
        if order_by is not None:
            stmt = stmt.order_by(order_by)
        elif hasattr(self.model, 'created_at'):
            # Default: newest first
            stmt = stmt.order_by(self.model.created_at.desc())
        
        # Apply pagination
        stmt = stmt.offset(skip).limit(limit)
        
        return list(self.db.execute(stmt).scalars().all())
    
    def count(self, filters: Optional[dict[str, Any]] = None) -> int:
        """
        Count records (with automatic isolation).
        
        Args:
            filters: Additional filters as dict {column_name: value}
        
        Returns:
            Number of records
        """
        stmt = self._base_query()
        
        # Apply additional filters
        if filters:
            for key, value in filters.items():
                if hasattr(self.model, key) and value is not None:
                    stmt = stmt.where(getattr(self.model, key) == value)
        
        # Count using subquery
        from sqlalchemy import func
        stmt = select(func.count()).select_from(stmt.subquery())
        return self.db.execute(stmt).scalar() or 0
    
    def create(self, data: dict[str, Any]) -> ModelType:
        """
        Create new record with automatic business_partner_id injection.
        
        For EXTERNAL users, business_partner_id is automatically injected
        from context to prevent data spoofing.
        
        Args:
            data: Data dictionary for model creation
        
        Returns:
            Created model instance
        
        Raises:
            SecurityError: If EXTERNAL user context missing
        """
        # Auto-inject business_partner_id for external users
        if self._has_business_partner_column() and is_external_user():
            bp_id = get_current_business_partner_id()
            if not bp_id:
                raise SecurityError(
                    "Business partner context missing - cannot create record"
                )
            
            # Force business_partner_id from context (prevent spoofing)
            data['business_partner_id'] = bp_id
        
        # Create object
        obj = self.model(**data)
        self.db.add(obj)
        self.db.flush()
        self.db.refresh(obj)
        
        return obj
    
    def update(self, id: UUID, data: dict[str, Any]) -> Optional[ModelType]:
        """
        Update record (with automatic isolation check).
        
        Args:
            id: Record UUID
            data: Data dictionary with fields to update
        
        Returns:
            Updated model instance if found and user has access, None otherwise
        """
        obj = self.get_by_id(id)
        if not obj:
            return None
        
        # Prevent business_partner_id modification (security)
        data.pop('business_partner_id', None)
        
        # Update fields
        for key, value in data.items():
            if hasattr(obj, key):
                setattr(obj, key, value)
        
        # Update timestamp if exists
        if hasattr(obj, 'updated_at'):
            obj.updated_at = datetime.now(timezone.utc)
        
        self.db.flush()
        self.db.refresh(obj)
        
        return obj
    
    def delete(self, id: UUID, hard_delete: bool = False) -> bool:
        """
        Delete record (soft delete by default for compliance).
        
        Soft Delete (default):
        - Sets is_deleted = True
        - Keeps record for 7-year retention (Income Tax Act)
        - Supports GDPR right to erasure with retention
        
        Hard Delete:
        - Permanently removes record
        - Use only after retention period or for GDPR erasure
        
        Args:
            id: Record UUID
            hard_delete: If True, permanently delete; if False, soft delete
        
        Returns:
            bool: True if deleted, False if not found or no access
        """
        obj = self.get_by_id(id)
        if not obj:
            return False
        
        if hard_delete or not hasattr(obj, 'is_deleted'):
            # Hard delete (permanent)
            self.db.delete(obj)
        else:
            # Soft delete (GDPR-compliant retention)
            obj.is_deleted = True
            obj.deleted_at = datetime.now(timezone.utc)
            
            # Track who deleted it
            if hasattr(obj, 'deleted_by'):
                try:
                    obj.deleted_by = get_current_user_id()
                except SecurityError:
                    pass  # Context not available (e.g., background job)
        
        self.db.flush()
        return True
    
    def restore(self, id: UUID) -> bool:
        """
        Restore soft-deleted record.
        
        Args:
            id: Record UUID
        
        Returns:
            bool: True if restored, False if not found or not deleted
        """
        # Temporarily disable soft delete filter to find deleted records
        stmt = select(self.model).where(self.model.id == id)
        stmt = self._apply_isolation_filter(stmt)
        
        obj = self.db.execute(stmt).scalar_one_or_none()
        if not obj or not hasattr(obj, 'is_deleted'):
            return False
        
        if not obj.is_deleted:
            return False  # Not deleted
        
        # Restore
        obj.is_deleted = False
        obj.deleted_at = None
        
        self.db.flush()
        return True
    
    def exists(self, id: UUID) -> bool:
        """
        Check if record exists (with automatic isolation).
        
        Args:
            id: Record UUID
        
        Returns:
            bool: True if exists and user has access, False otherwise
        """
        stmt = self._base_query().where(self.model.id == id)
        result = self.db.execute(stmt).first()
        return result is not None
