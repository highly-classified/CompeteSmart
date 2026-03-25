"use client";

import { motion } from "framer-motion";
import { XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Area, AreaChart } from "recharts";

interface DataPoint {
    month: string;
    differentiation: number;
    saturation: number;
}

export function TrajectoryChart({ data }: { data: DataPoint[] }) {
    return (
        <motion.div
            initial={{ opacity: 0, scale: 0.95 }}
            animate={{ opacity: 1, scale: 1 }}
            className="bg-zinc-900 border border-zinc-800 rounded-2xl p-6 h-[450px] w-full shadow-xl relative overflow-hidden"
        >
            <div className="mb-6 relative z-10">
                <h3 className="text-xl font-bold text-white">Live Market Trajectory</h3>
                <p className="text-sm text-zinc-400 mt-1">Analyzing competitive whitespace vs. market saturation overlap.</p>
            </div>

            <div className="absolute inset-0 z-0 bg-gradient-to-b from-transparent to-zinc-900/50 pointer-events-none" />

            <ResponsiveContainer width="100%" height="80%" className="relative z-10">
                <AreaChart data={data} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
                    <defs>
                        <linearGradient id="colorDiff" x1="0" y1="0" x2="0" y2="1">
                            <stop offset="5%" stopColor="#10b981" stopOpacity={0.4} />
                            <stop offset="95%" stopColor="#10b981" stopOpacity={0} />
                        </linearGradient>
                        <linearGradient id="colorSat" x1="0" y1="0" x2="0" y2="1">
                            <stop offset="5%" stopColor="#f43f5e" stopOpacity={0.4} />
                            <stop offset="95%" stopColor="#f43f5e" stopOpacity={0} />
                        </linearGradient>
                    </defs>

                    <CartesianGrid strokeDasharray="4 4" stroke="#27272a" vertical={false} />

                    <XAxis
                        dataKey="month"
                        stroke="#71717a"
                        fontSize={12}
                        tickLine={false}
                        axisLine={false}
                        dy={10}
                    />

                    <YAxis
                        stroke="#71717a"
                        fontSize={12}
                        tickLine={false}
                        axisLine={false}
                        dx={-10}
                        tickFormatter={(value) => `${value}%`}
                    />

                    <Tooltip
                        contentStyle={{ backgroundColor: '#18181b', border: '1px solid #27272a', borderRadius: '12px', boxShadow: '0 4px 6px -1px rgb(0 0 0 / 0.1)' }}
                        itemStyle={{ color: '#e4e4e7', fontWeight: 500 }}
                        labelStyle={{ color: '#a1a1aa', fontWeight: 600, marginBottom: '4px' }}
                    />

                    {/* isAnimationActive={false} is critical because the Parent orchestrator trickles data down slowly, creating a natural hand-drawn effect natively! */}
                    <Area
                        type="monotone"
                        dataKey="differentiation"
                        name="Whitespace Diff."
                        stroke="#10b981"
                        strokeWidth={3}
                        fillOpacity={1}
                        fill="url(#colorDiff)"
                        isAnimationActive={false}
                    />
                    <Area
                        type="monotone"
                        dataKey="saturation"
                        name="Market Saturation"
                        stroke="#f43f5e"
                        strokeWidth={3}
                        fillOpacity={1}
                        fill="url(#colorSat)"
                        isAnimationActive={false}
                    />
                </AreaChart>
            </ResponsiveContainer>
        </motion.div>
    );
}
