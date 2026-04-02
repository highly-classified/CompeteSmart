"use client";

import { useState, useRef, useEffect } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { LiveKpiPanel } from "./LiveKpiPanel";
import { TrajectoryChart } from "./TrajectoryChart";
import { Play, RotateCcw, Save, ShieldAlert, Sparkles, X, CheckCircle2, Trophy, Loader2 } from "lucide-react";

// ─── Types ───────────────────────────────────────────────────────────────────

interface StageEntry {
    id: number;
    title: string;
    desc: string;
    status: "RUNNING" | "SUCCESS" | "FAILURE";
}

export interface SavedExperiment {
    id: string;
    name: string;
    savedAt: string;
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

const WS_BASE = process.env.NEXT_PUBLIC_BACKEND_URL?.replace("http", "ws") || "ws://localhost:8000";

export function SimulationOrchestrator() {
    const defaultKpis = { differentiation: 20, saturation: 80, persona_drift: 0, resonance: 1.0 };

    const [status, setStatus] = useState<"IDLE" | "RUNNING" | "SUCCESS" | "FAILURE">("IDLE");
    const [stages, setStages] = useState<StageEntry[]>([]);
    const [chartData, setChartData] = useState<{ month: string; differentiation: number; saturation: number }[]>([]);
    const [rawKpis, setRawKpis] = useState(defaultKpis);
    const [verdictText, setVerdictText] = useState("");
    const [iteration, setIteration] = useState(0);
    const [maxIterations, setMaxIterations] = useState(8);

    const [showSaveModal, setShowSaveModal] = useState(false);
    const [savedToast, setSavedToast] = useState(false);

    const wsRef = useRef<WebSocket | null>(null);
    const logRef = useRef<HTMLDivElement>(null);

    // Auto-scroll the log panel to the bottom when new stages arrive
    useEffect(() => {
        if (logRef.current) {
            logRef.current.scrollTop = logRef.current.scrollHeight;
        }
    }, [stages]);

    const formattedKpis = [
        { label: "Whitespace Map", suffix: "%", value: rawKpis.differentiation, previousValue: 20 },
        { label: "Saturation Score", suffix: "%", value: rawKpis.saturation, previousValue: 80, inverseGood: true },
        { label: "Persona Drift", suffix: "px", value: rawKpis.persona_drift, previousValue: 0 },
        { label: "Signal Resonance", suffix: "x", value: rawKpis.resonance, previousValue: 1.0 }
    ];

    const startSimulation = () => {
        // Reset state
        setStatus("RUNNING");
        setStages([]);
        setChartData([]);
        setRawKpis(defaultKpis);
        setVerdictText("");
        setIteration(0);

        const ws = new WebSocket(`${WS_BASE}/ws/simulate`);
        wsRef.current = ws;

        ws.onopen = () => {
            console.log("Simulation WS connected");
        };

        ws.onmessage = (event) => {
            try {
                const data = JSON.parse(event.data);

                if (data.iteration !== undefined) setIteration(data.iteration);
                if (data.maxIterations !== undefined) setMaxIterations(data.maxIterations);

                if (data.stageData) {
                    const entry: StageEntry = { ...data.stageData, status: data.status };
                    setStages(prev => [...prev, entry]);
                }
                if (data.chartPoint) {
                    setChartData(prev => [...prev, data.chartPoint]);
                }
                if (data.kpis) {
                    setRawKpis(data.kpis);
                }

                // Final status
                if (data.status === "SUCCESS" || data.status === "FAILURE") {
                    setStatus(data.status);
                    setVerdictText(data.stageData?.desc || "Simulation complete.");
                    ws.close();
                    wsRef.current = null;
                }
            } catch (e) {
                console.error("Failed to parse WS message", e);
            }
        };

        ws.onerror = () => {
            setStatus("FAILURE");
            setVerdictText("Connection error: Unable to reach Simulation Engine. Please ensure the backend server is running.");
            wsRef.current = null;
        };

        ws.onclose = () => {
            // If status is still running when ws closes unexpectedly, mark error
            setStatus(prev => prev === "RUNNING" ? "FAILURE" : prev);
            if (wsRef.current) {
                setVerdictText("WebSocket connection was lost unexpectedly.");
            }
            wsRef.current = null;
        };
    };

    const resetSimulation = () => {
        // Close any lingering connection
        if (wsRef.current) {
            wsRef.current.close();
            wsRef.current = null;
        }
        setStatus("IDLE");
        setStages([]);
        setChartData([]);
        setRawKpis(defaultKpis);
        setVerdictText("");
        setIteration(0);
    };

    const handleSave = (name: string) => {
        const exp: SavedExperiment = {
            id: `EX_${Date.now()}`,
            name,
            savedAt: new Date().toISOString(),
            stageIndex: stages.length,
            chartData,
            kpis: formattedKpis.map(k => ({ label: k.label, value: k.value, suffix: k.suffix })),
            verdict: status === "SUCCESS" ? "success" : "failure",
            verdictText,
        };
        saveExperiment(exp);
        setShowSaveModal(false);
        setSavedToast(true);
        setTimeout(() => setSavedToast(false), 3000);
    };

    const isFinished = status === "SUCCESS" || status === "FAILURE";
    const progressPercent = maxIterations > 0 ? Math.round((iteration / maxIterations) * 100) : 0;

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

                <div className="flex gap-4 items-center">
                    {status === "IDLE" && (
                        <button onClick={startSimulation} className="flex items-center gap-2 px-8 py-3 bg-emerald-500 hover:bg-emerald-600 shadow-[0_0_20px_rgba(16,185,129,0.3)] text-white rounded-xl font-bold transition-all hover:scale-105 active:scale-95">
                            <Play className="fill-current w-5 h-5" /> Execute Simulation
                        </button>
                    )}
                    {status === "RUNNING" && (
                        <div className="flex items-center gap-3 px-6 py-3 border border-emerald-500/30 bg-emerald-500/10 text-emerald-400 rounded-xl font-bold">
                            <Loader2 className="w-4 h-4 animate-spin" />
                            Iteration {iteration} / {maxIterations}
                        </div>
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

            {/* Progress Bar (only visible during running) */}
            {status === "RUNNING" && (
                <div className="mb-6">
                    <div className="w-full bg-zinc-800 rounded-full h-2 overflow-hidden">
                        <motion.div
                            className="h-full bg-gradient-to-r from-emerald-500 to-emerald-400 rounded-full"
                            initial={{ width: 0 }}
                            animate={{ width: `${progressPercent}%` }}
                            transition={{ duration: 0.8, ease: "easeOut" }}
                        />
                    </div>
                    <p className="text-xs text-zinc-500 mt-1.5 text-right">{progressPercent}% complete</p>
                </div>
            )}

            <LiveKpiPanel metrics={formattedKpis} />

            <div className="grid lg:grid-cols-3 gap-6">
                <div className="lg:col-span-2">
                    <TrajectoryChart data={chartData.length > 0 ? chartData : [{ month: "—", differentiation: 20, saturation: 80 }]} />
                </div>

                <div className="space-y-6">
                    <div className="bg-zinc-900 border border-zinc-800 rounded-2xl p-6 h-[450px] flex flex-col shadow-xl relative overflow-hidden">
                        {/* Header */}
                        <div className="flex items-center gap-3 mb-4 flex-shrink-0">
                            <div className="relative flex h-3 w-3">
                                {status === "RUNNING" && (
                                    <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75"></span>
                                )}
                                <span className={`relative inline-flex rounded-full h-3 w-3 ${
                                    status === "SUCCESS" ? "bg-emerald-500" :
                                    status === "FAILURE" ? "bg-rose-500" :
                                    status === "RUNNING" ? "bg-emerald-500" : "bg-zinc-700"
                                }`}></span>
                            </div>
                            <h3 className="text-sm uppercase tracking-widest font-semibold text-zinc-400">Live Agent Log</h3>
                            {stages.length > 0 && (
                                <span className="ml-auto text-xs text-zinc-600 font-mono">{stages.length} events</span>
                            )}
                        </div>

                        {/* Scrollable Log */}
                        <div ref={logRef} className="flex-1 overflow-y-auto space-y-3 pr-1 scrollbar-thin scrollbar-track-zinc-900 scrollbar-thumb-zinc-700">
                            {stages.length === 0 && status === "IDLE" && (
                                <div className="flex items-center justify-center h-full text-zinc-600 text-sm">
                                    Click &quot;Execute Simulation&quot; to start the agentic engine.
                                </div>
                            )}

                            <AnimatePresence initial={false}>
                                {stages.map((stage) => {
                                    const isSuccess = stage.title.includes("✓") || stage.status === "SUCCESS";
                                    const isFail = stage.title.includes("✗") || stage.status === "FAILURE";
                                    const borderColor = isSuccess ? "border-emerald-500/30" : isFail ? "border-rose-500/30" : "border-zinc-700/50";
                                    const accentColor = isSuccess ? "text-emerald-400" : isFail ? "text-rose-400" : "text-zinc-300";

                                    return (
                                        <motion.div
                                            key={stage.id}
                                            initial={{ opacity: 0, y: 12, scale: 0.97 }}
                                            animate={{ opacity: 1, y: 0, scale: 1 }}
                                            transition={{ duration: 0.4 }}
                                            className={`border ${borderColor} rounded-xl p-4 bg-zinc-950/50`}
                                        >
                                            <h4 className={`text-sm font-bold ${accentColor} mb-1.5`}>{stage.title}</h4>
                                            <p className="text-xs text-zinc-400 leading-relaxed">{stage.desc}</p>
                                        </motion.div>
                                    );
                                })}
                            </AnimatePresence>

                            {status === "RUNNING" && stages.length > 0 && (
                                <div className="flex items-center gap-2 text-emerald-500/60 text-xs py-2">
                                    <Loader2 className="w-3 h-3 animate-spin" />
                                    Processing next strategy...
                                </div>
                            )}
                        </div>

                        {/* Verdict Banner */}
                        <AnimatePresence>
                            {isFinished && (
                                <motion.div
                                    initial={{ opacity: 0, scale: 0.95 }} animate={{ opacity: 1, scale: 1 }} transition={{ delay: 0.3 }}
                                    className={`flex-shrink-0 border rounded-xl p-4 mt-3 relative overflow-hidden
                                        ${status === "SUCCESS" ? "border-emerald-500/30 bg-emerald-500/5" : "border-rose-500/30 bg-rose-500/5"}
                                    `}
                                >
                                    <div className={`absolute top-0 left-0 w-1 h-full ${status === "SUCCESS" ? "bg-emerald-500" : "bg-rose-500"}`} />
                                    <div className={`flex items-center gap-2 mb-2 ${status === "SUCCESS" ? "text-emerald-400" : "text-rose-400"}`}>
                                        {status === "SUCCESS" ? <Trophy className="w-4 h-4" /> : <ShieldAlert className="w-4 h-4" />}
                                        <h5 className="font-bold text-sm">{status === "SUCCESS" ? "Simulation Success" : "Failure Projection"}</h5>
                                    </div>
                                    <p className="text-xs text-zinc-300 leading-relaxed">{verdictText}</p>
                                </motion.div>
                            )}
                        </AnimatePresence>
                    </div>
                </div>
            </div>
        </div>
    );
}
