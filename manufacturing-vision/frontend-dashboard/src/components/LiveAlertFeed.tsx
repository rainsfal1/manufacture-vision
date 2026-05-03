"use client";

import { useState } from "react";
import { EventOut } from "@/types";
import AlertCard from "./AlertCard";
import VideoModal from "./VideoModal";

interface LiveAlertFeedProps {
  events: EventOut[];
  token: string;
  connected: boolean;
}

const CSS = `
  .feed-wrap { display:flex; flex-direction:column; height:100%; background:#080808; }
  .feed-hdr { display:flex; align-items:center; justify-content:space-between; padding:10px 14px 8px; border-bottom:1px solid var(--border); flex-shrink:0; }
  .feed-title { font-size:9px; font-weight:700; letter-spacing:.14em; text-transform:uppercase; color:rgba(255,255,255,.22); }
  .feed-hdr-right { display:flex; align-items:center; gap:8px; }
  .feed-count { font-size:9px; font-weight:700; padding:1px 6px; border-radius:3px; background:rgba(239,68,68,.1); color:rgba(248,113,113,.85); border:1px solid rgba(239,68,68,.2); font-family:monospace; }
  .feed-dot { width:5px; height:5px; border-radius:50%; }
  .feed-dot.live { background:var(--green); animation:breathe 2s ease-in-out infinite; }
  @keyframes breathe { 0%,100%{opacity:1} 50%{opacity:.4} }
  .feed-dot.offline { background:var(--text3); }
  .feed-body { flex:1; overflow-y:auto; padding:10px 14px 14px; }
  .feed-empty { display:flex; flex-direction:column; align-items:center; justify-content:center; height:100%; gap:8px; color:var(--text3); }
  .feed-empty-icon { font-size:22px; opacity:.3; }
  .feed-empty-text { font-size:12px; color:rgba(255,255,255,.2); }
  .feed-empty-sub { font-size:10px; color:var(--text3); }
`;

export default function LiveAlertFeed({ events, token, connected }: LiveAlertFeedProps) {
  const [selectedClipKey, setSelectedClipKey] = useState<string | null>(null);

  const incidents = events.filter((ev) =>
    ["PPE_VIOLATION", "FIRE_DETECTED", "SMOKE_DETECTED", "ZONE_ENTER"].includes(ev.event_type)
  );

  return (
    <>
      <style>{CSS}</style>
      <div className="feed-wrap">
        <div className="feed-hdr">
          <span className="feed-title">Live Alerts</span>
          <div className="feed-hdr-right">
            {incidents.length > 0 && (
              <span className="feed-count">{incidents.length}</span>
            )}
            <div className={`feed-dot ${connected ? "live" : "offline"}`} />
          </div>
        </div>

        <div className="feed-body">
          {incidents.length === 0 ? (
            <div className="feed-empty">
              <span className="feed-empty-icon">✓</span>
              <span className="feed-empty-text">No violations or incidents detected</span>
              {!connected && (
                <span className="feed-empty-sub">Connecting to stream…</span>
              )}
            </div>
          ) : (
            incidents.map((ev) => (
              <AlertCard key={ev.id} event={ev} onPlayClip={setSelectedClipKey} />
            ))
          )}
        </div>
      </div>

      {selectedClipKey && (
        <VideoModal
          clipKey={selectedClipKey}
          token={token}
          onClose={() => setSelectedClipKey(null)}
        />
      )}
    </>
  );
}
