from __future__ import annotations

from typing import Callable, Iterable

from fastapi import Depends, Header, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from backend.db.async_session import get_db
from backend.modules.settings.repositories.settings_repositories import UserRepository
from backend.modules.settings.services.settings_services import RBACService
from backend.core.auth.capabilities.definitions import Capabilities


async def get_current_user(
    db: AsyncSession = Depends(get_db), x_user_id: str | None = Header(default=None, alias="X-User-Id")
):
    # Temporary bootstrap: if header missing, take first user if exists.
    repo = UserRepository(db)
    user = None
    if x_user_id:
        user = await repo.get_by_id(x_user_id)
    if user is None:
        user = await repo.get_first()
    if user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Unauthenticated")
    return user


def require_permissions(*required: Capabilities) -> Callable:
    async def _dep(
        user=Depends(get_current_user), db: AsyncSession = Depends(get_db)
    ):  # noqa: ANN001 - FastAPI dynamic typing
        rbac = RBACService(db)
        codes = [p.value for p in required]
        if not await rbac.user_has_permissions(user.id, codes):  # type: ignore[attr-defined]
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")
    return _dep
