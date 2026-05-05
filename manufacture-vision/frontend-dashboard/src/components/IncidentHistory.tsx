"use client";

import { useEffect, useState } from "react";
import { apiFetch } from "@/lib/api";
import { EventListOut, EventOut } from "@/types";
import VideoModal from "./VideoModal";

interface IncidentHistoryProps {
  token: string;
  initialEvents: EventOut[];
}

const PAGE_SIZE = 20;

const RANGES: Record<string, number> = {
  "1h": 1 * 3600 * 1000,
  "6h": 6 * 3600 * 1000,
  "24h": 24 * 3600 * 1000,
  "7d": 7 * 24 * 3600 * 1000,
};

const CSS = `
  .inc-log { flex-shrink:0; background:var(--s1); border-top:1px solid var(--border); display:flex; flex-direction:column; max-height:226px; }
  .inc-head { display:flex; align-items:center; justify-content:space-between; padding:6px 14px; border-bottom:1px solid var(--border); flex-shrink:0; gap:12px; }
  .inc-title { font-size:9px; font-weight:700; letter-spacing:.14em; text-transform:uppercase; color:rgba(255,255,255,.22); white-space:nowrap; }
  .inc-filters { display:flex; align-items:center; gap:5px; margin-left:auto; }
  .inc-sel { background:var(--s2); border:1px solid var(--border); color:rgba(255,255,255,.35); font-size:10px; font-family:inherit; border-radius:4px; padding:2px 7px; outline:none; cursor:pointer; transition:border-color .15s; appearance:none; -webkit-appearance:none; }
  .inc-sel:focus { border-color:var(--border2); }
  .inc-body { overflow-y:auto; flex:1; min-height:0; }
  .inc-table { width:100%; border-collapse:collapse; }
  .inc-table th { text-align:left; font-size:9px; font-weight:500; letter-spacing:.1em; text-transform:uppercase; color:rgba(255,255,255,.18); padding:5px 14px; border-bottom:1px solid var(--border); position:sticky; top:0; background:var(--s1); z-index:1; white-space:nowrap; }
  .inc-table td { padding:5px 14px; font-size:11px; color:rgba(255,255,255,.42); border-bottom:1px solid rgba(255,255,255,.03); white-space:nowrap; }
  .inc-table tr:hover td { background:rgba(255,255,255,.018); }
  .inc-mono { font-family:monospace; }
  .inc-pill { font-size:9px; font-weight:700; letter-spacing:.05em; padding:1px 6px; border-radius:3px; display:inline-block; }
  .inc-pill.ppe { background:rgba(59,130,246,.08); color:rgba(96,165,250,.8); border:1px solid rgba(59,130,246,.18); }
  .inc-pill.fire { background:rgba(239,68,68,.1); color:rgba(248,113,113,.85); border:1px solid rgba(239,68,68,.2); }
  .inc-pill.smoke { background:rgba(107,114,128,.08); color:rgba(156,163,175,.7); border:1px solid rgba(107,114,128,.18); }
  .inc-pill.zone { background:rgba(250,204,21,.1); color:rgba(250,204,21,.85); border:1px solid rgba(250,204,21,.2); }
  .inc-clip-btn { background:none; border:none; color:rgba(255,255,255,.22); font-size:13px; cursor:pointer; padding:0 3px; line-height:1; transition:color .15s; }
  .inc-clip-btn:hover { color:rgba(255,255,255,.6); }
  .inc-foot { display:flex; align-items:center; justify-content:space-between; padding:5px 16px; border-top:1px solid var(--border); flex-shrink:0; }
  .inc-count { font-size:10px; color:rgba(255,255,255,.18); font-family:monospace; }
  .inc-pg { display:flex; align-items:center; gap:10px; }
  .inc-pg-btn { background:none; border:none; color:rgba(255,255,255,.22); font-size:13px; cursor:pointer; padding:0 2px; line-height:1; transition:color .15s; font-family:inherit; }
  .inc-pg-btn:hover:not(:disabled) { color:rgba(255,255,255,.55); }
  .inc-pg-btn:disabled { opacity:.2; cursor:default; }
  .inc-pg-info { font-size:10px; color:rgba(255,255,255,.18); font-family:monospace; }
  .inc-loading { text-align:center; color:var(--text3); padding:20px; font-size:11px; }
  .inc-empty { text-align:center; color:var(--text3); padding:20px; font-size:11px; }
`;

function formatTime(tsMs: number): string {
  return new Date(tsMs).toLocaleTimeString("en-GB", {
    hour: "2-digit", minute: "2-digit", second: "2-digit",
  });
}

function parseMissingPpe(raw: string | null): string {
  if (!raw) return "—";
  try {
    const parsed = JSON.parse(raw.replace(/'/g, '"'));
    if (Array.isArray(parsed)) return parsed.join(", ");
    return String(parsed);
  } catch {
    return raw;
  }
}

function eventPillCls(evType: string) {
  if (evType === "PPE_VIOLATION") return "inc-pill ppe";
  if (evType === "FIRE_DETECTED") return "inc-pill fire";
  if (evType === "SMOKE_DETECTED") return "inc-pill smoke";
  if (evType === "ZONE_ENTER") return "inc-pill zone";
  return "inc-pill smoke";
}

function eventLabel(evType: string) {
  if (evType === "PPE_VIOLATION") return "PPE";
  if (evType === "FIRE_DETECTED") return "FIRE";
  if (evType === "SMOKE_DETECTED") return "SMOKE";
  if (evType === "ZONE_ENTER") return "INTRUSION";
  return evType;
}

export default function IncidentHistory({ token, initialEvents }: IncidentHistoryProps) {
  const [events, setEvents] = useState<EventOut[]>(initialEvents);
  const [total, setTotal] = useState(initialEvents.length);
  const [page, setPage] = useState(0);
  const [filterZone, setFilterZone] = useState("");
  const [filterType, setFilterType] = useState("");
  const [filterRange, setFilterRange] = useState("24h");
  const [loading, setLoading] = useState(false);
  const [selectedClipKey, setSelectedClipKey] = useState<string | null>(null);

  const zones = Array.from(
    new Set(initialEvents.map((e) => e.zone_id).filter(Boolean) as string[])
  );

  useEffect(() => {
    const from_ts = Date.now() - RANGES[filterRange];
    const params = new URLSearchParams({
      limit: String(PAGE_SIZE),
      offset: String(page * PAGE_SIZE),
      from_ts: String(from_ts),
    });
    if (filterZone) params.set("zone_id", filterZone);
    if (filterType) params.set("event_type", filterType);

    setLoading(true);
    apiFetch<EventListOut>(`/events?${params}`, token)
      .then((data) => { setEvents(data.items); setTotal(data.total); })
      .catch(() => {})
      .finally(() => setLoading(false));
  }, [token, filterZone, filterType, filterRange, page]);

  const totalPages = Math.max(1, Math.ceil(total / PAGE_SIZE));

  return (
    <>
      <style>{CSS}</style>
      <div className="inc-log">
        <div className="inc-head">
          <span className="inc-title">Incident History</span>
          <div className="inc-filters">
            {zones.length > 0 && (
              <select className="inc-sel" value={filterZone} onChange={(e) => { setFilterZone(e.target.value); setPage(0); }}>
                <option value="">All zones</option>
                {zones.map((z) => <option key={z} value={z}>{z}</option>)}
              </select>
            )}
            <select className="inc-sel" value={filterType} onChange={(e) => { setFilterType(e.target.value); setPage(0); }}>
              <option value="">All types</option>
              <option value="PPE_VIOLATION">PPE Violation</option>
              <option value="FIRE_DETECTED">Fire</option>
              <option value="SMOKE_DETECTED">Smoke</option>
            </select>
            <select className="inc-sel" value={filterRange} onChange={(e) => { setFilterRange(e.target.value); setPage(0); }}>
              {Object.keys(RANGES).map((r) => <option key={r} value={r}>{r}</option>)}
            </select>
          </div>
        </div>

        <div className="inc-body">
          <table className="inc-table">
            <thead>
              <tr>
                <th>Time</th>
                <th>Camera</th>
                <th>Zone</th>
                <th>Type</th>
                <th>Details</th>
                <th>Clip</th>
              </tr>
            </thead>
            <tbody>
              {loading && (
                <tr><td colSpan={6} className="inc-loading">Loading…</td></tr>
              )}
              {!loading && events.length === 0 && (
                <tr><td colSpan={6} className="inc-empty">No incidents found</td></tr>
              )}
              {!loading && events.map((ev) => (
                <tr key={ev.id}>
                  <td className="inc-mono">{formatTime(ev.event_ts_ms)}</td>
                  <td className="inc-mono" style={{ color: "rgba(255,255,255,.6)" }}>{ev.source_id ?? "—"}</td>
                  <td className="inc-mono">{ev.zone_id ?? "—"}</td>
                  <td>
                    <span className={eventPillCls(ev.event_type)}>{eventLabel(ev.event_type)}</span>
                  </td>
                  <td>{parseMissingPpe(ev.missing_ppe)}</td>
                  <td>
                    {ev.clip_key ? (
                      <button className="inc-clip-btn" onClick={() => setSelectedClipKey(ev.clip_key!)} title="Play clip">▶</button>
                    ) : (
                      <span style={{ color: "var(--text3)" }}>—</span>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        <div className="inc-foot">
          <span className="inc-count">{total} incident{total !== 1 ? "s" : ""}</span>
          <div className="inc-pg">
            <button className="inc-pg-btn" disabled={page === 0} onClick={() => setPage((p) => p - 1)}>←</button>
            <span className="inc-pg-info">{page + 1} / {totalPages}</span>
            <button className="inc-pg-btn" disabled={page >= totalPages - 1} onClick={() => setPage((p) => p + 1)}>→</button>
          </div>
        </div>
      </div>

      {selectedClipKey && (
        <VideoModal clipKey={selectedClipKey} token={token} onClose={() => setSelectedClipKey(null)} />
      )}
    </>
  );
}
