"use client";

import React from "react";
import {
  LineChart,
  Line,
  ScatterChart,
  Scatter,
  PieChart,
  Pie,
  Cell,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
  ZAxis,
  ReferenceArea,
} from "recharts";
import { Target, TrendingUp, AlertTriangle, Lightbulb, CheckCircle2, RefreshCw } from "lucide-react";
import Link from "next/link";
import { ArrowLeft } from "lucide-react";
import { useState, useEffect } from "react";
import { motion } from "framer-motion";
import { CopilotChat } from "@/components/CopilotChat";

// ─────────────────────────────────────────────
// Types
// ─────────────────────────────────────────────

type TrendPoint = { time: string;[key: string]: string | number };
type PositioningPoint = { name: string; x: number; y: number; dominant_cluster: string; fill: string };
type DistributionPoint = { name: string; value: number; fill: string };
type WhitespacePoint = { name: string; x: number; y: number; fill: string };
type ComparisonPoint = { name: string; pricing: number; quality: number; ai: number; convenience: number };

// ─────────────────────────────────────────────
// Config
// ─────────────────────────────────────────────

const API_BASE = "http://127.0.0.1:8000";
const CLIENT_ID = 1;
const CACHE_TTL_MS = 24 * 60 * 60 * 1000; // 24 hours

// ─── Cache Helpers ───────────────────────────────────────────────────────────

function getCached<T>(key: string): T | null {
  if (typeof window === "undefined") return null;
  try {
    const raw = localStorage.getItem(key);
    if (!raw) return null;
    const { ts, data } = JSON.parse(raw) as { ts: number; data: T };
    if (Date.now() - ts > CACHE_TTL_MS) {
      localStorage.removeItem(key);
      return null;
    }
    return data;
  } catch {
    return null;
  }
}

function setCache(key: string, data: unknown): void {
  if (typeof window === "undefined") return;
  try {
    localStorage.setItem(key, JSON.stringify({ ts: Date.now(), data }));
  } catch { }
}

function clearDashboardCache(): void {
  if (typeof window === "undefined") return;
  [
    `/api/trends?client_id=${CLIENT_ID}`,
    `/api/positioning?client_id=${CLIENT_ID}`,
    `/api/distribution?client_id=${CLIENT_ID}`,
    `/api/charts/opportunity?client_id=${CLIENT_ID}`,
    `/api/charts/competitor-scores?client_id=${CLIENT_ID}`,
  ].forEach((k) => localStorage.removeItem(`cs_cache:${k}`));
}

// Color palette for dynamic keys
const CLUSTER_COLORS = ["#a78bfa", "#f87171", "#60a5fa", "#fbbf24", "#34d399", "#f472b6"];
const PIE_COLORS = ["#f87171", "#60a5fa", "#34d399", "#a78bfa", "#f472b6"];
const COMPETITOR_COLORS = {
  pricing: "#f87171",
  quality: "#60a5fa",
  ai: "#a78bfa",
  convenience: "#34d399",
};

const QUADRANT_FILLS: Record<string, string> = {
  "BEST opportunity": "#34d399",
  Crowded: "#fbbf24",
  Weak: "#60a5fa",
  Avoid: "#f87171",
};

interface Experiment {
  insight: string;
  cluster_id: string;
  trend: string;
  confidence: number;
  risk: number;
  recommended_action: string;
  evidence: string[];
}

// Custom Tooltips
// ─────────────────────────────────────────────

const CustomTooltip = ({ active, payload, label }: any) => {
  if (active && payload && payload.length) {
    return (
      <div className="bg-zinc-900/95 backdrop-blur-md border border-white/10 p-4 rounded-xl shadow-2xl text-sm ring-1 ring-white/5">
        <p className="font-bold text-white mb-2 pb-2 border-b border-white/5">{label}</p>
        <div className="space-y-1">
          {payload.map((p: any, i: number) => (
            <div key={i} className="flex items-center justify-between gap-4">
              <span className="text-zinc-400 capitalize">{p.name}:</span>
              <span className="font-mono font-medium" style={{ color: p.color || p.fill }}>
                {p.value}
              </span>
            </div>
          ))}
        </div>
      </div>
    );
  }
  return null;
};

const ScatterTooltip = ({ active, payload }: any) => {
  if (active && payload && payload.length) {
    const data = payload[0].payload;
    return (
      <div className="bg-zinc-900/95 backdrop-blur-md border border-white/10 p-4 rounded-xl shadow-2xl text-sm ring-1 ring-white/5">
        <p className="font-bold text-white mb-2 pb-2 border-b border-white/5">{data.name}</p>
        <div className="space-y-1">
          {data.dominant_cluster && (
            <div className="flex items-center justify-between gap-4">
              <span className="text-zinc-400">Cluster:</span>
              <span className="text-white font-mono text-xs">{data.dominant_cluster}</span>
            </div>
          )}
          {data.quadrant && (
            <div className="flex items-center justify-between gap-4">
              <span className="text-zinc-400">Quadrant:</span>
              <span className="font-mono font-medium" style={{ color: data.fill }}>
                {data.quadrant}
              </span>
            </div>
          )}
          <div className="flex items-center justify-between gap-4">
            <span className="text-zinc-400">X:</span>
            <span className="text-white font-mono">{data.x}</span>
          </div>
          <div className="flex items-center justify-between gap-4">
            <span className="text-zinc-400">Y:</span>
            <span className="text-white font-mono">{data.y}</span>
          </div>
        </div>
      </div>
    );
  }
  return null;
};

// ─────────────────────────────────────────────
// Loading Screen
// ─────────────────────────────────────────────

function IntelligenceLoader() {
  const [progress, setProgress] = useState(0);
  const [statusText, setStatusText] = useState("Fetching competitor signals...");
  const STATUS_STEPS = [
    "Fetching competitor signals...",
    "Processing cluster embeddings...",
    "Calculating saturation scores...",
    "Analyzing whitespace opportunities...",
    "Compiling live intelligence...",
  ];

  useEffect(() => {
    const interval = setInterval(() => {
      setProgress((prev) => Math.min(prev + 3, 90));
    }, 150);

    let step = 0;
    const textInterval = setInterval(() => {
      step = (step + 1) % STATUS_STEPS.length;
      setStatusText(STATUS_STEPS[step]);
    }, 1800);

    return () => {
      clearInterval(interval);
      clearInterval(textInterval);
    };
  }, []);

  return (
    <div className="min-h-screen bg-[#050505] flex flex-col items-center justify-center gap-8">
      <div className="relative w-32 h-32">
        <svg className="w-full h-full -rotate-90" viewBox="0 0 120 120">
          <circle cx="60" cy="60" r="54" fill="none" stroke="rgba(255,255,255,0.05)" strokeWidth="3" />
          <circle
            cx="60" cy="60" r="54"
            fill="none" stroke="#a78bfa" strokeWidth="3" strokeLinecap="round"
            strokeDasharray={2 * Math.PI * 54}
            strokeDashoffset={2 * Math.PI * 54 * (1 - progress / 100)}
            className="transition-all duration-300 ease-out"
          />
        </svg>
        <div className="absolute inset-0 flex items-center justify-center">
          <span className="text-white text-xl font-bold font-mono">{progress}%</span>
        </div>
      </div>

      <div className="text-center space-y-2">
        <p className="text-xs uppercase tracking-[0.3em] font-black text-violet-400">
          Compiling Live Intelligence
        </p>
        <motion.p
          key={statusText}
          initial={{ opacity: 0, y: 5 }}
          animate={{ opacity: 1, y: 0 }}
          exit={{ opacity: 0 }}
          className="text-zinc-500 text-sm"
        >
          {statusText}
        </motion.p>
      </div>

      <div className="flex gap-1.5">
        {[0, 1, 2].map((i) => (
          <span
            key={i}
            className="w-1.5 h-1.5 bg-violet-500 rounded-full animate-pulse"
            style={{ animationDelay: `${i * 0.2}s` }}
          />
        ))}
      </div>
    </div>
  );
}

// ─────────────────────────────────────────────
// Dashboard Component
// ─────────────────────────────────────────────

export default function Dashboard() {
  const [experiments, setExperiments] = useState<Experiment[]>([]);
  const [selectedExp, setSelectedExp] = useState<string | null>(null);

  const chartStroke = "rgba(255, 255, 255, 0.05)";
  const axisColor = "rgba(255, 255, 255, 0.4)";

  // ── State ──
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [trendData, setTrendData] = useState<TrendPoint[]>([]);
  const [trendKeys, setTrendKeys] = useState<string[]>([]);
  const [positioningData, setPositioningData] = useState<PositioningPoint[]>([]);
  const [distributionData, setDistributionData] = useState<DistributionPoint[]>([]);
  const [whitespaceData, setWhitespaceData] = useState<WhitespacePoint[]>([]);
  const [comparisonData, setComparisonData] = useState<ComparisonPoint[]>([]);

  // ── Summary Cards derived from live data ──
  const fastestGrowingCluster = trendKeys.length ? trendKeys[0] : "—";
  const highestSaturation = distributionData.length ? distributionData[0].name : "—";
  const topOpportunity = whitespaceData.find((d) => d.fill === QUADRANT_FILLS["BEST opportunity"])?.name ?? "—";

  // ─────────────────────────────────────────
  // Fetch helper — 8s timeout, always adds client_id
  // ─────────────────────────────────────────
  async function apiFetch(path: string) {
    // Append client_id if not already present
    const url = path.includes("client_id") ? path : `${path}?client_id=${CLIENT_ID}`;
    const cacheKey = `cs_cache:${url}`;

    // Return cached data if fresh
    const cached = getCached<unknown>(cacheKey);
    if (cached !== null) {
      console.log(`[cache hit] ${url}`);
      return cached;
    }

    const token = typeof window !== "undefined" ? localStorage.getItem("token") : null;
    const headers: Record<string, string> = { "Content-Type": "application/json" };
    if (token) headers["Authorization"] = `Bearer ${token}`;

    const controller = new AbortController();
    const timeout = setTimeout(() => controller.abort(), 8000);

    try {
      const res = await fetch(`${API_BASE}${url}`, { headers, signal: controller.signal });
      if (!res.ok) throw new Error(`${url} → ${res.status} ${res.statusText}`);
      const json = await res.json();
      setCache(cacheKey, json);
      return json;
    } finally {
      clearTimeout(timeout);
    }
  }

  // ─────────────────────────────────────────
  // Data mapping helpers
  // ─────────────────────────────────────────

  const TOP_N_TRENDS = 5; // only show the N most prominent clusters

  function mapTrends(raw: { clusters: { name: string; data: { date: string; value: number }[] }[] }): {
    rows: TrendPoint[];
    keys: string[];
  } {
    // Rank clusters by total signal volume, keep only top N
    const ranked = [...raw.clusters]
      .map((c) => ({ ...c, total: c.data.reduce((s, d) => s + d.value, 0) }))
      .sort((a, b) => b.total - a.total)
      .slice(0, TOP_N_TRENDS);

    // Shorten names for legend readability (max 22 chars)
    const shorten = (s: string) => s.length > 22 ? s.slice(0, 21) + "…" : s;

    const dateMap: Record<string, TrendPoint> = {};
    const keys: string[] = [];

    ranked.forEach((cluster) => {
      const label = shorten(cluster.name);
      if (!keys.includes(label)) keys.push(label);
      cluster.data.forEach(({ date, value }) => {
        if (!dateMap[date]) dateMap[date] = { time: date };
        dateMap[date][label] = (Number(dateMap[date][label] ?? 0)) + value;
      });
    });

    const rows = Object.values(dateMap).sort((a, b) => String(a.time).localeCompare(String(b.time)));
    return { rows, keys };
  }

  function mapPositioning(raw: { competitors: { name: string; x: number; y: number; dominant_cluster: string }[] }): PositioningPoint[] {
    return raw.competitors.map((c, i) => ({
      ...c,
      fill: CLUSTER_COLORS[i % CLUSTER_COLORS.length],
    }));
  }

  function mapDistribution(raw: { clusters: { name: string; percentage: number }[] }): DistributionPoint[] {
    return raw.clusters.map((c, i) => ({
      name: c.name,
      value: c.percentage,
      fill: PIE_COLORS[i % PIE_COLORS.length],
    }));
  }

  function mapWhitespace(raw: { name: string; competition: number; growth: number; quadrant: string }[]): WhitespacePoint[] {
    return raw.map((d) => ({
      name: d.name,
      x: d.competition,   // competition → X axis (low→high)
      y: d.growth,        // growth rate → Y axis
      fill: QUADRANT_FILLS[d.quadrant] ?? "#a78bfa",
    }));
  }

  function mapComparison(raw: { competitor: string; pricing: number; quality: number; ai: number; convenience: number }[]): ComparisonPoint[] {
    return raw.map((r) => ({ ...r, name: r.competitor }));
  }

  // ─────────────────────────────────────────
  // Fetch all on mount — cache-first, 24-hour TTL
  // ─────────────────────────────────────────
  useEffect(() => {
    async function loadDashboard(bustCache = false) {
      if (bustCache) clearDashboardCache();
      setLoading(true);
      setError(null);
      try {
        const [trendsRes, posRes, distRes, oppRes, compRes] = await Promise.allSettled([
          apiFetch(`/api/trends?client_id=${CLIENT_ID}`),
          apiFetch(`/api/positioning?client_id=${CLIENT_ID}`),
          apiFetch(`/api/distribution?client_id=${CLIENT_ID}`),
          apiFetch(`/api/charts/opportunity?client_id=${CLIENT_ID}`),
          apiFetch(`/api/charts/competitor-scores?client_id=${CLIENT_ID}`),
        ]);

        if (trendsRes.status === "fulfilled") {
          const { rows, keys } = mapTrends(trendsRes.value);
          setTrendData(rows);
          setTrendKeys(keys);
        } else {
          console.warn("Trends fetch failed:", trendsRes.reason);
        }

        if (posRes.status === "fulfilled") {
          setPositioningData(mapPositioning(posRes.value));
        } else {
          console.warn("Positioning fetch failed:", posRes.reason);
        }

        if (distRes.status === "fulfilled") {
          setDistributionData(mapDistribution(distRes.value));
        } else {
          console.warn("Distribution fetch failed:", distRes.reason);
        }

        if (oppRes.status === "fulfilled") {
          setWhitespaceData(mapWhitespace(oppRes.value));
        } else {
          console.warn("Opportunity fetch failed:", oppRes.reason);
        }

        if (compRes.status === "fulfilled") {
          setComparisonData(mapComparison(compRes.value));
        } else {
          console.warn("Competitor scores fetch failed:", compRes.reason);
        }

      } catch (err: any) {
        console.error("Dashboard critical error:", err);
        setError(err.message || "Failed to connect to intelligence API.");
      } finally {
        setLoading(false);
      }
    }

    // Expose reload function for the Refresh button
    (window as any).__dashboardReload = () => loadDashboard(true);
    loadDashboard();
  }, []);

  // ─────────────────────────────────────────
  // Render states
  // ─────────────────────────────────────────

  if (loading) return <IntelligenceLoader />;

  if (error) {
    return (
      <div className="min-h-screen bg-[#050505] flex flex-col items-center justify-center gap-6">
        <div className="bg-red-500/10 border border-red-500/20 rounded-2xl p-8 max-w-md text-center">
          <AlertTriangle className="w-8 h-8 text-red-400 mx-auto mb-3" />
          <h2 className="text-white font-bold text-lg mb-2">Intelligence Feed Unavailable</h2>
          <p className="text-zinc-500 text-sm mb-4">{error}</p>
          <button
            onClick={() => window.location.reload()}
            className="inline-flex items-center gap-2 px-4 py-2 bg-zinc-800 hover:bg-zinc-700 text-white rounded-xl text-sm transition-all"
          >
            <RefreshCw className="w-4 h-4" /> Retry
          </button>
        </div>
      </div>
    );
  }

  // ─────────────────────────────────────────
  // Main render
  // ─────────────────────────────────────────

  return (
    <div className="min-h-screen bg-[#050505] text-[#e4e4e7] p-4 md:p-8 font-sans selection:bg-violet-500/30">

      {/* Header */}
      <div className="flex items-center justify-between mb-8 max-w-7xl mx-auto">
        <div>
          <button
            onClick={() => {
              localStorage.removeItem("token");
              window.location.href = "/";
            }}
            className="inline-flex items-center gap-2 text-zinc-500 hover:text-white text-xs uppercase tracking-[0.2em] font-bold mb-3 transition-all group"
          >
            <ArrowLeft className="w-4 h-4 group-hover:-translate-x-1 transition-transform" /> Sign Out / Home
          </button>
          <h1 className="text-4xl font-bungee tracking-wider text-white drop-shadow-[0_0_15px_rgba(255,255,255,0.1)]">
            Market Intelligence
          </h1>
          <p className="text-zinc-500 text-sm mt-2 max-w-md leading-relaxed">
            Live competitive insights and strategic recommendations with AI-driven analysis.
          </p>
        </div>
        <div className="flex items-center gap-3">
          {/* Refresh button — clears 24h cache and re-fetches */}
          <button
            onClick={() => (window as any).__dashboardReload?.()}
            title="Clear cache and refresh data"
            className="hidden md:flex items-center gap-2 px-4 py-2 bg-zinc-900 border border-white/5 rounded-full text-[10px] font-bold tracking-widest uppercase text-zinc-400 hover:text-white hover:border-white/20 transition-all"
          >
            <RefreshCw className="w-3 h-3" /> Refresh Data
          </button>
          <Link
            href="/experiment-builder"
            className="hidden md:flex px-4 py-2 bg-violet-500/10 border border-violet-500/20 rounded-full text-[10px] font-bold tracking-widest uppercase text-violet-400 hover:bg-violet-500/20 transition-colors items-center gap-2"
          >
            Experiment Builder →
          </Link>
          <div className="hidden md:block">
            <div className="px-4 py-2 bg-zinc-900 border border-white/5 rounded-full text-[10px] font-bold tracking-widest uppercase text-emerald-400 flex items-center gap-2">
              <span className="w-2 h-2 bg-emerald-400 rounded-full animate-pulse" />
              Live Analysis Active
            </div>
          </div>
        </div>
      </div>

      <div className="max-w-7xl mx-auto space-y-8">

        {/* ── SUMMARY CARDS ── */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
          <div className="bg-zinc-900/40 backdrop-blur-sm border border-white/5 p-6 rounded-3xl hover:bg-zinc-900/60 transition-all group overflow-hidden relative">
            <div className="absolute top-0 right-0 w-24 h-24 bg-emerald-500/5 blur-3xl rounded-full" />
            <div className="bg-emerald-500/10 p-3 rounded-2xl text-emerald-400 w-fit mb-4 group-hover:scale-110 transition-transform"><TrendingUp className="w-6 h-6" /></div>
            <h3 className="text-xs uppercase tracking-widest text-zinc-500 font-bold mb-1">Fastest Growing</h3>
            <p className="text-xl font-bold text-white mb-2 truncate" title={fastestGrowingCluster}>{fastestGrowingCluster}</p>
            <p className="text-xs text-zinc-500 leading-relaxed">Top emerging cluster from competitor signals.</p>
          </div>

          <div className="bg-zinc-900/40 backdrop-blur-sm border border-white/5 p-6 rounded-3xl hover:bg-zinc-900/60 transition-all group overflow-hidden relative">
            <div className="absolute top-0 right-0 w-24 h-24 bg-red-500/5 blur-3xl rounded-full" />
            <div className="bg-red-500/10 p-3 rounded-2xl text-red-400 w-fit mb-4 group-hover:scale-110 transition-transform"><AlertTriangle className="w-6 h-6" /></div>
            <h3 className="text-xs uppercase tracking-widest text-zinc-500 font-bold mb-1">Highest Saturation</h3>
            <p className="text-xl font-bold text-white mb-2 truncate" title={highestSaturation}>{highestSaturation}</p>
            <p className="text-xs text-zinc-500 leading-relaxed">Most crowded segment. Avoid direct competition.</p>
          </div>

          <div className="bg-zinc-900/40 backdrop-blur-sm border border-white/5 p-6 rounded-3xl hover:bg-zinc-900/60 transition-all group overflow-hidden relative">
            <div className="absolute top-0 right-0 w-24 h-24 bg-violet-500/5 blur-3xl rounded-full" />
            <div className="bg-violet-500/10 p-3 rounded-2xl text-violet-400 w-fit mb-4 group-hover:scale-110 transition-transform"><Lightbulb className="w-6 h-6" /></div>
            <h3 className="text-xs uppercase tracking-widest text-zinc-500 font-bold mb-1">Top Opportunity</h3>
            <p className="text-xl font-bold text-white mb-2 truncate" title={topOpportunity}>{topOpportunity !== "—" ? topOpportunity : "Run pipeline first"}</p>
            <p className="text-xs text-zinc-500 leading-relaxed">Highest ROI whitespace gap identified.</p>
          </div>

          <div className="bg-zinc-900/40 backdrop-blur-sm border border-white/5 p-6 rounded-3xl hover:bg-zinc-900/60 transition-all flex flex-col justify-center overflow-hidden relative">
            <div className="absolute top-0 right-0 w-24 h-24 bg-red-500/5 blur-3xl rounded-full" />
            <h3 className="text-xs uppercase tracking-widest text-zinc-500 font-bold mb-4">Clusters Tracked</h3>
            <p className="text-4xl font-black text-white">{trendKeys.length}</p>
            <p className="text-xs text-zinc-500 mt-2 uppercase tracking-widest font-bold">Active Themes</p>
          </div>
        </div>

        {/* ── ANALYSIS CHARTS ── */}
        <div>
          <h2 className="text-[10px] uppercase tracking-[0.3em] text-zinc-500 font-black mb-6 flex items-center gap-3">
            Market Analysis <div className="h-[1px] flex-1 bg-white/5" />
          </h2>
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">

            {/* Chart 1: Trend Over Time (live from /api/trends) */}
            <div className="bg-zinc-900/40 backdrop-blur-sm border border-white/5 p-8 rounded-[2.5rem] shadow-2xl">
              <div className="mb-8">
                <h3 className="font-bold text-xl text-white">Trend Over Time</h3>
                <p className="text-zinc-500 text-xs mt-1">Evolving messaging clusters</p>
                {trendKeys[0] && (
                  <div className="mt-4 bg-violet-500/10 text-violet-300 text-[10px] px-3 py-1.5 rounded-lg border border-violet-500/20 inline-block font-bold uppercase tracking-widest">
                    Rising: {trendKeys[0]}
                  </div>
                )}
              </div>
              <div className="h-64 w-full">
                {trendData.length > 0 ? (
                  <ResponsiveContainer width="100%" height="100%">
                    <LineChart data={trendData}>
                      <CartesianGrid strokeDasharray="3 3" vertical={false} stroke={chartStroke} />
                      <XAxis dataKey="time" axisLine={false} tickLine={false} tick={{ fontSize: 10, fill: axisColor, fontWeight: 600 }} />
                      <YAxis axisLine={false} tickLine={false} tick={{ fontSize: 10, fill: axisColor, fontWeight: 600 }} />
                      <Tooltip content={<CustomTooltip />} />
                      <Legend iconType="circle" wrapperStyle={{ fontSize: "10px", paddingTop: "20px", fontWeight: 600, textTransform: "uppercase", letterSpacing: "0.1em" }} />
                      {trendKeys.map((key, i) => (
                        <Line
                          key={key}
                          type="monotone"
                          dataKey={key}
                          stroke={CLUSTER_COLORS[i % CLUSTER_COLORS.length]}
                          strokeWidth={3}
                          dot={{ r: 0 }}
                          activeDot={{ r: 5, strokeWidth: 0 }}
                        />
                      ))}
                    </LineChart>
                  </ResponsiveContainer>
                ) : (
                  <div className="h-full flex items-center justify-center">
                    <p className="text-zinc-600 text-xs uppercase tracking-widest">No trend data — run pipeline first</p>
                  </div>
                )}
              </div>
            </div>

            {/* Chart 3: Messaging Distribution (live from /api/distribution) */}
            <div className="bg-zinc-900/40 backdrop-blur-sm border border-white/5 p-8 rounded-[2.5rem] shadow-2xl">
              <div className="mb-8">
                <h3 className="font-bold text-xl text-white">Theme Distribution</h3>
                <p className="text-zinc-500 text-xs mt-1">Dominant market narratives</p>
                {distributionData[0] && (
                  <div className="mt-4 bg-red-500/10 text-red-300 text-[10px] px-3 py-1.5 rounded-lg border border-red-500/20 inline-block font-bold uppercase tracking-widest">
                    Oversaturated: {distributionData[0].name}
                  </div>
                )}
              </div>
              <div className="h-64 w-full relative">
                {distributionData.length > 0 ? (
                  <>
                    <ResponsiveContainer width="100%" height="100%">
                      <PieChart>
                        <Pie data={distributionData} cx="50%" cy="50%" innerRadius={70} outerRadius={90} paddingAngle={8} dataKey="value" stroke="none">
                          {distributionData.map((entry, index) => (
                            <Cell key={`cell-${index}`} fill={entry.fill} />
                          ))}
                        </Pie>
                        <Tooltip content={<CustomTooltip />} />
                        <Legend iconType="circle" wrapperStyle={{ fontSize: "10px", fontWeight: 600, textTransform: "uppercase", letterSpacing: "0.1em" }} />
                      </PieChart>
                    </ResponsiveContainer>
                    <div className="absolute inset-0 flex flex-col items-center justify-center pointer-events-none mt-[-25px]">
                      <span className="text-3xl font-black text-white">{distributionData[0]?.value}%</span>
                      <span className="text-[10px] text-zinc-500 uppercase tracking-[0.2em] font-bold">{distributionData[0]?.name}</span>
                    </div>
                  </>
                ) : (
                  <div className="h-full flex items-center justify-center">
                    <p className="text-zinc-600 text-xs uppercase tracking-widest">No distribution data</p>
                  </div>
                )}
              </div>
            </div>

            {/* Chart 2: Competitor Positioning Map (live from /api/positioning) */}
            <div className="bg-zinc-900/40 backdrop-blur-sm border border-white/5 p-8 rounded-[2.5rem] shadow-2xl">
              <div className="mb-8">
                <h3 className="font-bold text-xl text-white">Positioning Map</h3>
                <p className="text-zinc-500 text-xs mt-1">Competitor strategy landscape</p>
                {positioningData[0] && (
                  <div className="mt-4 bg-violet-500/10 text-violet-300 text-[10px] px-3 py-1.5 rounded-lg border border-violet-500/20 inline-block font-bold uppercase tracking-widest">
                    Leader: {positioningData[0].name}
                  </div>
                )}
              </div>
              <div className="h-64 w-full relative">
                <span className="absolute bottom-1 left-1/2 -translate-x-1/2 text-[9px] font-bold tracking-[0.2em] uppercase text-zinc-600">Affordable ⟷ Premium</span>
                <span className="absolute left-1 top-1/2 -translate-y-1/2 -rotate-90 text-[9px] font-bold tracking-[0.2em] uppercase text-zinc-600">Feature ⟷ Outcome</span>
                {positioningData.length > 0 ? (
                  <ResponsiveContainer width="100%" height="100%">
                    <ScatterChart margin={{ top: 20, right: 20, bottom: 20, left: 20 }}>
                      <CartesianGrid strokeDasharray="3 3" stroke={chartStroke} />
                      <XAxis type="number" dataKey="x" name="Premium" domain={[0, 1]} hide />
                      <YAxis type="number" dataKey="y" name="Outcome" domain={[0, 1]} hide />
                      <ZAxis range={[150, 600]} />
                      <Tooltip content={<ScatterTooltip />} cursor={{ strokeDasharray: "3 3", stroke: "rgba(255,255,255,0.2)" }} />
                      {positioningData.map((entry, index) => (
                        <Scatter key={index} name={entry.name} data={[entry]} fill={entry.fill} />
                      ))}
                    </ScatterChart>
                  </ResponsiveContainer>
                ) : (
                  <div className="h-full flex items-center justify-center">
                    <p className="text-zinc-600 text-xs uppercase tracking-widest">No positioning data</p>
                  </div>
                )}
              </div>
            </div>
          </div>
        </div>

        {/* ── ACTION & STRATEGY ── */}
        <div>
          <h2 className="text-[10px] uppercase tracking-[0.3em] text-zinc-500 font-black mb-6 flex items-center gap-3">
            Action &amp; Strategy <div className="h-[1px] flex-1 bg-white/5" />
          </h2>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6 pb-20">

            {/* Chart 4: Opportunity / Whitespace (live from /api/charts/opportunity) */}
            <div className="bg-zinc-900/40 backdrop-blur-sm border border-white/5 p-8 rounded-[2.5rem] shadow-2xl overflow-hidden relative">
              <div className="flex justify-between items-start mb-10">
                <div>
                  <h3 className="font-bold text-xl text-white">Whitespace Opportunities</h3>
                  <p className="text-zinc-500 text-xs mt-1">Highest ROI focus areas</p>
                </div>
                {whitespaceData.find((d) => d.fill === QUADRANT_FILLS["BEST opportunity"]) && (
                  <div className="bg-emerald-500/10 text-emerald-300 text-[10px] px-3 py-1.5 rounded-lg border border-emerald-500/20 font-bold uppercase tracking-widest">
                    Target: {whitespaceData.find((d) => d.fill === QUADRANT_FILLS["BEST opportunity"])?.name}
                  </div>
                )}
              </div>
              <div className="h-72 w-full relative">
                <span className="absolute bottom-1 left-1/2 -translate-x-1/2 text-[9px] font-bold tracking-[0.2em] uppercase text-zinc-600">Low Comp ⟷ High Comp</span>
                <span className="absolute left-1 top-1/2 -translate-y-1/2 -rotate-90 text-[9px] font-bold tracking-[0.2em] uppercase text-zinc-600">Low Growth ⟷ High Growth</span>
                {whitespaceData.length > 0 ? (
                  <ResponsiveContainer width="100%" height="100%">
                    <ScatterChart margin={{ top: 20, right: 20, bottom: 20, left: 20 }}>
                      <CartesianGrid stroke={chartStroke} />
                      <ReferenceArea x1={0} x2={50} y1={50} y2={100} fill="#34d399" fillOpacity={0.03} />
                      <ReferenceArea x1={50} x2={100} y1={0} y2={50} fill="#f87171" fillOpacity={0.03} />
                      <XAxis type="number" dataKey="x" name="Competition" domain={[0, 100]} hide />
                      <YAxis type="number" dataKey="y" name="Growth" domain={[0, 100]} hide />
                      <ZAxis range={[300, 800]} />
                      <Tooltip content={<ScatterTooltip />} cursor={{ fill: "rgba(255,255,255,0.05)" }} />
                      {whitespaceData.map((entry, index) => (
                        <Scatter key={index} name={entry.name} data={[entry]} fill={entry.fill} />
                      ))}
                    </ScatterChart>
                  </ResponsiveContainer>
                ) : (
                  <div className="h-full flex items-center justify-center">
                    <p className="text-zinc-600 text-xs uppercase tracking-widest">No whitespace data — run pipeline first</p>
                  </div>
                )}
                <div className="absolute top-[15%] left-[15%] pointer-events-none opacity-40">
                  <span className="text-[9px] font-black tracking-widest uppercase text-emerald-400">Golden Opportunity</span>
                </div>
                <div className="absolute bottom-[15%] right-[15%] pointer-events-none opacity-40">
                  <span className="text-[9px] font-black tracking-widest uppercase text-red-400">Avoid Zone</span>
                </div>
              </div>
            </div>

            {/* Chart 5: Competitor Comparison (live from /api/charts/competitor-scores) */}
            <div className="bg-zinc-900/40 backdrop-blur-sm border border-white/5 p-8 rounded-[2.5rem] shadow-2xl">
              <div className="flex justify-between items-start mb-10">
                <div>
                  <h3 className="font-bold text-xl text-white">Competitor Strength</h3>
                  <p className="text-zinc-500 text-xs mt-1">Cross-brand pillar indexing</p>
                </div>
                <div className="bg-blue-500/10 text-blue-300 text-[10px] px-3 py-1.5 rounded-lg border border-blue-500/20 font-bold uppercase tracking-widest">
                  Scoring: 4 Pillars
                </div>
              </div>
              <div className="h-72 w-full">
                {comparisonData.length > 0 ? (
                  <ResponsiveContainer width="100%" height="100%">
                    <BarChart data={comparisonData} margin={{ top: 10, right: 0, left: -20, bottom: 0 }}>
                      <CartesianGrid strokeDasharray="3 3" vertical={false} stroke={chartStroke} />
                      <XAxis dataKey="name" axisLine={false} tickLine={false} tick={{ fontSize: 10, fill: axisColor, fontWeight: 600 }} />
                      <YAxis axisLine={false} tickLine={false} tick={{ fontSize: 10, fill: axisColor, fontWeight: 600 }} />
                      <Tooltip content={<CustomTooltip />} cursor={{ fill: "rgba(255,255,255,0.03)" }} />
                      <Legend wrapperStyle={{ fontSize: "10px", paddingTop: "15px", fontWeight: 600, textTransform: "uppercase", letterSpacing: "0.1em" }} />
                      <Bar dataKey="pricing" name="Pricing" fill={COMPETITOR_COLORS.pricing} radius={[6, 6, 0, 0]} barSize={16} />
                      <Bar dataKey="quality" name="Quality" fill={COMPETITOR_COLORS.quality} radius={[6, 6, 0, 0]} barSize={16} />
                      <Bar dataKey="ai" name="AI / Tech" fill={COMPETITOR_COLORS.ai} radius={[6, 6, 0, 0]} barSize={16} />
                      <Bar dataKey="convenience" name="Convenience" fill={COMPETITOR_COLORS.convenience} radius={[6, 6, 0, 0]} barSize={16} />
                    </BarChart>
                  </ResponsiveContainer>
                ) : (
                  <div className="h-full flex items-center justify-center">
                    <p className="text-zinc-600 text-xs uppercase tracking-widest">No competitor data</p>
                  </div>
                )}
              </div>
            </div>
          </div>
        </div>

        {/* 🔹 SUGGESTED EXPERIMENTS */}
        <div>
          <h2 className="text-[10px] uppercase tracking-[0.3em] text-zinc-500 font-black mb-6 flex items-center gap-3">
            Suggested Experiments <div className="h-[1px] flex-1 bg-white/5" />
          </h2>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6 pb-20">

            {/* Experiment 1 */}
            <div className="bg-zinc-900/40 backdrop-blur-sm border border-white/5 p-8 rounded-[2.5rem] shadow-2xl hover:bg-zinc-900/60 transition-all group overflow-hidden relative">
              <div className="absolute top-0 right-0 w-32 h-32 bg-emerald-500/5 blur-3xl rounded-full" />
              <div className="flex items-center gap-2 mb-4">
                <span className="bg-emerald-500/10 text-emerald-300 text-[10px] px-3 py-1 rounded-lg border border-emerald-500/20 font-bold uppercase tracking-widest">Low Risk</span>
                <span className="bg-violet-500/10 text-violet-300 text-[10px] px-3 py-1 rounded-lg border border-violet-500/20 font-bold uppercase tracking-widest">Trust: 0.22</span>
              </div>
              <h3 className="font-bold text-lg text-white mb-2">Deploy AI-Powered Messaging</h3>
              <p className="text-zinc-500 text-xs leading-relaxed mb-6">
                Leverage AI-driven communication to differentiate from pricing-focused competitors. Intelligence Layer shows 3x growth momentum with low saturation.
              </p>
              <div className="flex flex-wrap gap-2 mb-6">
                <span className="text-[9px] px-2 py-1 rounded-md bg-white/5 text-zinc-400 font-medium">Intelligence Layer</span>
                <span className="text-[9px] px-2 py-1 rounded-md bg-white/5 text-zinc-400 font-medium">Decision Layer</span>
                <span className="text-[9px] px-2 py-1 rounded-md bg-white/5 text-zinc-400 font-medium">Trust Layer</span>
              </div>
              <Link href="/experiment-builder" className="inline-flex items-center gap-2 text-emerald-400 text-xs font-bold uppercase tracking-widest hover:gap-3 transition-all">
                Launch Experiment <span className="text-lg">→</span>
              </Link>
            </div>

            {/* Experiment 2 */}
            <div className="bg-zinc-900/40 backdrop-blur-sm border border-white/5 p-8 rounded-[2.5rem] shadow-2xl hover:bg-zinc-900/60 transition-all group overflow-hidden relative">
              <div className="absolute top-0 right-0 w-32 h-32 bg-amber-500/5 blur-3xl rounded-full" />
              <div className="flex items-center gap-2 mb-4">
                <span className="bg-amber-500/10 text-amber-300 text-[10px] px-3 py-1 rounded-lg border border-amber-500/20 font-bold uppercase tracking-widest">Medium Risk</span>
                <span className="bg-violet-500/10 text-violet-300 text-[10px] px-3 py-1 rounded-lg border border-violet-500/20 font-bold uppercase tracking-widest">Trust: 0.51</span>
              </div>
              <h3 className="font-bold text-lg text-white mb-2">Premium Verified Professionals Tier</h3>
              <p className="text-zinc-500 text-xs leading-relaxed mb-6">
                Launch a verified-only premium service tier. Decision Layer recommends targeting high-value urban segments. Trust Layer flags moderate positioning mismatch.
              </p>
              <div className="flex flex-wrap gap-2 mb-6">
                <span className="text-[9px] px-2 py-1 rounded-md bg-white/5 text-zinc-400 font-medium">Intelligence Layer</span>
                <span className="text-[9px] px-2 py-1 rounded-md bg-white/5 text-zinc-400 font-medium">Decision Layer</span>
                <span className="text-[9px] px-2 py-1 rounded-md bg-white/5 text-zinc-400 font-medium">Trust Layer</span>
              </div>
              <Link href="/experiment-builder" className="inline-flex items-center gap-2 text-amber-400 text-xs font-bold uppercase tracking-widest hover:gap-3 transition-all">
                Launch Experiment <span className="text-lg">→</span>
              </Link>
            </div>

            {/* Experiment 3 */}
            <div className="bg-zinc-900/40 backdrop-blur-sm border border-white/5 p-8 rounded-[2.5rem] shadow-2xl hover:bg-zinc-900/60 transition-all group overflow-hidden relative">
              <div className="absolute top-0 right-0 w-32 h-32 bg-red-500/5 blur-3xl rounded-full" />
              <div className="flex items-center gap-2 mb-4">
                <span className="bg-red-500/10 text-red-300 text-[10px] px-3 py-1 rounded-lg border border-red-500/20 font-bold uppercase tracking-widest">High Risk</span>
                <span className="bg-violet-500/10 text-violet-300 text-[10px] px-3 py-1 rounded-lg border border-violet-500/20 font-bold uppercase tracking-widest">Trust: 0.78</span>
              </div>
              <h3 className="font-bold text-lg text-white mb-2">Aggressive Discount Campaign</h3>
              <p className="text-zinc-500 text-xs leading-relaxed mb-6">
                Undercut competitor pricing to capture market share. Trust Layer warns of high saturation and low trend momentum. Decision Layer advises against for premium clients.
              </p>
              <div className="flex flex-wrap gap-2 mb-6">
                <span className="text-[9px] px-2 py-1 rounded-md bg-white/5 text-zinc-400 font-medium">Intelligence Layer</span>
                <span className="text-[9px] px-2 py-1 rounded-md bg-white/5 text-zinc-400 font-medium">Decision Layer</span>
                <span className="text-[9px] px-2 py-1 rounded-md bg-white/5 text-zinc-400 font-medium">Trust Layer</span>
              </div>
              <Link href="/experiment-builder" className="inline-flex items-center gap-2 text-red-400 text-xs font-bold uppercase tracking-widest hover:gap-3 transition-all">
                Launch Experiment <span className="text-lg">→</span>
              </Link>
            </div>

          </div>
        </div>
      </div>

      <CopilotChat
        selectedExperiment={selectedExp || undefined}
        experiments={experiments}
      />
    </div>
  );
}
