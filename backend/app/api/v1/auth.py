"""Registro, login e perfil de usuários."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.config import settings
from app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_password,
    verify_password,
)
from app.db.base import utcnow
from app.db.session import get_db
from app.models.enums import UserRole
from app.models.user import AuditLog, User
from app.schemas.auth import RefreshRequest, Token, UserCreate, UserLogin, UserOut

router = APIRouter(prefix="/auth", tags=["Autenticação"])


def _issue_tokens(user: User) -> Token:
    return Token(
        access_token=create_access_token(str(user.id), role=user.role.value),
        refresh_token=create_refresh_token(str(user.id)),
        expires_in=settings.access_token_expire_minutes * 60,
    )


@router.post("/registrar", response_model=UserOut, status_code=status.HTTP_201_CREATED)
def register(payload: UserCreate, db: Session = Depends(get_db)) -> User:
    if db.scalar(select(User).where(User.email == payload.email.lower())) is not None:
        raise HTTPException(status_code=409, detail="Já existe uma conta com este e-mail.")
    user = User(
        email=payload.email.lower(),
        full_name=payload.full_name,
        password_hash=hash_password(payload.password),
        role=UserRole.CITIZEN,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@router.post("/login", response_model=Token)
def login(payload: UserLogin, request: Request, db: Session = Depends(get_db)) -> Token:
    user = db.scalar(select(User).where(User.email == payload.email.lower()))
    if user is None or not verify_password(payload.password, user.password_hash):
        raise HTTPException(status_code=401, detail="E-mail ou senha inválidos.")
    if not user.is_active:
        raise HTTPException(status_code=403, detail="Conta desativada.")
    user.last_login_at = utcnow()
    db.add(
        AuditLog(
            actor_user_id=user.id,
            action="login",
            ip_address=request.client.host if request.client else None,
            user_agent=request.headers.get("user-agent"),
        )
    )
    db.commit()
    return _issue_tokens(user)


@router.post("/renovar", response_model=Token)
def refresh(payload: RefreshRequest, db: Session = Depends(get_db)) -> Token:
    data = decode_token(payload.refresh_token)
    if data.get("type") != "refresh":
        raise HTTPException(status_code=401, detail="Token de renovação inválido.")
    user = db.get(User, int(data["sub"]))
    if user is None or not user.is_active:
        raise HTTPException(status_code=401, detail="Usuário inválido.")
    return _issue_tokens(user)


@router.get("/eu", response_model=UserOut)
def me(user: User = Depends(get_current_user)) -> User:
    return user
