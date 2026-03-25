"use client";

import React, { useState, useEffect, useRef } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { MessageSquare, Send, X, Bot, User, Loader2, Sparkles, ChevronRight } from "lucide-react";

interface Message {
  role: "user" | "assistant";
  content: string;
}

interface CopilotChatProps {
  selectedExperiment?: string;
  experiments: any[];
}

export function CopilotChat({ selectedExperiment, experiments }: CopilotChatProps) {
  const [isOpen, setIsOpen] = useState(false);
  const [input, setInput] = useState("");
  const [messages, setMessages] = useState<Message[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const scrollRef = useRef<HTMLDivElement>(null);

  // Auto-scroll to bottom
  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [messages, isOpen]);

  const handleSend = async () => {
    if (!input.trim() || isLoading) return;

    const userMessage: Message = { role: "user", content: input };
    setMessages((prev) => [...prev, userMessage]);
    setInput("");
    setIsLoading(true);

    try {
      const response = await fetch("http://localhost:8000/api/copilot/chat", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          experiment_text: selectedExperiment || "No specific experiment chosen.",
          user_query: input,
          chat_history: messages
        }),
      });

      const data = await response.json();
      setMessages((prev) => [...prev, { role: "assistant", content: data.response }]);
    } catch (error) {
      setMessages((prev) => [...prev, { role: "assistant", content: "Sorry, I'm having trouble connecting to the intelligence engine." }]);
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <>
      {/* Floating Toggle Button */}
      <button
        onClick={() => setIsOpen(true)}
        className="fixed bottom-8 right-8 w-16 h-16 bg-violet-600 hover:bg-violet-500 text-white rounded-full shadow-[0_0_30px_rgba(139,92,246,0.3)] flex items-center justify-center transition-all hover:scale-110 active:scale-95 z-50 border border-white/20 group"
      >
        <MessageSquare className="w-7 h-7 group-hover:rotate-12 transition-transform" />
        <span className="absolute -top-1 -right-1 w-4 h-4 bg-emerald-500 rounded-full border-2 border-[#050505] animate-pulse" />
      </button>

      {/* Chat Window */}
      <AnimatePresence>
        {isOpen && (
          <motion.div
            initial={{ opacity: 0, scale: 0.9, y: 20, transformOrigin: "bottom right" }}
            animate={{ opacity: 1, scale: 1, y: 0 }}
            exit={{ opacity: 0, scale: 0.9, y: 20 }}
            className="fixed bottom-28 right-8 w-[400px] h-[600px] bg-zinc-900/95 backdrop-blur-xl border border-white/10 rounded-[2rem] shadow-2xl flex flex-col z-50 overflow-hidden ring-1 ring-white/5"
          >
            {/* Header */}
            <div className="p-6 bg-gradient-to-r from-violet-600/20 to-indigo-600/20 border-b border-white/5 flex items-center justify-between">
              <div className="flex items-center gap-3">
                <div className="w-10 h-10 bg-violet-600 rounded-xl flex items-center justify-center">
                  <Bot className="w-6 h-6 text-white" />
                </div>
                <div>
                  <h3 className="text-sm font-bold text-white tracking-wide">Execution Copilot</h3>
                  <div className="flex items-center gap-1.5">
                    <span className="w-1.5 h-1.5 bg-emerald-500 rounded-full animate-pulse" />
                    <span className="text-[10px] text-zinc-400 uppercase font-black tracking-widest">Neural Mode</span>
                  </div>
                </div>
              </div>
              <button onClick={() => setIsOpen(false)} className="text-zinc-500 hover:text-white transition-colors">
                <X className="w-5 h-5" />
              </button>
            </div>

            {/* Experiment Context Bar */}
            <div className="px-6 py-3 bg-white/5 border-b border-white/5">
              <div className="flex items-center gap-2 mb-1">
                <Sparkles className="w-3 h-3 text-violet-400" />
                <span className="text-[9px] font-black uppercase tracking-[0.2em] text-violet-400">Context: Active Experiment</span>
              </div>
              <p className="text-[11px] text-zinc-300 line-clamp-2 leading-relaxed italic">
                {selectedExperiment ? `"${selectedExperiment}"` : "Please select an experiment from the dashboard to enable specialized analysis."}
              </p>
            </div>

            {/* Messages */}
            <div ref={scrollRef} className="flex-1 overflow-y-auto p-6 space-y-6 scrollbar-thin scrollbar-thumb-white/10">
              {messages.length === 0 && (
                <div className="h-full flex flex-col items-center justify-center text-center opacity-40 px-8">
                  <Bot className="w-12 h-12 mb-4" />
                  <p className="text-sm font-medium">Hello! I'm your Market Copilot. Select an experiment and ask me about risks, logistics, or market alignment.</p>
                </div>
              )}
              {messages.map((msg, i) => (
                <motion.div
                  key={i}
                  initial={{ opacity: 0, y: 10 }}
                  animate={{ opacity: 1, y: 0 }}
                  className={`flex ${msg.role === "user" ? "justify-end" : "justify-start"}`}
                >
                  <div className={`flex gap-3 max-w-[85%] ${msg.role === "user" ? "flex-row-reverse" : ""}`}>
                    <div className={`w-8 h-8 rounded-lg flex-shrink-0 flex items-center justify-center ${msg.role === "user" ? "bg-zinc-800" : "bg-violet-600/20 text-violet-400"}`}>
                      {msg.role === "user" ? <User className="w-4 h-4" /> : <Bot className="w-4 h-4" />}
                    </div>
                    <div className={`p-4 rounded-2xl text-sm leading-relaxed ${msg.role === "user" ? "bg-violet-600 text-white rounded-tr-none" : "bg-white/5 text-zinc-100 rounded-tl-none border border-white/5"}`}>
                      {msg.content}
                    </div>
                  </div>
                </motion.div>
              ))}
              {isLoading && (
                <div className="flex justify-start">
                  <div className="flex gap-3 items-center bg-white/5 px-4 py-3 rounded-2xl border border-white/5">
                    <Loader2 className="w-4 h-4 text-violet-400 animate-spin" />
                    <span className="text-xs text-zinc-400 font-medium italic">Analyzing market signals...</span>
                  </div>
                </div>
              )}
            </div>

            {/* Input */}
            <div className="p-6 bg-zinc-900 border-t border-white/5">
              <div className="relative">
                <input
                  type="text"
                  value={input}
                  onChange={(e) => setInput(e.target.value)}
                  onKeyDown={(e) => e.key === "Enter" && handleSend()}
                  placeholder="Ask about risks, competitors..."
                  className="w-full bg-white/5 border border-white/10 rounded-2xl py-4 pl-5 pr-14 text-sm focus:outline-none focus:border-violet-500 transition-all text-white placeholder:text-zinc-600"
                />
                <button
                  onClick={handleSend}
                  disabled={isLoading || !input.trim()}
                  className="absolute right-2 top-2 w-10 h-10 bg-violet-600 hover:bg-violet-500 disabled:opacity-50 disabled:bg-zinc-800 text-white rounded-xl flex items-center justify-center transition-all active:scale-90"
                >
                  <Send className="w-4 h-4" />
                </button>
              </div>
              <p className="text-[10px] text-zinc-600 mt-4 text-center font-bold tracking-widest uppercase">
                Powered by CompeteSmart RAG Engine
              </p>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </>
  );
}
