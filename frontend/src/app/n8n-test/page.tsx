"use client";

import React from "react";
import { N8nTestChat } from "../../components/N8nTestChat";
import { Bot, FlaskConical, ArrowLeft } from "lucide-react";
import Link from "next/link";

export default function N8nTestPage() {
  return (
    <main className="min-h-screen bg-[#050505] text-zinc-100 flex flex-col items-center justify-center p-8 relative overflow-hidden">
      {/* Background Glow */}
      <div className="absolute top-1/4 left-1/4 w-96 h-96 bg-emerald-600/10 blur-[120px] rounded-full" />
      <div className="absolute bottom-1/4 right-1/4 w-96 h-96 bg-teal-600/10 blur-[120px] rounded-full" />

      <div className="z-10 w-full max-w-4xl text-center space-y-8">
        <Link 
          href="/" 
          className="inline-flex items-center gap-2 text-zinc-500 hover:text-white transition-colors mb-8 group"
        >
          <ArrowLeft className="w-4 h-4 group-hover:-translate-x-1 transition-transform" />
          Back to Dashboard
        </Link>

        <div className="space-y-4">
          <div className="flex items-center justify-center gap-4">
            <div className="p-4 bg-emerald-600/20 rounded-2xl border border-emerald-500/20">
              <FlaskConical className="w-12 h-12 text-emerald-500" />
            </div>
            <div className="text-left">
              <h1 className="text-4xl font-black tracking-tight text-white">n8n Workflow Test</h1>
              <p className="text-zinc-400 font-medium">Standalone integration for Experiment Suggestion Chatbot</p>
            </div>
          </div>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-6 mt-12">
          <div className="p-8 bg-zinc-900/50 border border-white/5 rounded-3xl backdrop-blur-sm text-left space-y-4">
            <h2 className="text-xl font-bold text-white flex items-center gap-2">
              <span className="w-2 h-6 bg-emerald-500 rounded-full" />
              How to Test
            </h2>
            <ul className="space-y-3 text-sm text-zinc-400">
              <li className="flex gap-2">
                <span className="text-emerald-500 font-bold">1.</span>
                <span>Ensure your n8n workflow is **Active**.</span>
              </li>
              <li className="flex gap-2">
                <span className="text-emerald-500 font-bold">2.</span>
                <span>Run <code>python backend/n8n_test_api.py</code> in a terminal.</span>
              </li>
              <li className="flex gap-2">
                <span className="text-emerald-500 font-bold">3.</span>
                <span>Click the green bubble on the bottom right to start chatting.</span>
              </li>
            </ul>
          </div>

          <div className="p-8 bg-zinc-900/50 border border-white/5 rounded-3xl backdrop-blur-sm text-left space-y-4">
            <h2 className="text-xl font-bold text-white flex items-center gap-2">
              <span className="w-2 h-6 bg-emerald-500 rounded-full" />
              Current Connection
            </h2>
            <div className="space-y-4">
              <div className="flex flex-col gap-1">
                <span className="text-[10px] text-zinc-500 uppercase font-black tracking-widest">N8N Webhook Endpoint</span>
                <code className="text-xs bg-black/50 p-2 rounded-lg border border-white/5 text-emerald-400 truncate">
                  /webhook/competesmart-chatbot
                </code>
              </div>
              <div className="flex flex-col gap-1">
                <span className="text-[10px] text-zinc-500 uppercase font-black tracking-widest">Test Bridge Port</span>
                <code className="text-xs bg-black/50 p-2 rounded-lg border border-white/5 text-emerald-400">
                  8001
                </code>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* The Chat Component */}
      <N8nTestChat />
    </main>
  );
}
