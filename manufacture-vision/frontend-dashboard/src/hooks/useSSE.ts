"use client";

import { useEffect, useRef, useState } from "react";
import { EventOut } from "@/types";

const BASE = "http://localhost:8000";

export function useSSE(token: string | null): {
  events: EventOut[];
  connected: boolean;
} {
  const [events, setEvents] = useState<EventOut[]>([]);
  const [connected, setConnected] = useState(false);
  const esRef = useRef<EventSource | null>(null);

  useEffect(() => {
    if (!token) return;

    function connect() {
      const es = new EventSource(`${BASE}/events/stream?token=${token}`);
      esRef.current = es;

      es.onopen = () => setConnected(true);

      es.onmessage = (e) => {
        try {
          const ev = JSON.parse(e.data) as EventOut;

          // Compute clip_key from clip_ref (stored as Python repr dict string).
          // Guard against the literal string "null" which older ZONE events emit.
          const rawRef = ev.clip_ref;
          if (rawRef && rawRef !== "null") {
            try {
              const parsed = JSON.parse(rawRef.replace(/'/g, '"'));
              ev.clip_key = typeof parsed === "object" && parsed !== null
                ? (parsed.key ?? null)
                : rawRef;
            } catch {
              ev.clip_key = rawRef; // already a bare key string
            }
          } else {
            ev.clip_key = null;
          }

          setEvents((prev) => [ev, ...prev].slice(0, 50));
        } catch {
          // ignore malformed messages
        }
      };

      es.onerror = () => {
        setConnected(false);
        es.close();
        // Auto-reconnect after 3s
        setTimeout(connect, 3000);
      };
    }

    connect();

    return () => {
      esRef.current?.close();
      esRef.current = null;
      setConnected(false);
    };
  }, [token]);

  return { events, connected };
}
