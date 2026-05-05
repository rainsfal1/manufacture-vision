"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { apiFetch } from "@/lib/api";
import { getToken } from "@/lib/token";
import { EventListOut, EventOut } from "@/types";
import ConsoleLayout from "@/components/ConsoleLayout";

export default function DashboardPage() {
  const router = useRouter();
  const [token, setToken] = useState<string | null>(null);
  const [initialEvents, setInitialEvents] = useState<EventOut[]>([]);
  const [ready, setReady] = useState(false);

  useEffect(() => {
    const t = getToken();
    if (!t) {
      router.replace("/login");
      return;
    }
    setToken(t);

    apiFetch<EventListOut>("/events?limit=50", t)
      .then((data) => setInitialEvents(data.items))
      .catch(() => {})
      .finally(() => setReady(true));
  }, [router]);

  if (!ready || !token) {
    return (
      <div className="min-h-screen bg-[#0a0a0a] flex flex-col items-center justify-center gap-4 relative overflow-hidden">
        {/* ambient glow */}
        <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[400px] h-[400px] rounded-full bg-[#fbbf24]/[0.02] blur-[100px] pointer-events-none" />
        
        {/* custom high-tech spinner */}
        <div className="relative w-10 h-10">
          <div className="absolute inset-0 border border-[#222] rounded-full" />
          <div className="absolute inset-0 border-t-2 border-[#fbbf24] rounded-full animate-spin" />
        </div>

        <span className="text-[10px] text-[#555] tracking-[0.14em] uppercase font-mono font-medium animate-pulse">
          Establishing Secure Link…
        </span>
      </div>
    );
  }

  return <ConsoleLayout token={token} initialEvents={initialEvents} />;
}
