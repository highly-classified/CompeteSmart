"use client";

import { useState, useEffect } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { LiveKpiPanel } from "./LiveKpiPanel";
import { TrajectoryChart } from "./TrajectoryChart";
import { Play, RotateCcw, Save, ShieldAlert, Sparkles, X, CheckCircle2 } from "lucide-react";

// ─── Types ───────────────────────────────────────────────────────────────────

export interface SavedExperiment {
    id: string;
    name: string;
    savedAt: string; // ISO string
    stageIndex: number;
    chartData: { month: string; differentiation: number; saturation: number }[];
    kpis: { label: string; value: number; suffix: string }[];
    verdict: "success" | "failure";
    verdictText: string;
}

const LS_KEY = "cs_experiments";

export function loadExperiments(): SavedExperiment[] {
    if (typeof window === "undefined") return [];
    try { return JSON.parse(localStorage.getItem(LS_KEY) || "[]"); } catch { return []; }
}

function saveExperiment(exp: SavedExperiment) {
    const list = loadExperiments();
    list.unshift(exp);
    localStorage.setItem(LS_KEY, JSON.stringify(list));
}

// ─── Stage / Data Config ─────────────────────────────────────────────────────

const STAGES = [
    { id: 0, title: "Ready for Simulation", desc: "Select a generated hypothesis strategy to begin testing against live competitor models.", duration: 0 },
    { id: 1, title: "Experiment Applied", desc: "Deploying new messaging. Initial customer segment resonance increasing rapidly.", duration: 3500 },
    { id: 2, title: "Market Reaction", desc: "Mainstream ad exposure finalized. Aggressive whitespace gap formally established.", duration: 3500 },
    { id: 3, title: "Competitor Response", desc: "Warning: Fast-following competitors detected the narrative shift and are cloning the verbiage.", duration: 4000 },
    { id: 4, title: "Outcome Evolution", desc: "Market stabilizes. Initial advantages fully analyzed against long-term saturation.", duration: 4000 }
];

const RAW_TRAJECTORY = [
    { month: "Jan", differentiation: 20, saturation: 80 },
    { month: "Feb", differentiation: 35, saturation: 78 },
    { month: "Mar", differentiation: 60, saturation: 72 },
    { month: "Apr", differentiation: 75, saturation: 65 },
    { month: "May", differentiation: 82, saturation: 60 },
    { month: "Jun", differentiation: 78, saturation: 64 },
    { month: "Jul", differentiation: 70, saturation: 75 },
    { month: "Aug", differentiation: 65, saturation: 78 },
    { month: "Sep", differentiation: 62, saturation: 80 }
];

const VERDICT_TEXT = "The aggressive differentiation strategy successfully dominated the whitespace initially. However, due to low persona drift complexity, competitors cloned the narrative offset within 6 months, returning market saturation back to baseline 80% with lost margin.";

// ─── Save Name Modal ──────────────────────────────────────────────────────────

function SaveModal({ onSave, onClose }: { onSave: (name: string) => void; onClose: () => void }) {
    const [name, setName] = useState("");
    return (
        <AnimatePresence>
            <motion.div
                initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}
                className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 backdrop-blur-sm"
                onClick={onClose}
            >
                <motion.div
                    initial={{ scale: 0.92, opacity: 0, y: 20 }} animate={{ scale: 1, opacity: 1, y: 0 }}
                    exit={{ scale: 0.92, opacity: 0 }} transition={{ type: "spring", damping: 20 }}
                    className="bg-zinc-900 border border-white/10 rounded-3xl p-8 w-full max-w-md shadow-2xl"
                    onClick={(e) => e.stopPropagation()}
                >
                    <div className="flex items-center justify-between mb-6">
                        <h2 className="text-xl font-bold text-white">Save Experiment</h2>
                        <button onClick={onClose} className="text-zinc-500 hover:text-white transition-colors">
                            <X className="w-5 h-5" />
                        </button>
                    </div>
                    <p className="text-zinc-400 text-sm mb-5">Give this experiment a name so you can find it later in your history.</p>
                    <input
                        autoFocus
                        type="text"
                        value={name}
                        onChange={(e) => setName(e.target.value)}
                        onKeyDown={(e) => e.key === "Enter" && name.trim() && onSave(name.trim())}
                        placeholder="e.g. AI Scheduling Q2 Trial"
                        className="w-full bg-zinc-800 border border-white/10 rounded-xl px-4 py-3 text-white placeholder-zinc-600 focus:outline-none focus:border-emerald-500/60 focus:ring-1 focus:ring-emerald-500/30 transition-all mb-5"
                    />
                    <div className="flex gap-3">
                        <button
                            onClick={() => name.trim() && onSave(name.trim())}
                            disabled={!name.trim()}
                            className="flex-1 flex items-center justify-center gap-2 px-5 py-3 bg-emerald-500 hover:bg-emerald-600 disabled:opacity-40 disabled:cursor-not-allowed text-white rounded-xl font-bold transition-all"
                        >
                            <Save className="w-4 h-4" /> Save
                        </button>
                        <button onClick={onClose} className="px-5 py-3 border border-white/10 hover:bg-zinc-800 text-zinc-400 rounded-xl font-medium transition-all">
                            Cancel
                        </button>
                    </div>
                </motion.div>
            </motion.div>
        </AnimatePresence>
    );
}

// ─── Main Orchestrator ────────────────────────────────────────────────────────

export function SimulationOrchestrator() {
    const [isRunning, setIsRunning] = useState(false);
    const [stageIndex, setStageIndex] = useState(0);
    const [chartData, setChartData] = useState<any[]>([]);
    const [dataIndex, setDataIndex] = useState(0);
    const [showSaveModal, setShowSaveModal] = useState(false);
    const [savedToast, setSavedToast] = useState(false);

    const kpis = [
        { label: "Whitespace Map", suffix: "%", value: stageIndex === 0 ? 20 : stageIndex === 1 ? 60 : stageIndex === 2 ? 82 : stageIndex === 3 ? 70 : 62, previousValue: 20 },
        { label: "Saturation Score", suffix: "%", value: stageIndex === 0 ? 80 : stageIndex === 1 ? 72 : stageIndex === 2 ? 60 : stageIndex === 3 ? 75 : 80, previousValue: 80, inverseGood: true },
        { label: "Persona Drift", suffix: "px", value: stageIndex === 0 ? 0 : stageIndex >= 1 ? 145 : 0, previousValue: 0 },
        { label: "Signal Resonance", suffix: "x", value: stageIndex === 0 ? 1.0 : stageIndex === 1 ? 1.5 : stageIndex === 2 ? 2.3 : stageIndex === 3 ? 1.8 : 1.6, previousValue: 1.0 }
    ];

    useEffect(() => {
        if (!isRunning || stageIndex >= STAGES.length - 1) return;
        const timer = setTimeout(() => setStageIndex(prev => prev + 1), STAGES[stageIndex + 1].duration);
        return () => clearTimeout(timer);
    }, [isRunning, stageIndex]);

    useEffect(() => {
        if (!isRunning || dataIndex >= RAW_TRAJECTORY.length) return;
        const totalSimTime = STAGES.slice(1).reduce((acc, s) => acc + s.duration, 0);
        const msPerPoint = totalSimTime / RAW_TRAJECTORY.length;
        const timer = setTimeout(() => {
            setChartData(prev => [...prev, RAW_TRAJECTORY[dataIndex]]);
            setDataIndex(prev => prev + 1);
        }, msPerPoint);
        return () => clearTimeout(timer);
    }, [isRunning, dataIndex]);

    const startSimulation = () => { setIsRunning(true); setStageIndex(1); setChartData([RAW_TRAJECTORY[0]]); setDataIndex(1); };
    const resetSimulation = () => { setIsRunning(false); setStageIndex(0); setChartData([]); setDataIndex(0); };

    const handleSave = (name: string) => {
        const exp: SavedExperiment = {
            id: `EX_${Date.now()}`,
            name,
            savedAt: new Date().toISOString(),
            stageIndex,
            chartData: chartData.length ? chartData : RAW_TRAJECTORY,
            kpis: kpis.map(k => ({ label: k.label, value: k.value, suffix: k.suffix })),
            verdict: "failure",
            verdictText: VERDICT_TEXT,
        };
        saveExperiment(exp);
        setShowSaveModal(false);
        setSavedToast(true);
        setTimeout(() => setSavedToast(false), 3000);
    };

    const currentStage = STAGES[stageIndex];
    const isFinished = stageIndex === STAGES.length - 1;

    return (
        <div className="max-w-7xl mx-auto p-6 text-zinc-100 min-h-screen">
            {showSaveModal && <SaveModal onSave={handleSave} onClose={() => setShowSaveModal(false)} />}

            {/* Saved toast */}
            <AnimatePresence>
                {savedToast && (
                    <motion.div
                        initial={{ opacity: 0, y: -20 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0, y: -20 }}
                        className="fixed top-6 right-6 z-50 flex items-center gap-3 bg-emerald-500/20 border border-emerald-500/40 text-emerald-300 rounded-2xl px-5 py-3 shadow-xl backdrop-blur-md"
                    >
                        <CheckCircle2 className="w-5 h-5" /> Experiment saved to history!
                    </motion.div>
                )}
            </AnimatePresence>

            {/* Header */}
            <div className="flex justify-between items-center mb-10 mt-6">
                <div>
                    <div className="flex items-center gap-2 mb-1">
                        <Sparkles className="w-5 h-5 text-emerald-400" />
                        <span className="text-emerald-400 font-medium tracking-wide text-sm uppercase">Sim Engine Active</span>
                    </div>
                    <h1 className="text-4xl font-bold bg-clip-text text-transparent bg-gradient-to-r from-white to-zinc-400">
                        Experiment Builder
                    </h1>
                    <p className="text-zinc-400 mt-2 text-lg">Simulate and project strategic pivots against your competitors.</p>
                </div>

                <div className="flex gap-4">
                    {!isRunning && stageIndex === 0 && (
                        <button onClick={startSimulation} className="flex items-center gap-2 px-8 py-3 bg-emerald-500 hover:bg-emerald-600 shadow-[0_0_20px_rgba(16,185,129,0.3)] text-white rounded-xl font-bold transition-all hover:scale-105 active:scale-95">
                            <Play className="fill-current w-5 h-5" /> Execute Simulation
                        </button>
                    )}
                    {isFinished && (
                        <motion.div initial={{ opacity: 0, x: 20 }} animate={{ opacity: 1, x: 0 }} className="flex gap-4">
                            <button
                                onClick={() => setShowSaveModal(true)}
                                className="flex items-center gap-2 px-6 py-3 bg-emerald-500/10 hover:bg-emerald-500/20 border border-emerald-500/30 text-emerald-300 rounded-xl font-medium transition-all"
                            >
                                <Save className="w-4 h-4" /> Save Result
                            </button>
                            <button onClick={resetSimulation} className="flex items-center gap-2 px-6 py-3 border border-zinc-700 hover:bg-zinc-800 text-zinc-300 rounded-xl font-medium transition-all">
                                <RotateCcw className="w-4 h-4" /> Reset
                            </button>
                        </motion.div>
                    )}
                </div>
            </div>

            <LiveKpiPanel metrics={kpis} />

            <div className="grid lg:grid-cols-3 gap-6">
                <div className="lg:col-span-2">
                    <TrajectoryChart data={chartData.length ? chartData : [{ month: "Jan", differentiation: 20, saturation: 80 }]} />
                </div>

                <div className="space-y-6">
                    <div className="bg-zinc-900 border border-zinc-800 rounded-2xl p-6 h-[450px] flex flex-col justify-between shadow-xl relative overflow-hidden">
                        <div>
                            <div className="flex items-center gap-3 mb-8">
                                <div className="relative flex h-3 w-3">
                                    {isRunning && stageIndex < STAGES.length - 1 && (
                                        <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75"></span>
                                    )}
                                    <span className={`relative inline-flex rounded-full h-3 w-3 ${stageIndex > 0 ? 'bg-emerald-500' : 'bg-zinc-700'}`}></span>
                                </div>
                                <h3 className="text-sm uppercase tracking-widest font-semibold text-zinc-400">Sequence Log</h3>
                            </div>

                            <AnimatePresence mode="wait">
                                <motion.div
                                    key={currentStage.id}
                                    initial={{ opacity: 0, y: 15 }} animate={{ opacity: 1, y: 0 }}
                                    exit={{ opacity: 0, y: -15 }} transition={{ duration: 0.4 }}
                                >
                                    <h4 className="text-2xl font-bold text-white mb-3">{currentStage.title}</h4>
                                    <p className="text-zinc-400 text-lg leading-relaxed">{currentStage.desc}</p>
                                </motion.div>
                            </AnimatePresence>
                        </div>

                        <AnimatePresence>
                            {isFinished && (
                                <motion.div
                                    initial={{ opacity: 0, scale: 0.95 }} animate={{ opacity: 1, scale: 1 }} transition={{ delay: 0.5 }}
                                    className="bg-zinc-950/50 border border-rose-500/20 rounded-xl p-5 mt-4 relative overflow-hidden"
                                >
                                    <div className="absolute top-0 left-0 w-1 h-full bg-rose-500" />
                                    <div className="flex items-center gap-2 mb-3 text-rose-400">
                                        <ShieldAlert className="w-5 h-5" />
                                        <h5 className="font-bold text-lg">Failure Projection</h5>
                                    </div>
                                    <p className="text-sm text-zinc-300 leading-relaxed font-medium">{VERDICT_TEXT}</p>
                                </motion.div>
                            )}
                        </AnimatePresence>
                    </div>
                </div>
            </div>
        </div>
    );
}
