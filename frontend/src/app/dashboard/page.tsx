"use client";

// Force Next.js to never cache this page — always render fresh
export const dynamic = "force-dynamic";

import React, { useState } from "react";
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
import { motion } from "framer-motion";
import { CopilotChat } from "@/components/CopilotChat";
import { useEffect } from "react";


// ─────────────────────────────────────────────
// Types
// ─────────────────────────────────────────────

type TrendPoint = { time: string;[key: string]: string | number };
type PositioningPoint = { name: string; x: number; y: number; dominant_cluster: string; fill: string };
type DistributionPoint = { name: string; value: number; fill: string };
type WhitespacePoint = { competitor: string; x: number; y: number; fill: string };
type ThemeGroupEntry = { competitor: string; category: string; percentage: number };
type StrengthGroupEntry = { competitor: string; segments: { label: string; value: number }[] };

interface Experiment {
  title?: string;
  category?: string;
  insight: string;
  cluster_id: string;
  cluster_name?: string;
  trend: string;
  confidence: number;
  confidence_label?: string;
  confidence_score?: number;
  risk: number;
  risk_label?: string;
  recommended_action: string;
  experiment?: string;
  hypothesis?: string;
  metric?: string;
  expected_impact?: string;
  evidence: string[];
  traceability?: {
    summary?: string;
    total_signals?: number;
    sample_signals?: string[];
    competitor_ids?: string[];
    reasons?: string[];
  };
}

const getConfidenceLabel = (exp: Experiment) => {
  const explicitLabel = exp.confidence_label?.trim();
  if (explicitLabel && explicitLabel !== "0%") {
    return explicitLabel;
  }

  const numericConfidence = [exp.confidence_score, exp.confidence]
    .find((value) => Number.isFinite(value) && Number(value) > 0);

  if (numericConfidence !== undefined) {
    const pct = Math.round(Math.max(0.6, Math.min(Number(numericConfidence), 0.95)) * 100);
    return `${pct}%`;
  }

  const riskFallback = Number.isFinite(exp.risk) ? Number(exp.risk) : 0.5;
  const pct = Math.round(Math.max(0.6, Math.min(1 - riskFallback, 0.95)) * 100);
  return `${pct}%`;
};

// ─────────────────────────────────────────────
// Config
// ─────────────────────────────────────────────

const CLUSTER_COLORS = ["#a78bfa", "#f87171", "#60a5fa", "#fbbf24", "#34d399", "#f472b6"];
const COMP_BRAND_COLORS: Record<string, string> = {
  "Urban Company": "#a78bfa", // Purple
  "Housejoy": "#34d399", // Green
  "House Joy": "#34d399", // Green
  "Sulekha": "#fbbf24", // Yellow
};
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

const DISPLAY_COMPETITORS = ["House Joy", "Sulekha", "Urban Company"];

const normalizeCompetitorName = (name: string) => {
  const normalized = name.replace(/[^a-z]/gi, "").toLowerCase();
  if (normalized === "urbancompany") return "Urban Company";
  if (normalized === "housejoy") return "House Joy";
  if (normalized === "sulekha") return "Sulekha";
  return name;
};

const toApiCompetitorName = (name: string) => {
  if (name === "House Joy") return "Housejoy";
  return name;
};

// ─────────────────────────────────────────────
// Mock Data
// ─────────────────────────────────────────────

const MOCK_TREND_DATA: TrendPoint[] = [
  { time: "Jan", "AI & Automation": 12, "Premium Quality": 28, "Price & Value": 45, "Convenience": 18, "Trust & Safety": 9 },
  { time: "Feb", "AI & Automation": 18, "Premium Quality": 31, "Price & Value": 42, "Convenience": 22, "Trust & Safety": 11 },
  { time: "Mar", "AI & Automation": 27, "Premium Quality": 29, "Price & Value": 38, "Convenience": 25, "Trust & Safety": 14 },
  { time: "Apr", "AI & Automation": 35, "Premium Quality": 33, "Price & Value": 35, "Convenience": 28, "Trust & Safety": 16 },
  { time: "May", "AI & Automation": 48, "Premium Quality": 30, "Price & Value": 31, "Convenience": 33, "Trust & Safety": 20 },
  { time: "Jun", "AI & Automation": 62, "Premium Quality": 27, "Price & Value": 28, "Convenience": 40, "Trust & Safety": 24 },
  { time: "Jul", "AI & Automation": 74, "Premium Quality": 32, "Price & Value": 25, "Convenience": 45, "Trust & Safety": 29 },
];
const MOCK_TREND_KEYS = ["AI & Automation", "Premium Quality", "Price & Value", "Convenience", "Trust & Safety"];

const MOCK_POSITIONING_DATA: PositioningPoint[] = [
  { name: "UrbanCompany", x: 0.78, y: 0.82, dominant_cluster: "AI & Automation", fill: "#a78bfa" },
  { name: "Housejoy", x: 0.35, y: 0.55, dominant_cluster: "Price & Value", fill: "#f87171" },
  { name: "Helpr", x: 0.52, y: 0.40, dominant_cluster: "Convenience", fill: "#60a5fa" },
  { name: "Zimmber", x: 0.22, y: 0.30, dominant_cluster: "Price & Value", fill: "#fbbf24" },
  { name: "TaskBob", x: 0.63, y: 0.68, dominant_cluster: "Premium Quality", fill: "#34d399" },
];

const MOCK_DISTRIBUTION_DATA: DistributionPoint[] = [
  { name: "Price & Value", value: 38, fill: "#f87171" },
  { name: "Convenience", value: 24, fill: "#60a5fa" },
  { name: "Premium Quality", value: 18, fill: "#34d399" },
  { name: "AI & Automation", value: 12, fill: "#a78bfa" },
  { name: "Trust & Safety", value: 8, fill: "#f472b6" },
];



const MOCK_EXPERIMENTS: Experiment[] = [
  {
    insight: "UrbanCompany tested 30-min service guarantee in Bangalore last month → +18% increase in repeat bookings",
    cluster_id: "Instant Booking Guarantee",
    trend: "rising",
    confidence: 0.92,
    risk: 0.15,
    recommended_action: "Implement a 30-minute service guarantee to drive repeat customer behavior. Optimized for high-density urban zones.",
    evidence: ["sig-1", "sig-2"],
  },
  {
    insight: "UrbanCompany expanded “UC Plus” subscription aggressively last month → +40% increase in monthly recurring revenue",
    cluster_id: "Subscription Home Services",
    trend: "rising",
    confidence: 0.88,
    risk: 0.45,
    recommended_action: "Launch a recurring service model to stabilize monthly revenue and increase LTV. Target UC Plus lookalikes.",
    evidence: ["sig-3", "sig-4"],
  },
  {
    insight: "UrbanCompany experimented with peak-hour surge pricing 10 days ago → +15% revenue uplift but slight user drop-off",
    cluster_id: "Dynamic Surge Pricing",
    trend: "declining",
    confidence: 0.65,
    risk: 0.82,
    recommended_action: "Optimize unit economics by introducing surge pricing during hyper-peak windows. Balance revenue with churn.",
    evidence: ["sig-5", "sig-6"],
  },
];

// ─────────────────────────────────────────────
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
    const name = data.competitor || data.name || "Unknown";
    const xLabel = data.competitor ? "Competition" : "X";
    const yLabel = data.competitor ? "Growth" : "Y";

    return (
      <div className="bg-zinc-900/95 backdrop-blur-md border border-white/10 p-4 rounded-xl shadow-2xl text-sm ring-1 ring-white/5">
        <p className="font-bold text-white mb-2 pb-2 border-b border-white/5">{name}</p>
        <div className="space-y-1">
          {data.dominant_cluster && (
            <div className="flex items-center justify-between gap-4">
              <span className="text-zinc-400">Cluster:</span>
              <span className="text-white font-mono text-xs">{data.dominant_cluster}</span>
            </div>
          )}
          <div className="flex items-center justify-between gap-4">
            <span className="text-zinc-400">{xLabel}:</span>
            <span className="text-white font-mono">{data.x}</span>
          </div>
          <div className="flex items-center justify-between gap-4">
            <span className="text-zinc-400">{yLabel}:</span>
            <span className="text-white font-mono">{data.y}</span>
          </div>
        </div>
      </div>
    );
  }
  return null;
};

// ─────────────────────────────────────────────
// Dashboard Component
// ─────────────────────────────────────────────

export default function Dashboard() {
  const [experiments, setExperiments] = useState<Experiment[]>([]);
  const [selectedExp, setSelectedExp] = useState<string | null>(null);


  const [selectedCompetitor, setSelectedCompetitor] = useState("ALL");
  const [availableCompetitors, setAvailableCompetitors] = useState<string[]>([]);
  const [analysisData, setAnalysisData] = useState<{
    trend: { data: any[]; keys: string[] };
    themes: any[];
    themeCompetitors: string[];
    positioning: any[];
    whitespace: any[];
    strength: any[];
    strengthLabels: string[];
  } | null>(null);
  const [summary, setSummary] = useState<any>(null);

  useEffect(() => {
    fetch("/api/summary-insights")
      .then(res => res.json())
      .then(setSummary)
      .catch(e => console.error("Summary fetch error", e));

    fetch("/api/experiments")
      .then(async (res) => {
        const rawText = await res.text();
        let payload: any;
        try {
          payload = rawText ? JSON.parse(rawText) : [];
        } catch {
          throw new Error(rawText || "API returned non-JSON response");
        }

        if (!res.ok) {
          throw new Error(payload?.error || "Experiments API error");
        }

        return payload;
      })
      .then(data => {
        const experimentList = Array.isArray(data) ? data : Array.isArray(data?.experiments) ? data.experiments : [];
        console.log("Suggested experiment payload", experimentList);

        if (experimentList.length === 0) {
            console.warn("No structured experiments were returned by /api/experiments");
        }
        setExperiments(experimentList.slice(0, 3));
      })
      .catch(e => console.error("Experiments fetch error", e));
  }, []);


  useEffect(() => {
    fetch(`/api/competitor-analysis?competitor=${encodeURIComponent(toApiCompetitorName(selectedCompetitor))}`)
      .then((res) => {
        if (!res.ok) throw new Error("API error");
        return res.json();
      })
      .then((data) => {
        // Transform trend data into Recharts format (pivot by month)
        const trendMap: Record<string, any> = {};
        const compsInTrend = new Set<string>();
        for (const item of data.trend) {
          if (!trendMap[item.month]) trendMap[item.month] = { time: item.month };
          trendMap[item.month][item.competitor] = item.activity;
          compsInTrend.add(item.competitor);
        }

        // Apply advanced smoothing and log-scaling for 4-year visual balance
        const sortedMonths = Object.keys(trendMap).sort();
        const smoothedData = sortedMonths.map((month, i, arr) => {
          const current = trendMap[month];
          const smoothed: any = { ...current };
          
          Array.from(compsInTrend).forEach(comp => {
            // Gap filling: If 0, try to average neighbors
            let val = current[comp] || 0;
            if (val === 0 && i > 0 && i < arr.length - 1) {
              const pVal = trendMap[arr[i-1]][comp] || 0;
              const nVal = trendMap[arr[i+1]][comp] || 0;
              if (pVal > 0 && nVal > 0) val = (pVal + nVal) / 2;
            }

            // 3-point Moving Average
            const prev = i > 0 ? (trendMap[arr[i-1]][comp] !== undefined ? trendMap[arr[i-1]][comp] : val) : val;
            const next = i < arr.length - 1 ? (trendMap[arr[i+1]][comp] !== undefined ? trendMap[arr[i+1]][comp] : val) : val;
            const avg = (prev + val + next) / 3;

            // Log-scaling: log(1 + activity) to normalize heights across competitors
            smoothed[comp] = parseFloat(Math.log1p(avg).toFixed(3));
          });
          return smoothed;
        });

        const rawThemeGroups = data.theme_groups || {};
        const themeGroups = Object.entries(rawThemeGroups).reduce((acc: Record<string, ThemeGroupEntry[]>, [competitorName, entries]: [string, any]) => {
          const normalizedName = normalizeCompetitorName(competitorName);
          if (!acc[normalizedName]) {
            acc[normalizedName] = [];
          }
          acc[normalizedName].push(
            ...((entries || []) as ThemeGroupEntry[]).map((entry) => ({
              ...entry,
              competitor: normalizedName,
            }))
          );
          return acc;
        }, {});
        const themeCompetitors = DISPLAY_COMPETITORS.filter((competitorName) => themeGroups[competitorName]?.length);
        if (themeCompetitors.length > 0) {
          setAvailableCompetitors(themeCompetitors);
        }

        const themeRows = new Map<string, any>();
        themeCompetitors.forEach((competitorName) => {
          const entries: ThemeGroupEntry[] = themeGroups[competitorName] || [];
          entries.forEach((entry) => {
            if (!themeRows.has(entry.category)) {
              themeRows.set(entry.category, { category: entry.category });
            }
            themeRows.get(entry.category)[competitorName] = entry.percentage;
          });
        });

        const processedThemes =
          selectedCompetitor === "ALL"
            ? Array.from(themeRows.values())
            : ((themeGroups[selectedCompetitor] || []) as ThemeGroupEntry[]).map((entry, index) => ({
                name: entry.category,
                value: entry.percentage,
                fill: PIE_COLORS[index % PIE_COLORS.length],
              }));

        // Positioning
        const processedPositioning = data.positioning.map((p: any) => ({
            name: normalizeCompetitorName(p.competitor),
            x: p.price_index,
            y: p.trust_score,
            z: p.activity_score,
            fill: COMP_BRAND_COLORS[normalizeCompetitorName(p.competitor)] || "#60a5fa"
        }));

        const processedWhitespace = data.whitespace
            .filter((w: any) => w.competitor)
            .map((w: any) => ({
                competitor: normalizeCompetitorName(w.competitor),
                x: w.x,
                y: w.y,
                fill: COMP_BRAND_COLORS[normalizeCompetitorName(w.competitor)] || "#60a5fa"
            }));

        const normalizedStrengthGroups = ((data.strength_groups || []) as StrengthGroupEntry[]).reduce((acc: StrengthGroupEntry[], group) => {
          const normalizedName = normalizeCompetitorName(group.competitor);
          const existing = acc.find((entry) => entry.competitor === normalizedName);
          if (existing) {
            group.segments.forEach((segment) => {
              const current = existing.segments.find((item) => item.label === segment.label);
              if (current) {
                current.value += segment.value;
              } else {
                existing.segments.push({ ...segment });
              }
            });
          } else {
            acc.push({
              competitor: normalizedName,
              segments: group.segments.map((segment) => ({ ...segment })),
            });
          }
          return acc;
        }, []).filter((group) => DISPLAY_COMPETITORS.includes(group.competitor));

        const processedStrength = normalizedStrengthGroups.map((group) => {
          const row: Record<string, string | number> = { name: group.competitor };
          group.segments.forEach((segment) => {
            row[segment.label] = Number(segment.value.toFixed(2));
          });
          return row;
        });

        setAnalysisData({
          trend: { data: smoothedData, keys: Array.from(compsInTrend) },
          themes: processedThemes,
          themeCompetitors,
          positioning: processedPositioning,
          whitespace: processedWhitespace,
          strength: processedStrength,
          strengthLabels: data.strength_labels || []
        });
      })
      .catch((e) => console.error("Analysis fetch error", e));
  }, [selectedCompetitor]);

  const strengthKeys = analysisData?.strengthLabels?.length
    ? [
        ...analysisData.strengthLabels,
        ...(analysisData?.strength?.some((row: any) => Number(row.Others || 0) > 0) ? ["Others"] : []),
      ]
    : (analysisData?.strength && analysisData.strength.length > 0)
      ? Object.keys(analysisData.strength[0]).filter(k => k !== "name")
    : [];

  const chartStroke = "rgba(255, 255, 255, 0.05)";
  const axisColor = "rgba(255, 255, 255, 0.4)";

  // Derived summary values from dynamic API
  const fastestGrowingName = summary?.fastest_growing?.name || "Loading...";
  const fastestGrowingGrowth = summary?.fastest_growing?.growth || 0;
  const highestSaturation = summary?.saturation?.theme || "Loading...";
  const topOpportunity = summary?.opportunity?.theme || "Loading...";
  const trackedClusters = summary?.clusters?.count || 0;

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
          <p className="text-zinc-400 text-sm mt-2 max-w-md leading-relaxed">
            Live competitive insights and strategic recommendations with AI-driven analysis.
          </p>
        </div>
        <div className="flex items-center gap-3">
          <select 
            className="px-3 py-2 bg-zinc-900 border border-white/10 rounded-xl text-xs font-bold text-white focus:outline-none focus:border-violet-500"
            value={selectedCompetitor}
            onChange={(e) => setSelectedCompetitor(e.target.value)}
          >
            <option value="ALL">All Competitors</option>
            {availableCompetitors.map((competitor) => (
              <option key={competitor} value={competitor}>{competitor}</option>
            ))}
          </select>
          
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
            <p className="text-xl font-bold text-white mb-2 truncate" title={fastestGrowingName}>{fastestGrowingName}</p>
            <p className="text-xs text-zinc-500 leading-relaxed">+{fastestGrowingGrowth} growth in last 30 days.</p>
          </div>

          <div className="bg-zinc-900/40 backdrop-blur-sm border border-white/5 p-6 rounded-3xl hover:bg-zinc-900/60 transition-all group overflow-hidden relative">
            <div className="absolute top-0 right-0 w-24 h-24 bg-red-500/5 blur-3xl rounded-full" />
            <div className="bg-red-500/10 p-3 rounded-2xl text-red-400 w-fit mb-4 group-hover:scale-110 transition-transform"><AlertTriangle className="w-6 h-6" /></div>
            <h3 className="text-xs uppercase tracking-widest text-zinc-500 font-bold mb-1">Highest Saturation</h3>
            <p className="text-xl font-bold text-white mb-2 truncate" title={highestSaturation}>{highestSaturation}</p>
            <p className="text-xs text-zinc-500 leading-relaxed">Most crowded segment.</p>
          </div>

          <div className="bg-zinc-900/40 backdrop-blur-sm border border-white/5 p-6 rounded-3xl hover:bg-zinc-900/60 transition-all group overflow-hidden relative">
            <div className="absolute top-0 right-0 w-24 h-24 bg-violet-500/5 blur-3xl rounded-full" />
            <div className="bg-violet-500/10 p-3 rounded-2xl text-violet-400 w-fit mb-4 group-hover:scale-110 transition-transform"><Lightbulb className="w-6 h-6" /></div>
            <h3 className="text-xs uppercase tracking-widest text-zinc-500 font-bold mb-1">Top Opportunity</h3>
            <p className="text-xl font-bold text-white mb-2 truncate" title={topOpportunity}>{topOpportunity}</p>
            <p className="text-xs text-zinc-500 leading-relaxed">Low competition, high potential.</p>
          </div>

          <div className="bg-zinc-900/40 backdrop-blur-sm border border-white/5 p-6 rounded-3xl hover:bg-zinc-900/60 transition-all flex flex-col justify-center overflow-hidden relative">
            <div className="absolute top-0 right-0 w-24 h-24 bg-violet-500/5 blur-3xl rounded-full" />
            <h3 className="text-xs uppercase tracking-widest text-zinc-500 font-bold mb-4">Clusters Tracked</h3>
            <p className="text-4xl font-black text-white">{trackedClusters}</p>
            <p className="text-xs text-zinc-500 mt-2 uppercase tracking-widest font-bold">Active Themes Identifed</p>
          </div>
        </div>

        {/* ── ANALYSIS CHARTS ── */}
        <div>
          <h2 className="text-[20px] uppercase tracking-[0.3em] text-zinc-300 font-black mb-6 flex items-center gap-3">
            Market Analysis <div className="h-[1px] flex-1 bg-white/5" />
          </h2>
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">

            {/* Chart 1: Trend Over Time */}
            <div className="bg-zinc-900/40 backdrop-blur-sm border border-white/5 p-8 rounded-[2.5rem] shadow-2xl">
              <div className="mb-8">
                <h3 className="font-bold text-xl text-white">Momentum Over Time</h3>
                <p className="text-zinc-500 text-[10px] uppercase tracking-widest mt-1 opacity-70">4-year activity evolution</p>
                <div className="mt-4 bg-violet-500/10 text-violet-300 text-[10px] px-3 py-1.5 rounded-lg border border-violet-500/20 inline-block font-bold uppercase tracking-widest">
                  Competitor Growth Trends
                </div>
              </div>
              <div className="h-64 w-full">
                <ResponsiveContainer width="100%" height="100%">
                  <LineChart data={analysisData ? analysisData.trend.data : MOCK_TREND_DATA}>
                    <CartesianGrid strokeDasharray="3 3" vertical={false} stroke={chartStroke} opacity={0.1} />
                    <XAxis 
                      dataKey={analysisData ? "time" : "time"} 
                      axisLine={false} 
                      tickLine={false} 
                      interval={6}
                      tick={{ fontSize: 9, fill: axisColor, fontWeight: 600 }} 
                    />
                    <YAxis 
                      axisLine={false} 
                      tickLine={false} 
                      tick={{ fontSize: 9, fill: axisColor, fontWeight: 600 }}
                      domain={[0, 'auto']}
                      label={{ value: 'Activity Score', angle: -90, position: 'insideLeft', style: { fill: axisColor, fontSize: '10px', fontWeight: 600, textTransform: 'uppercase', letterSpacing: '0.1em' }, offset: 10 }}
                      width={45}
                    />
                    <Tooltip content={<CustomTooltip />} />
                    <Legend iconType="circle" wrapperStyle={{ fontSize: "10px", paddingTop: "20px", fontWeight: 600, textTransform: "uppercase", letterSpacing: "0.1em", lineHeight: "24px" }} />
                    {(analysisData ? analysisData.trend.keys : MOCK_TREND_KEYS).map((key: string, i: number) => (
                      <Line
                        key={key}
                        type="monotone"
                        dataKey={key}
                        stroke={COMP_BRAND_COLORS[key] || CLUSTER_COLORS[i % CLUSTER_COLORS.length]}
                        strokeWidth={4}
                        dot={false}
                        activeDot={{ r: 4, strokeWidth: 0 }}
                      />
                    ))}
                  </LineChart>
                </ResponsiveContainer>
              </div>
            </div>

            {/* Chart 2: Theme Distribution */}
            <div className="bg-zinc-900/40 backdrop-blur-sm border border-white/5 p-8 rounded-[2.5rem] shadow-2xl">
              <div className="mb-8">
                <h3 className="font-bold text-xl text-white">Theme Distribution</h3>
                <p className="text-zinc-500 text-xs mt-1">Dominant market narratives</p>
                <div className="mt-4 bg-red-500/10 text-red-300 text-[10px] px-3 py-1.5 rounded-lg border border-red-500/20 inline-block font-bold uppercase tracking-widest">
                  Oversaturated: {(analysisData ? (selectedCompetitor === "ALL" ? analysisData.themes[0]?.category : analysisData.themes[0]?.name) : MOCK_DISTRIBUTION_DATA[0].name) || "—"}
                </div>
              </div>
              <div className="h-64 w-full relative">
                {selectedCompetitor === "ALL" ? (
                  <ResponsiveContainer width="100%" height="100%">
                    <BarChart data={analysisData ? analysisData.themes : []}>
                      <CartesianGrid strokeDasharray="3 3" vertical={false} stroke={chartStroke} />
                      <XAxis dataKey="category" axisLine={false} tickLine={false} tick={{ fontSize: 10, fill: axisColor, fontWeight: 600 }} />
                      <YAxis axisLine={false} tickLine={false} tick={{ fontSize: 10, fill: axisColor, fontWeight: 600 }} />
                      <Tooltip content={<CustomTooltip />} />
                      <Legend iconType="circle" wrapperStyle={{ fontSize: "10px", paddingTop: "20px", fontWeight: 600, textTransform: "uppercase", letterSpacing: "0.1em", lineHeight: "24px" }} />
                      {(analysisData?.themeCompetitors || []).map((competitor, index) => (
                        <Bar
                          key={competitor}
                          dataKey={competitor}
                          stackId="a"
                          fill={COMP_BRAND_COLORS[competitor] || CLUSTER_COLORS[index % CLUSTER_COLORS.length]}
                        />
                      ))}
                    </BarChart>
                  </ResponsiveContainer>
                ) : (
                  <>
                    <ResponsiveContainer width="100%" height="100%">
                      <PieChart>
                        <Pie data={analysisData ? analysisData.themes : MOCK_DISTRIBUTION_DATA} cx="50%" cy="50%" innerRadius={70} outerRadius={90} paddingAngle={8} dataKey="value" stroke="none">
                          {(analysisData ? analysisData.themes : MOCK_DISTRIBUTION_DATA).map((entry: any, index: number) => (
                            <Cell key={`cell-${index}`} fill={entry.fill} />
                          ))}
                        </Pie>
                        <Tooltip content={<CustomTooltip />} />
                        <Legend iconType="circle" wrapperStyle={{ fontSize: "10px", fontWeight: 600, textTransform: "uppercase", letterSpacing: "0.1em", lineHeight: "24px" }} />
                      </PieChart>
                    </ResponsiveContainer>
                    <div className="absolute inset-0 flex flex-col items-center justify-center pointer-events-none pb-[70px]">
                      <span className="text-3xl font-black text-white">{(analysisData ? analysisData.themes : MOCK_DISTRIBUTION_DATA)[0]?.value?.toFixed(1) || 0}%</span>
                      <span className="text-[10px] text-zinc-500 uppercase tracking-[0.2em] font-bold">{(analysisData ? analysisData.themes : MOCK_DISTRIBUTION_DATA)[0]?.name || "—"}</span>
                    </div>
                  </>
                )}
              </div>
            </div>

            {/* Chart 3: Competitor Positioning Map */}
            <div className="bg-zinc-900/40 backdrop-blur-sm border border-white/5 p-8 rounded-[2.5rem] shadow-2xl">
              <div className="mb-8">
                <h3 className="font-bold text-xl text-white">Positioning Map</h3>
                <p className="text-zinc-500 text-xs mt-1">Competitor strategy landscape</p>
                <div className="mt-4 bg-violet-500/10 text-violet-300 text-[10px] px-3 py-1.5 rounded-lg border border-violet-500/20 inline-block font-bold uppercase tracking-widest">
                  Leader: {MOCK_POSITIONING_DATA[0].name}
                </div>
              </div>
              <div className="h-64 w-full relative">
                <span className="absolute bottom-1 left-1/2 -translate-x-1/2 text-[9px] font-bold tracking-[0.2em] uppercase text-zinc-600">Affordable ⟷ Premium</span>
                <span className="absolute left-1 top-1/2 -translate-y-1/2 -rotate-90 text-[9px] font-bold tracking-[0.2em] uppercase text-zinc-600">Feature ⟷ Outcome</span>
                <ResponsiveContainer width="100%" height="100%">
                  <ScatterChart margin={{ top: 20, right: 20, bottom: 20, left: 20 }}>
                    <CartesianGrid strokeDasharray="3 3" stroke={chartStroke} />
                    <XAxis type="number" dataKey="x" name="Premium" domain={[0, 1]} hide />
                    <YAxis type="number" dataKey="y" name="Outcome" domain={[0, 1]} hide />
                    <ZAxis range={[150, 600]} />
                    <Tooltip content={<ScatterTooltip />} cursor={{ strokeDasharray: "3 3", stroke: "rgba(255,255,255,0.2)" }} />
                    {(analysisData ? analysisData.positioning : MOCK_POSITIONING_DATA).map((entry: any, index: number) => (
                      <Scatter key={index} name={entry.name} data={[entry]} fill={entry.fill} />
                    ))}
                  </ScatterChart>
                </ResponsiveContainer>
              </div>
            </div>
          </div>
        </div>

        {/* ── ACTION & STRATEGY ── */}
        <div>
          <h2 className="text-[20px] uppercase tracking-[0.3em] text-zinc-300 font-black mb-6 flex items-center gap-3">
            Action &amp; Strategy <div className="h-[1px] flex-1 bg-white/5" />
          </h2>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6 pb-8">

            {/* Chart 4: Whitespace / Opportunity */}
            <div className="bg-zinc-900/40 backdrop-blur-sm border border-white/5 p-8 rounded-[2.5rem] shadow-2xl overflow-hidden relative">
              <div className="flex justify-between items-start mb-10">
                <div>
                  <h3 className="font-bold text-xl text-white">Whitespace Opportunities</h3>
                  <p className="text-zinc-500 text-xs mt-1">Highest ROI focus areas</p>
                </div>
                <div className="bg-emerald-500/10 text-emerald-300 text-[10px] px-3 py-1.5 rounded-lg border border-emerald-500/20 font-bold uppercase tracking-widest">
                  Target: {topOpportunity}
                </div>
              </div>
              <div className="h-72 w-full relative">
                <span className="absolute bottom-1 left-1/2 -translate-x-1/2 text-[9px] font-bold tracking-[0.2em] uppercase text-zinc-600">Density ⟷ Niche</span>
                <span className="absolute left-1 top-1/2 -translate-y-1/2 -rotate-90 text-[9px] font-bold tracking-[0.2em] uppercase text-zinc-600">Growth ⟷ Decay</span>
                <ResponsiveContainer width="100%" height="100%">
                  <ScatterChart margin={{ top: 20, right: 20, bottom: 20, left: 20 }}>
                    <CartesianGrid stroke={chartStroke} strokeDasharray="3 3" opacity={0.1} />
                    
                    {/* Quadrant Shadows */}
                    <ReferenceArea x1={0} x2={0.5} y1={0} y2={1} fill="#34d399" fillOpacity={0.03} />
                    <ReferenceArea x1={0.5} x2={1} y1={-1} y2={0} fill="#f87171" fillOpacity={0.03} />

                    <XAxis type="number" dataKey="x" name="Competition" domain={[0, 1]} hide />
                    <YAxis type="number" dataKey="y" name="Growth" domain={[-1, 1]} hide />
                    <ZAxis range={[300, 800]} />
                    <Tooltip content={<ScatterTooltip />} cursor={{ fill: "rgba(255,255,255,0.05)" }} />
                    <Legend iconType="circle" wrapperStyle={{ fontSize: "10px", fontWeight: 600, textTransform: "uppercase", letterSpacing: "0.1em" }} />
                    {(analysisData?.whitespace || []).map((entry: any, index: number) => (
                      <Scatter key={index} name={entry.competitor} data={[entry]} fill={entry.fill} />
                    ))}
                  </ScatterChart>
                </ResponsiveContainer>
                
                {/* Quadrant Labels */}
                <div className="absolute top-[10%] left-[10%] pointer-events-none">
                  <span className="text-[8px] font-black tracking-widest uppercase text-emerald-400/40">Opportunity</span>
                </div>
                <div className="absolute top-[10%] right-[10%] pointer-events-none">
                  <span className="text-[8px] font-black tracking-widest uppercase text-blue-400/40">Competitive Growth</span>
                </div>
                <div className="absolute bottom-[10%] left-[10%] pointer-events-none">
                  <span className="text-[8px] font-black tracking-widest uppercase text-zinc-400/40">Low Priority</span>
                </div>
                <div className="absolute bottom-[10%] right-[10%] pointer-events-none">
                  <span className="text-[8px] font-black tracking-widest uppercase text-red-400/40">Saturated</span>
                </div>
              </div>
            </div>

            {/* Chart 5: Competitor Strength */}
            <div className="bg-zinc-900/40 backdrop-blur-sm border border-white/5 p-8 rounded-[2.5rem] shadow-2xl">
              <div className="flex justify-between items-start mb-10">
                <div>
                  <h3 className="font-bold text-xl text-white">Market Segment Strength</h3>
                  <p className="text-zinc-500 text-xs mt-1">Signal volume by top segments</p>
                </div>
                <div className="bg-blue-500/10 text-blue-300 text-[10px] px-3 py-1.5 rounded-lg border border-blue-500/20 font-bold uppercase tracking-widest">
                  Scoring: Top Segments
                </div>
              </div>

              <div className="h-72 w-full">
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart data={analysisData ? analysisData.strength : []} margin={{ top: 10, right: 0, left: -20, bottom: 0 }}>
                    <CartesianGrid strokeDasharray="3 3" vertical={false} stroke={chartStroke} />
                    <XAxis dataKey="name" axisLine={false} tickLine={false} tick={{ fontSize: 10, fill: axisColor, fontWeight: 600 }} />
                    <YAxis axisLine={false} tickLine={false} tick={{ fontSize: 10, fill: axisColor, fontWeight: 600 }} />
                    <Tooltip content={<CustomTooltip />} cursor={{ fill: "rgba(255,255,255,0.03)" }} />
                    <Legend wrapperStyle={{ fontSize: "10px", paddingTop: "15px", fontWeight: 600, textTransform: "uppercase", letterSpacing: "0.1em" }} />
                    {strengthKeys.map((key, i) => (
                      <Bar 
                        key={key} 
                        dataKey={key} 
                        name={key} 
                        fill={CLUSTER_COLORS[i % CLUSTER_COLORS.length]} 
                        radius={[6, 6, 0, 0]} 
                        barSize={16} 
                      />
                    ))}

                  </BarChart>
                </ResponsiveContainer>
              </div>
            </div>
          </div>
        </div>

        {/* ── SUGGESTED EXPERIMENTS ── */}
        <div>
          <h2 className="text-[20px] uppercase tracking-[0.3em] text-zinc-300 font-black mb-6 flex items-center gap-3">
            Suggested Experiments <div className="h-[1px] flex-1 bg-white/5" />
          </h2>
          {experiments.length === 0 ? (
            <div className="pb-20">
              <div className="rounded-[2rem] border border-white/10 bg-zinc-950 px-8 py-10">
                <p className="text-white text-lg font-semibold mb-2">No structured experiments are available right now.</p>
                <p className="text-gray-300 text-sm leading-relaxed">
                  This usually means the backend returned an empty experiment list, the structured experiment cache has not been regenerated yet,
                  or the API is still serving stale data from before the new pipeline was connected.
                </p>
              </div>
            </div>
          ) : (
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6 pb-20">
            {experiments.slice(0, 3).map((exp, index) => {
              const activeExperiment = exp.experiment || exp.recommended_action;
              const isActive = selectedExp === activeExperiment;
              const riskScore = Number.isFinite(exp.risk) ? exp.risk : 0.5;
              const rawRiskLabel = exp.risk_label || (riskScore < 0.35 ? "Low Risk" : riskScore < 0.65 ? "Medium Risk" : "High Risk");
              const riskLabel = rawRiskLabel.toLowerCase().includes("risk") ? rawRiskLabel : `${rawRiskLabel} Risk`;
              const glowColor = riskScore < 0.35 ? "bg-emerald-500/10" : riskScore < 0.65 ? "bg-amber-500/10" : "bg-red-500/10";
              const riskBadge = riskScore < 0.35
                ? "bg-emerald-500/10 text-emerald-300 border-emerald-500/20"
                : riskScore < 0.65
                  ? "bg-amber-500/10 text-amber-300 border-amber-500/20"
                  : "bg-red-500/10 text-red-300 border-red-500/20";
              const linkColor = riskScore < 0.35 ? "text-emerald-400" : riskScore < 0.65 ? "text-amber-400" : "text-red-400";
              const confidenceLabel = getConfidenceLabel(exp);
              const traceabilityItems = exp.traceability?.reasons?.slice(0, 3) || [];
              return (
                <div
                  key={exp.cluster_id}
                  onClick={() => setSelectedExp(activeExperiment)}
                  className={`bg-zinc-950 border p-8 rounded-[2.5rem] shadow-2xl hover:scale-[1.015] hover:shadow-[0_20px_50px_rgba(0,0,0,0.45)] transition-all duration-300 group overflow-hidden relative cursor-pointer ${isActive ? "border-violet-500/40 ring-1 ring-violet-500/20" : "border-white/10"}`}
                >
                  <div className={`absolute top-0 right-0 w-36 h-36 ${glowColor} blur-3xl rounded-full`} />
                  {isActive && (
                    <div className="absolute top-4 right-4">
                      <CheckCircle2 className="w-5 h-5 text-violet-400" />
                    </div>
                  )}
                  <div className="flex items-start justify-between gap-4 mb-6">
                    <div>
                      <p className="text-[10px] font-black uppercase tracking-[0.24em] text-gray-400 mb-2">Category</p>
                      <h3 className="text-white text-xl font-semibold drop-shadow-[0_0_18px_rgba(255,255,255,0.08)]">
                        {exp.category || exp.title || exp.cluster_name || exp.cluster_id}
                      </h3>
                    </div>
                    <div className="flex items-center gap-2 flex-wrap justify-end">
                      <span className={`${riskBadge} text-[10px] px-3 py-1 rounded-full border font-bold uppercase tracking-widest`}>{riskLabel}</span>
                      <span className="bg-violet-500/10 text-violet-200 text-[10px] px-3 py-1 rounded-full border border-violet-500/25 font-bold uppercase tracking-widest">
                        Confidence: {confidenceLabel}
                      </span>
                    </div>
                  </div>

                  <div className="mb-6">
                    <p className="text-[11px] font-black uppercase tracking-[0.22em] text-gray-400 mb-3">Experiment</p>
                    <p className="text-gray-200 text-md font-small leading-snug mb-3">
                      {exp.experiment}
                    </p>
                    <p className="text-gray-300 text-sm leading-relaxed">
                      {exp.hypothesis}
                    </p>
                  </div>

                  <div className="mb-6 flex items-end justify-between gap-4">
                    <div>
                      <p className="text-green-400 text-2xl font-semibold leading-none">{exp.expected_impact}</p>
                      <p className="text-gray-400 text-[11px] uppercase tracking-[0.18em] mt-2">Expected Impact</p>
                    </div>
                    <div className="text-right">
                      <p className="text-gray-100 text-sm font-semibold">{exp.metric}</p>
                      <p className="text-gray-400 text-[11px] uppercase tracking-[0.18em] mt-2">Primary KPI</p>
                    </div>
                  </div>

                  <div className="mb-6 p-4 bg-white/[0.03] rounded-2xl border border-white/10 group-hover:bg-white/[0.05] transition-colors">
                    <p className="text-[11px] font-black uppercase tracking-[0.22em] text-gray-400 mb-3 flex items-center gap-2">
                      <span className={`w-1.5 h-1.5 rounded-full ${riskScore < 0.35 ? "bg-emerald-500" : riskScore < 0.65 ? "bg-amber-500" : "bg-red-500"}`} />
                      Traceability
                    </p>
                    <div className="space-y-2">
                      {traceabilityItems.length > 0 ? traceabilityItems.map((reason, reasonIndex) => (
                        <div key={`${exp.cluster_id}-reason-${reasonIndex}`} className="flex items-start gap-2">
                          <span className="text-gray-300 text-xs leading-5">&bull;</span>
                          <p className="text-gray-300 text-sm leading-relaxed">{reason}</p>
                        </div>
                      )) : (
                        <p className="text-gray-300 text-sm leading-relaxed">{exp.traceability?.summary}</p>
                      )}
                    </div>
                  </div>

                  <div className="flex flex-wrap gap-2 mb-6">
                    <span className="text-[9px] px-2 py-1 rounded-md bg-white/[0.05] text-gray-400 font-medium">Intelligence Layer</span>
                    <span className="text-[9px] px-2 py-1 rounded-md bg-white/[0.05] text-gray-400 font-medium">Decision Layer</span>
                    <span className="text-[9px] px-2 py-1 rounded-md bg-white/[0.05] text-gray-400 font-medium">Trust Layer</span>
                  </div>
                  <Link href={`/experiment-builder?cluster_id=${exp.cluster_id}`} className={`inline-flex items-center gap-2 ${linkColor} text-xs font-bold uppercase tracking-widest hover:gap-3 transition-all`}>
                    Launch Experiment <span className="text-lg">→</span>
                  </Link>

                </div>
              );
            })}
          </div>
          )}
        </div>

      </div>

      <CopilotChat
        selectedExperiment={selectedExp || undefined}
        experiments={experiments}
      />
    </div >
  );
}
