import json

from fastapi import APIRouter, Depends, HTTPException, Query, Response
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import get_current_user
from app.models.policy import Policy
from app.schemas.policy import PolicyIn, PolicyOut
from app.services.policy_service import get_active_policy_for_zone, write_audit

router = APIRouter()


@router.get("", response_model=list[PolicyOut])
def list_policies(
    zone_id: str | None = Query(None),
    db: Session = Depends(get_db),
    _user: dict = Depends(get_current_user),
):
    q = db.query(Policy)
    if zone_id:
        q = q.filter(Policy.zone_id == zone_id)
    return q.order_by(Policy.created_at).all()


@router.get("/{policy_id}", response_model=PolicyOut)
def get_policy(
    policy_id: str,
    db: Session = Depends(get_db),
    _user: dict = Depends(get_current_user),
):
    policy = db.query(Policy).filter(Policy.id == policy_id).first()
    if not policy:
        raise HTTPException(status_code=404, detail="Policy not found")
    return policy


@router.post("", response_model=PolicyOut, status_code=201)
def create_policy(
    body: PolicyIn,
    db: Session = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    policy = Policy(
        zone_id=body.zone_id,
        required_ppe=json.dumps(body.required_ppe),
        active=True,
    )
    db.add(policy)
    write_audit(db, user["sub"], "create", "policy", body.zone_id,
                {"zone_id": body.zone_id, "required_ppe": body.required_ppe})
    db.commit()
    db.refresh(policy)
    return policy


@router.put("/{policy_id}", response_model=PolicyOut)
def update_policy(
    policy_id: str,
    body: PolicyIn,
    db: Session = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    policy = db.query(Policy).filter(Policy.id == policy_id).first()
    if not policy:
        raise HTTPException(status_code=404, detail="Policy not found")

    before = {"required_ppe": policy.required_ppe}
    policy.required_ppe = json.dumps(body.required_ppe)
    write_audit(db, user["sub"], "update", "policy", policy_id,
                {"before": before, "after": {"required_ppe": policy.required_ppe}})
    db.commit()
    db.refresh(policy)
    return policy


@router.delete("/{policy_id}", status_code=204)
def delete_policy(
    policy_id: str,
    db: Session = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    policy = db.query(Policy).filter(Policy.id == policy_id).first()
    if not policy:
        raise HTTPException(status_code=404, detail="Policy not found")

    write_audit(db, user["sub"], "delete", "policy", policy_id)
    db.delete(policy)
    db.commit()
    return Response(status_code=204)


@router.post("/{policy_id}/activate", response_model=PolicyOut)
def activate_policy(
    policy_id: str,
    db: Session = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    policy = db.query(Policy).filter(Policy.id == policy_id).first()
    if not policy:
        raise HTTPException(status_code=404, detail="Policy not found")

    if policy.active:
        return policy  # already active — idempotent

    # Auto-deactivate any other active policy for the same zone
    competing = get_active_policy_for_zone(db, policy.zone_id)
    if competing and competing.id != policy_id:
        competing.active = False
        write_audit(db, user["sub"], "deactivate", "policy", competing.id,
                    {"reason": f"superseded by {policy_id}"})

    policy.active = True
    write_audit(db, user["sub"], "activate", "policy", policy_id)
    db.commit()
    db.refresh(policy)
    return policy


@router.post("/{policy_id}/deactivate", response_model=PolicyOut)
def deactivate_policy(
    policy_id: str,
    db: Session = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    policy = db.query(Policy).filter(Policy.id == policy_id).first()
    if not policy:
        raise HTTPException(status_code=404, detail="Policy not found")

    policy.active = False
    write_audit(db, user["sub"], "deactivate", "policy", policy_id)
    db.commit()
    db.refresh(policy)
    return policy
