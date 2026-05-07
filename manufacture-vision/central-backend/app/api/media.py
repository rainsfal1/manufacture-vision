import io
import json

import av
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import Response, StreamingResponse
from minio import Minio
from minio.error import S3Error
from PIL import Image as PILImage
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import get_db
from app.core.security import decode_token, get_current_user
from app.models.event import Event
from app.services.media_auth import generate_presigned_url

router = APIRouter()


class ClipUrlOut(BaseModel):
    url: str
    expires_in: int


def _clip_key_from_ref(clip_ref: str | None) -> str | None:
    if not clip_ref:
        return None
    try:
        data = json.loads(clip_ref.replace("'", '"'))
        return data.get("key") if isinstance(data, dict) else clip_ref
    except Exception:
        return clip_ref


@router.get("/clip", response_model=ClipUrlOut)
def get_clip_url(
    key: str = Query(..., description="MinIO object key, e.g. clips/12345_1_PPE_VIOLATION.mp4"),
    _user: dict = Depends(get_current_user),
):
    try:
        url = generate_presigned_url(key)
    except S3Error as e:
        if e.code == "NoSuchKey":
            raise HTTPException(status_code=404, detail="Clip not found")
        raise HTTPException(status_code=500, detail=f"MinIO error: {e}")
    return ClipUrlOut(url=url, expires_in=settings.MEDIA_URL_EXPIRE_SECONDS)


@router.get("/clip/stream")
def stream_clip(
    key: str = Query(..., description="MinIO object key, e.g. clips/12345_1_PPE_VIOLATION.mp4"),
    token: str = Query(..., description="JWT — passed as query param because <video> can't set headers"),
):
    """
    Proxy-stream a clip from MinIO through the backend.
    Avoids browser CORS issues with direct presigned MinIO URLs.
    Token is accepted as a query param (same pattern as /events/stream SSE).
    """
    decode_token(token)  # raises 401 if invalid

    client = Minio(
        settings.MINIO_ENDPOINT,
        access_key=settings.MINIO_ACCESS_KEY,
        secret_key=settings.MINIO_SECRET_KEY,
        secure=settings.MINIO_SECURE,
    )
    try:
        stat = client.stat_object(settings.MINIO_BUCKET, key)
        obj = client.get_object(settings.MINIO_BUCKET, key)
    except S3Error as e:
        if e.code == "NoSuchKey":
            raise HTTPException(status_code=404, detail="Clip not found")
        raise HTTPException(status_code=500, detail=f"MinIO error: {e}")

    return StreamingResponse(
        obj.stream(32 * 1024),
        media_type="video/mp4",
        headers={
            "Content-Length": str(stat.size),
            "Accept-Ranges": "bytes",
            "Cache-Control": "private, max-age=300",
        },
    )


@router.get("/snapshot")
def get_snapshot(
    camera_id: str = Query(..., description="Camera ID (matches source_id on events)"),
    db: Session = Depends(get_db),
    _user: dict = Depends(get_current_user),
):
    """
    Return a JPEG snapshot (first frame) of the most recent clip for a given camera.
    Used by the zone polygon editor to provide a visual background.
    Fallback to snapshots/{camera_id}.jpg if no clip events exist.
    """
    client = Minio(
        settings.MINIO_ENDPOINT,
        access_key=settings.MINIO_ACCESS_KEY,
        secret_key=settings.MINIO_SECRET_KEY,
        secure=settings.MINIO_SECURE,
    )

    event = (
        db.query(Event)
        .filter(Event.source_id == camera_id, Event.clip_ref.isnot(None), Event.clip_ref != "")
        .order_by(Event.event_ts_ms.desc())
        .first()
    )
    
    if not event:
        # Fallback to the startup snapshot
        try:
            obj = client.get_object(settings.MINIO_BUCKET, f"snapshots/{camera_id}.jpg")
            return Response(content=obj.read(), media_type="image/jpeg")
        except S3Error:
            raise HTTPException(status_code=404, detail=f"No clips or snapshots found for camera '{camera_id}'")

    clip_key = _clip_key_from_ref(event.clip_ref)
    if not clip_key:
        raise HTTPException(status_code=404, detail="Could not resolve clip key")

    try:
        obj = client.get_object(settings.MINIO_BUCKET, clip_key)
        video_bytes = obj.read()
    except S3Error as e:
        raise HTTPException(status_code=404, detail=f"Clip not in storage: {e}")

    try:
        buf = io.BytesIO(video_bytes)
        container = av.open(buf)
        frame = next(container.decode(video=0))
        pil_img: PILImage.Image = frame.to_image()
        out = io.BytesIO()
        pil_img.save(out, format="JPEG", quality=85)
        return Response(content=out.getvalue(), media_type="image/jpeg")
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Frame extraction failed: {exc}")
