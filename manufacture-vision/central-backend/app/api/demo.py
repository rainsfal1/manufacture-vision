import redis as sync_redis
from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel

from app.core.config import settings
from app.core.database import get_db
from app.core.security import get_current_user
from app.models.event import Event
from sqlalchemy.orm import Session

router = APIRouter()


class ReplayResponse(BaseModel):
    status: str
    message: str


@router.post("/replay", response_model=ReplayResponse)
def trigger_replay(
    camera_id: str = Query("all", description="Camera source_id or 'all'"),
    _user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Trigger a demo replay by publishing to the 'demo.replay' Redis channel.
    The perception node reader will restart the video from the beginning when it receives this signal.
    Also clears event history for a clean demo experience.
    """
    # Clear events for this camera (or all) for a clean slate
    q = db.query(Event)
    if camera_id != "all":
        q = q.filter(Event.source_id == camera_id)
    q.delete(synchronize_session=False)
    db.commit()

    # Signal perception nodes via Redis pub/sub
    r = sync_redis.from_url(settings.REDIS_URL)
    subscribers = r.publish("demo.replay", camera_id)

    return ReplayResponse(
        status="ok",
        message=f"Replay signal sent to '{camera_id}' ({subscribers} subscriber(s) notified). Event history cleared."
    )
