"use client";

import { useEffect, useState } from "react";

const BASE = "http://localhost:8000";

interface VideoModalProps {
  clipKey: string;
  token: string;
  onClose: () => void;
}

const CSS = `
  .modal-backdrop { position:fixed; inset:0; background:rgba(0,0,0,.75); display:flex; align-items:center; justify-content:center; z-index:100; padding:16px; }
  .modal-box { background:var(--s1); border:1px solid var(--border2); border-radius:8px; width:100%; max-width:640px; box-shadow:0 16px 48px rgba(0,0,0,.7); }
  .modal-hdr { display:flex; align-items:center; justify-content:space-between; padding:10px 16px; border-bottom:1px solid var(--border); }
  .modal-title { font-size:12px; font-weight:500; color:var(--text); letter-spacing:-.01em; }
  .modal-close { background:none; border:none; color:var(--text3); font-size:18px; cursor:pointer; padding:0 4px; line-height:1; transition:color .15s; font-family:inherit; }
  .modal-close:hover { color:var(--text); }
  .modal-body { padding:16px; }
  .modal-loading { display:flex; align-items:center; justify-content:center; height:160px; }
  .modal-spinner { width:20px; height:20px; border:2px solid rgba(255,255,255,.1); border-top-color:var(--green); border-radius:50%; animation:spin 1s linear infinite; }
  @keyframes spin { to { transform:rotate(360deg); } }
  .modal-error { display:flex; align-items:center; justify-content:center; height:160px; color:var(--red); font-size:12px; }
  .modal-video { width:100%; border-radius:5px; background:#000; display:block; }
  .modal-key { margin-top:10px; font-size:10px; color:var(--text3); font-family:monospace; word-break:break-all; }
`;

export default function VideoModal({ clipKey, token, onClose }: VideoModalProps) {
  const [url, setUrl] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    // Stream through the backend to avoid MinIO CORS issues.
    // Token is passed as a query param — same pattern as the SSE endpoint.
    const streamUrl = `${BASE}/media/clip/stream?key=${encodeURIComponent(clipKey)}&token=${encodeURIComponent(token)}`;
    setUrl(streamUrl);
    setLoading(false);
  }, [clipKey, token]);

  useEffect(() => {
    const handler = (e: KeyboardEvent) => { if (e.key === "Escape") onClose(); };
    window.addEventListener("keydown", handler);
    return () => window.removeEventListener("keydown", handler);
  }, [onClose]);

  return (
    <>
      <style>{CSS}</style>
      <div className="modal-backdrop" onClick={(e) => { if (e.target === e.currentTarget) onClose(); }}>
        <div className="modal-box">
          <div className="modal-hdr">
            <span className="modal-title">Evidence Clip</span>
            <button className="modal-close" onClick={onClose}>×</button>
          </div>
          <div className="modal-body">
            {loading && (
              <div className="modal-loading">
                <div className="modal-spinner" />
              </div>
            )}
            {error && <div className="modal-error">{error}</div>}
            {url && <video src={url} controls autoPlay className="modal-video" />}
            <p className="modal-key">{clipKey}</p>
          </div>
        </div>
      </div>
    </>
  );
}
