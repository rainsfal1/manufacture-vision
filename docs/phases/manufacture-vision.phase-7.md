# Phase 7: RTSP / ONVIF Live Camera Ingestion

> Feature: Manufacture Vision Platform
> Linear project: manufacture-vision
> PRD: /docs/manufacture-vision-platform.prd.md
> Status: Planned

## User stories covered

- User story 16: Connect to existing RTSP cameras via ONVIF discovery
- User story 21: Edge node self-recovers from camera disconnects

## Blocked by

Phase 1

## What to build

Replace the MP4 file adapter with a live RTSP adapter that connects to real cameras. ONVIF discovery scans the local network for cameras and retrieves their RTSP profiles (main stream + sub-stream). The RTSP reader connects using PyAV or GStreamer, negotiates the stream, and emits `(frame, pts_ms)` tuples through the same adapter interface established in Phase 1 — no inference pipeline changes. A reconnection watchdog monitors the stream connection and retries with exponential backoff on disconnect. Both MP4 and RTSP adapters coexist, selected via config.

## Architectural decisions

- Adapter interface is unchanged: `(frame: ndarray, pts_ms: int)` — RTSP is a drop-in for MP4.
- ONVIF discovery uses WS-Discovery broadcast; camera credentials stored in config (not in code).
- Dual-stream via RTSP: main stream (high-res) → ring buffer, sub-stream (low-res) → AI queue. If camera only exposes one stream, downsample in software.
- Reconnection: exponential backoff starting at 1s, cap at 60s. Watchdog thread monitors stream health via heartbeat.
- On disconnect: log event, increment reconnect counter in telemetry, continue attempting reconnect — do not crash the process.
- PTS from RTSP: use stream PTS from PyAV/GStreamer; fall back to wall-clock if PTS is non-monotonic.

## Acceptance criteria

- [ ] ONVIF discovery identifies cameras on local network and retrieves RTSP stream URLs.
- [ ] RTSP adapter connects to a live camera stream and emits `(frame, pts_ms)` tuples.
- [ ] Inference pipeline operates identically on RTSP frames as on MP4 frames.
- [ ] Camera disconnect triggers reconnect watchdog; stream resumes without process restart.
- [ ] Reconnect counter visible in telemetry.
- [ ] Exponential backoff applied between reconnect attempts (1s → 2s → 4s ... → 60s cap).
- [ ] Config selects adapter type (`mp4` or `rtsp`) without code changes.
- [ ] Dual RTSP stream (main + sub) correctly routes to ring buffer and AI queue respectively.

## Notes

This phase is pure edge-side. No backend or dashboard changes. It can be developed in parallel with Phases 4, 5, and 6 since it only depends on Phase 1. This is the gate for any live pilot deployment.
