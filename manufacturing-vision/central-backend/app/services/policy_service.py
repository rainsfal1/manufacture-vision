import json

from sqlalchemy.orm import Session

from app.models.audit_log import AuditLog
from app.models.policy import Policy


def write_audit(
    db: Session,
    actor: str,
    action: str,
    entity_type: str,
    entity_id: str,
    diff: dict | None = None,
) -> None:
    """Append an audit log entry. Must be called before db.commit()."""
    db.add(AuditLog(
        actor=actor,
        action=action,
        entity_type=entity_type,
        entity_id=entity_id,
        diff=json.dumps(diff) if diff else None,
    ))


def get_active_policy_for_zone(db: Session, zone_id: str) -> Policy | None:
    return (
        db.query(Policy)
        .filter(Policy.zone_id == zone_id, Policy.active.is_(True))
        .first()
    )
