# Phase 2: PPE Detection Engine

> Feature: Manufacture Vision Platform
> Linear project: manufacture-vision
> PRD: /docs/manufacture-vision-platform.prd.md
> Status: Planned

## User stories covered

- User story 8: Define which zones require which PPE
- User story 9: Alert when worker detected without required PPE in a controlled zone
- User story 10: PPE alerts include a clip showing the worker and missing equipment

## Blocked by

Phase 1

## What to build

Extend the perception node to detect PPE attributes — hard hats, safety vests, and gloves — on tracked persons. A new ONNX model (or extended model) runs attribute detection on each person bounding box. The policy layer maps zones to required PPE. When a tracked person inside a required-PPE zone is detected without the required gear for N consecutive frames, a `PPE_VIOLATION` event fires. Validated against MP4 clips. No backend changes — events publish to Redis Streams using the same spine as Phase 1.

## Architectural decisions

- PPE detection runs as a second-stage classifier on each person crop — avoids retraining the base detector.
- PPE model is ONNX-exported and swappable without code changes.
- Policy config: `zones.json` extended with `required_ppe[]` per zone.
- `PPE_VIOLATION` event extends base envelope with `zone_id`, `missing_ppe[]`, `required_ppe[]`.
- Hysteresis applies: N consecutive frames without required PPE before event fires (same anti-flicker pattern as zone transitions).
- Cooldown per track × zone pair: suppress repeat violations for same continuous non-compliance window.

## Acceptance criteria

- [ ] PPE attribute detection (helmet, vest) runs on every tracked person bbox.
- [ ] Zones configured with `required_ppe` list fire `PPE_VIOLATION` on non-compliance.
- [ ] Hysteresis prevents single-frame false positives.
- [ ] Cooldown suppresses repeat events for continuous violations.
- [ ] `PPE_VIOLATION` events appear in Redis `vision.events` stream with correct schema.
- [ ] Service runs ≥2 minutes on test clips without crashing or latency regression.

## Notes

This phase is edge-only. No backend, dashboard, or clip evidence yet — those come in Phases 3–5. PPE violations will not be reviewable end-to-end until Phase 5 at earliest.
