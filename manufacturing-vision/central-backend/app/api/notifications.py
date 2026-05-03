import json

from fastapi import APIRouter, Depends, HTTPException, Query, Response
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import get_current_user
from app.models.notification_channel import NotificationChannel
from app.models.notification_rule import NotificationRule
from app.schemas.notification import ChannelIn, ChannelOut, RuleIn, RuleOut
from app.services.channel_drivers import get_driver
from app.services.policy_service import write_audit

router = APIRouter()

# ─── Channels ────────────────────────────────────────────────────────────────


@router.get("/channels", response_model=list[ChannelOut])
def list_channels(
    db: Session = Depends(get_db),
    _user: dict = Depends(get_current_user),
):
    return db.query(NotificationChannel).order_by(NotificationChannel.created_at).all()


@router.post("/channels", response_model=ChannelOut, status_code=201)
def create_channel(
    body: ChannelIn,
    db: Session = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    ch = NotificationChannel(
        name=body.name,
        type=body.type,
        config=json.dumps(body.config),
        active=True,
    )
    db.add(ch)
    write_audit(db, user["sub"], "create", "notification_channel", None,
                {"name": body.name, "type": body.type})
    db.commit()
    db.refresh(ch)
    return ch


@router.put("/channels/{channel_id}", response_model=ChannelOut)
def update_channel(
    channel_id: str,
    body: ChannelIn,
    db: Session = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    ch = db.query(NotificationChannel).filter(NotificationChannel.id == channel_id).first()
    if not ch:
        raise HTTPException(status_code=404, detail="Channel not found")

    ch.name = body.name
    ch.type = body.type
    ch.config = json.dumps(body.config)
    write_audit(db, user["sub"], "update", "notification_channel", channel_id,
                {"name": body.name, "type": body.type})
    db.commit()
    db.refresh(ch)
    return ch


@router.patch("/channels/{channel_id}/active", response_model=ChannelOut)
def toggle_channel(
    channel_id: str,
    db: Session = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    ch = db.query(NotificationChannel).filter(NotificationChannel.id == channel_id).first()
    if not ch:
        raise HTTPException(status_code=404, detail="Channel not found")
    ch.active = not ch.active
    write_audit(db, user["sub"], "toggle", "notification_channel", channel_id,
                {"active": ch.active})
    db.commit()
    db.refresh(ch)
    return ch


@router.delete("/channels/{channel_id}", status_code=204)
def delete_channel(
    channel_id: str,
    db: Session = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    ch = db.query(NotificationChannel).filter(NotificationChannel.id == channel_id).first()
    if not ch:
        raise HTTPException(status_code=404, detail="Channel not found")
    write_audit(db, user["sub"], "delete", "notification_channel", channel_id)
    db.delete(ch)
    db.commit()
    return Response(status_code=204)


@router.post("/channels/{channel_id}/test")
def test_channel(
    channel_id: str,
    db: Session = Depends(get_db),
    _user: dict = Depends(get_current_user),
):
    ch = db.query(NotificationChannel).filter(NotificationChannel.id == channel_id).first()
    if not ch:
        raise HTTPException(status_code=404, detail="Channel not found")

    config = json.loads(ch.config) if isinstance(ch.config, str) else ch.config
    payload = {
        "event_type": "TEST",
        "zone_id": "test-zone",
        "source_id": "test",
        "track_id": 0,
        "missing_ppe": [],
        "event_ts_ms": 0,
        "clip_key": None,
    }
    try:
        get_driver(ch.type).send(config, payload)
        return {"ok": True}
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc))


# ─── Rules ───────────────────────────────────────────────────────────────────


@router.get("/rules", response_model=list[RuleOut])
def list_rules(
    channel_id: str | None = Query(None),
    db: Session = Depends(get_db),
    _user: dict = Depends(get_current_user),
):
    q = db.query(NotificationRule)
    if channel_id:
        q = q.filter(NotificationRule.channel_id == channel_id)
    return q.order_by(NotificationRule.created_at).all()


@router.post("/rules", response_model=RuleOut, status_code=201)
def create_rule(
    body: RuleIn,
    db: Session = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    # Ensure referenced channel exists
    ch = db.query(NotificationChannel).filter(NotificationChannel.id == body.channel_id).first()
    if not ch:
        raise HTTPException(status_code=404, detail="Channel not found")

    rule = NotificationRule(
        channel_id=body.channel_id,
        event_type=body.event_type,
        zone_id=body.zone_id,
        active=body.active,
    )
    db.add(rule)
    write_audit(db, user["sub"], "create", "notification_rule", None,
                {"channel_id": body.channel_id, "event_type": body.event_type, "zone_id": body.zone_id})
    db.commit()
    db.refresh(rule)
    return rule


@router.put("/rules/{rule_id}", response_model=RuleOut)
def update_rule(
    rule_id: str,
    body: RuleIn,
    db: Session = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    rule = db.query(NotificationRule).filter(NotificationRule.id == rule_id).first()
    if not rule:
        raise HTTPException(status_code=404, detail="Rule not found")

    rule.channel_id = body.channel_id
    rule.event_type = body.event_type
    rule.zone_id = body.zone_id
    rule.active = body.active
    write_audit(db, user["sub"], "update", "notification_rule", rule_id,
                {"event_type": body.event_type, "zone_id": body.zone_id, "active": body.active})
    db.commit()
    db.refresh(rule)
    return rule


@router.patch("/rules/{rule_id}/active", response_model=RuleOut)
def toggle_rule(
    rule_id: str,
    db: Session = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    rule = db.query(NotificationRule).filter(NotificationRule.id == rule_id).first()
    if not rule:
        raise HTTPException(status_code=404, detail="Rule not found")
    rule.active = not rule.active
    write_audit(db, user["sub"], "toggle", "notification_rule", rule_id,
                {"active": rule.active})
    db.commit()
    db.refresh(rule)
    return rule


@router.delete("/rules/{rule_id}", status_code=204)
def delete_rule(
    rule_id: str,
    db: Session = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    rule = db.query(NotificationRule).filter(NotificationRule.id == rule_id).first()
    if not rule:
        raise HTTPException(status_code=404, detail="Rule not found")
    write_audit(db, user["sub"], "delete", "notification_rule", rule_id)
    db.delete(rule)
    db.commit()
    return Response(status_code=204)
