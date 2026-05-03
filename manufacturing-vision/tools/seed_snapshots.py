#!/usr/bin/env python3
"""
seed_snapshots.py — Extract the first frame from each demo video and upload
it to MinIO as snapshots/{camera_id}.jpg so the zone editor has a real camera
background without needing the perception node to have run first.

Runs once at stack startup (docker-compose seed-snapshots service) or manually:
    python tools/seed_snapshots.py
"""

import io
import os
import sys
import time
import urllib.request

import av
import cv2
from minio import Minio
from minio.error import S3Error

MINIO_ENDPOINT  = os.getenv("MINIO_ENDPOINT",   "localhost:9000")
MINIO_ACCESS    = os.getenv("MINIO_ACCESS_KEY",  "minioadmin")
MINIO_SECRET    = os.getenv("MINIO_SECRET_KEY",  "minioadmin")
MINIO_BUCKET    = os.getenv("MINIO_BUCKET",      "vision-evidence")
MINIO_SECURE    = os.getenv("MINIO_SECURE", "false").lower() == "true"

# camera_id → video path (matches docker-compose.dev.yml INPUT_STREAM values)
CAMERAS = {
    "camera-01": os.getenv("VIDEO_ZONE",      "/demo-videos/zone-detection.mp4"),
    "camera-02": os.getenv("VIDEO_HELMET",    "/demo-videos/helmet.mp4"),
    "camera-03": os.getenv("VIDEO_NO_HELMET", "/demo-videos/no-helmet-.mp4"),
    "camera-04": os.getenv("VIDEO_FIRE",      "/demo-videos/fire-detection.mp4"),
}


def wait_for_minio(retries: int = 30, delay: float = 2.0) -> None:
    """Poll MinIO's unauthenticated health endpoint — no credentials needed."""
    scheme = "https" if MINIO_SECURE else "http"
    health_url = f"{scheme}://{MINIO_ENDPOINT}/minio/health/live"
    print(f"Waiting for MinIO at {health_url} ...")
    for attempt in range(retries):
        try:
            with urllib.request.urlopen(health_url, timeout=3) as resp:
                if resp.status == 200:
                    print("MinIO is ready.")
                    return
        except Exception as e:
            print(f"  attempt {attempt + 1}/{retries}: {e}")
        time.sleep(delay)
    print("ERROR: MinIO never became ready.", file=sys.stderr)
    sys.exit(1)


def ensure_bucket(client: Minio, bucket: str) -> None:
    try:
        if not client.bucket_exists(bucket):
            client.make_bucket(bucket)
            print(f"Created bucket '{bucket}'")
    except S3Error as e:
        print(f"ERROR: could not ensure bucket: {e}", file=sys.stderr)
        sys.exit(1)


def extract_first_frame_jpeg(video_path: str) -> bytes | None:
    """Return JPEG bytes of the first decodable video frame, or None."""
    try:
        container = av.open(video_path)
        for frame in container.decode(video=0):
            img = frame.to_ndarray(format="bgr24")
            ok, buf = cv2.imencode(".jpg", img, [cv2.IMWRITE_JPEG_QUALITY, 85])
            if ok:
                return buf.tobytes()
        print(f"  WARNING: no frames decoded from {video_path}")
    except Exception as e:
        print(f"  WARNING: could not open {video_path}: {e}")
    return None


def upload_snapshot(client: Minio, bucket: str, camera_id: str, jpeg: bytes) -> None:
    key = f"snapshots/{camera_id}.jpg"
    client.put_object(
        bucket, key,
        io.BytesIO(jpeg), length=len(jpeg),
        content_type="image/jpeg",
    )
    print(f"  Uploaded {key} ({len(jpeg) // 1024} KB)")


def main() -> None:
    wait_for_minio()

    print(f"Connecting to MinIO as '{MINIO_ACCESS}' ...")
    client = Minio(MINIO_ENDPOINT, access_key=MINIO_ACCESS,
                   secret_key=MINIO_SECRET, secure=MINIO_SECURE)
    ensure_bucket(client, MINIO_BUCKET)

    ok = 0
    for camera_id, video_path in CAMERAS.items():
        print(f"[{camera_id}] {video_path}")
        if not os.path.exists(video_path):
            print(f"  SKIP — file not found: {video_path}")
            continue

        # Skip if snapshot already exists (don't overwrite a live one)
        try:
            client.stat_object(MINIO_BUCKET, f"snapshots/{camera_id}.jpg")
            print(f"  Already exists — skipping")
            ok += 1
            continue
        except S3Error:
            pass

        jpeg = extract_first_frame_jpeg(video_path)
        if jpeg:
            upload_snapshot(client, MINIO_BUCKET, camera_id, jpeg)
            ok += 1

    print(f"\nDone: {ok}/{len(CAMERAS)} snapshots seeded.")


if __name__ == "__main__":
    main()
