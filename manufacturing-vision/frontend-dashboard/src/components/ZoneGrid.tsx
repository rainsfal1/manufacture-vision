"use client";

import { useEffect, useState } from "react";
import { EventOut } from "@/types";
import { CAMERA_CONFIGS, DUTY_LABELS } from "@/lib/cameraConfig";

interface CameraStatus {
  sourceId: string;
  isAlert: boolean;
  zoneId?: string;
}

const ALERT_WINDOW_MS = 60_000;

function deriveCameraStatus(events: EventOut[]): Map<string, CameraStatus> {
  const now = Date.now();
  const map = new Map<string, CameraStatus>(
    CAMERA_CONFIGS.map((c) => [c.sourceId, { sourceId: c.sourceId, isAlert: false }])
  );
  for (const ev of events) {
    const src = ev.source_id ?? "unknown";
    if (!map.has(src)) continue;
    const existing = map.get(src)!;
    const isRecent = now - ev.event_ts_ms < ALERT_WINDOW_MS;
    const isIncident = ["PPE_VIOLATION", "FIRE_DETECTED", "SMOKE_DETECTED"].includes(ev.event_type);
    map.set(src, {
      ...existing,
      isAlert: existing.isAlert || (isRecent && isIncident),
      zoneId: ev.zone_id ?? existing.zoneId,
    });
  }
  return map;
}

const CSS = `
  .zone-section { padding:12px 14px 0; }
  .role-hdr { display:flex; align-items:baseline; gap:5px; padding:12px 14px 6px; }
  .role-label { font-size:9px; font-weight:700; letter-spacing:.14em; text-transform:uppercase; color:rgba(255,255,255,.3); }
  .role-count { font-size:9px; color:rgba(255,255,255,.15); font-family:monospace; letter-spacing:.04em; }
  .role-rule { height:1px; background:linear-gradient(90deg,var(--border) 60%,transparent); margin:0 14px 2px; }
  .cam-grid { display:grid; grid-template-columns: 1fr 1fr; grid-auto-rows:1fr; gap:6px; padding:8px 14px 4px; }
  .cam-item { display:flex; flex-direction:column; gap:4px; height:100%; }
  .cam-lbl { font-size:9px; color:rgba(255,255,255,.18); font-family:monospace; letter-spacing:.04em; padding-left:1px; }
  .cam-card { flex:1; display:flex; flex-direction:column; padding:6px 10px 5px; border-radius:7px; background:rgba(255,255,255,.02); border:1px solid rgba(255,255,255,.04); cursor:default; transition:background .1s,border-color .1s; }
  .cam-card.alert { background:rgba(239,68,68,.06); border-color:rgba(239,68,68,.2); }
  .cam-card:hover { background:rgba(255,255,255,.045); border-color:rgba(255,255,255,.08); }
  .cam-card.alert:hover { background:rgba(239,68,68,.09); }
  .cam-top { display:flex; align-items:center; gap:5px; margin-bottom:5px; }
  .cam-dot { width:5px; height:5px; border-radius:50%; flex-shrink:0; }
  .cam-dot.ok { background:var(--green-dim); opacity:.45; }
  .cam-dot.alert { background:var(--red-dim); animation:breathe-fast 1.5s ease-in-out infinite; box-shadow:0 0 5px rgba(239,68,68,.5); }
  @keyframes breathe-fast { 0%,100%{opacity:1} 50%{opacity:.3} }
  .cam-sev { font-size:9px; font-weight:700; letter-spacing:.06em; text-transform:uppercase; }
  .cam-sev.ok { color:rgba(74,222,128,.45); }
  .cam-sev.alert { color:rgba(248,113,113,.7); }
  .cam-id { font-size:14px; font-weight:700; font-family:monospace; color:var(--text); letter-spacing:-.02em; line-height:1; margin-bottom:6px; }
  .cam-id.alert { color:rgba(248,113,113,.9); }
  .cam-duties { display:flex; flex-direction:column; gap:4px; }
  .cam-duty { font-size:9px; font-weight:600; letter-spacing:.08em; text-transform:uppercase; color:rgba(255,255,255,.6); display:flex; align-items:center; gap:5px; }
  .cam-duty::before { content: ""; display: inline-block; width: 4px; height: 4px; border-radius: 50%; }
  .cam-duty.ppe::before { background: #fbbf24; box-shadow: 0 0 4px rgba(251,191,36,.5); }
  .cam-duty.fire::before { background: #f87171; box-shadow: 0 0 4px rgba(248,113,113,.5); }
  .cam-duty.zone::before { background: #22d3ee; box-shadow: 0 0 4px rgba(34,211,238,.5); }
  .cam-zone-id { margin-top:1px; font-size:9px; color:rgba(34,211,238,.55); font-family:monospace; padding-left: 9px; }
`;

interface ZoneGridProps {
  events: EventOut[];
}

export default function ZoneGrid({ events }: ZoneGridProps) {
  const [statusMap, setStatusMap] = useState<Map<string, CameraStatus>>(deriveCameraStatus([]));

  useEffect(() => {
    setStatusMap(deriveCameraStatus(events));
    const id = setInterval(() => setStatusMap(deriveCameraStatus(events)), 10_000);
    return () => clearInterval(id);
  }, [events]);

  return (
    <>
      <style>{CSS}</style>
      <div className="role-hdr">
        <span className="role-label">Cameras</span>
        <span className="role-count">· {CAMERA_CONFIGS.length}</span>
      </div>
      <div className="role-rule" />

      <div className="cam-grid">
        {CAMERA_CONFIGS.map((cam, i) => {
          const status = statusMap.get(cam.sourceId)!;
          const alert = status?.isAlert ?? false;

          return (
            <div key={cam.sourceId} className="cam-item">
              <span className="cam-lbl">cam-{String(i + 1).padStart(2, "0")}</span>
              <div className={`cam-card${alert ? " alert" : ""}`} title={cam.description}>
                <div className="cam-top">
                  <div className={`cam-dot ${alert ? "alert" : "ok"}`} />
                  <span className={`cam-sev ${alert ? "alert" : "ok"}`}>
                    {alert ? "Alert" : "OK"}
                  </span>
                </div>

                <div className={`cam-id${alert ? " alert" : ""}`}>{cam.label}</div>

                <div className="cam-duties">
                  {cam.duties.map((duty) => {
                    const meta = DUTY_LABELS[duty];
                    // map duty to color class
                    const cls =
                      duty === "ppe-compliance" ? "ppe" :
                      duty === "fire-smoke" ? "fire" :
                      "zone";
                    return (
                      <span key={duty} className={`cam-duty ${cls}`}>
                        {meta.label}
                        {duty === "zone-intrusion" && status?.zoneId && (
                          <span style={{ fontSize: "8px", opacity: 0.4, letterSpacing: "normal", textTransform: "none", fontFamily: "monospace", marginLeft: "4px" }}>
                            → {status.zoneId}
                          </span>
                        )}
                      </span>
                    );
                  })}
                </div>
              </div>
            </div>
          );
        })}
      </div>
    </>
  );
}
