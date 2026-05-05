"use client";

import { EventOut } from "@/types";

interface AlertCardProps {
  event: EventOut;
  onPlayClip: (clipKey: string) => void;
}

const CSS = `
  .alert-card { animation:slide-in-r .2s ease-out; background:rgba(239,68,68,.05); border-left:2px solid rgba(239,68,68,.35); border-radius:0 5px 5px 0; padding:10px 12px; margin-bottom:6px; }
  @keyframes slide-in-r { from { opacity:0; transform:translateX(8px); } to { opacity:1; transform:translateX(0); } }
  .alert-top { display:flex; align-items:baseline; justify-content:space-between; gap:8px; }
  .alert-type { display:flex; align-items:center; gap:5px; min-width:0; }
  .alert-icon { font-size:10px; color:var(--red); flex-shrink:0; }
  .alert-event { font-size:11px; font-weight:600; color:rgba(248,113,113,.85); letter-spacing:.03em; overflow:hidden; text-overflow:ellipsis; white-space:nowrap; }
  .alert-time { font-size:10px; color:var(--text3); font-family:monospace; flex-shrink:0; }
  .alert-meta { margin-top:3px; font-size:10px; color:rgba(255,255,255,.3); font-family:monospace; }
  .alert-detail { margin-top:4px; font-size:10px; display:flex; align-items:center; gap:5px; }
  .alert-detail.fire { color:rgba(248,113,113,.75); }
  .alert-detail.smoke { color:rgba(255,255,255,.35); }
  .alert-detail.ppe { color:rgba(255,255,255,.4); }
  .alert-detail.zone { color:rgba(250,204,21,.85); }
  .alert-ping { width:6px; height:6px; border-radius:50%; flex-shrink:0; }
  .alert-ping.fire { background:var(--red-dim); animation:breathe-fast 1s ease-in-out infinite; }
  .alert-ping.smoke { background:var(--text3); }
  .alert-ping.zone { background:rgba(250,204,21,.5); animation:breathe-fast 1.5s ease-in-out infinite; }
  @keyframes breathe-fast { 0%,100%{opacity:1} 50%{opacity:.2} }
  .alert-clip-btn { margin-top:6px; font-size:10px; color:rgba(248,113,113,.5); background:none; border:none; cursor:pointer; display:flex; align-items:center; gap:4px; padding:0; font-family:inherit; transition:color .15s; }
  .alert-clip-btn:hover { color:rgba(248,113,113,.85); }
`;

function elapsed(tsMs: number): string {
  const diffS = Math.floor((Date.now() - tsMs) / 1000);
  if (diffS < 60) return `${diffS}s ago`;
  const m = Math.floor(diffS / 60);
  const s = diffS % 60;
  return `${m}:${String(s).padStart(2, "0")} ago`;
}

function parseMissingPpe(raw: string | null): string {
  if (!raw) return "";
  try {
    const parsed = JSON.parse(raw.replace(/'/g, '"'));
    if (Array.isArray(parsed)) return parsed.join(", ");
    return String(parsed);
  } catch {
    return raw;
  }
}

export default function AlertCard({ event, onPlayClip }: AlertCardProps) {
  const missing = parseMissingPpe(event.missing_ppe);

  return (
    <>
      <style>{CSS}</style>
      <div className="alert-card">
        <div className="alert-top">
          <div className="alert-type">
            <span className="alert-icon">⚠</span>
            <span className="alert-event">{event.event_type}</span>
          </div>
          <span className="alert-time">{elapsed(event.event_ts_ms)}</span>
        </div>

        <div className="alert-meta">
          {[event.source_id, event.zone_id].filter(Boolean).join(" · ")}
        </div>

        {event.event_type === "PPE_VIOLATION" && missing && (
          <div className="alert-detail ppe">Missing: {missing}</div>
        )}

        {event.event_type === "FIRE_DETECTED" && (
          <div className="alert-detail fire">
            <div className="alert-ping fire" />
            Active fire threat detected
          </div>
        )}

        {event.event_type === "SMOKE_DETECTED" && (
          <div className="alert-detail smoke">
            <div className="alert-ping smoke" />
            Smoke detected
          </div>
        )}

        {event.event_type === "ZONE_ENTER" && (
          <div className="alert-detail zone">
            <div className="alert-ping zone" />
            Unauthorized Zone Intrusion
          </div>
        )}

        {event.clip_key && (
          <button
            className="alert-clip-btn"
            onClick={() => onPlayClip(event.clip_key!)}
          >
            ▶ Watch clip
          </button>
        )}
      </div>
    </>
  );
}
