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
  ReferenceArea
} from "recharts";
import { Target, TrendingUp, AlertTriangle, Lightbulb, CheckCircle2 } from "lucide-react";
import Link from "next/link";
import { ArrowLeft } from "lucide-react";
import { useEffect, useState } from "react";
import { CopilotChat } from "@/components/CopilotChat";

// --- MOCK DATA --- //

// 1. Trend Over Time
const trendData = [
  { time: "Jan", AI: 10, Pricing: 40, Quality: 30 },
  { time: "Feb", AI: 20, Pricing: 35, Quality: 30 },
  { time: "Mar", AI: 45, Pricing: 25, Quality: 32 },
  { time: "Apr", AI: 65, Pricing: 20, Quality: 35 },
  { time: "May", AI: 85, Pricing: 15, Quality: 35 },
];

// 2. Competitor Positioning Map (X=Affordable<->Premium, Y=Feature<->Outcome)
const positioningData = [
  { name: "Urban Company", x: 80, y: 85, fill: "#a78bfa" }, // Lightened for dark mode
  { name: "Comp. A", x: 20, y: 30, fill: "#f87171" },
  { name: "Comp. B", x: 30, y: 40, fill: "#fbbf24" },
  { name: "Comp. C", x: 45, y: 20, fill: "#60a5fa" },
];

// 3. Messaging Distribution (Donut)
const distributionData = [
  { name: "Pricing", value: 50, fill: "#f87171" },
  { name: "Quality", value: 20, fill: "#60a5fa" },
  { name: "Convenience", value: 15, fill: "#34d399" },
  { name: "AI/Tech", value: 10, fill: "#a78bfa" },
  { name: "Speed", value: 5, fill: "#f472b6" },
];

// 4. Opportunity / Whitespace (Quadrant)
// X = Competition (frequency), Y = Growth Rate
const whitespaceData = [
  { name: "AI Messaging", x: 20, y: 90, fill: "#34d399" }, // Low comp, high growth
  { name: "Pricing", x: 90, y: 10, fill: "#f87171" },      // High comp, low growth
  { name: "Quality", x: 60, y: 40, fill: "#60a5fa" },
  { name: "Convenience", x: 40, y: 60, fill: "#fbbf24" },
];

// 5. Competitor Comparison (Grouped Bar)
const comparisonData = [
  { name: "Urban Company", Pricing: 20, Quality: 80, AI: 90, Convenience: 85 },
  { name: "Competitor A", Pricing: 90, Quality: 40, AI: 10, Convenience: 30 },
  { name: "Competitor B", Pricing: 85, Quality: 50, AI: 20, Convenience: 40 },
];

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
const CustomTooltip = ({ active, payload, label }: any) => {
  if (active && payload && payload.length) {
    return (
      <div className="bg-zinc-900/95 backdrop-blur-md border border-white/10 p-4 rounded-xl shadow-2xl text-sm ring-1 ring-white/5">
        <p className="font-bold text-white mb-2 pb-2 border-b border-white/5">{label}</p>
        <div className="space-y-1">
          {payload.map((p: any, i: number) => (
            <div key={i} className="flex items-center justify-between gap-4">
              <span className="text-zinc-400 capitalize">{p.name}:</span>
              <span className="font-mono font-medium" style={{ color: p.color || p.fill }}>{p.value}</span>
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
          <div className="flex items-center justify-between gap-4">
            <span className="text-zinc-400">Positioning (X):</span>
            <span className="text-white font-mono">{data.x}</span>
          </div>
          <div className="flex items-center justify-between gap-4">
            <span className="text-zinc-400">Strategy (Y):</span>
            <span className="text-white font-mono">{data.y}</span>
          </div>
        </div>
      </div>
    );
  }
  return null;
};

export default function Dashboard() {
  const [experiments, setExperiments] = useState<Experiment[]>([]);
  const [selectedExp, setSelectedExp] = useState<string | null>(null);

  const chartStroke = "rgba(255, 255, 255, 0.05)";
  const axisColor = "rgba(255, 255, 255, 0.4)";

  useEffect(() => {
    fetch("http://localhost:8000/api/experiments")
      .then(res => res.json())
      .then(data => {
        setExperiments(data);
        if (data.length > 0) setSelectedExp(data[0].recommended_action);
      })
      .catch(err => console.error("Failed to fetch experiments:", err));
  }, []);

  return (
    <div className="min-h-screen bg-[#050505] text-[#e4e4e7] p-4 md:p-8 font-sans selection:bg-violet-500/30">
      
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
        <div className="hidden md:block">
          <div className="px-4 py-2 bg-zinc-900 border border-white/5 rounded-full text-[10px] font-bold tracking-widest uppercase text-violet-400 flex items-center gap-2">
            <span className="w-2 h-2 bg-violet-400 rounded-full animate-pulse" />
            Live Analysis Active
          </div>
        </div>
      </div>

      <div className="max-w-7xl mx-auto space-y-8">
        
        {/* 🔹 TOP SECTION: SUMMARY */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
          <div className="bg-zinc-900/40 backdrop-blur-sm border border-white/5 p-6 rounded-3xl hover:bg-zinc-900/60 transition-all group overflow-hidden relative">
            <div className="absolute top-0 right-0 w-24 h-24 bg-emerald-500/5 blur-3xl rounded-full" />
            <div className="bg-emerald-500/10 p-3 rounded-2xl text-emerald-400 w-fit mb-4 group-hover:scale-110 transition-transform"><TrendingUp className="w-6 h-6" /></div>
            <h3 className="text-xs uppercase tracking-widest text-zinc-500 font-bold mb-1">Fastest Growing</h3>
            <p className="text-xl font-bold text-white mb-2">AI Messaging</p>
            <p className="text-xs text-zinc-500 leading-relaxed">Growing 3x faster than pricing strategies.</p>
          </div>

          <div className="bg-zinc-900/40 backdrop-blur-sm border border-white/5 p-6 rounded-3xl hover:bg-zinc-900/60 transition-all group overflow-hidden relative">
            <div className="absolute top-0 right-0 w-24 h-24 bg-red-500/5 blur-3xl rounded-full" />
            <div className="bg-red-500/10 p-3 rounded-2xl text-red-400 w-fit mb-4 group-hover:scale-110 transition-transform"><AlertTriangle className="w-6 h-6" /></div>
            <h3 className="text-xs uppercase tracking-widest text-zinc-500 font-bold mb-1">Highest Saturation</h3>
            <p className="text-xl font-bold text-white mb-2">Pricing Tactics</p>
            <p className="text-xs text-zinc-500 leading-relaxed">Market is overcrowded. Avoid direct price wars.</p>
          </div>

          <div className="bg-zinc-900/40 backdrop-blur-sm border border-white/5 p-6 rounded-3xl hover:bg-zinc-900/60 transition-all group overflow-hidden relative">
            <div className="absolute top-0 right-0 w-24 h-24 bg-violet-500/5 blur-3xl rounded-full" />
            <div className="bg-violet-500/10 p-3 rounded-2xl text-violet-400 w-fit mb-4 group-hover:scale-110 transition-transform"><Lightbulb className="w-6 h-6" /></div>
            <h3 className="text-xs uppercase tracking-widest text-zinc-500 font-bold mb-1">Top Opportunity</h3>
            <p className="text-xl font-bold text-white mb-2">AI + Convenience</p>
            <p className="text-xs text-zinc-500 leading-relaxed">Combine tech with logistics for maximum impact.</p>
          </div>

          <div className="bg-zinc-900/40 backdrop-blur-sm border border-white/5 p-6 rounded-3xl hover:bg-zinc-900/60 transition-all flex flex-col justify-center overflow-hidden relative">
            <div className="absolute top-0 right-0 w-24 h-24 bg-red-500/5 blur-3xl rounded-full" />
            <h3 className="text-xs uppercase tracking-widest text-zinc-500 font-bold mb-4">Market Risk Score</h3>
            <div className="w-full bg-zinc-800/50 rounded-full h-4 overflow-hidden flex ring-1 ring-white/5">
              <div className="bg-emerald-500/80 w-[20%]" />
              <div className="bg-amber-500/80 w-[30%]" />
              <div className="bg-red-500/80 w-[50%]" />
            </div>
            <div className="flex justify-between mt-3 text-[10px] text-zinc-500 uppercase font-black tracking-widest">
              <span>Stable</span>
              <span className="text-red-400 drop-shadow-[0_0_5px_rgba(248,113,113,0.3)]">Volatile (72/100)</span>
            </div>
          </div>
        </div>

        {/* 🔹 MIDDLE SECTION: ANALYSIS */}
        <div>
          <h2 className="text-[10px] uppercase tracking-[0.3em] text-zinc-500 font-black mb-6 flex items-center gap-3">
             Market Analysis <div className="h-[1px] flex-1 bg-white/5" />
          </h2>
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
            
            {/* Chart 1: Trend Over Time */}
            <div className="bg-zinc-900/40 backdrop-blur-sm border border-white/5 p-8 rounded-[2.5rem] shadow-2xl">
              <div className="mb-8">
                <h3 className="font-bold text-xl text-white">Trend Over Time</h3>
                <p className="text-zinc-500 text-xs mt-1">Evolving messaging clusters</p>
                <div className="mt-4 bg-violet-500/10 text-violet-300 text-[10px] px-3 py-1.5 rounded-lg border border-violet-500/20 inline-block font-bold uppercase tracking-widest">
                  Market shifting to AI intel
                </div>
              </div>
              <div className="h-64 w-full">
                <ResponsiveContainer width="100%" height="100%">
                  <LineChart data={trendData}>
                    <CartesianGrid strokeDasharray="3 3" vertical={false} stroke={chartStroke} />
                    <XAxis dataKey="time" axisLine={false} tickLine={false} tick={{ fontSize: 10, fill: axisColor, fontWeight: 600 }} />
                    <YAxis axisLine={false} tickLine={false} tick={{ fontSize: 10, fill: axisColor, fontWeight: 600 }} />
                    <Tooltip content={<CustomTooltip />} />
                    <Legend iconType="circle" wrapperStyle={{ fontSize: '10px', paddingTop: '20px', fontWeight: 600, textTransform: 'uppercase', letterSpacing: '0.1em' }} />
                    <Line type="monotone" dataKey="AI" stroke="#a78bfa" strokeWidth={4} dot={{r: 0, fill: '#a78bfa'}} activeDot={{ r: 6, strokeWidth: 0 }} />
                    <Line type="monotone" dataKey="Pricing" stroke="#f87171" strokeWidth={4} dot={{r: 0}} activeDot={{ r: 6, strokeWidth: 0 }} />
                    <Line type="monotone" dataKey="Quality" stroke="#60a5fa" strokeWidth={4} dot={{r: 0}} activeDot={{ r: 6, strokeWidth: 0 }} />
                  </LineChart>
                </ResponsiveContainer>
              </div>
            </div>

            {/* Chart 3: Messaging Distribution */}
            <div className="bg-zinc-900/40 backdrop-blur-sm border border-white/5 p-8 rounded-[2.5rem] shadow-2xl">
              <div className="mb-8">
                <h3 className="font-bold text-xl text-white">Theme Distribution</h3>
                <p className="text-zinc-500 text-xs mt-1">Dominant market narratives</p>
                <div className="mt-4 bg-red-500/10 text-red-300 text-[10px] px-3 py-1.5 rounded-lg border border-red-500/20 inline-block font-bold uppercase tracking-widest">
                  Oversaturated: Pricing
                </div>
              </div>
              <div className="h-64 w-full relative">
                <ResponsiveContainer width="100%" height="100%">
                  <PieChart>
                    <Pie data={distributionData} cx="50%" cy="50%" innerRadius={70} outerRadius={90} paddingAngle={8} dataKey="value" stroke="none">
                      {distributionData.map((entry, index) => (
                        <Cell key={`cell-${index}`} fill={entry.fill} />
                      ))}
                    </Pie>
                    <Tooltip content={<CustomTooltip />} />
                    <Legend iconType="circle" wrapperStyle={{ fontSize: '10px', fontWeight: 600, textTransform: 'uppercase', letterSpacing: '0.1em' }} />
                  </PieChart>
                </ResponsiveContainer>
                <div className="absolute inset-0 flex flex-col items-center justify-center pointer-events-none mt-[-25px]">
                  <span className="text-3xl font-black text-white">50%</span>
                  <span className="text-[10px] text-zinc-500 uppercase tracking-[0.2em] font-bold">Pricing</span>
                </div>
              </div>
            </div>

            {/* Chart 2: Competitor Positioning Map */}
            <div className="bg-zinc-900/40 backdrop-blur-sm border border-white/5 p-8 rounded-[2.5rem] shadow-2xl">
              <div className="mb-8">
                <h3 className="font-bold text-xl text-white">Positioning Map</h3>
                <p className="text-zinc-500 text-xs mt-1">Market landscape visualization</p>
                <div className="mt-4 bg-violet-500/10 text-violet-300 text-[10px] px-3 py-1.5 rounded-lg border border-violet-500/20 inline-block font-bold uppercase tracking-widest">
                  UC: Premium Leader
                </div>
              </div>
              <div className="h-64 w-full relative">
                <span className="absolute bottom-1 left-1/2 -translate-x-1/2 text-[9px] font-bold tracking-[0.2em] uppercase text-zinc-600">Affordable ⟷ Premium</span>
                <span className="absolute left-1 top-1/2 -translate-y-1/2 -rotate-90 text-[9px] font-bold tracking-[0.2em] uppercase text-zinc-600">Feature ⟷ Outcome</span>
                <ResponsiveContainer width="100%" height="100%">
                  <ScatterChart margin={{ top: 20, right: 20, bottom: 20, left: 20 }}>
                    <CartesianGrid strokeDasharray="3 3" stroke={chartStroke} />
                    <XAxis type="number" dataKey="x" name="Premium" domain={[0, 100]} hide />
                    <YAxis type="number" dataKey="y" name="Outcome" domain={[0, 100]} hide />
                    <ZAxis range={[150, 600]} />
                    <Tooltip content={<ScatterTooltip />} cursor={{ strokeDasharray: '3 3', stroke: 'rgba(255,255,255,0.2)' }} />
                    {positioningData.map((entry, index) => (
                      <Scatter key={index} name={entry.name} data={[entry]} fill={entry.fill} className="drop-shadow-[0_0_8px_rgba(255,255,255,0.1)]" />
                    ))}
                  </ScatterChart>
                </ResponsiveContainer>
              </div>
            </div>
          </div>
        </div>

        {/* 🔹 BOTTOM SECTION: ACTION */}
        <div>
          <h2 className="text-[10px] uppercase tracking-[0.3em] text-zinc-500 font-black mb-6 flex items-center gap-3">
             Action & Strategy <div className="h-[1px] flex-1 bg-white/5" />
          </h2>
          
          {/* New: Dynamic Experiment Recommendations */}
          <div className="mb-8 overflow-hidden bg-zinc-900/40 backdrop-blur-sm border border-white/5 rounded-[2.5rem]">
            <div className="p-8 border-b border-white/5 flex justify-between items-center">
              <div>
                <h3 className="font-bold text-xl text-white">Suggested Experiments</h3>
                <p className="text-zinc-500 text-xs mt-1">Live tactical plays based on competitor shifts</p>
              </div>
              <div className="bg-emerald-500/10 text-emerald-400 text-[10px] px-4 py-2 rounded-full border border-emerald-500/20 font-bold uppercase tracking-widest flex items-center gap-2">
                <CheckCircle2 className="w-3 h-3" /> Analysis Synchronized
              </div>
            </div>
            
            <div className="p-4 grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
              {experiments.length > 0 ? (
                experiments.map((exp: Experiment, i: number) => (
                  <button
                    key={i}
                    onClick={() => setSelectedExp(exp.recommended_action)}
                    className={`p-6 rounded-3xl text-left transition-all relative overflow-hidden group border ${
                      selectedExp === exp.recommended_action 
                      ? "bg-violet-600/20 border-violet-500/50 shadow-[0_0_20px_rgba(139,92,246,0.1)]" 
                      : "bg-white/5 border-white/5 hover:bg-white/10"
                    }`}
                  >
                    <div className="flex items-start justify-between mb-4">
                      <div className={`p-2 rounded-xl ${selectedExp === exp.recommended_action ? "bg-violet-600 text-white" : "bg-zinc-800 text-zinc-400 group-hover:bg-zinc-700 transition-colors"}`}>
                        <Lightbulb className="w-4 h-4" />
                      </div>
                      <span className="text-[9px] font-black uppercase tracking-widest text-zinc-500">
                        {exp.trend}
                      </span>
                    </div>
                    <p className="text-sm font-bold text-white mb-2 leading-tight">
                      {exp.recommended_action}
                    </p>
                    <div className="flex items-center gap-4 mt-4">
                      <div className="flex flex-col">
                        <span className="text-[8px] uppercase tracking-widest text-zinc-500 font-bold">Confidence</span>
                        <span className="text-xs font-mono text-emerald-400">{(exp.confidence * 100).toFixed(0)}%</span>
                      </div>
                      <div className="flex flex-col">
                        <span className="text-[8px] uppercase tracking-widest text-zinc-500 font-bold">Evidence</span>
                        <span className="text-xs font-mono text-violet-400">{exp.evidence?.length || 0} signals</span>
                      </div>
                    </div>
                    {selectedExp === exp.recommended_action && (
                      <div className="absolute top-2 right-2">
                        <div className="bg-violet-500 w-2 h-2 rounded-full animate-ping" />
                      </div>
                    )}
                  </button>
                ))
              ) : (
                <div className="col-span-full py-12 text-center text-zinc-500 text-sm italic">
                  Run the intelligence pipeline in settings to generate fresh experiments.
                </div>
              )}
            </div>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-6 pb-20">
            
            {/* Chart 4: Opportunity / Whitespace */}
            <div className="bg-zinc-900/40 backdrop-blur-sm border border-white/5 p-8 rounded-[2.5rem] shadow-2xl overflow-hidden relative">
              <div className="flex justify-between items-start mb-10">
                <div>
                  <h3 className="font-bold text-xl text-white">Whitespace Opportunities</h3>
                  <p className="text-zinc-500 text-xs mt-1">Highest ROI focus areas</p>
                </div>
                <div className="bg-emerald-500/10 text-emerald-300 text-[10px] px-3 py-1.5 rounded-lg border border-emerald-500/20 font-bold uppercase tracking-widest">
                  Action: Deploy AI Messaging
                </div>
              </div>
              <div className="h-72 w-full relative">
                <span className="absolute bottom-1 left-1/2 -translate-x-1/2 text-[9px] font-bold tracking-[0.2em] uppercase text-zinc-600">Low Comp ⟷ High Comp</span>
                <span className="absolute left-1 top-1/2 -translate-y-1/2 -rotate-90 text-[9px] font-bold tracking-[0.2em] uppercase text-zinc-600">Low Growth ⟷ High Growth</span>
                <ResponsiveContainer width="100%" height="100%">
                  <ScatterChart margin={{ top: 20, right: 20, bottom: 20, left: 20 }}>
                    <CartesianGrid stroke={chartStroke} />
                    <ReferenceArea x1={0} x2={50} y1={50} y2={100} fill="#34d399" fillOpacity={0.03} />
                    <ReferenceArea x1={50} x2={100} y1={0} y2={50} fill="#f87171" fillOpacity={0.03} />
                    
                    <XAxis type="number" dataKey="x" name="Competition" domain={[0, 100]} hide />
                    <YAxis type="number" dataKey="y" name="Growth" domain={[0, 100]} hide />
                    <ZAxis range={[300, 800]} />
                    <Tooltip content={<ScatterTooltip />} cursor={{ fill: 'rgba(255,255,255,0.05)' }} />
                    {whitespaceData.map((entry, index) => (
                      <Scatter key={index} name={entry.name} data={[entry]} fill={entry.fill} />
                    ))}
                  </ScatterChart>
                </ResponsiveContainer>
                {/* Quadrant Labels */}
                <div className="absolute top-[15%] left-[15%] pointer-events-none opacity-40">
                  <span className="text-[9px] font-black tracking-widest uppercase text-emerald-400">Golden Opportunity</span>
                </div>
                <div className="absolute bottom-[15%] right-[15%] pointer-events-none opacity-40">
                  <span className="text-[9px] font-black tracking-widest uppercase text-red-400">Avoid Zone</span>
                </div>
              </div>
            </div>

            {/* Chart 5: Competitor Comparison */}
            <div className="bg-zinc-900/40 backdrop-blur-sm border border-white/5 p-8 rounded-[2.5rem] shadow-2xl">
              <div className="flex justify-between items-start mb-10">
                <div>
                  <h3 className="font-bold text-xl text-white">Competitor Strength</h3>
                  <p className="text-zinc-500 text-xs mt-1">Cross-brand metric indexing</p>
                </div>
                <div className="bg-blue-500/10 text-blue-300 text-[10px] px-3 py-1.5 rounded-lg border border-blue-500/20 font-bold uppercase tracking-widest">
                  Avoid Pricing Wars
                </div>
              </div>
              <div className="h-72 w-full">
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart data={comparisonData} margin={{ top: 10, right: 0, left: -20, bottom: 0 }}>
                    <CartesianGrid strokeDasharray="3 3" vertical={false} stroke={chartStroke} />
                    <XAxis dataKey="name" axisLine={false} tickLine={false} tick={{ fontSize: 10, fill: axisColor, fontWeight: 600 }} />
                    <YAxis axisLine={false} tickLine={false} tick={{ fontSize: 10, fill: axisColor, fontWeight: 600 }} />
                    <Tooltip content={<CustomTooltip />} cursor={{fill: 'rgba(255,255,255,0.03)'}} />
                    <Legend wrapperStyle={{ fontSize: '10px', paddingTop: '15px', fontWeight: 600, textTransform: 'uppercase', letterSpacing: '0.1em' }} />
                    <Bar dataKey="Pricing" fill="#f87171" radius={[6, 6, 0, 0]} barSize={20} />
                    <Bar dataKey="Quality" fill="#60a5fa" radius={[6, 6, 0, 0]} barSize={20} />
                    <Bar dataKey="AI" fill="#a78bfa" radius={[6, 6, 0, 0]} barSize={20} />
                  </BarChart>
                </ResponsiveContainer>
              </div>
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
