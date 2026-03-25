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
import { Target, TrendingUp, AlertTriangle, Lightbulb } from "lucide-react";
import Link from "next/link";
import { ArrowLeft } from "lucide-react";

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
  { name: "Urban Company", x: 80, y: 85, fill: "#8b5cf6" },
  { name: "Comp. A", x: 20, y: 30, fill: "#ef4444" },
  { name: "Comp. B", x: 30, y: 40, fill: "#f59e0b" },
  { name: "Comp. C", x: 45, y: 20, fill: "#3b82f6" },
];

// 3. Messaging Distribution (Donut)
const distributionData = [
  { name: "Pricing", value: 50, fill: "#ef4444" },
  { name: "Quality", value: 20, fill: "#3b82f6" },
  { name: "Convenience", value: 15, fill: "#10b981" },
  { name: "AI/Tech", value: 10, fill: "#8b5cf6" },
  { name: "Speed", value: 5, fill: "#f472b6" },
];

// 4. Opportunity / Whitespace (Quadrant)
// X = Competition (frequency), Y = Growth Rate
const whitespaceData = [
  { name: "AI Messaging", x: 20, y: 90, fill: "#10b981" }, // Low comp, high growth
  { name: "Pricing", x: 90, y: 10, fill: "#ef4444" },      // High comp, low growth
  { name: "Quality", x: 60, y: 40, fill: "#3b82f6" },
  { name: "Convenience", x: 40, y: 60, fill: "#f59e0b" },
];

// 5. Competitor Comparison (Grouped Bar)
const comparisonData = [
  { name: "Urban Company", Pricing: 20, Quality: 80, AI: 90, Convenience: 85 },
  { name: "Competitor A", Pricing: 90, Quality: 40, AI: 10, Convenience: 30 },
  { name: "Competitor B", Pricing: 85, Quality: 50, AI: 20, Convenience: 40 },
];

// Custom Tooltips
const CustomTooltip = ({ active, payload, label }: any) => {
  if (active && payload && payload.length) {
    return (
      <div className="bg-background/90 backdrop-blur-sm border border-foreground/10 p-3 rounded-lg shadow-xl text-sm">
        <p className="font-semibold mb-1">{label}</p>
        {payload.map((p: any, i: number) => (
          <p key={i} style={{ color: p.color || p.fill }}>{p.name}: {p.value}</p>
        ))}
      </div>
    );
  }
  return null;
};

const ScatterTooltip = ({ active, payload }: any) => {
  if (active && payload && payload.length) {
    const data = payload[0].payload;
    return (
      <div className="bg-background/90 backdrop-blur-sm border border-foreground/10 p-3 rounded-lg shadow-xl text-sm">
        <p className="font-semibold mb-1">{data.name}</p>
        <p className="text-foreground/80">X: {data.x}</p>
        <p className="text-foreground/80">Y: {data.y}</p>
      </div>
    );
  }
  return null;
};

export default function Dashboard() {
  return (
    <div className="min-h-screen bg-[#fafafa] dark:bg-[#0a0a0a] text-foreground p-4 md:p-8 font-sans transition-colors">
      
      <div className="flex items-center justify-between mb-8">
        <div>
          <button 
            onClick={() => {
              localStorage.removeItem("token");
              window.location.href = "/";
            }}
            className="inline-flex items-center gap-2 text-foreground/50 hover:text-foreground text-xs uppercase tracking-widest font-semibold mb-2 transition-colors"
          >
            <ArrowLeft className="w-4 h-4" /> Sign Out / Home
          </button>
          <h1 className="text-3xl font-bungee tracking-wide text-foreground">Market Intelligence</h1>
          <p className="text-foreground/60 text-sm mt-1">Live competitive insights and strategic recommendations.</p>
        </div>
      </div>

      {/* 🔹 TOP SECTION: SUMMARY */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-6">
        <div className="bg-white dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-800 p-5 rounded-2xl shadow-sm flex items-start gap-4">
          <div className="bg-emerald-500/10 p-3 rounded-xl text-emerald-500"><TrendingUp className="w-6 h-6" /></div>
          <div>
            <h3 className="text-xs uppercase tracking-widest text-foreground/50 font-semibold">Fastest Growing</h3>
            <p className="text-lg font-bold mt-1">AI Messaging</p>
            <p className="text-xs text-foreground/60 mt-1">Growing 3x faster than pricing.</p>
          </div>
        </div>

        <div className="bg-white dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-800 p-5 rounded-2xl shadow-sm flex items-start gap-4">
          <div className="bg-red-500/10 p-3 rounded-xl text-red-500"><AlertTriangle className="w-6 h-6" /></div>
          <div>
            <h3 className="text-xs uppercase tracking-widest text-foreground/50 font-semibold">Highest Saturation</h3>
            <p className="text-lg font-bold mt-1">Pricing Tactics</p>
            <p className="text-xs text-foreground/60 mt-1">Market is overcrowded. Avoid.</p>
          </div>
        </div>

        <div className="bg-white dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-800 p-5 rounded-2xl shadow-sm flex items-start gap-4">
          <div className="bg-violet-500/10 p-3 rounded-xl text-violet-500"><Lightbulb className="w-6 h-6" /></div>
          <div>
            <h3 className="text-xs uppercase tracking-widest text-foreground/50 font-semibold">Top Opportunity</h3>
            <p className="text-lg font-bold mt-1">AI + Convenience</p>
            <p className="text-xs text-foreground/60 mt-1">Test AI-based messaging immediately.</p>
          </div>
        </div>

        <div className="bg-white dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-800 p-5 rounded-2xl shadow-sm flex flex-col justify-center">
          <h3 className="text-xs uppercase tracking-widest text-foreground/50 font-semibold mb-3">Overall Market Risk Score</h3>
          <div className="w-full bg-zinc-100 dark:bg-zinc-800 rounded-full h-3 overflow-hidden flex">
            <div className="bg-emerald-500 w-[20%]" title="Low Risk"></div>
            <div className="bg-amber-500 w-[30%]" title="Medium Risk"></div>
            <div className="bg-red-500 w-[50%]" title="High Risk (Pricing)"></div>
          </div>
          <div className="flex justify-between mt-2 text-[10px] text-foreground/50 uppercase font-semibold">
            <span>Low</span>
            <span className="text-red-500">High (72/100)</span>
          </div>
        </div>
      </div>

      {/* 🔹 MIDDLE SECTION: ANALYSIS */}
      <h2 className="text-xs uppercase tracking-widest text-foreground/40 font-bold mb-4 ml-1">Market Analysis</h2>
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 mb-6">
        
        {/* Chart 1: Trend Over Time */}
        <div className="bg-white dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-800 p-5 rounded-3xl shadow-sm col-span-1 lg:col-span-1">
          <div className="mb-4">
            <h3 className="font-bold text-lg">Trend Over Time</h3>
            <p className="text-foreground/60 text-xs mt-0.5">How competitor messaging is evolving</p>
            <div className="mt-3 bg-violet-500/10 text-violet-600 dark:text-violet-400 text-xs px-3 py-1.5 rounded-md inline-block font-medium">
              👉 Market is shifting from price to intelligence
            </div>
          </div>
          <div className="h-64 w-full">
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={trendData}>
                <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="currentColor" className="opacity-10" />
                <XAxis dataKey="time" axisLine={false} tickLine={false} tick={{ fontSize: 12, fill: "currentColor", opacity: 0.6 }} />
                <YAxis axisLine={false} tickLine={false} tick={{ fontSize: 12, fill: "currentColor", opacity: 0.6 }} />
                <Tooltip content={<CustomTooltip />} />
                <Legend iconType="circle" wrapperStyle={{ fontSize: '12px' }} />
                <Line type="monotone" dataKey="AI" stroke="#8b5cf6" strokeWidth={3} dot={false} activeDot={{ r: 6 }} />
                <Line type="monotone" dataKey="Pricing" stroke="#ef4444" strokeWidth={3} dot={false} activeDot={{ r: 6 }} />
                <Line type="monotone" dataKey="Quality" stroke="#3b82f6" strokeWidth={3} dot={false} activeDot={{ r: 6 }} />
              </LineChart>
            </ResponsiveContainer>
          </div>
        </div>

        {/* Chart 3: Messaging Distribution */}
        <div className="bg-white dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-800 p-5 rounded-3xl shadow-sm col-span-1 lg:col-span-1">
          <div className="mb-4">
            <h3 className="font-bold text-lg">Messaging Distribution</h3>
            <p className="text-foreground/60 text-xs mt-0.5">What themes dominate the market</p>
            <div className="mt-3 bg-red-500/10 text-red-600 dark:text-red-400 text-xs px-3 py-1.5 rounded-md inline-block font-medium">
              👉 Market is overcrowded in pricing
            </div>
          </div>
          <div className="h-64 w-full relative">
            <ResponsiveContainer width="100%" height="100%">
              <PieChart>
                <Pie data={distributionData} cx="50%" cy="50%" innerRadius={60} outerRadius={80} paddingAngle={5} dataKey="value">
                  {distributionData.map((entry, index) => (
                    <Cell key={`cell-${index}`} fill={entry.fill} />
                  ))}
                </Pie>
                <Tooltip content={<CustomTooltip />} />
                <Legend iconType="circle" wrapperStyle={{ fontSize: '12px' }} />
              </PieChart>
            </ResponsiveContainer>
            {/* Center Text */}
            <div className="absolute inset-0 flex flex-col items-center justify-center pointer-events-none mt-[-20px]">
              <span className="text-2xl font-bold">50%</span>
              <span className="text-[10px] text-foreground/50 uppercase tracking-widest font-semibold">Pricing</span>
            </div>
          </div>
        </div>

        {/* Chart 2: Competitor Positioning Map */}
        <div className="bg-white dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-800 p-5 rounded-3xl shadow-sm col-span-1 lg:col-span-1">
          <div className="mb-4">
            <h3 className="font-bold text-lg">Positioning Map</h3>
            <p className="text-foreground/60 text-xs mt-0.5">Where competitors stand in the market</p>
            <div className="mt-3 bg-violet-500/10 text-violet-600 dark:text-violet-400 text-xs px-3 py-1.5 rounded-md inline-block font-medium">
              👉 Urban Company is positioning as premium experience
            </div>
          </div>
          <div className="h-64 w-full relative">
            {/* Axis Labels via absolute positioning */}
            <span className="absolute bottom-[-15px] left-1/2 -translate-x-1/2 text-[10px] font-semibold tracking-widest uppercase text-foreground/40">Affordable ⟷ Premium</span>
            <span className="absolute left-[-20px] top-1/2 -translate-y-1/2 -rotate-90 text-[10px] font-semibold tracking-widest uppercase text-foreground/40">Feature ⟷ Outcome</span>
            <ResponsiveContainer width="100%" height="100%">
              <ScatterChart margin={{ top: 20, right: 20, bottom: 20, left: 20 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="currentColor" className="opacity-10" />
                <XAxis type="number" dataKey="x" name="Premium" domain={[0, 100]} hide />
                <YAxis type="number" dataKey="y" name="Outcome" domain={[0, 100]} hide />
                <ZAxis range={[100, 400]} />
                <Tooltip content={<ScatterTooltip />} cursor={{ strokeDasharray: '3 3' }} />
                {positioningData.map((entry, index) => (
                  <Scatter key={index} name={entry.name} data={[entry]} fill={entry.fill} />
                ))}
              </ScatterChart>
            </ResponsiveContainer>
          </div>
        </div>
      </div>

      {/* 🔹 BOTTOM SECTION: ACTION */}
      <h2 className="text-xs uppercase tracking-widest text-foreground/40 font-bold mb-4 ml-1">Action & Strategy</h2>
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6 pb-12">
        
        {/* Chart 4: Opportunity / Whitespace */}
        <div className="bg-white dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-800 p-5 rounded-3xl shadow-sm">
          <div className="mb-4">
            <h3 className="font-bold text-lg">Whitespace Opportunities</h3>
            <p className="text-foreground/60 text-xs mt-0.5">Where you should focus next</p>
            <div className="mt-3 bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 text-xs px-3 py-1.5 rounded-md inline-block font-medium">
              👉 Test AI-based messaging immediately
            </div>
          </div>
          <div className="h-72 w-full relative">
            <span className="absolute bottom-[-15px] left-1/2 -translate-x-1/2 text-[10px] font-semibold tracking-widest uppercase text-foreground/40">Low Competition ⟷ High Competition</span>
            <span className="absolute left-[-15px] top-1/2 -translate-y-1/2 -rotate-90 text-[10px] font-semibold tracking-widest uppercase text-foreground/40">Low Growth ⟷ High Growth</span>
            <ResponsiveContainer width="100%" height="100%">
              <ScatterChart margin={{ top: 20, right: 20, bottom: 20, left: 20 }}>
                <CartesianGrid stroke="currentColor" className="opacity-10" />
                {/* Quadrant Lines overlay mapping */}
                <ReferenceArea x1={0} x2={50} y1={50} y2={100} fill="#10b981" fillOpacity={0.05} />
                <ReferenceArea x1={50} x2={100} y1={50} y2={100} fill="#f59e0b" fillOpacity={0.05} />
                <ReferenceArea x1={0} x2={50} y1={0} y2={50} fill="#3b82f6" fillOpacity={0.05} />
                <ReferenceArea x1={50} x2={100} y1={0} y2={50} fill="#ef4444" fillOpacity={0.05} />
                
                <XAxis type="number" dataKey="x" name="Competition" domain={[0, 100]} hide />
                <YAxis type="number" dataKey="y" name="Growth" domain={[0, 100]} hide />
                <ZAxis range={[200, 600]} />
                <Tooltip content={<ScatterTooltip />} cursor={{ strokeDasharray: '3 3' }} />
                {whitespaceData.map((entry, index) => (
                  <Scatter key={index} name={entry.name} data={[entry]} fill={entry.fill}>
                    {/* Render Text Label directly on Scatters */}
                  </Scatter>
                ))}
              </ScatterChart>
            </ResponsiveContainer>
             {/* Hardcoded labels for visual clarity */}
             <div className="absolute top-[18%] left-[25%] -translate-x-1/2 -translate-y-1/2 pointer-events-none">
              <span className="text-[11px] font-semibold">AI Messaging</span>
            </div>
            <div className="absolute bottom-[20%] right-[15%] -translate-x-1/2 pointer-events-none">
              <span className="text-[11px] font-semibold">Pricing</span>
            </div>
          </div>
        </div>

        {/* Chart 5: Competitor Comparison */}
        <div className="bg-white dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-800 p-5 rounded-3xl shadow-sm">
          <div className="mb-4">
            <h3 className="font-bold text-lg">Competitor Comparison</h3>
            <p className="text-foreground/60 text-xs mt-0.5">Who is strong in what</p>
            <div className="mt-3 bg-blue-500/10 text-blue-600 dark:text-blue-400 text-xs px-3 py-1.5 rounded-md inline-block font-medium">
              👉 Differentiation exists — don't compete on price
            </div>
          </div>
          <div className="h-72 w-full">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={comparisonData} margin={{ top: 20, right: 0, left: -20, bottom: 0 }}>
                <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="currentColor" className="opacity-10" />
                <XAxis dataKey="name" axisLine={false} tickLine={false} tick={{ fontSize: 12, fill: "currentColor", opacity: 0.6 }} />
                <YAxis axisLine={false} tickLine={false} tick={{ fontSize: 12, fill: "currentColor", opacity: 0.6 }} />
                <Tooltip content={<CustomTooltip />} cursor={{fill: 'currentColor', opacity: 0.05}} />
                <Legend wrapperStyle={{ fontSize: '11px', paddingTop: '10px' }} />
                <Bar dataKey="Pricing" fill="#ef4444" radius={[4, 4, 0, 0]} />
                <Bar dataKey="Quality" fill="#3b82f6" radius={[4, 4, 0, 0]} />
                <Bar dataKey="AI" fill="#8b5cf6" radius={[4, 4, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>

      </div>

    </div>
  );
}
