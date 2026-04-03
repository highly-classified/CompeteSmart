"use client";

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
type ComparisonPoint = { name: string; pricing: number; quality: number; ai: number; convenience: number };

interface Experiment {
  insight: string;
  cluster_id: string;
  trend: string;
  confidence: number;
  risk: number;
  recommended_action: string;
  evidence: string[];
}

// ─────────────────────────────────────────────
// Config
// ─────────────────────────────────────────────

const CLUSTER_COLORS = ["#a78bfa", "#f87171", "#60a5fa", "#fbbf24", "#34d399", "#f472b6"];
const COMP_BRAND_COLORS: Record<string, string> = {
  "Urban Company": "#a78bfa", // Purple
  "Housejoy": "#34d399", // Green
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
  const [experiments] = useState<Experiment[]>(MOCK_EXPERIMENTS);
  const [selectedExp, setSelectedExp] = useState<string | null>(null);

  const [selectedCompetitor, setSelectedCompetitor] = useState("ALL");
  const [analysisData, setAnalysisData] = useState<{ trend: { data: any[]; keys: string[] }; themes: any[]; positioning: any[]; whitespace: any[]; strength: any[] } | null>(null);
  const [summary, setSummary] = useState<any>(null);

  useEffect(() => {
    fetch("/api/summary-insights")
      .then(res => res.json())
      .then(setSummary)
      .catch(e => console.error("Summary fetch error", e));
  }, []);

  useEffect(() => {
    fetch(`/api/competitor-analysis?competitor=${selectedCompetitor}`)
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

        // Pivot themes for grouping if ALL, else straightforward
        let processedThemes = [];
        if (selectedCompetitor === "ALL") {
            const themeMap: Record<string, any> = {};
            for (const item of data.themes) {
                if (!themeMap[item.category]) themeMap[item.category] = { category: item.category };
                themeMap[item.category][item.competitor] = item.percentage;
            }
            processedThemes = Object.values(themeMap);
        } else {
            processedThemes = data.themes.map((t: any, i: number) => ({
                name: t.category,
                value: t.percentage,
                fill: PIE_COLORS[i % PIE_COLORS.length]
            }));
        }

        // Positioning
        const processedPositioning = data.positioning.map((p: any) => ({
            name: p.competitor,
            x: p.price_index,
            y: p.trust_score,
            z: p.activity_score,
            fill: COMP_BRAND_COLORS[p.competitor] || "#60a5fa"
        }));

        const processedWhitespace = data.whitespace
            .filter((w: any) => w.competitor)
            .map((w: any) => ({
                competitor: w.competitor,
                x: w.x,
                y: w.y,
                fill: COMP_BRAND_COLORS[w.competitor] || "#60a5fa"
            }));

        setAnalysisData({
          trend: { data: smoothedData, keys: Array.from(compsInTrend) },
          themes: processedThemes,
          positioning: processedPositioning,
          whitespace: processedWhitespace,
          strength: data.strength
        });
      })
      .catch((e) => console.error("Analysis fetch error", e));
  }, [selectedCompetitor]);

  const strengthKeys = analysisData?.strength?.length > 0 
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
          <p className="text-zinc-500 text-sm mt-2 max-w-md leading-relaxed">
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
            <option value="Urban Company">Urban Company</option>
            <option value="Housejoy">Housejoy</option>
            <option value="Sulekha">Sulekha</option>
          </select>
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
          <h2 className="text-[10px] uppercase tracking-[0.3em] text-zinc-500 font-black mb-6 flex items-center gap-3">
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
                  Oversaturated: {MOCK_DISTRIBUTION_DATA[0].name}
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
                      <Bar dataKey="Urban Company" stackId="a" fill={COMP_BRAND_COLORS["Urban Company"]} />
                      <Bar dataKey="Housejoy" stackId="a" fill={COMP_BRAND_COLORS["Housejoy"]} />
                      <Bar dataKey="Sulekha" stackId="a" fill={COMP_BRAND_COLORS["Sulekha"]} />
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
          <h2 className="text-[10px] uppercase tracking-[0.3em] text-zinc-500 font-black mb-6 flex items-center gap-3">
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
          <h2 className="text-[10px] uppercase tracking-[0.3em] text-zinc-500 font-black mb-6 flex items-center gap-3">
            Suggested Experiments <div className="h-[1px] flex-1 bg-white/5" />
          </h2>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6 pb-20">
            {experiments.map((exp, index) => {
              const isActive = selectedExp === exp.recommended_action;
              const riskLabel = exp.risk < 0.35 ? "Low Risk" : exp.risk < 0.65 ? "Medium Risk" : "High Risk";
              const glowColor = exp.risk < 0.35 ? "bg-emerald-500/5" : exp.risk < 0.65 ? "bg-amber-500/5" : "bg-red-500/5";
              const riskBadge = exp.risk < 0.35
                ? "bg-emerald-500/10 text-emerald-300 border-emerald-500/20"
                : exp.risk < 0.65
                  ? "bg-amber-500/10 text-amber-300 border-amber-500/20"
                  : "bg-red-500/10 text-red-300 border-red-500/20";
              const linkColor = exp.risk < 0.35 ? "text-emerald-400" : exp.risk < 0.65 ? "text-amber-400" : "text-red-400";
              return (
                <div
                  key={exp.cluster_id}
                  onClick={() => setSelectedExp(exp.recommended_action)}
                  className={`bg-zinc-900/40 backdrop-blur-sm border p-8 rounded-[2.5rem] shadow-2xl hover:bg-zinc-900/60 transition-all group overflow-hidden relative cursor-pointer ${isActive ? "border-violet-500/40 ring-1 ring-violet-500/20" : "border-white/5"}`}
                >
                  <div className={`absolute top-0 right-0 w-32 h-32 ${glowColor} blur-3xl rounded-full`} />
                  {isActive && (
                    <div className="absolute top-4 right-4">
                      <CheckCircle2 className="w-5 h-5 text-violet-400" />
                    </div>
                  )}
                  <div className="flex items-center gap-2 mb-4 flex-wrap">
                    <span className={`${riskBadge} text-[10px] px-3 py-1 rounded-lg border font-bold uppercase tracking-widest`}>{riskLabel}</span>
                    <span className="bg-violet-500/10 text-violet-300 text-[10px] px-3 py-1 rounded-lg border border-violet-500/20 font-bold uppercase tracking-widest">
                      Confidence: {(exp.confidence * 100).toFixed(0)}%
                    </span>
                  </div>
                  <h3 className="font-bold text-lg text-white mb-2">{exp.cluster_id}</h3>
                  <p className="text-zinc-500 text-xs leading-relaxed mb-6">{exp.recommended_action}</p>

                  <div className="mb-6 p-4 bg-white/5 rounded-2xl border border-white/10 group-hover:bg-white/10 transition-colors">
                    <p className="text-[10px] font-bold text-zinc-400 uppercase tracking-widest mb-1.5 flex items-center gap-2">
                      <span className={`w-1 h-1 rounded-full ${exp.risk < 0.35 ? "bg-emerald-500" : exp.risk < 0.65 ? "bg-amber-500" : "bg-red-500"}`} /> Traceability
                    </p>
                    <p className="text-[11px] text-zinc-300 leading-relaxed italic">
                      {exp.insight}
                    </p>
                  </div>

                  <div className="flex flex-wrap gap-2 mb-6">
                    <span className="text-[9px] px-2 py-1 rounded-md bg-white/5 text-zinc-400 font-medium">Intelligence Layer</span>
                    <span className="text-[9px] px-2 py-1 rounded-md bg-white/5 text-zinc-400 font-medium">Decision Layer</span>
                    <span className="text-[9px] px-2 py-1 rounded-md bg-white/5 text-zinc-400 font-medium">Trust Layer</span>
                  </div>
                  <Link href="/experiment-builder" className={`inline-flex items-center gap-2 ${linkColor} text-xs font-bold uppercase tracking-widest hover:gap-3 transition-all`}>
                    Launch Experiment <span className="text-lg">→</span>
                  </Link>
                </div>
              );
            })}
          </div>
        </div>

      </div>

      <CopilotChat
        selectedExperiment={selectedExp || undefined}
        experiments={experiments}
      />
    </div >
  );
}
