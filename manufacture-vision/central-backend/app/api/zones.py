import json
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Response
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import get_current_user
from app.models.zone import Zone
from app.schemas.zone import ZoneIn, ZoneOut
from app.services.policy_service import write_audit

router = APIRouter()


@router.get("", response_model=list[ZoneOut])
def list_zones(
    db: Session = Depends(get_db),
    _user: dict = Depends(get_current_user),
):
    return db.query(Zone).order_by(Zone.created_at).all()


@router.get("/{zone_id}", response_model=ZoneOut)
def get_zone(
    zone_id: str,
    db: Session = Depends(get_db),
    _user: dict = Depends(get_current_user),
):
    zone = db.query(Zone).filter(Zone.zone_id == zone_id).first()
    if not zone:
        raise HTTPException(status_code=404, detail="Zone not found")
    return zone


@router.post("", response_model=ZoneOut, status_code=201)
def create_zone(
    body: ZoneIn,
    db: Session = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    if db.query(Zone).filter(Zone.zone_id == body.zone_id).first():
        raise HTTPException(status_code=409, detail="zone_id already exists")

    zone = Zone(
        zone_id=body.zone_id,
        polygon=json.dumps(body.polygon) if body.polygon is not None else None,
        required_ppe=json.dumps(body.required_ppe) if body.required_ppe is not None else None,
        camera_id=body.camera_id,
    )
    db.add(zone)
    write_audit(db, user["sub"], "create", "zone", body.zone_id,
                {"zone_id": body.zone_id, "required_ppe": body.required_ppe})
    db.commit()
    db.refresh(zone)
    return zone


@router.put("/{zone_id}", response_model=ZoneOut)
def update_zone(
    zone_id: str,
    body: ZoneIn,
    db: Session = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    zone = db.query(Zone).filter(Zone.zone_id == zone_id).first()
    if not zone:
        raise HTTPException(status_code=404, detail="Zone not found")

    before = {"polygon": zone.polygon, "required_ppe": zone.required_ppe, "camera_id": zone.camera_id}

    zone.polygon = json.dumps(body.polygon) if body.polygon is not None else None
    zone.required_ppe = json.dumps(body.required_ppe) if body.required_ppe is not None else None
    zone.camera_id = body.camera_id
    zone.updated_at = datetime.now(timezone.utc)

    write_audit(db, user["sub"], "update", "zone", zone_id,
                {"before": before, "after": {"polygon": zone.polygon, "required_ppe": zone.required_ppe}})
    db.commit()
    db.refresh(zone)
    return zone


@router.delete("/{zone_id}", status_code=204)
def delete_zone(
    zone_id: str,
    db: Session = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    zone = db.query(Zone).filter(Zone.zone_id == zone_id).first()
    if not zone:
        raise HTTPException(status_code=404, detail="Zone not found")

    write_audit(db, user["sub"], "delete", "zone", zone_id)
    db.delete(zone)
    db.commit()
    return Response(status_code=204)
