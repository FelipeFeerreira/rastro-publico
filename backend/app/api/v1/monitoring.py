"""Monitoramento de entidades e notificações (autenticado)."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Response, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.enums import SubscriptionKind
from app.models.investigation import MonitoringSubscription, Notification
from app.models.user import User

router = APIRouter(prefix="/monitoramento", tags=["Monitoramento e alertas"])


class SubscriptionCreate(BaseModel):
    kind: str
    target_reference: str = Field(min_length=1, max_length=120)
    label: str = Field(min_length=1, max_length=300)
    filters: dict | None = None
    channel: str = "in_app"


def _subscription(db: Session, sub_id: int, user: User) -> MonitoringSubscription:
    sub = db.get(MonitoringSubscription, sub_id)
    if sub is None or sub.user_id != user.id:
        raise HTTPException(status_code=404, detail="Assinatura não encontrada.")
    return sub


@router.post("/assinaturas", status_code=status.HTTP_201_CREATED)
def create_subscription(
    payload: SubscriptionCreate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> dict:
    if payload.kind not in {k.value for k in SubscriptionKind}:
        raise HTTPException(status_code=422, detail="Tipo de assinatura inválido.")
    sub = MonitoringSubscription(
        user_id=user.id,
        kind=SubscriptionKind(payload.kind),
        target_reference=payload.target_reference,
        label=payload.label,
        filters=payload.filters,
        channel=payload.channel,
    )
    db.add(sub)
    db.commit()
    db.refresh(sub)
    return {"id": sub.id, "kind": sub.kind.value, "label": sub.label, "is_active": sub.is_active}


@router.get("/assinaturas")
def list_subscriptions(
    db: Session = Depends(get_db), user: User = Depends(get_current_user)
) -> list[dict]:
    subs = db.scalars(
        select(MonitoringSubscription).where(MonitoringSubscription.user_id == user.id)
    )
    return [
        {
            "id": s.id,
            "kind": s.kind.value,
            "target_reference": s.target_reference,
            "label": s.label,
            "filters": s.filters,
            "channel": s.channel.value,
            "is_active": s.is_active,
        }
        for s in subs
    ]


@router.delete("/assinaturas/{sub_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_subscription(
    sub_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)
) -> Response:
    sub = _subscription(db, sub_id, user)
    db.delete(sub)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/notificacoes")
def list_notifications(
    db: Session = Depends(get_db), user: User = Depends(get_current_user)
) -> list[dict]:
    notes = db.scalars(
        select(Notification)
        .where(Notification.user_id == user.id)
        .order_by(Notification.created_at.desc())
        .limit(100)
    )
    return [
        {
            "id": n.id,
            "title": n.title,
            "body": n.body,
            "link": n.link,
            "is_read": n.is_read,
            "created_at": n.created_at.isoformat(),
        }
        for n in notes
    ]


@router.patch("/notificacoes/{notification_id}/ler")
def mark_read(
    notification_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> dict:
    notification = db.get(Notification, notification_id)
    if notification is None or notification.user_id != user.id:
        raise HTTPException(status_code=404, detail="Notificação não encontrada.")
    notification.is_read = True
    db.commit()
    return {"id": notification.id, "is_read": True}
