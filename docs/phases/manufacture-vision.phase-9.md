# Phase 9: Integration Outputs

> Feature: Manufacture Vision Platform
> Linear project: manufacture-vision
> PRD: /docs/manufacture-vision-platform.prd.md
> Status: Planned

## User stories covered

- Plant and IT admin integration needs: route alerts to external plant systems without custom code.

## Blocked by

Phase 4

## What to build

Two configurable integration adapters on the central backend: a webhook router and an MQTT bridge. The webhook router fires outbound HTTP POST requests to configured URLs when specified event types occur — covering notification routing to Teams, Jira, ServiceNow, or any webhook-capable system. The MQTT bridge publishes matching events to a configured MQTT broker for plant systems and IIoT integrations. Both adapters are output-only — they consume from the internal event stream, they do not produce to it. Configuration is managed via the admin API.

## Architectural decisions

- Both adapters subscribe to the internal event fan-out (not Redis directly) — they receive events after the central consumer has already persisted them.
- Webhook router: configurable list of `{ url, event_types[], secret }`. Retry on 5xx: 3 attempts with 2s/4s/8s backoff. Dead-letter logged on final failure.
- MQTT bridge: connects to a configured MQTT broker. Topic pattern: `vision/{site_id}/{event_type}`. QoS 1.
- Both adapters enabled/disabled via config — not running if not configured.
- Integration config API routes: `GET/POST/PUT /api/v1/integrations/webhooks`, `GET/PUT /api/v1/integrations/mqtt`.
- Adapters are stateless — no local queue. Events are best-effort delivery.

## Acceptance criteria

- [ ] Configured webhook URLs receive HTTP POST with event payload on matching event types.
- [ ] Webhook retries 3 times with backoff on 5xx responses; dead-letters on final failure.
- [ ] MQTT bridge publishes events to configured broker on correct topic pattern.
- [ ] Both adapters can be enabled/disabled independently via config without restart.
- [ ] Integration config manageable via API (RBAC: `it_admin` only).
- [ ] Neither adapter blocks event processing if the external system is unavailable.

## Notes

MQTT and webhooks are integration outputs — they are not the internal event spine. Do not route events through them internally. OPC UA / Modbus / SCADA adapters are explicitly out of scope for MVP.
