"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { clearToken } from "@/lib/token";
import { EventOut } from "@/types";
import { useSSE } from "@/hooks/useSSE";
import { triggerDemoReplay } from "@/lib/api";
import ZoneGrid from "./ZoneGrid";
import SystemStatus from "./SystemStatus";
import LiveAlertFeed from "./LiveAlertFeed";
import IncidentHistory from "./IncidentHistory";
import ConfigPanel from "./ConfigPanel";
import AnalyticsPanel from "./AnalyticsPanel";
import FactoryIcon from "./icons/FactoryIcon";

interface ConsoleLayoutProps {
  token: string;
  initialEvents: EventOut[];
}

const CSS = `
  .app { display:flex; flex-direction:column; height:100vh; background:var(--bg); color:var(--text); font-size:13px; line-height:1.5; }
  
  /* ── HEADER ── */
  .header { height:44px; background:var(--s1); border-bottom:1px solid var(--border); display:flex; align-items:center; padding:0 16px; gap:12px; flex-shrink:0; z-index:20; }
  .logo { display:flex; align-items:center; gap:7px; user-select:none; }
  .logo-icon { width:20px; height:20px; display:flex; align-items:center; justify-content:center; }
  .logo-name { font-size:13px; font-weight:600; color:var(--text); letter-spacing:-.02em; }
  .logo-badge { font-size:9px; color:rgba(255,255,255,.28); border:1px solid rgba(255,255,255,.1); border-radius:3px; padding:1px 6px; letter-spacing:.08em; text-transform:uppercase; }
  .live-pill { display:flex; align-items:center; gap:5px; padding:3px 8px; border-radius:4px; }
  .live-dot { width:5px; height:5px; border-radius:50%; }
  .live-text { font-size:10px; font-weight:500; letter-spacing:.08em; }
  .hdr-sep { flex:1; }
  .hdr-right { display:flex; align-items:center; gap:12px; }
  .vdiv { width:1px; height:14px; background:var(--border); }
  .hdr-stat { font-size:12px; color:var(--text3); display:flex; align-items:center; gap:5px; }
  .hdr-stat-val { font-family:monospace; font-weight:600; }
  .hdr-stat-val.crit { color:var(--red); }
  .hdr-stat-val.ok { color:var(--text3); }
  .hdr-btn { font-size:10px; color:var(--text3); background:none; border:1px solid var(--border); border-radius:4px; padding:3px 9px; cursor:pointer; transition:color .15s,border-color .15s; display:flex; align-items:center; gap:5px; font-family:inherit; letter-spacing:.04em; }
  .hdr-btn:hover { color:var(--text2); border-color:var(--border2); }
  .hdr-btn.active { color:var(--text); border-color:var(--border2); background:rgba(255,255,255,.04); }
  .demo-btn { font-size:10px; font-family:inherit; background:rgba(251,191,36,.07); border:1px solid rgba(251,191,36,.25); border-radius:4px; padding:3px 9px; cursor:pointer; color:var(--amber); display:flex; align-items:center; gap:5px; transition:background .15s,border-color .15s; letter-spacing:.04em; }
  .demo-btn:hover:not(:disabled) { background:rgba(251,191,36,.12); border-color:rgba(251,191,36,.4); }
  .demo-btn.loading { color:var(--text3); border-color:var(--border); background:none; cursor:wait; }
  .demo-btn.done { color:var(--green); border-color:rgba(74,222,128,.3); background:rgba(74,222,128,.06); }
  .spinner { width:9px; height:9px; border:1.5px solid rgba(255,255,255,.15); border-top-color:var(--amber); border-radius:50%; animation:spin 1s linear infinite; }
  @keyframes spin { to { transform:rotate(360deg); } }
  .logout-btn { font-size:11px; color:var(--text3); background:none; border:1px solid var(--border); border-radius:4px; padding:3px 9px; cursor:pointer; transition:color .15s,border-color .15s; font-family:inherit; }
  .logout-btn:hover { color:var(--text2); border-color:var(--border2); }

  /* ── BODY ── */
  .below-hdr { flex:1; display:flex; flex-direction:column; overflow:hidden; }
  .content { display:flex; flex:1; overflow:hidden; }

  /* ── SIDEBAR ── */
  .sidebar { width:252px; flex-shrink:0; background:var(--s1); border-right:1px solid var(--border); display:flex; flex-direction:column; overflow-y:auto; }

  /* ── MAIN ── */
  .main-area { flex:1; overflow:hidden; background:#080808; display:flex; flex-direction:column; }

  /* ── SLIDE-UP OVERLAY ── */
  .overlay-panel { position:fixed; bottom:0; left:0; right:0; z-index:50; min-height:45vh; max-height:65vh; overflow-y:auto; background:var(--s1); border-top:1px solid var(--border); box-shadow:0 -8px 32px rgba(0,0,0,.6); }
`;

export default function ConsoleLayout({ token, initialEvents }: ConsoleLayoutProps) {
  const router = useRouter();
  const [showConfig, setShowConfig] = useState(false);
  const [showAnalytics, setShowAnalytics] = useState(false);
  const [demoState, setDemoState] = useState<"idle" | "loading" | "done">("idle");
  const { events: liveEvents, connected } = useSSE(token);

  // Merge live (SSE) + historical (DB load), dedup by ID so a refresh doesn't
  // blank the feed when the DB was cleared by a Demo replay.
  const seen = new Set<string>();
  const allEvents = [...liveEvents, ...initialEvents].filter((e) => {
    if (seen.has(e.id)) return false;
    seen.add(e.id);
    return true;
  });

  const todayStart = new Date();
  todayStart.setHours(0, 0, 0, 0);
  const todayCount = allEvents.filter((e) => e.event_ts_ms >= todayStart.getTime()).length;

  function handleLogout() {
    clearToken();
    router.replace("/login");
  }

  async function handleDemoReplay() {
    if (demoState === "loading") return;
    setDemoState("loading");
    try {
      await triggerDemoReplay(token, "all");
      setDemoState("done");
      setTimeout(() => setDemoState("idle"), 2500);
    } catch {
      setDemoState("idle");
    }
  }

  // Live pill styles
  const liveColor = connected ? "rgba(74,222,128,.07)" : "rgba(239,68,68,.07)";
  const liveBorder = connected ? "rgba(74,222,128,.15)" : "rgba(239,68,68,.15)";
  const liveDotColor = connected ? "var(--green)" : "var(--red)";
  const liveText = connected ? "LIVE" : "OFFLINE";
  const liveTextColor = connected ? "var(--green)" : "var(--red)";

  return (
    <>
      <style>{CSS}</style>
      <div className="app">

        {/* HEADER */}
        <header className="header">
          <div className="logo">
            <div className="logo-icon">
              <FactoryIcon size={12} color="var(--amber)" />
            </div>
            <span className="logo-name">Manufacture Vision</span>
            <span className="logo-badge">Console</span>
          </div>

          <div className="live-pill" style={{ background: liveColor, border: `1px solid ${liveBorder}` }}>
            <div className="live-dot" style={{ background: liveDotColor, animation: connected ? "breathe 2s ease-in-out infinite" : "none" }} />
            <span className="live-text" style={{ color: liveTextColor }}>{liveText}</span>
          </div>

          <div className="hdr-sep" />

          <div className="hdr-right">
            {todayCount > 0 && (
              <div className="hdr-stat">
                <span className={`hdr-stat-val ${todayCount > 0 ? "crit" : "ok"}`}>{todayCount}</span>
                today
              </div>
            )}

            <div className="vdiv" />

            <button
              className={`hdr-btn${showAnalytics ? " active" : ""}`}
              onClick={() => setShowAnalytics((v) => !v)}
              title="Analytics"
            >
              <svg width="11" height="11" viewBox="0 0 16 16" fill="currentColor">
                <rect x="1" y="9" width="3" height="6" rx="0.5"/>
                <rect x="6" y="5" width="3" height="10" rx="0.5"/>
                <rect x="11" y="1" width="3" height="14" rx="0.5"/>
              </svg>
              Analytics
            </button>

            <button
              className={`hdr-btn${showConfig ? " active" : ""}`}
              onClick={() => setShowConfig((v) => !v)}
              title="Configure zones & policies"
            >
              <svg width="11" height="11" viewBox="0 0 16 16" fill="currentColor">
                <path d="M8 10.5a2.5 2.5 0 1 0 0-5 2.5 2.5 0 0 0 0 5Z"/>
                <path fillRule="evenodd" d="M6.43 1.5a1.75 1.75 0 0 0-1.674 1.244l-.194.632a.75.75 0 0 1-.476.495l-.6.196a.75.75 0 0 1-.708-.126l-.5-.416A1.75 1.75 0 0 0 .03 5.7l.416.5a.75.75 0 0 1 .126.708l-.196.6a.75.75 0 0 1-.495.476l-.632.194A1.75 1.75 0 0 0 .5 9.57l.632.194a.75.75 0 0 1 .495.476l.196.6a.75.75 0 0 1-.126.708l-.416.5a1.75 1.75 0 0 0 2.248 2.248l.5-.416a.75.75 0 0 1 .708-.126l.6.196a.75.75 0 0 1 .476.495l.194.632A1.75 1.75 0 0 0 6.43 14.5h3.14a1.75 1.75 0 0 0 1.674-1.244l.194-.632a.75.75 0 0 1 .476-.495l.6-.196a.75.75 0 0 1 .708.126l.5.416a1.75 1.75 0 0 0 2.248-2.248l-.416-.5a.75.75 0 0 1-.126-.708l.196-.6a.75.75 0 0 1 .495-.476l.632-.194A1.75 1.75 0 0 0 15.5 6.43v-.86a1.75 1.75 0 0 0-1.245-1.674l-.632-.194a.75.75 0 0 1-.495-.476l-.196-.6a.75.75 0 0 1 .126-.708l.416-.5A1.75 1.75 0 0 0 11.226 0l-.5.416a.75.75 0 0 1-.708.126l-.6-.196a.75.75 0 0 1-.476-.495L8.748.219A1.75 1.75 0 0 0 6.43 1.5Zm1.57 2a4.5 4.5 0 1 0 0 9 4.5 4.5 0 0 0 0-9Z" clipRule="evenodd"/>
              </svg>
              Configure
            </button>

            <div className="vdiv" />

            <button
              className={`demo-btn${demoState === "loading" ? " loading" : demoState === "done" ? " done" : ""}`}
              onClick={handleDemoReplay}
              disabled={demoState === "loading"}
              title="Reset and replay all demo videos"
            >
              {demoState === "loading" ? (
                <><div className="spinner" /> Replaying…</>
              ) : demoState === "done" ? (
                <>✓ Replaying!</>
              ) : (
                <>
                  <svg width="9" height="9" viewBox="0 0 12 12" fill="currentColor">
                    <path d="M2 1.5v9l8-4.5-8-4.5z"/>
                  </svg>
                  Demo
                </>
              )}
            </button>

            <div className="vdiv" />

            <button className="logout-btn" onClick={handleLogout}>
              Sign out
            </button>
          </div>
        </header>

        {/* BODY */}
        <div className="below-hdr">
          <div className="content">
            {/* SIDEBAR */}
            <aside className="sidebar">
              <ZoneGrid events={allEvents} />
              <SystemStatus sseConnected={connected} />
            </aside>

            {/* MAIN — live alert feed */}
            <main className="main-area">
              <LiveAlertFeed events={allEvents} token={token} connected={connected} />
            </main>
          </div>

          {/* INCIDENT HISTORY — bottom panel */}
          <IncidentHistory token={token} initialEvents={initialEvents} />
        </div>

        {/* OVERLAY panels */}
        {(showAnalytics || showConfig) && (
          <div className="overlay-panel">
            {showAnalytics && <AnalyticsPanel token={token} />}
            {showConfig && <ConfigPanel token={token} />}
          </div>
        )}
      </div>
    </>
  );
}
