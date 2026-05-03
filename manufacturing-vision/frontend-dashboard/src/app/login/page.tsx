"use client";

import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import { login } from "@/lib/api";
import { getToken, setToken } from "@/lib/token";
import FactoryIcon from "@/components/icons/FactoryIcon";

export default function LoginPage() {
  const router = useRouter();
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [showPw, setShowPw] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (getToken()) router.replace("/dashboard");
  }, [router]);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    setLoading(true);
    try {
      const token = await login(username, password);
      setToken(token);
      router.replace("/dashboard");
    } catch {
      setError("Invalid username or password");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="min-h-screen bg-[#0a0a0a] flex flex-col items-center justify-center relative overflow-hidden">

      {/* ambient glows */}
      <div className="pointer-events-none absolute inset-0">
        <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[800px] h-[600px] rounded-full bg-[#fbbf24]/[0.04] blur-[160px]" />
        <div className="absolute top-1/4 left-1/3 w-[300px] h-[300px] rounded-full bg-[#fbbf24]/[0.025] blur-[120px]" />
      </div>

      {/* subtle grid overlay */}
      <div
        className="pointer-events-none absolute inset-0 opacity-[0.018]"
        style={{
          backgroundImage:
            "linear-gradient(#fff 1px,transparent 1px),linear-gradient(90deg,#fff 1px,transparent 1px)",
          backgroundSize: "48px 48px",
        }}
      />

      <div className="relative z-10 flex flex-col items-center gap-8 w-full max-w-sm px-4">

        {/* logo + wordmark */}
        <div className="flex flex-col items-center gap-2">
          <div className="flex items-center justify-center gap-2.5 flex-nowrap whitespace-nowrap">
            <FactoryIcon size={22} color="#fbbf24" />
            <span className="text-[17px] font-semibold text-[#f0f0f0] tracking-[-0.02em]">
              Manufacture Vision
            </span>
            <span className="text-[9px] text-[#3a3a3a] border border-[#222] rounded px-1.5 py-0.5 uppercase tracking-[0.08em]">
              Safety Console
            </span>
          </div>
          <p className="text-[10px] text-[#333] tracking-[0.12em] uppercase">
            Restricted Access
          </p>
        </div>

        {/* sign-in card */}
        <form
          onSubmit={handleSubmit}
          className="w-full bg-[#131313] border border-[#232323] rounded-xl p-7 flex flex-col gap-5"
          style={{ boxShadow: "0 0 0 1px #232323, 0 24px 60px rgba(0,0,0,0.7)" }}
        >
          {/* username */}
          <div className="flex flex-col gap-1.5">
            <label className="text-[10px] font-medium text-[#555] uppercase tracking-[0.08em]">
              Username
            </label>
            <input
              type="text"
              autoComplete="username"
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              placeholder="Enter your username"
              required
              autoFocus
              className="w-full bg-[#1a1a1a] border border-[#2a2a2a] rounded-[7px] px-3 py-2.5 text-[13px] text-[#f0f0f0] placeholder-[#444] outline-none focus:border-[#383838] transition-colors font-mono"
            />
          </div>

          {/* password */}
          <div className="flex flex-col gap-1.5">
            <label className="text-[10px] font-medium text-[#555] uppercase tracking-[0.08em]">
              Password
            </label>
            <div className="relative">
              <input
                type={showPw ? "text" : "password"}
                autoComplete="current-password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder="Enter your password"
                required
                className="w-full bg-[#1a1a1a] border border-[#2a2a2a] rounded-[7px] px-3 py-2.5 pr-10 text-[13px] text-[#f0f0f0] placeholder-[#444] outline-none focus:border-[#383838] transition-colors font-mono"
              />
              <button
                type="button"
                onClick={() => setShowPw((v) => !v)}
                className="absolute right-3 top-1/2 -translate-y-1/2 text-[#444] hover:text-[#888] transition-colors"
                tabIndex={-1}
              >
                {showPw ? (
                  <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
                    <path d="M17.94 17.94A10.07 10.07 0 0 1 12 20c-7 0-11-8-11-8a18.45 18.45 0 0 1 5.06-5.94"/>
                    <path d="M9.9 4.24A9.12 9.12 0 0 1 12 4c7 0 11 8 11 8a18.5 18.5 0 0 1-2.16 3.19"/>
                    <line x1="1" y1="1" x2="23" y2="23"/>
                  </svg>
                ) : (
                  <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
                    <path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"/>
                    <circle cx="12" cy="12" r="3"/>
                  </svg>
                )}
              </button>
            </div>
          </div>

          {/* error */}
          {error && (
            <p className="text-[11px] text-[#f87171] -mt-1">{error}</p>
          )}

          {/* submit */}
          <button
            type="submit"
            disabled={loading}
            className="w-full bg-[#fbbf24] hover:bg-[#f59e0b] disabled:opacity-50 disabled:cursor-not-allowed text-black text-[12px] font-semibold rounded-[7px] py-2.5 tracking-[0.03em] transition-colors"
          >
            {loading ? "Signing in…" : "Sign in"}
          </button>
        </form>

        {/* status indicator */}
        <div className="flex items-center gap-2">
          <div className="w-1.5 h-1.5 rounded-full bg-[#22c55e] shadow-[0_0_6px_#22c55e]" />
          <span className="text-[10px] text-[#333] tracking-[0.1em] uppercase">
            System operational
          </span>
        </div>

      </div>
    </div>
  );
}
