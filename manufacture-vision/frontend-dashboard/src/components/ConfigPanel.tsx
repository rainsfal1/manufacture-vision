"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import {
  activatePolicy,
  createChannel,
  createPolicy,
  createRule,
  createZone,
  deactivatePolicy,
  deleteChannel,
  deletePolicy,
  deleteRule,
  deleteZone,
  getChannels,
  getPolicies,
  getRules,
  getZones,
  testChannel,
  toggleChannel,
  toggleRule,
  updateZone,
} from "@/lib/api";
import { ChannelOut, PolicyOut, RuleOut, ZoneOut } from "@/types";
import ZoneEditorModal from "./ZoneEditorModal";
import { CAMERA_CONFIGS, CAMERA_MAP, DUTY_LABELS } from "@/lib/cameraConfig";

interface ConfigPanelProps {
  token: string;
}

type Tab = "zones" | "policies" | "notifications";

const CSS = `
  .cfg-panel { display:flex; flex-direction:column; height:100%; }
  .cfg-header { display:flex; align-items:center; gap:0; padding:0 16px; border-bottom:1px solid var(--border); flex-shrink:0; }
  .cfg-label { font-size:9px; font-weight:700; letter-spacing:.14em; text-transform:uppercase; color:rgba(255,255,255,.25); padding:12px 16px 12px 0; border-right:1px solid var(--border); margin-right:4px; }
  .cfg-tab { font-size:11px; padding:12px 12px 10px; border-bottom:2px solid transparent; color:var(--text3); background:none; cursor:pointer; transition:color .15s,border-color .15s; letter-spacing:.02em; }
  .cfg-tab:hover { color:var(--text2); }
  .cfg-tab.active { border-bottom-color:var(--amber); color:var(--text); }
  .cfg-body { padding:16px; overflow-y:auto; }

  /* section headers */
  .sec-hdr { display:flex; align-items:center; justify-content:space-between; margin-bottom:10px; }
  .sec-label { font-size:9px; font-weight:700; letter-spacing:.14em; text-transform:uppercase; color:rgba(255,255,255,.25); }
  .sec-count { font-size:9px; font-family:monospace; color:rgba(255,255,255,.18); letter-spacing:.04em; }

  /* action buttons */
  .act-btn { font-size:10px; font-family:inherit; background:none; border:1px solid var(--border); border-radius:4px; padding:3px 9px; cursor:pointer; color:var(--text3); transition:color .15s,border-color .15s; letter-spacing:.04em; }
  .act-btn:hover { color:var(--text2); border-color:var(--border2); }
  .act-btn.primary { background:rgba(255,255,255,.04); color:var(--text); border-color:var(--border2); }
  .act-btn.primary:hover { background:rgba(255,255,255,.07); }
  .act-btn.danger:hover { color:var(--red); border-color:rgba(239,68,68,.3); }

  /* camera assign list */
  .cam-list { display:flex; flex-direction:column; margin-bottom:16px; border:1px solid rgba(255,255,255,.05); border-radius:7px; overflow:hidden; }
  .cam-row { display:flex; align-items:center; gap:10px; padding:9px 12px; border-bottom:1px solid rgba(255,255,255,.04); }
  .cam-row:last-child { border-bottom:none; }
  .cam-row-id { font-size:11px; font-weight:700; font-family:monospace; color:var(--text); letter-spacing:-.01em; min-width:50px; flex-shrink:0; }
  .cam-row-badges { display:flex; gap:3px; flex-shrink:0; }
  .cam-row-desc { font-size:10px; color:rgba(255,255,255,.28); flex:1; }
  .cam-zone-req { font-size:9px; color:rgba(139,92,246,.55); }

  .duty-badge { font-size:8px; font-weight:700; letter-spacing:.06em; text-transform:uppercase; padding:1px 5px; border-radius:3px; display:inline-block; }
  .duty-badge.ppe { background:rgba(59,130,246,.08); color:rgba(96,165,250,.7); border:1px solid rgba(59,130,246,.18); }
  .duty-badge.fire { background:rgba(239,68,68,.08); color:rgba(248,113,113,.7); border:1px solid rgba(239,68,68,.18); }
  .duty-badge.zone { background:rgba(34,211,238,.06); color:rgba(34,211,238,.65); border:1px solid rgba(34,211,238,.16); }

  /* zone rule */
  .sec-rule { height:1px; background:linear-gradient(90deg,var(--border) 60%,transparent); margin:0 0 14px; }

  /* table */
  .cfg-table { width:100%; border-collapse:collapse; font-size:11px; }
  .cfg-table th { text-align:left; font-size:9px; font-weight:600; letter-spacing:.08em; text-transform:uppercase; color:rgba(255,255,255,.22); padding:6px 8px; border-bottom:1px solid var(--border); }
  .cfg-table td { padding:7px 8px; border-bottom:1px solid rgba(255,255,255,.04); vertical-align:middle; }
  .cfg-table tr:hover td { background:rgba(255,255,255,.015); }
  .cfg-table .mono { font-family:monospace; color:var(--text); letter-spacing:-.01em; }
  .cfg-table .dim { color:var(--text3); }
  .cfg-table .val { color:var(--text2); }

  /* inline form */
  .form-row { display:flex; flex-wrap:wrap; align-items:center; gap:6px; padding:8px 10px; background:rgba(255,255,255,.02); border:1px solid var(--border); border-radius:6px; margin-bottom:10px; }
  .cfg-input { background:rgba(255,255,255,.04); border:1px solid var(--border); color:var(--text); font-size:11px; font-family:monospace; border-radius:4px; padding:4px 8px; outline:none; transition:border-color .15s; }
  .cfg-input:focus { border-color:var(--border2); }
  .cfg-input::placeholder { color:rgba(255,255,255,.2); }
  .cfg-input.w-28 { width:7rem; }
  .cfg-input.w-36 { width:9rem; }
  .cfg-input.w-40 { width:10rem; }
  .cfg-input.w-48 { width:12rem; }
  .cfg-input.flex-1 { flex:1; min-width:12rem; }

  /* toggle */
  .toggle { position:relative; width:28px; height:15px; border-radius:8px; border:none; cursor:pointer; transition:background .2s; flex-shrink:0; }
  .toggle.on { background:rgba(74,222,128,.2); }
  .toggle.off { background:rgba(255,255,255,.08); }
  .toggle-dot { position:absolute; top:2px; width:11px; height:11px; border-radius:50%; transition:left .2s; }
  .toggle.on .toggle-dot { left:15px; background:var(--green); }
  .toggle.off .toggle-dot { left:2px; background:rgba(255,255,255,.3); }

  /* type badge */
  .type-badge { font-size:9px; font-weight:600; letter-spacing:.06em; text-transform:uppercase; padding:2px 6px; border-radius:3px; }
  .type-badge.slack { background:rgba(74,222,128,.07); color:rgba(74,222,128,.8); border:1px solid rgba(74,222,128,.15); }
  .type-badge.webhook { background:rgba(59,130,246,.07); color:rgba(96,165,250,.8); border:1px solid rgba(59,130,246,.15); }
  .type-badge.email { background:rgba(255,255,255,.04); color:var(--text3); border:1px solid var(--border); }

  /* empty state */
  .empty-state { text-align:center; padding:28px 16px; color:var(--text3); font-size:11px; }
  .empty-icon { font-size:22px; opacity:.2; margin-bottom:6px; }

  /* error */
  .cfg-error { font-size:11px; color:var(--red); margin-bottom:8px; padding:6px 10px; background:rgba(239,68,68,.06); border:1px solid rgba(239,68,68,.15); border-radius:4px; }

  /* draw zone button */
  .draw-btn { font-size:10px; font-family:inherit; background:rgba(34,211,238,.06); border:1px solid rgba(34,211,238,.18); color:rgba(34,211,238,.75); border-radius:4px; padding:3px 9px; cursor:pointer; transition:background .15s,border-color .15s; white-space:nowrap; }
  .draw-btn:hover { background:rgba(34,211,238,.1); border-color:rgba(34,211,238,.3); }
  .draw-btn:disabled { opacity:.35; cursor:not-allowed; }
  .draw-btn.done { color:rgba(74,222,128,.8); border-color:rgba(74,222,128,.2); background:rgba(74,222,128,.05); }

  /* polygon json link */
  .poly-json { font-size:9px; color:var(--text3); font-family:monospace; cursor:pointer; text-decoration:underline; text-underline-offset:2px; }
  .poly-json:hover { color:var(--text2); }
`;

const inputCls = "cfg-input";

// ─── Zones tab ──────────────────────────────────────────────────────────────

interface ZoneFormState {
  zone_id: string;
  camera_id: string;
  required_ppe: string;
  polygon: string;
}

const emptyZoneForm: ZoneFormState = {
  zone_id: "",
  camera_id: "",
  required_ppe: "",
  polygon: "",
};

function ZonesTab({ token }: { token: string }) {
  const [zones, setZones] = useState<ZoneOut[]>([]);
  const [loading, setLoading] = useState(true);
  const [editing, setEditing] = useState<string | null>(null);
  const [adding, setAdding] = useState(false);
  const [form, setForm] = useState<ZoneFormState>(emptyZoneForm);
  const [error, setError] = useState<string | null>(null);
  const [showEditor, setShowEditor] = useState(false);
  const [polygonPreview, setPolygonPreview] = useState<string>("");
  const [quickCamId, setQuickCamId] = useState<string | null>(null);

  const reload = useCallback(() => {
    setLoading(true);
    getZones(token)
      .then(setZones)
      .catch(() => setError("Failed to load zones"))
      .finally(() => setLoading(false));
  }, [token]);

  useEffect(() => { reload(); }, [reload]);

  function startEdit(z: ZoneOut) {
    setEditing(z.zone_id);
    setAdding(false);
    const poly = z.polygon ? JSON.stringify(z.polygon) : "";
    setForm({
      zone_id: z.zone_id,
      camera_id: z.camera_id ?? "",
      required_ppe: z.required_ppe?.join(", ") ?? "",
      polygon: poly,
    });
    setPolygonPreview(z.polygon ? `${z.polygon.length} pts` : "");
  }

  function startAdd() {
    setAdding(true);
    setEditing(null);
    setForm(emptyZoneForm);
    setPolygonPreview("");
  }

  function cancel() {
    setAdding(false);
    setEditing(null);
    setForm(emptyZoneForm);
    setPolygonPreview("");
    setError(null);
  }

  function parseForm() {
    const ppe = form.required_ppe
      ? form.required_ppe.split(",").map((s) => s.trim()).filter(Boolean)
      : null;
    let polygon = null;
    if (form.polygon.trim()) {
      try { polygon = JSON.parse(form.polygon); } catch { throw new Error("Polygon must be valid JSON"); }
    }
    return { zone_id: form.zone_id, camera_id: form.camera_id || null, required_ppe: ppe, polygon };
  }

  async function handleSave() {
    setError(null);
    try {
      const body = parseForm();
      if (editing) {
        await updateZone(token, editing, body);
      } else {
        await createZone(token, body);
      }
      cancel();
      reload();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Save failed");
    }
  }

  async function handleDelete(zoneId: string) {
    if (!window.confirm(`Delete zone "${zoneId}"?`)) return;
    try {
      await deleteZone(token, zoneId);
      reload();
    } catch {
      setError("Delete failed");
    }
  }

  async function handleQuickZoneSave(poly: [number, number][]) {
    const camId = quickCamId!;
    const existing = zones.find((z) => z.camera_id === camId);
    try {
      if (existing) {
        // ZoneIn requires zone_id — include all fields the PUT endpoint needs
        await updateZone(token, existing.zone_id, {
          zone_id: existing.zone_id,
          camera_id: existing.camera_id ?? null,
          required_ppe: existing.required_ppe ?? null,
          polygon: poly,
        });
      } else {
        await createZone(token, {
          zone_id: camId.replace("camera-", "zone-"),
          camera_id: camId,
          required_ppe: null,
          polygon: poly,
        });
      }
      reload();
    } catch {
      setError("Failed to save zone polygon");
    } finally {
      setQuickCamId(null);
    }
  }

  const renderFormRow = () => (
    <tr style={{ background: "rgba(255,255,255,.02)" }}>
      <td className="px-2 py-1.5">
        <input
          className={`${inputCls} w-28`}
          placeholder="zone_id"
          value={form.zone_id}
          onChange={(e) => setForm({ ...form, zone_id: e.target.value })}
          disabled={!!editing}
        />
      </td>
      <td className="px-2 py-1.5">
        <input
          className={`${inputCls} w-28`}
          placeholder="camera-01"
          value={form.camera_id}
          onChange={(e) => setForm({ ...form, camera_id: e.target.value })}
        />
      </td>
      <td className="px-2 py-1.5">
        <input
          className={`${inputCls} w-36`}
          placeholder="helmet, vest"
          value={form.required_ppe}
          onChange={(e) => setForm({ ...form, required_ppe: e.target.value })}
        />
      </td>
      <td className="px-2 py-1.5">
        <div style={{ display: "flex", alignItems: "center", gap: "6px" }}>
          <button
            type="button"
            onClick={() => setShowEditor(true)}
            disabled={!form.camera_id}
            className={`draw-btn${polygonPreview ? " done" : ""}`}
            title={form.camera_id ? "Open visual editor" : "Enter a camera ID first"}
          >
            {polygonPreview ? `✓ ${polygonPreview}` : "Draw zone"}
          </button>
          {form.polygon && (
            <span
              className="poly-json"
              title={form.polygon}
              onClick={() => {
                const raw = window.prompt("Edit polygon JSON:", form.polygon);
                if (raw !== null) {
                  setForm({ ...form, polygon: raw });
                  try { const p = JSON.parse(raw); setPolygonPreview(`${p.length} pts`); } catch { setPolygonPreview(""); }
                }
              }}
            >
              JSON
            </span>
          )}
        </div>
      </td>
      <td className="px-2 py-1.5" style={{ whiteSpace: "nowrap" }}>
        <button onClick={handleSave} className="act-btn primary" style={{ marginRight: "4px" }}>Save</button>
        <button onClick={cancel} className="act-btn">Cancel</button>
      </td>
    </tr>
  );

  return (
    <div>
      {/* Camera duty list */}
      <div className="sec-hdr">
        <span className="sec-label">Camera assignments</span>
      </div>
      <div className="cam-list">
        {CAMERA_CONFIGS.map((cam) => {
          const existingZone = zones.find((z) => z.camera_id === cam.sourceId);
          const hasPolygon = !!existingZone?.polygon;
          return (
            <div key={cam.sourceId} className="cam-row">
              <span className="cam-row-id">{cam.label}</span>
              <div className="cam-row-badges">
                {cam.duties.map((duty) => {
                  const meta = DUTY_LABELS[duty];
                  const cls = duty === "ppe-compliance" ? "ppe" : duty === "fire-smoke" ? "fire" : "zone";
                  return <span key={duty} className={`duty-badge ${cls}`}>{meta.label}</span>;
                })}
              </div>
              <span className="cam-row-desc">{cam.description}</span>
              {cam.requiresZone && (
                <button
                  className={`draw-btn${hasPolygon ? " done" : ""}`}
                  onClick={() => setQuickCamId(cam.sourceId)}
                >
                  {hasPolygon ? `✓ ${existingZone!.polygon!.length} pts` : "Draw zone"}
                </button>
              )}
            </div>
          );
        })}
      </div>

      <div className="sec-rule" />

      {/* Zone table header */}
      <div className="sec-hdr">
        <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
          <span className="sec-label">Zones</span>
          <span className="sec-count">· {zones.length}</span>
        </div>
        {!adding && !editing && (
          <button onClick={startAdd} className="act-btn">+ Add zone</button>
        )}
      </div>

      {error && <div className="cfg-error">{error}</div>}

      <div style={{ overflowX: "auto" }}>
        <table className="cfg-table">
          <thead>
            <tr>
              <th>Zone ID</th>
              <th>Camera</th>
              <th>Required PPE</th>
              <th>Polygon</th>
              <th style={{ width: "7rem" }} />
            </tr>
          </thead>
          <tbody>
            {adding && renderFormRow()}
            {loading && (
              <tr><td colSpan={5} className="empty-state">Loading…</td></tr>
            )}
            {!loading && zones.length === 0 && !adding && (
              <tr>
                <td colSpan={5} className="empty-state">
                  <div className="empty-icon">⬡</div>
                  No zones configured
                  <div style={{ fontSize: "9px", marginTop: "4px", color: "rgba(255,255,255,.15)" }}>
                    Add a zone to enable restricted area monitoring
                  </div>
                </td>
              </tr>
            )}
            {!loading && zones.map((z) =>
              editing === z.zone_id ? (
                renderFormRow()
              ) : (
                <tr key={z.zone_id}>
                  <td className="mono">{z.zone_id}</td>
                  <td>
                    <div style={{ display: "flex", alignItems: "center", gap: "6px" }}>
                      <span className="val">{z.camera_id ?? "—"}</span>
                      {z.camera_id && CAMERA_MAP.has(z.camera_id) && (() => {
                        const cam = CAMERA_MAP.get(z.camera_id)!;
                        const duty = cam.duties[0];
                        const cls = duty === "ppe-compliance" ? "ppe" : duty === "fire-smoke" ? "fire" : "zone";
                        const meta = DUTY_LABELS[duty];
                        return <span className={`duty-badge ${cls}`}>{meta.label}</span>;
                      })()}
                    </div>
                  </td>
                  <td className="val">{z.required_ppe?.join(", ") ?? "—"}</td>
                  <td className="dim" style={{ fontFamily: "monospace", fontSize: "10px" }}>
                    {z.polygon ? `[${z.polygon.length} pts]` : "—"}
                  </td>
                  <td style={{ whiteSpace: "nowrap" }}>
                    <button onClick={() => startEdit(z)} className="act-btn" style={{ marginRight: "4px" }}>Edit</button>
                    <button onClick={() => handleDelete(z.zone_id)} className="act-btn danger">Delete</button>
                  </td>
                </tr>
              )
            )}
          </tbody>
        </table>
      </div>

      {showEditor && form.camera_id && (
        <ZoneEditorModal
          token={token}
          cameraId={form.camera_id}
          initialPolygon={(() => {
            try { return form.polygon ? JSON.parse(form.polygon) : null; } catch { return null; }
          })()}
          onSave={(poly) => {
            const json = JSON.stringify(poly);
            setForm((f) => ({ ...f, polygon: json }));
            setPolygonPreview(`${poly.length} pts`);
            setShowEditor(false);
          }}
          onClose={() => setShowEditor(false)}
        />
      )}

      {quickCamId && (
        <ZoneEditorModal
          token={token}
          cameraId={quickCamId}
          initialPolygon={(() => {
            const z = zones.find((z) => z.camera_id === quickCamId);
            return (z?.polygon as [number, number][] | undefined) ?? null;
          })()}
          onSave={handleQuickZoneSave}
          onClose={() => setQuickCamId(null)}
        />
      )}
    </div>
  );
}

// ─── Policies tab ────────────────────────────────────────────────────────────

function PoliciesTab({ token }: { token: string }) {
  const [policies, setPolicies] = useState<PolicyOut[]>([]);
  const [loading, setLoading] = useState(true);
  const [adding, setAdding] = useState(false);
  const [newZoneId, setNewZoneId] = useState("");
  const [newPpe, setNewPpe] = useState("");
  const [error, setError] = useState<string | null>(null);

  const reload = useCallback(() => {
    setLoading(true);
    getPolicies(token)
      .then(setPolicies)
      .catch(() => setError("Failed to load policies"))
      .finally(() => setLoading(false));
  }, [token]);

  useEffect(() => { reload(); }, [reload]);

  async function handleToggle(p: PolicyOut) {
    setPolicies((prev) =>
      prev.map((x) => (x.id === p.id ? { ...x, active: !p.active } : x))
    );
    try {
      const updated = p.active
        ? await deactivatePolicy(token, p.id)
        : await activatePolicy(token, p.id);
      setPolicies((prev) => prev.map((x) => (x.id === p.id ? updated : x)));
    } catch {
      setPolicies((prev) =>
        prev.map((x) => (x.id === p.id ? { ...x, active: p.active } : x))
      );
      setError("Toggle failed");
    }
  }

  async function handleDelete(id: string) {
    if (!window.confirm("Delete this policy?")) return;
    try {
      await deletePolicy(token, id);
      reload();
    } catch {
      setError("Delete failed");
    }
  }

  async function handleAdd() {
    setError(null);
    const ppe = newPpe.split(",").map((s) => s.trim()).filter(Boolean);
    try {
      await createPolicy(token, { zone_id: newZoneId, required_ppe: ppe });
      setAdding(false);
      setNewZoneId("");
      setNewPpe("");
      reload();
    } catch {
      setError("Create failed");
    }
  }

  return (
    <div>
      <div className="sec-hdr">
        <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
          <span className="sec-label">Policies</span>
          <span className="sec-count">· {policies.length}</span>
        </div>
        {!adding && (
          <button onClick={() => setAdding(true)} className="act-btn">+ Add policy</button>
        )}
      </div>

      {error && <div className="cfg-error">{error}</div>}

      {adding && (
        <div className="form-row">
          <input
            className={`${inputCls} w-36`}
            placeholder="zone_id"
            value={newZoneId}
            onChange={(e) => setNewZoneId(e.target.value)}
          />
          <input
            className={`${inputCls} flex-1`}
            placeholder="helmet, vest"
            value={newPpe}
            onChange={(e) => setNewPpe(e.target.value)}
          />
          <button onClick={handleAdd} className="act-btn primary">Save</button>
          <button onClick={() => { setAdding(false); setError(null); }} className="act-btn">Cancel</button>
        </div>
      )}

      <div style={{ overflowX: "auto" }}>
        <table className="cfg-table">
          <thead>
            <tr>
              <th>Zone ID</th>
              <th>Required PPE</th>
              <th>Active</th>
              <th>Created</th>
              <th style={{ width: "4rem" }} />
            </tr>
          </thead>
          <tbody>
            {loading && (
              <tr><td colSpan={5} className="empty-state">Loading…</td></tr>
            )}
            {!loading && policies.length === 0 && (
              <tr><td colSpan={5} className="empty-state">No policies configured</td></tr>
            )}
            {!loading && policies.map((p) => (
              <tr key={p.id}>
                <td className="mono">{p.zone_id}</td>
                <td className="val">{p.required_ppe?.join(", ") ?? "—"}</td>
                <td>
                  <button
                    onClick={() => handleToggle(p)}
                    className={`toggle ${p.active ? "on" : "off"}`}
                    title={p.active ? "Deactivate" : "Activate"}
                  >
                    <span className="toggle-dot" />
                  </button>
                </td>
                <td className="dim" style={{ fontFamily: "monospace", fontSize: "10px" }}>
                  {new Date(p.created_at).toLocaleDateString()}
                </td>
                <td>
                  <button onClick={() => handleDelete(p.id)} className="act-btn danger">Delete</button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

// ─── Notifications tab ───────────────────────────────────────────────────────

const EVENT_TYPES = ["PPE_VIOLATION", "ZONE_ENTER", "ZONE_EXIT", "FIRE_DETECTED", "SMOKE_DETECTED", "*"];

function NotificationsTab({ token }: { token: string }) {
  const [channels, setChannels] = useState<ChannelOut[]>([]);
  const [rules, setRules] = useState<RuleOut[]>([]);
  const [zones, setZones] = useState<ZoneOut[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const [addingCh, setAddingCh] = useState(false);
  const [chForm, setChForm] = useState({ name: "", type: "slack", url: "", headers: "" });

  const [addingRule, setAddingRule] = useState(false);
  const [ruleForm, setRuleForm] = useState({ channel_id: "", event_type: "PPE_VIOLATION", zone_id: "" });

  const [testFeedback, setTestFeedback] = useState<Record<string, string | null>>({});
  const timerRefs = useRef<Record<string, ReturnType<typeof setTimeout>>>({});

  const reload = useCallback(() => {
    setLoading(true);
    Promise.all([getChannels(token), getRules(token), getZones(token)])
      .then(([chs, rls, zns]) => { setChannels(chs); setRules(rls); setZones(zns); })
      .catch(() => setError("Failed to load notifications"))
      .finally(() => setLoading(false));
  }, [token]);

  useEffect(() => { reload(); }, [reload]);

  async function handleToggleCh(ch: ChannelOut) {
    setChannels((prev) => prev.map((c) => c.id === ch.id ? { ...c, active: !c.active } : c));
    try {
      const updated = await toggleChannel(token, ch.id);
      setChannels((prev) => prev.map((c) => c.id === ch.id ? updated : c));
    } catch {
      setChannels((prev) => prev.map((c) => c.id === ch.id ? { ...c, active: ch.active } : c));
      setError("Toggle failed");
    }
  }

  async function handleDeleteCh(ch: ChannelOut) {
    if (!window.confirm(`Delete channel "${ch.name}"?`)) return;
    try { await deleteChannel(token, ch.id); reload(); } catch { setError("Delete failed"); }
  }

  async function handleTest(ch: ChannelOut) {
    setTestFeedback((prev) => ({ ...prev, [ch.id]: null }));
    try {
      await testChannel(token, ch.id);
      setTestFeedback((prev) => ({ ...prev, [ch.id]: "ok" }));
    } catch (e) {
      setTestFeedback((prev) => ({ ...prev, [ch.id]: `error: ${e instanceof Error ? e.message : "failed"}` }));
    }
    if (timerRefs.current[ch.id]) clearTimeout(timerRefs.current[ch.id]);
    timerRefs.current[ch.id] = setTimeout(() => {
      setTestFeedback((prev) => ({ ...prev, [ch.id]: null }));
    }, 3000);
  }

  async function handleAddChannel() {
    setError(null);
    const config: Record<string, string> = { url: chForm.url };
    if (chForm.type === "webhook" && chForm.headers.trim()) {
      try { config.headers = JSON.parse(chForm.headers); } catch { setError("Headers must be valid JSON"); return; }
    }
    try {
      await createChannel(token, { name: chForm.name, type: chForm.type, config });
      setAddingCh(false);
      setChForm({ name: "", type: "slack", url: "", headers: "" });
      reload();
    } catch { setError("Create channel failed"); }
  }

  async function handleToggleRule(rule: RuleOut) {
    setRules((prev) => prev.map((r) => r.id === rule.id ? { ...r, active: !r.active } : r));
    try {
      const updated = await toggleRule(token, rule.id);
      setRules((prev) => prev.map((r) => r.id === rule.id ? updated : r));
    } catch {
      setRules((prev) => prev.map((r) => r.id === rule.id ? { ...r, active: rule.active } : r));
      setError("Toggle failed");
    }
  }

  async function handleDeleteRule(rule: RuleOut) {
    if (!window.confirm("Delete this rule?")) return;
    try { await deleteRule(token, rule.id); reload(); } catch { setError("Delete failed"); }
  }

  async function handleAddRule() {
    setError(null);
    try {
      await createRule(token, {
        channel_id: ruleForm.channel_id,
        event_type: ruleForm.event_type,
        zone_id: ruleForm.zone_id || null,
      });
      setAddingRule(false);
      setRuleForm({ channel_id: "", event_type: "PPE_VIOLATION", zone_id: "" });
      reload();
    } catch { setError("Create rule failed"); }
  }

  const chById = Object.fromEntries(channels.map((c) => [c.id, c]));

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "20px" }}>
      {error && <div className="cfg-error">{error}</div>}

      {/* ── Channels ── */}
      <div>
        <div className="sec-hdr">
          <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
            <span className="sec-label">Channels</span>
            <span className="sec-count">· {channels.length}</span>
          </div>
          {!addingCh && (
            <button onClick={() => setAddingCh(true)} className="act-btn">+ Add channel</button>
          )}
        </div>

        {addingCh && (
          <div className="form-row">
            <input
              className={`${inputCls} w-36`}
              placeholder="Name"
              value={chForm.name}
              onChange={(e) => setChForm({ ...chForm, name: e.target.value })}
            />
            <select
              className={`${inputCls} w-28`}
              value={chForm.type}
              onChange={(e) => setChForm({ ...chForm, type: e.target.value })}
            >
              <option value="slack">Slack</option>
              <option value="webhook">Webhook</option>
              <option value="email">Email</option>
            </select>
            {chForm.type !== "email" && (
              <input
                className={`${inputCls} flex-1`}
                placeholder={chForm.type === "slack" ? "Slack webhook URL" : "Webhook URL"}
                value={chForm.url}
                onChange={(e) => setChForm({ ...chForm, url: e.target.value })}
              />
            )}
            {chForm.type === "webhook" && (
              <input
                className={`${inputCls} w-48`}
                placeholder='Headers {"X-Key":"val"}'
                value={chForm.headers}
                onChange={(e) => setChForm({ ...chForm, headers: e.target.value })}
              />
            )}
            {chForm.type === "email" && (
              <span style={{ fontSize: "10px", color: "var(--text3)", padding: "4px 0" }}>SMTP not configured</span>
            )}
            <button onClick={handleAddChannel} className="act-btn primary">Save</button>
            <button onClick={() => { setAddingCh(false); setError(null); }} className="act-btn">Cancel</button>
          </div>
        )}

        <div style={{ overflowX: "auto" }}>
          <table className="cfg-table">
            <thead>
              <tr>
                <th>Name</th>
                <th>Type</th>
                <th>Active</th>
                <th style={{ width: "9rem" }} />
              </tr>
            </thead>
            <tbody>
              {loading && (
                <tr><td colSpan={4} className="empty-state">Loading…</td></tr>
              )}
              {!loading && channels.length === 0 && !addingCh && (
                <tr><td colSpan={4} className="empty-state">No channels configured</td></tr>
              )}
              {!loading && channels.map((ch) => (
                <tr key={ch.id}>
                  <td className="val">{ch.name}</td>
                  <td>
                    <span className={`type-badge ${ch.type}`}>{ch.type}</span>
                  </td>
                  <td>
                    <button
                      onClick={() => handleToggleCh(ch)}
                      className={`toggle ${ch.active ? "on" : "off"}`}
                      title={ch.active ? "Deactivate" : "Activate"}
                    >
                      <span className="toggle-dot" />
                    </button>
                  </td>
                  <td style={{ whiteSpace: "nowrap" }}>
                    <button onClick={() => handleTest(ch)} className="act-btn" style={{ marginRight: "4px" }}>Test</button>
                    {testFeedback[ch.id] != null && (
                      <span style={{ marginRight: "6px", fontSize: "10px", color: testFeedback[ch.id] === "ok" ? "var(--green)" : "var(--red)" }}>
                        {testFeedback[ch.id] === "ok" ? "✓ Sent" : `✗ ${testFeedback[ch.id]}`}
                      </span>
                    )}
                    <button onClick={() => handleDeleteCh(ch)} className="act-btn danger">Delete</button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {/* ── Rules ── */}
      <div>
        <div className="sec-hdr">
          <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
            <span className="sec-label">Rules</span>
            <span className="sec-count">· {rules.length}</span>
          </div>
          {!addingRule && channels.length > 0 && (
            <button
              onClick={() => {
                setAddingRule(true);
                setRuleForm({ channel_id: channels[0].id, event_type: "PPE_VIOLATION", zone_id: "" });
              }}
              className="act-btn"
            >
              + Add rule
            </button>
          )}
        </div>

        {addingRule && (
          <div className="form-row">
            <select
              className={`${inputCls} w-40`}
              value={ruleForm.event_type}
              onChange={(e) => setRuleForm({ ...ruleForm, event_type: e.target.value })}
            >
              {EVENT_TYPES.map((t) => (
                <option key={t} value={t}>{t === "*" ? "* (Any event)" : t}</option>
              ))}
            </select>
            <select
              className={`${inputCls} w-36`}
              value={ruleForm.zone_id}
              onChange={(e) => setRuleForm({ ...ruleForm, zone_id: e.target.value })}
            >
              <option value="">Any zone</option>
              {zones.map((z) => (
                <option key={z.zone_id} value={z.zone_id}>{z.zone_id}</option>
              ))}
            </select>
            <select
              className={`${inputCls} w-40`}
              value={ruleForm.channel_id}
              onChange={(e) => setRuleForm({ ...ruleForm, channel_id: e.target.value })}
            >
              {channels.map((c) => (
                <option key={c.id} value={c.id}>{c.name}</option>
              ))}
            </select>
            <button onClick={handleAddRule} className="act-btn primary">Save</button>
            <button onClick={() => { setAddingRule(false); setError(null); }} className="act-btn">Cancel</button>
          </div>
        )}

        <div style={{ overflowX: "auto" }}>
          <table className="cfg-table">
            <thead>
              <tr>
                <th>Event type</th>
                <th>Zone</th>
                <th>Channel</th>
                <th>Active</th>
                <th style={{ width: "4rem" }} />
              </tr>
            </thead>
            <tbody>
              {loading && (
                <tr><td colSpan={5} className="empty-state">Loading…</td></tr>
              )}
              {!loading && rules.length === 0 && !addingRule && (
                <tr><td colSpan={5} className="empty-state">No rules configured</td></tr>
              )}
              {!loading && rules.map((rule) => (
                <tr key={rule.id}>
                  <td className="mono" style={{ fontSize: "10px" }}>{rule.event_type}</td>
                  <td className="val">{rule.zone_id ?? <span className="dim" style={{ fontStyle: "italic" }}>Any zone</span>}</td>
                  <td className="val">{chById[rule.channel_id]?.name ?? rule.channel_id}</td>
                  <td>
                    <button
                      onClick={() => handleToggleRule(rule)}
                      className={`toggle ${rule.active ? "on" : "off"}`}
                      title={rule.active ? "Deactivate" : "Activate"}
                    >
                      <span className="toggle-dot" />
                    </button>
                  </td>
                  <td>
                    <button onClick={() => handleDeleteRule(rule)} className="act-btn danger">Delete</button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}

// ─── Main ConfigPanel ────────────────────────────────────────────────────────

export default function ConfigPanel({ token }: ConfigPanelProps) {
  const [tab, setTab] = useState<Tab>("zones");

  return (
    <>
      <style>{CSS}</style>
      <div className="cfg-panel">
        <div className="cfg-header">
          <span className="cfg-label">Configure</span>
          <button className={`cfg-tab${tab === "zones" ? " active" : ""}`} onClick={() => setTab("zones")}>
            Zones
          </button>
          <button className={`cfg-tab${tab === "policies" ? " active" : ""}`} onClick={() => setTab("policies")}>
            Policies
          </button>
          <button className={`cfg-tab${tab === "notifications" ? " active" : ""}`} onClick={() => setTab("notifications")}>
            Notifications
          </button>
        </div>
        <div className="cfg-body">
          {tab === "zones" && <ZonesTab token={token} />}
          {tab === "policies" && <PoliciesTab token={token} />}
          {tab === "notifications" && <NotificationsTab token={token} />}
        </div>
      </div>
    </>
  );
}
