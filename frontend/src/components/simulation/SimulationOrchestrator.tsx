"use client";

import { useState, useEffect } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { LiveKpiPanel } from "./LiveKpiPanel";
import { TrajectoryChart } from "./TrajectoryChart";
import { Play, RotateCcw, Save, ShieldAlert, Sparkles } from "lucide-react";

// Stage duration logic dictates how long the system processes an era before advancing
const STAGES = [
    { id: 0, title: "Ready for Simulation", desc: "Select a generated hypothesis strategy to begin testing against live competitor models.", duration: 0 },
    { id: 1, title: "Experiment Applied", desc: "Deploying new messaging. Initial customer segment resonance increasing rapidly.", duration: 3500 },
    { id: 2, title: "Market Reaction", desc: "Mainstream ad exposure finalized. Aggressive whitespace gap formally established.", duration: 3500 },
    { id: 3, title: "Competitor Response", desc: "Warning: Fast-following competitors detected the narrative shift and are cloning the verbiage.", duration: 4000 },
    { id: 4, title: "Outcome Evolution", desc: "Market stabilizes. Initial advantages fully analyzed against long-term saturation.", duration: 4000 }
];

// Mock trajectory simulating an AI backend stream across 9 months
const RAW_TRAJECTORY = [
    { month: "Jan", differentiation: 20, saturation: 80 },
    { month: "Feb", differentiation: 35, saturation: 78 },
    { month: "Mar", differentiation: 60, saturation: 72 }, // Stage 1 spikes
    { month: "Apr", differentiation: 75, saturation: 65 },
    { month: "May", differentiation: 82, saturation: 60 }, // Stage 2 peaks best ROI
    { month: "Jun", differentiation: 78, saturation: 64 },
    { month: "Jul", differentiation: 70, saturation: 75 }, // Stage 3 Competitors clone messaging
    { month: "Aug", differentiation: 65, saturation: 78 },
    { month: "Sep", differentiation: 62, saturation: 80 }  // Stage 4 Final status quo
];

export function SimulationOrchestrator() {
    const [isRunning, setIsRunning] = useState(false);
    const [stageIndex, setStageIndex] = useState(0);

    // Data slicing to create the continuous line drawing effect
    const [chartData, setChartData] = useState<any[]>([]);
    const [dataIndex, setDataIndex] = useState(0);

    // Dynamic values that feed into the LiveKpiPanel
    const kpis = [
        { label: "Whitespace Map", suffix: "%", value: stageIndex === 0 ? 20 : stageIndex === 1 ? 60 : stageIndex === 2 ? 82 : stageIndex === 3 ? 70 : 62, previousValue: 20 },
        { label: "Saturation Score", suffix: "%", value: stageIndex === 0 ? 80 : stageIndex === 1 ? 72 : stageIndex === 2 ? 60 : stageIndex === 3 ? 75 : 80, previousValue: 80, inverseGood: true },
        { label: "Persona Drift", suffix: "px", value: stageIndex === 0 ? 0 : stageIndex >= 1 ? 145 : 0, previousValue: 0 },
        { label: "Signal Resonance", suffix: "x", value: stageIndex === 0 ? 1.0 : stageIndex === 1 ? 1.5 : stageIndex === 2 ? 2.3 : stageIndex === 3 ? 1.8 : 1.6, previousValue: 1.0 }
    ];

    // Logic to process the stage transitions automatically like a chronological timeline
    useEffect(() => {
        if (!isRunning || stageIndex >= STAGES.length - 1) return;

        const duration = STAGES[stageIndex + 1].duration;
        const timer = setTimeout(() => {
            setStageIndex(prev => prev + 1);
        }, duration);

        return () => clearTimeout(timer);
    }, [isRunning, stageIndex]);

    // Logic to gradually trickle the chart dataset into the interface 
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

    const startSimulation = () => {
        setIsRunning(true);
        setStageIndex(1);
        setChartData([RAW_TRAJECTORY[0]]);
        setDataIndex(1);
    };

    const resetSimulation = () => {
        setIsRunning(false);
        setStageIndex(0);
        setChartData([]);
        setDataIndex(0);
    };

    const currentStage = STAGES[stageIndex];

    return (
        <div className="max-w-7xl mx-auto p-6 text-zinc-100 min-h-screen">
            {/* Header Panel */}
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
                    {stageIndex === STAGES.length - 1 && (
                        <motion.div initial={{ opacity: 0, x: 20 }} animate={{ opacity: 1, x: 0 }} className="flex gap-4">
                            <button className="flex items-center gap-2 px-6 py-3 bg-zinc-800 hover:bg-zinc-700 text-white rounded-xl font-medium transition-all">
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
                    {/* Default state shows an empty grid until execution */}
                    <TrajectoryChart data={chartData.length ? chartData : [{ month: "Jan", differentiation: 20, saturation: 80 }]} />
                </div>

                <div className="space-y-6">
                    {/* Dynamic Context Panel */}
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
                                    initial={{ opacity: 0, y: 15 }}
                                    animate={{ opacity: 1, y: 0 }}
                                    exit={{ opacity: 0, y: -15 }}
                                    transition={{ duration: 0.4 }}
                                >
                                    <h4 className="text-2xl font-bold text-white mb-3">{currentStage.title}</h4>
                                    <p className="text-zinc-400 text-lg leading-relaxed">{currentStage.desc}</p>
                                </motion.div>
                            </AnimatePresence>
                        </div>

                        {/* Stage 4 Final Judgment Assessment */}
                        <AnimatePresence>
                            {stageIndex === STAGES.length - 1 && (
                                <motion.div
                                    initial={{ opacity: 0, scale: 0.95 }}
                                    animate={{ opacity: 1, scale: 1 }}
                                    transition={{ delay: 0.5 }}
                                    className="bg-zinc-950/50 border border-rose-500/20 rounded-xl p-5 mt-4 relative overflow-hidden"
                                >
                                    <div className="absolute top-0 left-0 w-1 h-full bg-rose-500" />
                                    <div className="flex items-center gap-2 mb-3 text-rose-400">
                                        <ShieldAlert className="w-5 h-5" />
                                        <h5 className="font-bold text-lg">Failure Projection</h5>
                                    </div>
                                    <p className="text-sm text-zinc-300 leading-relaxed font-medium">
                                        The aggressive differentiation strategy successfully dominated the whitespace initially. However, due to low persona drift complexity, competitors cloned the narrative offset within 6 months, returning market saturation back to baseline 80% with lost margin.
                                    </p>
                                </motion.div>
                            )}
                        </AnimatePresence>
                    </div>
                </div>
            </div>
        </div>
    );
}
