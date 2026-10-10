"""Dependências compartilhadas da API (auth, paginação, rate limit)."""

from __future__ import annotations

from collections.abc import Callable

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.rate_limit import check_rate_limit
from app.core.security import decode_token
from app.db.session import get_db
from app.models.enums import UserRole
from app.models.user import User

bearer_scheme = HTTPBearer(auto_error=False)


def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    db: Session = Depends(get_db),
) -> User:
    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Autenticação necessária.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    payload = decode_token(credentials.credentials)
    if payload.get("type") != "access":
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token inválido.")
    user = db.get(User, int(payload["sub"]))
    if user is None or not user.is_active:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Usuário inativo.")
    return user


def get_optional_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    db: Session = Depends(get_db),
) -> User | None:
    if credentials is None:
        return None
    try:
        payload = decode_token(credentials.credentials)
        if payload.get("type") != "access":
            return None
        return db.get(User, int(payload["sub"]))
    except HTTPException:
        return None


def require_admin(user: User = Depends(get_current_user)) -> User:
    if user.role != UserRole.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Acesso restrito a administradores."
        )
    return user


def rate_limit(limit: int | None = None, scope: str = "default") -> Callable:
    """Dependência de limite de taxa por IP + escopo."""

    def dependency(request: Request) -> None:
        client_ip = request.client.host if request.client else "unknown"
        cap = limit or settings.rate_limit_per_minute
        allowed, _ = check_rate_limit(f"{scope}:{client_ip}", cap)
        if not allowed:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Muitas requisições. Aguarde um instante e tente novamente.",
            )

    return dependency


class Pagination:
    def __init__(self, page: int = 1, page_size: int = 20) -> None:
        self.page = max(1, page)
        self.page_size = min(max(1, page_size), 100)

    @property
    def offset(self) -> int:
        return (self.page - 1) * self.page_size
