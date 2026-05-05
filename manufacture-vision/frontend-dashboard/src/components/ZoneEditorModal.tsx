"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { getSnapshotUrl } from "@/lib/api";

type Point = [number, number];

interface ZoneEditorModalProps {
  token: string;
  cameraId: string;
  initialPolygon: Point[] | null;
  onSave: (polygon: Point[]) => void;
  onClose: () => void;
}

const SNAP_RADIUS = 14;

function dist(a: Point, b: Point) {
  return Math.sqrt((a[0] - b[0]) ** 2 + (a[1] - b[1]) ** 2);
}

export default function ZoneEditorModal({
  token,
  cameraId,
  initialPolygon,
  onSave,
  onClose,
}: ZoneEditorModalProps) {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const imgRef = useRef<HTMLImageElement | null>(null);
  const blobUrlRef = useRef<string | null>(null);

  const [vertices, setVertices] = useState<Point[]>(initialPolygon ?? []);
  const [closed, setClosed] = useState((initialPolygon ?? []).length >= 3);
  const [cursor, setCursor] = useState<Point | null>(null);
  const [imgSize, setImgSize] = useState<{ w: number; h: number } | null>(null);
  const [loading, setLoading] = useState(true);
  const [noSnapshot, setNoSnapshot] = useState(false);

  const PLACEHOLDER = { w: 1920, h: 1080 };

  useEffect(() => {
    let cancelled = false;
    getSnapshotUrl(token, cameraId)
      .then((url) => {
        if (cancelled) { URL.revokeObjectURL(url); return; }
        blobUrlRef.current = url;
        const img = new Image();
        img.onload = () => {
          if (cancelled) return;
          imgRef.current = img;
          setImgSize({ w: img.naturalWidth, h: img.naturalHeight });
          setLoading(false);
        };
        img.onerror = () => {
          if (!cancelled) {
            setNoSnapshot(true);
            setImgSize(PLACEHOLDER);
            setLoading(false);
          }
        };
        img.src = url;
      })
      .catch(() => {
        // No snapshot yet — use a blank reference canvas so the user can
        // define zones without needing inference to have run first.
        if (!cancelled) {
          setNoSnapshot(true);
          setImgSize(PLACEHOLDER);
          setLoading(false);
        }
      });
    return () => {
      cancelled = true;
      if (blobUrlRef.current) { URL.revokeObjectURL(blobUrlRef.current); blobUrlRef.current = null; }
    };
  }, [token, cameraId]);

  const drawPlaceholderBackground = useCallback((ctx: CanvasRenderingContext2D, w: number, h: number) => {
    ctx.fillStyle = "#0d1117";
    ctx.fillRect(0, 0, w, h);

    // Subtle grid
    ctx.strokeStyle = "rgba(255,255,255,0.04)";
    ctx.lineWidth = 1;
    const step = Math.round(w / 24);
    for (let x = 0; x <= w; x += step) {
      ctx.beginPath(); ctx.moveTo(x, 0); ctx.lineTo(x, h); ctx.stroke();
    }
    for (let y = 0; y <= h; y += step) {
      ctx.beginPath(); ctx.moveTo(0, y); ctx.lineTo(w, y); ctx.stroke();
    }

    // Center label
    ctx.fillStyle = "rgba(255,255,255,0.12)";
    ctx.font = `bold ${Math.round(w * 0.018)}px monospace`;
    ctx.textAlign = "center";
    ctx.fillText("No snapshot — draw zone on reference canvas (1920 × 1080)", w / 2, h / 2);
    ctx.textAlign = "left";
  }, []);

  const draw = useCallback(() => {
    const canvas = canvasRef.current;
    if (!canvas || !imgSize) return;
    const ctx = canvas.getContext("2d")!;

    ctx.clearRect(0, 0, canvas.width, canvas.height);

    if (imgRef.current) {
      ctx.drawImage(imgRef.current, 0, 0, canvas.width, canvas.height);
    } else {
      drawPlaceholderBackground(ctx, canvas.width, canvas.height);
    }

    if (vertices.length === 0) return;

    const scale = canvas.width / imgSize.w;
    const pts = vertices.map<Point>(([x, y]) => [x * scale, y * scale]);

    if (closed && pts.length >= 3) {
      ctx.beginPath();
      ctx.moveTo(pts[0][0], pts[0][1]);
      for (let i = 1; i < pts.length; i++) ctx.lineTo(pts[i][0], pts[i][1]);
      ctx.closePath();
      ctx.fillStyle = "rgba(34, 211, 238, 0.12)";
      ctx.fill();
    }

    ctx.beginPath();
    ctx.moveTo(pts[0][0], pts[0][1]);
    for (let i = 1; i < pts.length; i++) ctx.lineTo(pts[i][0], pts[i][1]);
    if (closed) ctx.closePath();
    ctx.strokeStyle = "#22d3ee";
    ctx.lineWidth = 1.5;
    ctx.setLineDash([]);
    ctx.stroke();

    if (!closed && cursor && pts.length > 0) {
      const last = pts[pts.length - 1];
      const snapToFirst = pts.length >= 3 && dist(cursor, pts[0]) < SNAP_RADIUS;
      const target = snapToFirst ? pts[0] : cursor;
      ctx.beginPath();
      ctx.moveTo(last[0], last[1]);
      ctx.lineTo(target[0], target[1]);
      ctx.strokeStyle = snapToFirst ? "#4ade80" : "rgba(34,211,238,0.4)";
      ctx.lineWidth = 1.5;
      ctx.setLineDash([4, 4]);
      ctx.stroke();
      ctx.setLineDash([]);
    }

    pts.forEach((pt, i) => {
      const isFirst = i === 0;
      const canSnap = !closed && vertices.length >= 3 && cursor &&
        dist(cursor, pts[0]) < SNAP_RADIUS;

      ctx.beginPath();
      ctx.arc(pt[0], pt[1], isFirst ? 6 : 4, 0, Math.PI * 2);

      if (isFirst && canSnap) {
        ctx.fillStyle = "#4ade80";
        ctx.strokeStyle = "rgba(255,255,255,0.6)";
      } else if (isFirst) {
        ctx.fillStyle = "#22d3ee";
        ctx.strokeStyle = "rgba(255,255,255,0.4)";
      } else {
        ctx.fillStyle = "#0891b2";
        ctx.strokeStyle = "#22d3ee";
      }
      ctx.lineWidth = 1.5;
      ctx.fill();
      ctx.stroke();
    });
  }, [vertices, closed, cursor, imgSize, drawPlaceholderBackground]);

  useEffect(() => { draw(); }, [draw]);

  function toNatural(e: React.MouseEvent<HTMLCanvasElement>): Point {
    const canvas = canvasRef.current!;
    const rect = canvas.getBoundingClientRect();
    const scaleX = (imgSize?.w ?? canvas.width) / rect.width;
    const scaleY = (imgSize?.h ?? canvas.height) / rect.height;
    return [
      (e.clientX - rect.left) * scaleX,
      (e.clientY - rect.top) * scaleY,
    ];
  }

  function toCSSScale(e: React.MouseEvent<HTMLCanvasElement>): Point {
    const canvas = canvasRef.current!;
    const rect = canvas.getBoundingClientRect();
    return [e.clientX - rect.left, e.clientY - rect.top];
  }

  function handleMouseMove(e: React.MouseEvent<HTMLCanvasElement>) {
    if (closed) return;
    setCursor(toCSSScale(e));
  }

  function handleMouseLeave() { setCursor(null); }

  function handleClick(e: React.MouseEvent<HTMLCanvasElement>) {
    if (closed) return;
    const cssPoint = toCSSScale(e);
    const naturalPoint = toNatural(e);

    if (vertices.length >= 3) {
      const canvas = canvasRef.current!;
      const scale = canvas.getBoundingClientRect().width / (imgSize?.w ?? canvas.width);
      const firstCSS: Point = [vertices[0][0] * scale, vertices[0][1] * scale];
      if (dist(cssPoint, firstCSS) < SNAP_RADIUS) {
        setClosed(true);
        return;
      }
    }
    setVertices((prev) => [...prev, naturalPoint]);
  }

  function handleUndo() {
    if (closed) { setClosed(false); }
    else { setVertices((prev) => prev.slice(0, -1)); }
  }

  function handleClear() { setVertices([]); setClosed(false); }
  function handleClosePolygon() { if (vertices.length >= 3) setClosed(true); }
  function handleApply() {
    if (vertices.length >= 3) {
      onSave(vertices.map(([x, y]) => [Math.round(x), Math.round(y)]));
    }
  }

  const toolBtn = "text-xs px-2 py-1 rounded border border-[var(--border)] text-[var(--text2)] hover:text-[var(--text)] hover:border-[var(--border2)] disabled:opacity-30 disabled:cursor-not-allowed transition-colors";

  return (
    <div
      className="fixed inset-0 z-[60] flex items-center justify-center bg-black/75 backdrop-blur-sm"
      onClick={(e) => { if (e.target === e.currentTarget) onClose(); }}
    >
      <div
        className="flex flex-col bg-[var(--s1)] border border-[var(--border)] rounded-xl shadow-2xl overflow-hidden"
        style={{ width: "min(900px, 92vw)", height: "min(600px, 88vh)" }}
      >

        {/* Header */}
        <div className="flex items-center justify-between px-5 py-3.5 border-b border-[var(--border)] flex-shrink-0">
          <div className="flex items-center gap-3">
            <span className="text-sm font-semibold text-[var(--text)] tracking-tight">Zone Editor</span>
            <span className="text-[10px] font-mono text-[var(--text3)] bg-[rgba(255,255,255,.04)] border border-[var(--border)] rounded px-2 py-0.5">{cameraId}</span>
          </div>
          <button
            onClick={onClose}
            className="text-[var(--text3)] hover:text-[var(--text)] transition-colors p-1 rounded hover:bg-[rgba(255,255,255,.05)]"
            title="Close"
          >
            <svg width="14" height="14" viewBox="0 0 16 16" fill="none">
              <path d="M3 3l10 10M13 3L3 13" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round"/>
            </svg>
          </button>
        </div>

        {/* Canvas area — flex-1 so it fills remaining height */}
        <div className="relative flex-1 bg-[#060606] flex items-center justify-center overflow-hidden min-h-0">
          {loading && (
            <div className="flex flex-col items-center gap-3 text-[var(--text3)]">
              <div className="w-7 h-7 border-2 border-[var(--border)] border-t-[var(--cyan)] rounded-full animate-spin" />
              <span className="text-xs tracking-wide">Loading snapshot…</span>
            </div>
          )}
          {!loading && noSnapshot && (
            <div className="absolute top-2 left-1/2 -translate-x-1/2 z-10 bg-[rgba(0,0,0,0.6)] border border-[var(--border)] rounded px-3 py-1.5 text-[10px] text-[var(--text3)] whitespace-nowrap pointer-events-none">
              No snapshot yet — drawing on 1920×1080 reference canvas
            </div>
          )}
          {!loading && imgSize && (
            <canvas
              ref={canvasRef}
              width={imgSize.w}
              height={imgSize.h}
              className="block"
              style={{
                maxWidth: "100%",
                maxHeight: "100%",
                objectFit: "contain",
                cursor: closed ? "default" : "crosshair",
              }}
              onClick={handleClick}
              onMouseMove={handleMouseMove}
              onMouseLeave={handleMouseLeave}
            />
          )}
        </div>

        {/* Footer: instruction line + toolbar */}
        <div className="flex-shrink-0 border-t border-[var(--border)] bg-[var(--s1)]">
          {/* Status line */}
          <div className="px-5 pt-3 pb-2">
            {closed ? (
              <p className="text-[11px] text-[var(--green)]">
                Polygon closed — {vertices.length} vertices. Click <strong>Apply</strong> to save, or <strong>Undo</strong> to reopen.
              </p>
            ) : vertices.length === 0 ? (
              <p className="text-[11px] text-[var(--text3)]">Click on the image to place polygon vertices. Close the shape by clicking the first point.</p>
            ) : vertices.length < 3 ? (
              <p className="text-[11px] text-[var(--text3)]">
                {vertices.length} {vertices.length === 1 ? "vertex" : "vertices"} placed — need at least 3 to close.
              </p>
            ) : (
              <p className="text-[11px] text-[var(--text3)]">
                {vertices.length} vertices — click near the first <span className="text-[var(--cyan)]">●</span> to close, or use <strong>Close polygon</strong>.
              </p>
            )}
          </div>

          {/* Toolbar */}
          <div className="flex items-center gap-2 px-5 pb-4">
            <button onClick={handleUndo} disabled={vertices.length === 0} className={toolBtn}>Undo</button>
            <button onClick={handleClear} disabled={vertices.length === 0} className={toolBtn}>Clear</button>
            <button onClick={handleClosePolygon} disabled={closed || vertices.length < 3} className={toolBtn}>Close polygon</button>

            <div className="flex-1" />

            <button
              onClick={onClose}
              className="text-xs px-4 py-1.5 rounded border border-[var(--border)] text-[var(--text2)] hover:text-[var(--text)] hover:border-[var(--border2)] transition-colors"
            >
              Cancel
            </button>
            <button
              onClick={handleApply}
              disabled={!closed || vertices.length < 3}
              className="text-xs px-5 py-1.5 rounded bg-[rgba(34,211,238,0.12)] border border-[rgba(34,211,238,0.3)] text-[var(--cyan)] font-semibold hover:bg-[rgba(34,211,238,0.2)] disabled:opacity-30 disabled:cursor-not-allowed transition-colors"
            >
              Apply
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
