import redis.asyncio as aioredis
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sse_starlette.sse import EventSourceResponse

from app.core.config import settings
from app.core.database import get_db
from app.core.security import decode_token, get_current_user
from app.models.event import Event
from app.schemas.event import EventListOut, EventOut

router = APIRouter()


@router.get("/stream")
async def event_stream(token: str = Query(...)):
    """Server-Sent Events endpoint — streams new events in real time.
    Token passed as query param because EventSource doesn't support custom headers.
    """
    decode_token(token)  # raises 401 if invalid

    async def generator():
        r = aioredis.from_url(settings.REDIS_URL, decode_responses=True)
        async with r.pubsub() as pubsub:
            await pubsub.subscribe("vision.events.broadcast")
            async for message in pubsub.listen():
                if message["type"] == "message":
                    yield {"data": message["data"]}

    return EventSourceResponse(generator())


@router.get("", response_model=EventListOut)
def list_events(
    event_type: str | None = Query(None),
    zone_id: str | None = Query(None),
    from_ts: int | None = Query(None, description="epoch ms"),
    to_ts: int | None = Query(None, description="epoch ms"),
    limit: int = Query(50, le=500),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
    _user: dict = Depends(get_current_user),
):
    q = db.query(Event)
    if event_type:
        q = q.filter(Event.event_type == event_type)
    if zone_id:
        q = q.filter(Event.zone_id == zone_id)
    if from_ts is not None:
        q = q.filter(Event.event_ts_ms >= from_ts)
    if to_ts is not None:
        q = q.filter(Event.event_ts_ms <= to_ts)

    total = q.count()
    items = q.order_by(Event.event_ts_ms.desc()).offset(offset).limit(limit).all()
    return EventListOut(items=items, total=total, limit=limit, offset=offset)


@router.get("/recent", response_model=list[EventOut])
def recent_events(
    limit: int = Query(50, le=500),
    db: Session = Depends(get_db),
    _user: dict = Depends(get_current_user),
):
    return db.query(Event).order_by(Event.event_ts_ms.desc()).limit(limit).all()


@router.get("/{event_id}", response_model=EventOut)
def get_event(
    event_id: str,
    db: Session = Depends(get_db),
    _user: dict = Depends(get_current_user),
):
    event = db.query(Event).filter(Event.id == event_id).first()
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")
    return event
