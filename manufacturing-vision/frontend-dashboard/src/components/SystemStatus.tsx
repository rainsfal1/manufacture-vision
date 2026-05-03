"use client";

import { useEffect, useState } from "react";

interface SystemStatusProps {
  sseConnected: boolean;
}

const CSS = `
  .sys-section { padding:12px 14px 14px; }
  .log-rule { height:1px; background:linear-gradient(90deg,var(--border) 60%,transparent); margin:10px 14px 0; }
  .sys-hdr { font-size:9px; font-weight:700; letter-spacing:.14em; text-transform:uppercase; color:rgba(255,255,255,.2); margin-bottom:8px; }
  .sys-rows { display:flex; flex-direction:column; gap:5px; }
  .sys-row { display:flex; align-items:center; justify-content:space-between; }
  .sys-row-left { display:flex; align-items:center; gap:7px; }
  .sys-dot { width:5px; height:5px; border-radius:50%; flex-shrink:0; }
  .sys-dot.ok { background:var(--green-dim); opacity:.5; }
  .sys-dot.down { background:var(--red-dim); }
  .sys-dot.pending { background:var(--text3); }
  .sys-name { font-size:11px; color:rgba(255,255,255,.35); }
  .sys-val { font-size:10px; font-weight:600; font-family:monospace; letter-spacing:.04em; }
  .sys-val.ok { color:rgba(74,222,128,.5); }
  .sys-val.down { color:rgba(248,113,113,.6); }
  .sys-val.pending { color:rgba(255,255,255,.2); }
`;

export default function SystemStatus({ sseConnected }: SystemStatusProps) {
  const [backendOk, setBackendOk] = useState<boolean | null>(null);

  useEffect(() => {
    async function check() {
      try {
        const res = await fetch("http://localhost:8000/health");
        setBackendOk(res.ok);
      } catch {
        setBackendOk(false);
      }
    }
    check();
    const id = setInterval(check, 15_000);
    return () => clearInterval(id);
  }, []);

  type St = boolean | null;

  function dotCls(ok: St) {
    if (ok === null) return "sys-dot pending";
    return ok ? "sys-dot ok" : "sys-dot down";
  }

  function valCls(ok: St) {
    if (ok === null) return "sys-val pending";
    return ok ? "sys-val ok" : "sys-val down";
  }

  function label(ok: St) {
    if (ok === null) return "—";
    return ok ? "OK" : "DOWN";
  }

  return (
    <>
      <style>{CSS}</style>
      <div className="log-rule" />
      <div className="sys-section">
        <div className="sys-hdr">System</div>
        <div className="sys-rows">
          <div className="sys-row">
            <div className="sys-row-left">
              <div className={dotCls(backendOk)} />
              <span className="sys-name">Backend</span>
            </div>
            <span className={valCls(backendOk)}>{label(backendOk)}</span>
          </div>
          <div className="sys-row">
            <div className="sys-row-left">
              <div className={dotCls(sseConnected)} />
              <span className="sys-name">Stream</span>
            </div>
            <span className={valCls(sseConnected)}>{label(sseConnected)}</span>
          </div>
        </div>
      </div>
    </>
  );
}
