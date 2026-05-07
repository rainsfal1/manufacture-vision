import csv
import io
import json
from collections import defaultdict
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import get_current_user
from app.schemas.report import SummaryBucket, SummaryOut, TrendOut, TrendPoint

router = APIRouter()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _parse_date(date_str: str) -> datetime:
    """Parse YYYY-MM-DD → UTC midnight datetime."""
    try:
        dt = datetime.fromisoformat(date_str)
        return dt.replace(tzinfo=timezone.utc) if dt.tzinfo is None else dt.astimezone(timezone.utc)
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Invalid date '{date_str}'. Use YYYY-MM-DD.")


def _to_ms(dt: datetime) -> int:
    return int(dt.timestamp() * 1000)


def _extract_clip_key(clip_ref: str | None) -> str | None:
    """Same logic as EventOut.clip_key — parse Python-repr or JSON clip_ref."""
    if not clip_ref:
        return None
    try:
        data = json.loads(clip_ref.replace("'", '"'))
        return data.get("key") if isinstance(data, dict) else clip_ref
    except Exception:
        return clip_ref


# ---------------------------------------------------------------------------
# GET /reports/summary
# ---------------------------------------------------------------------------

@router.get("/summary", response_model=SummaryOut)
def get_summary(
    from_date: str = Query(..., alias="from"),
    to_date: str = Query(..., alias="to"),
    granularity: str = Query("day"),
    zone_id: str | None = Query(None),
    db: Session = Depends(get_db),
    _user: dict = Depends(get_current_user),
):
    if granularity not in ("day", "shift", "week"):
        raise HTTPException(status_code=400, detail="granularity must be day, shift, or week")

    from_dt = _parse_date(from_date)
    to_dt = _parse_date(to_date).replace(hour=23, minute=59, second=59)

    if from_dt > to_dt:
        raise HTTPException(status_code=400, detail="'from' must be before 'to'")

    from_ms = _to_ms(from_dt)
    to_ms = _to_ms(to_dt)

    # For shift granularity use hourly SQL buckets; group into 8h blocks in Python
    trunc_unit = "hour" if granularity == "shift" else granularity

    where_clauses = ["event_ts_ms >= :from_ms", "event_ts_ms <= :to_ms"]
    params: dict = {"from_ms": from_ms, "to_ms": to_ms, "trunc_unit": trunc_unit}
    if zone_id:
        where_clauses.append("zone_id = :zone_id")
        params["zone_id"] = zone_id

    where_sql = " AND ".join(where_clauses)

    # Main aggregation — one query, indexed columns only
    agg_sql = text(f"""
        SELECT date_trunc(:trunc_unit, to_timestamp(event_ts_ms / 1000.0)) AS period,
               event_type,
               zone_id,
               COUNT(*) AS cnt
        FROM events
        WHERE {where_sql}
        GROUP BY period, event_type, zone_id
        ORDER BY period
    """)
    rows = db.execute(agg_sql, params).fetchall()

    # by_ppe breakdown — parse JSON missing_ppe column in Python (can't do in SQL cleanly)
    ppe_where = f"event_type = 'PPE_VIOLATION' AND {where_sql} AND missing_ppe IS NOT NULL"
    ppe_rows = db.execute(
        text(f"SELECT missing_ppe FROM events WHERE {ppe_where}"), params
    ).fetchall()

    global_by_ppe: dict[str, int] = {}
    for (ppe_json,) in ppe_rows:
        try:
            items = json.loads(ppe_json) if isinstance(ppe_json, str) else (ppe_json or [])
            for item in items:
                global_by_ppe[item] = global_by_ppe.get(item, 0) + 1
        except Exception:
            pass

    # Pivot rows: {period_key → {event_type → {zone_id → count}}}
    period_data: dict = defaultdict(lambda: defaultdict(lambda: defaultdict(int)))

    for row in rows:
        period_dt: datetime = row.period
        if period_dt.tzinfo is None:
            period_dt = period_dt.replace(tzinfo=timezone.utc)

        if granularity == "shift":
            h = period_dt.hour
            shift_num = 1 if 6 <= h < 14 else (2 if 14 <= h < 22 else 3)
            period_key = f"{period_dt.date()} shift-{shift_num}"
        elif granularity == "week":
            period_key = period_dt.strftime("%Y-W%W")
        else:
            period_key = period_dt.strftime("%Y-%m-%d")

        zid = row.zone_id or "unknown"
        period_data[period_key][row.event_type][zid] += row.cnt

    # Generate zero-filled period sequence
    expected_periods: list[str] = []
    if granularity == "day":
        cur = from_dt
        while cur.date() <= to_dt.date():
            expected_periods.append(cur.strftime("%Y-%m-%d"))
            cur += timedelta(days=1)
    elif granularity == "week":
        cur = from_dt
        while cur <= to_dt:
            expected_periods.append(cur.strftime("%Y-W%W"))
            cur += timedelta(weeks=1)
    else:  # shift
        cur = from_dt.replace(hour=0, minute=0, second=0, microsecond=0)
        while cur.date() <= to_dt.date():
            for shift_num, start_hour in [(1, 6), (2, 14), (3, 22)]:
                slot = cur.replace(hour=start_hour)
                if from_dt <= slot <= to_dt:
                    expected_periods.append(f"{slot.date()} shift-{shift_num}")
            cur += timedelta(days=1)

    all_periods = sorted(set(expected_periods) | set(period_data.keys()))

    buckets: list[SummaryBucket] = []
    total_violations = 0

    for period_key in all_periods:
        data = period_data.get(period_key, {})
        ppe_count = sum(data.get("PPE_VIOLATION", {}).values())
        enter_count = sum(data.get("ZONE_ENTER", {}).values())
        exit_count = sum(data.get("ZONE_EXIT", {}).values())

        by_zone: dict[str, int] = {}
        for zones in data.values():
            for zid, cnt in zones.items():
                by_zone[zid] = by_zone.get(zid, 0) + cnt

        total_violations += ppe_count
        buckets.append(SummaryBucket(
            period=period_key,
            ppe_violations=ppe_count,
            zone_enter=enter_count,
            zone_exit=exit_count,
            by_zone=by_zone,
            by_ppe=global_by_ppe if ppe_count > 0 else {},
        ))

    return SummaryOut(
        from_date=from_date,
        to_date=to_date,
        granularity=granularity,
        buckets=buckets,
        totals={"ppe_violations": total_violations},
    )


# ---------------------------------------------------------------------------
# GET /reports/trend
# ---------------------------------------------------------------------------

@router.get("/trend", response_model=TrendOut)
def get_trend(
    from_date: str = Query(..., alias="from"),
    to_date: str = Query(..., alias="to"),
    event_type: str = Query("PPE_VIOLATION"),
    interval: str = Query("hour"),
    zone_id: str | None = Query(None),
    db: Session = Depends(get_db),
    _user: dict = Depends(get_current_user),
):
    """
    Returns time-series counts for a specific event type, aggregated by zone.
    Used for the Trend Chart.
    """
    # Quick validation since we dynamically inject this into SQL
    if event_type not in ("PPE_VIOLATION", "ZONE_ENTER", "ZONE_EXIT", "FIRE_DETECTED", "SMOKE_DETECTED"):
        raise HTTPException(status_code=400, detail="event_type must be PPE_VIOLATION, ZONE_ENTER, ZONE_EXIT, FIRE_DETECTED, or SMOKE_DETECTED")

    from_dt = _parse_date(from_date)
    to_dt = _parse_date(to_date).replace(hour=23, minute=59, second=59)

    if from_dt > to_dt:
        raise HTTPException(status_code=400, detail="'from' must be before 'to'")

    max_days = 30 if interval == "hour" else 365
    if (to_dt - from_dt).days > max_days:
        raise HTTPException(
            status_code=400,
            detail=f"Range exceeds {max_days}-day limit for interval={interval}"
        )

    from_ms = _to_ms(from_dt)
    to_ms = _to_ms(to_dt)

    where_clauses = [
        "event_type = :event_type",
        "event_ts_ms >= :from_ms",
        "event_ts_ms <= :to_ms",
    ]
    params: dict = {
        "event_type": event_type,
        "from_ms": from_ms,
        "to_ms": to_ms,
        "interval": interval,
    }
    if zone_id:
        where_clauses.append("zone_id = :zone_id")
        params["zone_id"] = zone_id

    where_sql = " AND ".join(where_clauses)
    sql = text(f"""
        SELECT date_trunc(:interval, to_timestamp(event_ts_ms / 1000.0)) AS ts,
               COUNT(*) AS cnt
        FROM events
        WHERE {where_sql}
        GROUP BY ts
        ORDER BY ts
    """)

    rows = db.execute(sql, params).fetchall()
    series: list[TrendPoint] = []
    for row in rows:
        ts: datetime = row.ts
        if ts.tzinfo is None:
            ts = ts.replace(tzinfo=timezone.utc)
        series.append(TrendPoint(ts=ts, count=row.cnt))

    return TrendOut(event_type=event_type, interval=interval, series=series)


# ---------------------------------------------------------------------------
# GET /reports/export
# ---------------------------------------------------------------------------

@router.get("/export")
def export_csv(
    from_date: str = Query(..., alias="from"),
    to_date: str = Query(..., alias="to"),
    event_type: list[str] | None = Query(None),
    zone_id: str | None = Query(None),
    db: Session = Depends(get_db),
    _user: dict = Depends(get_current_user),
):
    from_dt = _parse_date(from_date)
    to_dt = _parse_date(to_date).replace(hour=23, minute=59, second=59)

    if from_dt > to_dt:
        raise HTTPException(status_code=400, detail="'from' must be before 'to'")
    if (to_dt - from_dt).days > 90:
        raise HTTPException(status_code=400, detail="Range exceeds 90-day limit for export")

    from_ms = _to_ms(from_dt)
    to_ms = _to_ms(to_dt)

    where_clauses = ["event_ts_ms >= :from_ms", "event_ts_ms <= :to_ms"]
    params: dict = {"from_ms": from_ms, "to_ms": to_ms}

    if event_type:
        placeholders = ", ".join(f":et_{i}" for i in range(len(event_type)))
        where_clauses.append(f"event_type IN ({placeholders})")
        for i, et in enumerate(event_type):
            params[f"et_{i}"] = et
    if zone_id:
        where_clauses.append("zone_id = :zone_id")
        params["zone_id"] = zone_id

    where_sql = " AND ".join(where_clauses)
    sql = text(f"""
        SELECT event_ts_ms, event_type, zone_id, track_id, missing_ppe, source_id, clip_ref
        FROM events
        WHERE {where_sql}
        ORDER BY event_ts_ms
    """)
    rows = db.execute(sql, params).fetchall()

    def generate():
        buf = io.StringIO()
        writer = csv.writer(buf)
        writer.writerow(["timestamp", "event_type", "zone_id", "track_id",
                         "missing_ppe", "source_id", "clip_key"])
        yield buf.getvalue()
        buf.seek(0)
        buf.truncate()

        for row in rows:
            ts = datetime.fromtimestamp(row.event_ts_ms / 1000.0, tz=timezone.utc).isoformat()
            clip_key = _extract_clip_key(row.clip_ref)
            writer.writerow([ts, row.event_type, row.zone_id, row.track_id,
                             row.missing_ppe, row.source_id, clip_key])
            yield buf.getvalue()
            buf.seek(0)
            buf.truncate()

    filename = f"violations_{from_date}_{to_date}.csv"
    return StreamingResponse(
        generate(),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )
