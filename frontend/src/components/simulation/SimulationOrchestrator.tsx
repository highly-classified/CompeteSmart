"use client";

import { useState, useRef, useEffect } from "react";
import { useSearchParams } from "next/navigation";
import Link from "next/link";
import { motion, AnimatePresence } from "framer-motion";
import { LiveKpiPanel } from "./LiveKpiPanel";
import { TrajectoryChart } from "./TrajectoryChart";
import { Play, RotateCcw, Save, ShieldAlert, Sparkles, X, CheckCircle2, Trophy, Loader2, FlaskConical } from "lucide-react";

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

const WS_BASE_DEFAULT = "ws://127.0.0.1:8000";

export function SimulationOrchestrator() {
    const searchParams = useSearchParams();
    const urlClusterId = searchParams.get("cluster_id");
    
    const [wsUrl, setWsUrl] = useState("");
    
    // Use Effect to safely access window/process in client component
    useEffect(() => {
        const envUrl = process.env.NEXT_PUBLIC_BACKEND_URL;
        if (envUrl) {
            setWsUrl(envUrl.replace("http", "ws"));
        } else {
            setWsUrl(WS_BASE_DEFAULT);
        }
    }, []);

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

    const [experimentPool, setExperimentPool] = useState<any[]>([]);
    const [selectedClusterId, setSelectedClusterId] = useState<string | null>(null);

    const wsRef = useRef<WebSocket | null>(null);
    const logRef = useRef<HTMLDivElement>(null);

    // Initial fetch of experiment pool
    useEffect(() => {
        fetch("/api/experiments")
            .then(res => res.json())
            .then(data => {
                const list = Array.isArray(data) ? data : (data?.experiments || []);
                setExperimentPool(list);
                
                // Prioritize URL parameter, then fallback to first in list
                if (urlClusterId) {
                    setSelectedClusterId(urlClusterId);
                } else if (list.length > 0 && !selectedClusterId) {
                    setSelectedClusterId(list[0].cluster_id);
                }
            })
            .catch(e => console.error("Experiment fetch failed", e));
    }, [urlClusterId]);
    
    // Scroll to execution button if pre-selected
    useEffect(() => {
        if (urlClusterId && experimentPool.length > 0) {
            // Give UI a moment to settle
            setTimeout(() => {
                window.scrollTo({ top: 0, behavior: "smooth" });
            }, 500);
        }
    }, [urlClusterId, experimentPool]);

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

        const backendUrl = process.env.NEXT_PUBLIC_BACKEND_URL || "http://127.0.0.1:8000";
        const protocol = backendUrl.startsWith("https") ? "wss" : "ws";
        const host = backendUrl.replace(/^https?:\/\//, "");
        
        const query = selectedClusterId ? `?cluster_focus=${encodeURIComponent(selectedClusterId)}` : "";
        const targetUrl = `${protocol}://${host}/ws/simulate${query}`;
        
        console.log("CompeteSmart: Connecting to Simulation WS at:", targetUrl);
        
        const ws = new WebSocket(targetUrl);
        wsRef.current = ws;

        // Connection watchdog
        const timeoutId = setTimeout(() => {
            if (ws.readyState !== WebSocket.OPEN) {
                console.error("CompeteSmart: WebSocket connection timed out.");
                setStatus("FAILURE");
                setVerdictText("Connection Timed Out: The simulation engine at " + targetUrl + " did not respond. Check if the backend is running.");
                ws.close();
            }
        }, 30000);

        ws.onopen = () => {
            clearTimeout(timeoutId);
            console.log("CompeteSmart: Simulation WS connected successfully.");
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

        ws.onerror = (err) => {
            console.error("CompeteSmart: WebSocket error occurred:", err);
            setStatus("FAILURE");
            const errorMessage = `Connection Error: Unable to reach Simulation Engine at ${targetUrl}/ws/simulate. 
            Confirm the backend is running on port 8000 and that no firewall is blocking WebSocket traffic.`;
            setVerdictText(errorMessage);
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
    // Progress toward the 80% differentiation breakthrough goal
    // This works regardless of whether maxIterations is 0 (dynamic mode) or fixed
    const progressPercent = Math.min(100, Math.round((rawKpis.differentiation / 80) * 100));

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

                {isFinished && (
                    <motion.div initial={{ opacity: 0, x: 20 }} animate={{ opacity: 1, x: 0 }} className="flex gap-4">
                        <button
                            onClick={() => setShowSaveModal(true)}
                            className="flex items-center gap-2 px-6 py-3 bg-emerald-500/10 hover:bg-emerald-500/20 border border-emerald-500/30 text-emerald-300 rounded-xl font-medium transition-all"
                        >
                            <Save className="w-4 h-4" /> Save Result
                        </button>
                        <button onClick={resetSimulation} className="flex items-center gap-2 px-6 py-3 border border-zinc-700 hover:bg-zinc-800 text-zinc-300 rounded-xl font-medium transition-all">
                            <RotateCcw className="w-4 h-4" /> New Sim
                        </button>
                    </motion.div>
                )}
            </div>

            {/* Strategic Focus (Visible only when IDLE) */}
            {status === "IDLE" && (
                <div className="mb-12">
                    {!urlClusterId ? (
                        <div className="p-12 border border-dashed border-zinc-800 rounded-3xl text-center bg-zinc-950/20">
                            <ShieldAlert className="w-8 h-8 text-rose-500 mx-auto mb-4 opacity-50" />
                            <p className="text-zinc-300 font-bold mb-2">No Strategic Goal Selected</p>
                            <p className="text-zinc-500 text-sm max-w-sm mx-auto mb-6">
                                Please return to the Market Intelligence dashboard and select an experiment idea to simulate its impact.
                            </p>
                            <Link href="/dashboard" className="px-6 py-2 bg-white/5 hover:bg-white/10 text-zinc-300 rounded-lg text-xs font-bold uppercase tracking-widest transition-all">
                                Go to Dashboard
                            </Link>
                        </div>
                    ) : experimentPool.length === 0 ? (
                        <div className="p-12 border border-dashed border-zinc-800 rounded-3xl text-center bg-zinc-950/20">
                            <Loader2 className="w-8 h-8 text-emerald-500 animate-spin mx-auto mb-4 opacity-50" />
                            <p className="text-zinc-500">Retrieving strategic focus data...</p>
                        </div>
                    ) : (
                        <div className="bg-zinc-900/40 border border-emerald-500/20 rounded-3xl p-8 backdrop-blur-md relative overflow-hidden group">
                            <div className="absolute top-0 right-0 w-64 h-64 bg-emerald-500/5 blur-3xl rounded-full translate-x-1/2 -translate-y-1/2" />
                            
                            <div className="flex flex-col md:flex-row md:items-center justify-between gap-8 relative z-10">
                                <div className="max-w-2xl">
                                    <div className="flex items-center gap-2 mb-4">
                                        <div className="bg-emerald-500/20 text-emerald-400 text-[10px] px-2 py-1 rounded-full border border-emerald-500/20 font-bold uppercase tracking-widest">
                                            Simulation Focus
                                        </div>
                                        <div className="text-zinc-500 text-xs font-mono">{urlClusterId}</div>
                                    </div>
                                    
                                    {experimentPool.find(e => e.cluster_id === urlClusterId) ? (
                                        <>
                                            <h2 className="text-2xl font-bold text-white mb-3">
                                                {experimentPool.find(e => e.cluster_id === urlClusterId).insight}
                                            </h2>
                                            <p className="text-zinc-400 leading-relaxed text-sm">
                                                {experimentPool.find(e => e.cluster_id === urlClusterId).recommended_action}
                                            </p>
                                        </>
                                    ) : (
                                        <p className="text-zinc-500 italic">Custom cluster focus detected. Initializing engine for direct simulation...</p>
                                    )}
                                </div>
                                
                                <div className="flex-shrink-0">
                                    <button 
                                        disabled={!selectedClusterId}
                                        onClick={startSimulation} 
                                        className="btn-glow-emerald flex items-center gap-3 px-10 py-5 bg-emerald-500 text-white rounded-2xl font-black text-lg shadow-[0_0_40px_rgba(16,185,129,0.3)] hover:scale-105 active:scale-95 transition-all"
                                    >
                                        <Play className="fill-current w-6 h-6" /> START SIMULATION
                                    </button>
                                </div>
                            </div>
                        </div>
                    )}
                </div>
            )}

            {status === "RUNNING" && (
                <div className="mb-10">
                    <div className="flex justify-between items-center mb-1.5">
                        <span className="text-xs text-zinc-500">
                            {rawKpis.differentiation < 10
                                ? "🔄 Booting ML strategy pipeline..."
                                : `Differentiation ${rawKpis.differentiation}% → target 80%`}
                        </span>
                        <div className="flex items-center gap-4">
                            <div className="flex items-center gap-2 px-3 py-1 bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 rounded-lg text-[10px] font-bold">
                                <Loader2 className="w-3 h-3 animate-spin" /> ITERATION {iteration}
                            </div>
                            <span className="text-xs text-emerald-400 font-mono">{progressPercent}%</span>
                        </div>
                    </div>
                    <div className="w-full bg-zinc-800 rounded-full h-2 overflow-hidden">
                        <motion.div
                            className="h-full bg-gradient-to-r from-emerald-500 to-emerald-400 rounded-full"
                            initial={{ width: 0 }}
                            animate={{ width: `${progressPercent}%` }}
                            transition={{ duration: 0.8, ease: "easeOut" }}
                        />
                    </div>
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
                                    Click &quot;Start Simulation&quot; above to begin.
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
                                <div className="flex architecture-status-dot flex items-center gap-2 text-emerald-500/60 text-xs py-2">
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
