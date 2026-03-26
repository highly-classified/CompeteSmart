"use client";

import { useState, useEffect } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { ArrowLeft, Clock, CheckCircle2, XCircle, ChevronRight, FlaskConical } from "lucide-react";
import { TrajectoryChart } from "./TrajectoryChart";
import { loadExperiments, SavedExperiment } from "./SimulationOrchestrator";

// ─── Mini preview chart (static sparkline) ───────────────────────────────────

function MiniPreview({ data, uid }: { data: SavedExperiment["chartData"]; uid: string }) {
    if (!data?.length) return <div className="w-full h-full bg-zinc-700 rounded-xl" />;
    const max = Math.max(...data.map((d) => d.differentiation));
    const min = Math.min(...data.map((d) => d.differentiation));
    const range = max - min || 1;
    const W = 200, H = 80;
    const pts = data.map((d, i) => {
        const x = (i / (data.length - 1)) * W;
        const y = H - ((d.differentiation - min) / range) * (H * 0.9) + H * 0.05;
        return `${x},${y}`;
    }).join(" ");
    const gradId = `grad-${uid}`;
    return (
        <svg viewBox={`0 0 ${W} ${H}`} className="w-full h-full" preserveAspectRatio="none">
            <defs>
                <linearGradient id={gradId} x1="0" y1="0" x2="0" y2="1">
                    <stop offset="0%" stopColor="#a78bfa" stopOpacity="0.4" />
                    <stop offset="100%" stopColor="#a78bfa" stopOpacity="0" />
                </linearGradient>
            </defs>
            <polyline
                points={`0,${H} ${pts} ${W},${H}`}
                fill={`url(#${gradId})`} stroke="none"
            />
            <polyline points={pts} fill="none" stroke="#a78bfa" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round" />
        </svg>
    );
}

// ─── Detail overlay ───────────────────────────────────────────────────────────

function ExperimentDetail({ exp, onClose }: { exp: SavedExperiment; onClose: () => void }) {
    const isSuccess = exp.verdict === "success";
    return (
        <motion.div
            initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}
            className="fixed inset-0 z-50 bg-black/80 backdrop-blur-sm flex items-center justify-center p-4"
            onClick={onClose}
        >
            <motion.div
                initial={{ scale: 0.94, opacity: 0, y: 24 }} animate={{ scale: 1, opacity: 1, y: 0 }}
                exit={{ scale: 0.94, opacity: 0 }}
                transition={{ type: "spring", damping: 22, stiffness: 280 }}
                className="bg-zinc-900 border border-white/10 rounded-3xl w-full max-w-4xl max-h-[90vh] overflow-y-auto shadow-2xl"
                onClick={(e) => e.stopPropagation()}
            >
                {/* Header */}
                <div className="flex items-center justify-between p-8 border-b border-white/5">
                    <div>
                        <p className="text-zinc-500 text-xs uppercase tracking-widest font-bold mb-1">{exp.id}</p>
                        <h2 className="text-2xl font-bold text-white">{exp.name}</h2>
                        <p className="text-zinc-500 text-sm mt-1 flex items-center gap-2">
                            <Clock className="w-3.5 h-3.5" />
                            Saved {new Date(exp.savedAt).toLocaleDateString("en-IN", { day: "numeric", month: "short", year: "numeric", hour: "2-digit", minute: "2-digit" })}
                        </p>
                    </div>
                    <button onClick={onClose} className="p-2 hover:bg-zinc-800 rounded-xl transition-colors text-zinc-400 hover:text-white">
                        <ArrowLeft className="w-5 h-5" />
                    </button>
                </div>

                {/* Trajectory Chart */}
                <div className="p-8 border-b border-white/5">
                    <h3 className="text-xs uppercase tracking-widest font-bold text-zinc-500 mb-4">Trajectory</h3>
                    <TrajectoryChart data={exp.chartData} />
                </div>

                {/* KPIs */}
                <div className="p-8 border-b border-white/5">
                    <h3 className="text-xs uppercase tracking-widest font-bold text-zinc-500 mb-4">Final KPIs</h3>
                    <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                        {exp.kpis.map((kpi) => (
                            <div key={kpi.label} className="bg-zinc-800/50 rounded-2xl p-4 border border-white/5">
                                <p className="text-zinc-500 text-[10px] uppercase tracking-widest font-bold mb-2">{kpi.label}</p>
                                <p className="text-2xl font-black text-white">{kpi.value}<span className="text-zinc-500 text-sm ml-0.5">{kpi.suffix}</span></p>
                            </div>
                        ))}
                    </div>
                </div>

                {/* Verdict */}
                <div className="p-8">
                    <div className={`rounded-2xl p-6 border relative overflow-hidden ${isSuccess ? "bg-emerald-500/10 border-emerald-500/20" : "bg-rose-500/10 border-rose-500/20"}`}>
                        <div className={`absolute top-0 left-0 w-1 h-full ${isSuccess ? "bg-emerald-500" : "bg-rose-500"}`} />
                        <div className={`flex items-center gap-3 mb-3 ${isSuccess ? "text-emerald-400" : "text-rose-400"}`}>
                            {isSuccess ? <CheckCircle2 className="w-6 h-6" /> : <XCircle className="w-6 h-6" />}
                            <h4 className="font-bold text-xl">{isSuccess ? "Success" : "Failure"} Projection</h4>
                        </div>
                        <p className="text-zinc-300 leading-relaxed">{exp.verdictText}</p>
                    </div>
                </div>
            </motion.div>
        </motion.div>
    );
}

// ─── History Gallery ──────────────────────────────────────────────────────────

export function ExperimentHistory({ onBack }: { onBack: () => void }) {
    const [experiments, setExperiments] = useState<SavedExperiment[]>([]);
    const [selected, setSelected] = useState<SavedExperiment | null>(null);

    useEffect(() => {
        setExperiments(loadExperiments());
    }, []);

    return (
        <div className="max-w-7xl mx-auto p-6 text-zinc-100 min-h-screen">
            <AnimatePresence>
                {selected && <ExperimentDetail exp={selected} onClose={() => setSelected(null)} />}
            </AnimatePresence>

            {/* Header */}
            <div className="flex items-center justify-between mb-10 mt-6">
                <div>
                    <button
                        onClick={onBack}
                        className="flex items-center gap-2 text-zinc-500 hover:text-white text-xs uppercase tracking-widest font-bold mb-3 transition-all group"
                    >
                        <ArrowLeft className="w-4 h-4 group-hover:-translate-x-1 transition-transform" /> Back to Builder
                    </button>
                    <h1 className="text-4xl font-bold bg-clip-text text-transparent bg-gradient-to-r from-white to-zinc-400">
                        Experiment History
                    </h1>
                    <p className="text-zinc-400 mt-2">All saved simulation runs — click any card to review results.</p>
                </div>
                <div className="text-zinc-600 text-sm font-bold uppercase tracking-widest">{experiments.length} saved</div>
            </div>

            {experiments.length === 0 ? (
                <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} className="flex flex-col items-center justify-center py-32 gap-4">
                    <div className="w-16 h-16 rounded-3xl bg-zinc-900 border border-white/5 flex items-center justify-center">
                        <FlaskConical className="w-8 h-8 text-zinc-600" />
                    </div>
                    <p className="text-zinc-500 text-sm">No saved experiments yet. Run a simulation and click Save Result.</p>
                    <button onClick={onBack} className="mt-2 text-xs font-bold uppercase tracking-widest text-violet-400 hover:text-violet-300 transition-colors flex items-center gap-1">
                        Go to Builder <ChevronRight className="w-3.5 h-3.5" />
                    </button>
                </motion.div>
            ) : (
                <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-5">
                    {experiments.map((exp, index) => (
                        <motion.div
                            key={exp.id}
                            initial={{ opacity: 0, y: 20 }}
                            animate={{ opacity: 1, y: 0 }}
                            transition={{ duration: 0.3, delay: index * 0.05 }}
                            onClick={() => setSelected(exp)}
                            className="group bg-zinc-800 border border-white/10 rounded-2xl overflow-hidden cursor-pointer hover:border-violet-500/40 hover:bg-zinc-700 hover:shadow-[0_0_30px_rgba(139,92,246,0.15)] transition-all"
                        >
                            {/* Thumbnail */}
                            <div className="h-36 bg-slate-900 p-3 border-b border-white/10 group-hover:bg-zinc-800 transition-colors">
                                <MiniPreview data={exp.chartData} uid={exp.id} />
                            </div>

                            {/* Info */}
                            <div className="p-4">
                                {/* Verdict badge */}
                                <div className="mb-3">
                                    {exp.verdict === "success" ? (
                                        <span className="inline-flex items-center gap-1 text-[9px] font-bold uppercase tracking-widest text-emerald-400 bg-emerald-500/10 border border-emerald-500/20 px-2 py-0.5 rounded-md">
                                            <CheckCircle2 className="w-2.5 h-2.5" /> Success
                                        </span>
                                    ) : (
                                        <span className="inline-flex items-center gap-1 text-[9px] font-bold uppercase tracking-widest text-rose-400 bg-rose-500/10 border border-rose-500/20 px-2 py-0.5 rounded-md">
                                            <XCircle className="w-2.5 h-2.5" /> Failure
                                        </span>
                                    )}
                                </div>

                                <p className="text-white font-semibold text-sm leading-tight mb-1 truncate" title={exp.name}>
                                    {exp.name}
                                </p>
                                <p className="text-zinc-600 text-[10px] font-bold uppercase tracking-widest">
                                    {exp.id.replace("EX_", "EX ")}
                                </p>
                                <p className="text-zinc-500 text-[11px] mt-1 flex items-center gap-1">
                                    <Clock className="w-3 h-3" />
                                    {new Date(exp.savedAt).toLocaleDateString("en-IN", { day: "numeric", month: "short", year: "numeric" })}
                                </p>
                            </div>
                        </motion.div>
                    ))}
                </div>
            )}
        </div>
    );
}
