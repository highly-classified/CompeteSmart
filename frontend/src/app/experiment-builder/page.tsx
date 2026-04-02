"use client";

import { useState } from "react";
import { SimulationOrchestrator } from "@/components/simulation/SimulationOrchestrator";
import { ExperimentHistory } from "@/components/simulation/ExperimentHistory";
import { History, FlaskConical, ArrowLeft } from "lucide-react";
import Link from "next/link";

export default function ExperimentBuilderPage() {
    const [view, setView] = useState<"builder" | "history">("builder");

    return (
        <main className="bg-black/95 text-white min-h-screen overflow-x-hidden selection:bg-emerald-500/30 font-sans">
            {/* Top nav toggle bar */}
            <div className="border-b border-white/5 bg-zinc-950/80 backdrop-blur-md sticky top-0 z-40">
                <div className="max-w-7xl mx-auto px-6 flex items-center gap-1 h-14">
                    <Link 
                        href="/dashboard"
                        className="flex items-center gap-2 px-3 py-1.5 mr-4 rounded-lg text-xs font-bold uppercase tracking-widest text-zinc-400 hover:text-white hover:bg-white/10 border border-white/5 transition-all"
                    >
                        <ArrowLeft className="w-3.5 h-3.5" /> Back
                    </Link>
                    <div className="w-px h-6 bg-white/10 mr-4"></div>
                    <button
                        onClick={() => setView("builder")}
                        className={`flex items-center gap-2 px-4 py-1.5 rounded-lg text-xs font-bold uppercase tracking-widest transition-all ${view === "builder"
                                ? "bg-white/10 text-white"
                                : "text-zinc-500 hover:text-zinc-300 hover:bg-white/5"
                            }`}
                    >
                        <FlaskConical className="w-3.5 h-3.5" /> Experiment Builder
                    </button>
                    <button
                        onClick={() => setView("history")}
                        className={`flex items-center gap-2 px-4 py-1.5 rounded-lg text-xs font-bold uppercase tracking-widest transition-all ${view === "history"
                                ? "bg-white/10 text-white"
                                : "text-zinc-500 hover:text-zinc-300 hover:bg-white/5"
                            }`}
                    >
                        <History className="w-3.5 h-3.5" /> History
                    </button>
                </div>
            </div>

            {view === "builder" ? (
                <SimulationOrchestrator />
            ) : (
                <ExperimentHistory onBack={() => setView("builder")} />
            )}
        </main>
    );
}
