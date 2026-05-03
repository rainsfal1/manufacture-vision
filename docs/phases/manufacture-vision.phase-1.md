# Phase 1: Perception Engine

> Feature: Manufacture Vision Platform
> Linear project: manufacture-vision
> PRD: /docs/manufacture-vision-platform.prd.md
> Status: Complete

## User stories covered

- Foundation for all user stories — no end-user feature is deliverable without this layer.

## Blocked by

None

## What to build

A self-contained, container-ready perception service that ingests video (MP4), runs real-time person detection and multi-object tracking, evaluates configurable polygon zone rules, and emits structured JSON events to Redis Streams only on meaningful transitions. Two threads — an ingest thread (PyAV reader + PTS-aligned pacing + drop-oldest frame buffer) and an inference loop (ONNX detection → ByteTrack → spatial footpoint check → hysteresis state machine → Redis publish) — run concurrently with bounded latency. Rich console UI shows live telemetry.

## Architectural decisions

- PyAV (not OpenCV) for PTS-accurate frame extraction — mandatory for temporal correctness.
- ONNX Runtime on CPU — no PyTorch at inference time, no GPU dependency.
- Drop-oldest frame buffer (max 5) — inference never falls behind on stale frames.
- Footpoint rule (bottom-center of bbox) for zone membership — reduces boundary false positives.
- Hysteresis: 2 consecutive frames required before ZONE_ENTER or ZONE_EXIT fires.
- Redis outage policy: drop event, log counter, continue — inference never stalls.
- Event schema version: `1.0`. Fields: `schema_version`, `event_type`, `event_ts_ms`, `source_id`, `track_id`, `zone_id`, `confidence`, `bbox`.

## Acceptance criteria

- [x] Service starts and runs continuously on ≥2 VIRAT MP4 clips without crashing.
- [x] PTS-based timestamps are monotonic and stable.
- [x] Latency ≤500ms steady-state, ≤1000ms under stress, does not increase over time.
- [x] ≥1 track retains same ID for ≥5 seconds per clip.
- [x] ≥1 ZONE_ENTER and ≥1 ZONE_EXIT emitted per clip to Redis Streams.
- [x] Redis disconnect does not stall the inference loop.
- [x] STATS telemetry logged every 5 seconds.

## Notes

All 9 issues closed (PERS-10 through PERS-18). Linear milestone: "Step 1: Perception Engine".
