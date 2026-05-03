# Phase 14: Fire & Smoke Detection

> Feature: Manufacture Vision Platform
> Linear project: manufacture-vision
> PRD: /docs/manufacture-vision-platform.prd.md
> Status: Planned

## User stories covered

- Safety: detect early indicators of fire and smoke in monitored areas and trigger real-time alerts with evidence capture.

## Blocked by

Phase 10

## What to build

Add fire and smoke detection as a dedicated detection feature with its own ONNX model. Unlike other features, fire and smoke detection does not rely on person tracking — it runs frame-level detection directly against the full frame. When fire or smoke is detected in a monitored zone for N consecutive frames, a `FIRE_DETECTED` or `SMOKE_DETECTED` event fires. Events are treated as high-priority in the dashboard with distinct visual treatment. Evidence clips are captured with a longer pre-event window (configurable, default 10s pre-event) given the nature of the threat.

## Architectural decisions

- Fire/smoke model runs in parallel to the person detection pipeline — separate ONNX inference call per frame, not sequential.
- Detection is frame-level (not track-based): no ByteTrack required. Spatial check still applies — detection must be within a monitored zone.
- Hysteresis: N=3 consecutive frames before event fires (slightly higher threshold than zone transitions to reduce false alarms from reflections/lighting changes).
- Cooldown: 5-minute cooldown per zone after a fire/smoke event to avoid alert storms during an active incident.
- `FIRE_DETECTED` and `SMOKE_DETECTED` extend envelope with `zone_id`, `detection_class`, `frame_confidence`.
- Dashboard: fire/smoke events displayed with red/orange highlight and an audible alert option.
- Clip pre-event window: configurable, default 10 seconds (vs. 5s for other events).

## Acceptance criteria

- [ ] Fire/smoke ONNX model runs per frame in parallel to person detection without latency regression.
- [ ] `FIRE_DETECTED` fires after N=3 consecutive frames with fire detection confidence above threshold in a monitored zone.
- [ ] `SMOKE_DETECTED` fires after N=3 consecutive frames with smoke detection confidence above threshold.
- [ ] Cooldown prevents repeat events within 5 minutes of a prior fire/smoke event in the same zone.
- [ ] Both event types publish to `vision.events` with correct schema.
- [ ] Dashboard renders fire/smoke alerts with distinct high-priority visual treatment.
- [ ] Evidence clips captured with 10-second pre-event window.
- [ ] No regression in existing detection features or inference latency.

## Notes

Fire/smoke is the only feature where the detection model is fundamentally different from the person detection pipeline. The ONNX runner should be extended to support multiple concurrent model instances (person model + fire/smoke model) running in the same inference loop iteration.
