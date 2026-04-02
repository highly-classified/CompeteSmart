"use client";

import React, { useState, useEffect, useRef } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { MessageSquare, Send, X, Bot, User, Loader2, Sparkles, ChevronRight } from "lucide-react";
import ReactMarkdown from "react-markdown";

interface Message {
  role: "user" | "assistant";
  content: string;
}

interface Experiment {
  insight: string;
  cluster_id: string;
  trend: string;
  confidence: number;
  risk: number;
  recommended_action: string;
  evidence: string[];
}

interface CopilotChatProps {
  selectedExperiment?: string;
  experiments: Experiment[];
}

export function CopilotChat({ selectedExperiment: dashboardSelected, experiments }: CopilotChatProps) {
  const [isOpen, setIsOpen] = useState(false);
  const [input, setInput] = useState("");
  const [messages, setMessages] = useState<Message[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [activeExperiment, setActiveExperiment] = useState<{ title: string, cluster_id: string } | null>(null);
  const scrollRef = useRef<HTMLDivElement>(null);

  // Load state from localStorage on mount
  useEffect(() => {
    const savedMessages = localStorage.getItem("copilotMessages");
    const savedExperiment = localStorage.getItem("copilotActiveExperiment");
    if (savedMessages) {
      try {
        setMessages(JSON.parse(savedMessages));
      } catch (e) {
        console.error("Failed to parse saved messages", e);
      }
    }
    if (savedExperiment) {
      try {
        setActiveExperiment(JSON.parse(savedExperiment));
      } catch (e) {
        console.error("Failed to parse saved active experiment", e);
      }
    }
  }, []);

  // Save state to localStorage whenever it changes
  useEffect(() => {
    // Only save if we have messages (prevents overwriting with empty array on initial render before load)
    if (messages.length > 0) {
      localStorage.setItem("copilotMessages", JSON.stringify(messages));
    }
  }, [messages]);

  useEffect(() => {
    if (activeExperiment !== null) {
      localStorage.setItem("copilotActiveExperiment", JSON.stringify(activeExperiment));
    }
  }, [activeExperiment]);

  // Initial Greeting & Pick 3
  useEffect(() => {
    // Only show greeting if chat is opened, there are no messages, and we haven't loaded from storage
    if (isOpen && messages.length === 0 && !localStorage.getItem("copilotMessages")) {
      const topExperiments = experiments.slice(0, 3);
      if (topExperiments.length > 0) {
        setMessages([
          {
            role: "assistant",
            content: "Hello! I've analyzed the market signals and identified 3 high-potential experiments for you. Which one would you like to build a step-by-step execution plan for?"
          }
        ]);
      } else {
        setMessages([
          {
            role: "assistant",
            content: "Hello! Once you run the intelligence pipeline, I'll be able to suggest experiments for you. How can I help you today?"
          }
        ]);
      }
    }
  }, [isOpen, experiments]);

  // Handle choice from dashboard
  useEffect(() => {
    if (dashboardSelected) {
      const exp = experiments.find(e => e.recommended_action === dashboardSelected);
      if (exp) {
        setActiveExperiment({ title: exp.recommended_action, cluster_id: exp.cluster_id });
      }
    }
  }, [dashboardSelected]);

  const selectAndPlan = async (title: string, clusterId: string) => {
    setActiveExperiment({ title, cluster_id: clusterId });
    setIsOpen(true);

    // Add user preference message
    const userMsg: Message = { role: "user", content: `Let's work on the experiment: "${title}"` };
    setMessages(prev => [...prev, userMsg]);

    setIsLoading(true);
    try {
      const response = await fetch("http://localhost:8000/api/copilot/chat", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          experiment_text: title,
          user_query: "Generate a curated step-by-step flow based on the provided signals and trust layer data.",
          chat_history: messages,
          cluster_id: clusterId
        }),
      });
      const data = await response.json();
      setMessages(prev => [...prev, { role: "assistant", content: data.response }]);
    } catch (error) {
      setMessages(prev => [...prev, { role: "assistant", content: "I encountered an error while generating your plan. Please check the backend connection." }]);
    } finally {
      setIsLoading(false);
    }
  };

  // Auto-scroll to bottom
  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [messages, isOpen, isLoading]);

  const handleSend = async (customInput?: string) => {
    const textToSend = customInput || input;
    if (!textToSend.trim() || isLoading) return;

    const userMessage: Message = { role: "user", content: textToSend };
    setMessages((prev) => [...prev, userMessage]);
    if (!customInput) setInput("");
    setIsLoading(true);

    try {
      const response = await fetch("http://localhost:8000/api/copilot/chat", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          experiment_text: activeExperiment?.title || dashboardSelected || "General market inquiry",
          user_query: textToSend,
          chat_history: messages,
          cluster_id: activeExperiment?.cluster_id
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
      <button
        onClick={() => setIsOpen(true)}
        className="fixed bottom-8 right-8 w-16 h-16 bg-violet-600 hover:bg-violet-500 text-white rounded-full shadow-[0_0_30px_rgba(139,92,246,0.3)] flex items-center justify-center transition-all hover:scale-110 active:scale-95 z-50 border border-white/20 group"
      >
        <MessageSquare className="w-7 h-7 group-hover:rotate-12 transition-transform" />
        <span className="absolute -top-1 -right-1 w-4 h-4 bg-emerald-500 rounded-full border-2 border-[#050505] animate-pulse" />
      </button>

      <AnimatePresence>
        {isOpen && (
          <motion.div
            initial={{ opacity: 0, scale: 0.9, y: 20, transformOrigin: "bottom right" }}
            animate={{ opacity: 1, scale: 1, y: 0 }}
            exit={{ opacity: 0, scale: 0.9, y: 20 }}
            className="fixed bottom-28 right-8 w-[450px] h-[650px] bg-zinc-900/95 backdrop-blur-xl border border-white/10 rounded-[2rem] shadow-2xl flex flex-col z-50 overflow-hidden ring-1 ring-white/5"
          >
            {/* Header */}
            <div className="p-6 bg-gradient-to-r from-violet-600/20 to-indigo-600/20 border-b border-white/5 flex items-center justify-between">
              <div className="flex items-center gap-3">
                <div className="w-10 h-10 bg-violet-600 rounded-xl flex items-center justify-center shadow-lg shadow-violet-500/20">
                  <Bot className="w-6 h-6 text-white" />
                </div>
                <div>
                  <h3 className="text-sm font-bold text-white tracking-wide">CompeteSmart AI</h3>
                  <div className="flex items-center gap-1.5">
                    <span className="w-1.5 h-1.5 bg-emerald-500 rounded-full animate-pulse" />
                    <span className="text-[10px] text-zinc-400 uppercase font-black tracking-widest">Gemini 1.5 Powered</span>
                  </div>
                </div>
              </div>
              <button onClick={() => setIsOpen(false)} className="text-zinc-500 hover:text-white transition-colors bg-white/5 p-2 rounded-full">
                <X className="w-4 h-4" />
              </button>
            </div>

            {activeExperiment && (
              <div className="px-6 py-3 bg-violet-500/5 border-b border-white/5 flex items-center justify-between">
                <div className="flex items-center gap-2 overflow-hidden">
                  <Sparkles className="w-3 h-3 text-violet-400 flex-shrink-0" />
                  <span className="text-[9px] font-black uppercase tracking-[0.1em] text-zinc-400 truncate">
                    Target: {activeExperiment.title}
                  </span>
                </div>
                <button
                  onClick={() => setActiveExperiment(null)}
                  className="text-[9px] text-violet-400 font-bold hover:underline ml-2"
                >
                  Change
                </button>
              </div>
            )}

            <div ref={scrollRef} className="flex-1 overflow-y-auto p-6 space-y-6 scrollbar-thin scrollbar-thumb-white/10">
              {messages.map((msg, i) => (
                <motion.div
                  key={i}
                  initial={{ opacity: 0, y: 10 }}
                  animate={{ opacity: 1, y: 0 }}
                  className={`flex ${msg.role === "user" ? "justify-end" : "justify-start"}`}
                >
                  <div className={`flex gap-3 max-w-[90%] ${msg.role === "user" ? "flex-row-reverse" : ""}`}>
                    <div className={`w-8 h-8 rounded-lg flex-shrink-0 flex items-center justify-center ${msg.role === "user" ? "bg-zinc-800" : "bg-violet-600/20 text-violet-400"}`}>
                      {msg.role === "user" ? <User className="w-4 h-4" /> : <Bot className="w-4 h-4" />}
                    </div>
                    <div className="space-y-3">
                      <div className={`p-4 rounded-2xl text-[13px] leading-relaxed ${msg.role === "user" ? "bg-violet-600 text-white rounded-tr-none shadow-lg shadow-violet-500/10 whitespace-pre-wrap" : "bg-white/5 text-zinc-100 rounded-tl-none border border-white/5 markdown-body"}`}>
                        {msg.role === "user" ? (
                          msg.content
                        ) : (
                          <ReactMarkdown
                            components={{
                              p: ({ ...props }) => <p className="mb-3 last:mb-0" { ...props } />,
                              ul: ({ ...props }) => <ul className="list-disc pl-5 mb-3 space-y-1" { ...props } />,
                              ol: ({ ...props }) => <ol className="list-decimal pl-5 mb-3 space-y-1" { ...props } />,
                              li: ({ ...props }) => <li className="" { ...props } />,
                              h1: ({ ...props }) => <h1 className="text-sm font-bold mt-4 mb-2 text-white" { ...props } />,
                              h2: ({ ...props }) => <h2 className="text-sm font-bold mt-4 mb-2 text-white" { ...props } />,
                              h3: ({ ...props }) => <h3 className="text-sm font-bold mt-4 mb-2 text-violet-300" { ...props } />,
                              strong: ({ ...props }) => <strong className="font-bold text-violet-200" { ...props } />,
                            }}
                          >
                            {msg.content}
                          </ReactMarkdown>
                        )}
                      </div>

                      {/* Pick 3 Options if it's the first message and no experiment is active */}
                      {i === 0 && msg.role === "assistant" && !activeExperiment && experiments.length > 0 && (
                        <div className="flex flex-col gap-2 mt-4">
                          {experiments.slice(0, 3).map((exp, idx) => (
                            <button
                              key={idx}
                              onClick={() => selectAndPlan(exp.recommended_action, exp.cluster_id)}
                              className="w-full text-left p-3 rounded-xl bg-white/5 border border-white/10 hover:bg-white/10 transition-all group flex items-center justify-between"
                            >
                              <div className="flex flex-col gap-1 overflow-hidden">
                                <span className="text-[10px] text-violet-400 font-bold uppercase tracking-wider">Experiment {idx + 1}</span>
                                <span className="text-xs text-zinc-300 truncate">{exp.recommended_action}</span>
                              </div>
                              <ChevronRight className="w-4 h-4 text-zinc-600 group-hover:text-white transition-colors flex-shrink-0" />
                            </button>
                          ))}
                        </div>
                      )}
                    </div>
                  </div>
                </motion.div>
              ))}
              {isLoading && (
                <div className="flex justify-start">
                  <div className="flex gap-3 items-center bg-white/5 px-4 py-3 rounded-2xl border border-white/5">
                    <Loader2 className="w-4 h-4 text-violet-400 animate-spin" />
                    <span className="text-xs text-zinc-400 font-medium italic">Gemini is synthesizing market intelligence...</span>
                  </div>
                </div>
              )}
            </div>

            <div className="p-6 bg-zinc-900 border-t border-white/5">
              <div className="relative">
                <input
                  type="text"
                  value={input}
                  onChange={(e) => setInput(e.target.value)}
                  onKeyDown={(e) => e.key === "Enter" && handleSend()}
                  placeholder={activeExperiment ? "Ask about phase details or risks..." : "First, pick an experiment above..."}
                  className="w-full bg-white/5 border border-white/10 rounded-2xl py-4 pl-5 pr-14 text-sm focus:outline-none focus:border-violet-500 transition-all text-white placeholder:text-zinc-600 shadow-inner"
                />
                <button
                  onClick={() => handleSend()}
                  disabled={isLoading || !input.trim()}
                  className="absolute right-2 top-2 w-10 h-10 bg-violet-600 hover:bg-violet-500 disabled:opacity-50 disabled:bg-zinc-800 text-white rounded-xl flex items-center justify-center transition-all active:scale-90 shadow-lg shadow-violet-500/20"
                >
                  <Send className="w-4 h-4" />
                </button>
              </div>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </>
  );
}
