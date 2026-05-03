# Phase 5: Live Dashboard — Alert Feed & Incident History

> Feature: Manufacture Vision Platform
> Linear project: manufacture-vision
> PRD: /docs/manufacture-vision-platform.prd.md
> Status: Planned

## User stories covered

- User story 1: Real-time alert when worker enters restricted zone
- User story 2: Each alert includes a video clip
- User story 3: See which zone was breached, camera, and time
- User story 4: Live feed of active alerts across all monitored zones
- User story 5: Alerts remain visible until acknowledged
- User story 6: Search incident history by date, zone, event type
- User story 7: Play back evidence clip for any historical incident
- User story 9: Notified when worker detected without required PPE
- User story 10: PPE alerts include clip showing worker and missing equipment

## Blocked by

Phase 3, Phase 4

## What to build

The control room UI. A Next.js app with two core views: a live alert feed (SSE connection, one card per incoming event, unacknowledged alerts visually distinct) and an incident history table (filterable by date range, zone, and event type, with clip playback inline). Clicking any event — live or historical — opens the video player, which fetches a signed MinIO URL from the backend and plays the evidence clip. The SSE broadcaster is added to the FastAPI backend in this phase to push new events to connected clients in real time.

## Architectural decisions

- SSE endpoint: `GET /api/v1/events/stream` — long-lived HTTP connection, no WebSocket.
- Alert cards show: timestamp, event type, zone label, source/camera ID, confidence, thumbnail (first frame of clip if available).
- Acknowledgement state stored in browser (localStorage for MVP); server-side acknowledgement in post-MVP.
- Video player: native HTML5 `<video>` tag with signed URL as `src`. No custom streaming server needed.
- Incident history table: client-side pagination against `GET /api/v1/events` with filter params.
- No pixel-perfect design requirement — functional and readable for a shift manager in a control room.
- Next.js App Router. TypeScript throughout.

## Acceptance criteria

- [ ] SSE connection established on dashboard load; new events appear as alert cards within 1 second of Redis publish.
- [ ] Alert cards display event type, zone, camera, timestamp, and confidence.
- [ ] Unacknowledged alerts are visually distinct from acknowledged ones.
- [ ] Incident history table renders and filters correctly by date range, zone, and event type.
- [ ] Clicking any event opens the video player with the evidence clip loaded.
- [ ] Video player fetches signed URL from backend and plays clip without authentication errors.
- [ ] Dashboard loads and renders in under 3 seconds on a local network.
- [ ] No hardcoded API URLs — all backend calls go through environment-configured base URL.

## Notes

Zone/policy configuration UI is NOT in this phase — that is Phase 6. Analytics charts are Phase 8. This phase delivers the core control room experience: see alerts live, investigate with video proof.
