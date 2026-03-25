"use client";

import { motion, useSpring, useTransform } from "framer-motion";
import { useEffect } from "react";
import { ArrowUpRight, ArrowDownRight, Activity } from "lucide-react";

interface KpiProps {
    label: string;
    value: number;
    previousValue: number;
    suffix?: string;
    inverseGood?: boolean; // For metrics where lower is better (like Saturation)
}

function AnimatedCounter({ from, to, suffix = "" }: { from: number, to: number, suffix?: string }) {
    const spring = useSpring(from, { bounce: 0, duration: 2500 });
    const display = useTransform(spring, (current) => current.toFixed(1) + suffix);

    useEffect(() => {
        spring.set(to);
    }, [spring, to]);

    // Handle immediate visual updates smoothly 
    return <motion.span>{display}</motion.span>;
}

export function LiveKpiPanel({ metrics }: { metrics: KpiProps[] }) {
    return (
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 mb-8">
            {metrics.map((m, i) => {
                const diff = m.value - m.previousValue;
                const isPositive = diff >= 0;
                const isGood = m.inverseGood ? !isPositive : isPositive;

                return (
                    <motion.div
                        key={m.label}
                        initial={{ opacity: 0, y: 20 }}
                        animate={{ opacity: 1, y: 0 }}
                        transition={{ delay: i * 0.1 }}
                        className="bg-zinc-900 border border-zinc-800 rounded-2xl p-6 shadow-xl relative overflow-hidden group hover:border-zinc-700 transition-colors"
                    >
                        <div className="flex justify-between items-start mb-4">
                            <span className="text-zinc-400 text-sm font-medium tracking-wide">{m.label.toUpperCase()}</span>
                            <Activity className={`w-4 h-4 ${isGood && Math.abs(diff) > 0 ? 'text-emerald-500' : 'text-zinc-600'}`} />
                        </div>

                        <div className="text-4xl font-bold text-white mb-3 tracking-tighter">
                            <AnimatedCounter from={m.previousValue} to={m.value} suffix={m.suffix} />
                        </div>

                        <div className={`flex items-center text-sm font-medium mt-auto ${isGood ? 'text-emerald-400' : 'text-rose-400'}`}>
                            {isPositive ? <ArrowUpRight className="w-4 h-4 mr-1" /> : <ArrowDownRight className="w-4 h-4 mr-1" />}
                            <span>{Math.abs(diff).toFixed(1)}{m.suffix} effect applied</span>
                        </div>

                        {/* Ambient Background Glow based on state */}
                        {Math.abs(diff) > 0 && (
                            <div className={`absolute -bottom-4 -right-4 w-24 h-24 blur-3xl rounded-full opacity-20 pointer-events-none ${isGood ? 'bg-emerald-500' : 'bg-rose-500'}`} />
                        )}
                    </motion.div>
                );
            })}
        </div>
    );
}
