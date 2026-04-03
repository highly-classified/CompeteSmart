"use client";

import React, { useState, useEffect, useRef } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { MessageSquare, Send, X, Bot, User, Loader2, Sparkles, ChevronRight } from "lucide-react";
import ReactMarkdown from "react-markdown";

interface Message {
  role: "user" | "assistant";
  content: string;
}

export function N8nTestChat() {
  const [isOpen, setIsOpen] = useState(false);
  const [input, setInput] = useState("");
  const [messages, setMessages] = useState<Message[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const scrollRef = useRef<HTMLDivElement>(null);
  const [sessionId, setSessionId] = useState<string>("");

  useEffect(() => {
    // Generate simple sessionId
    setSessionId("test_session_" + Math.random().toString(36).substr(2, 9));
    
    // Initial greeting for n8n test
    setMessages([
      {
        role: "assistant",
        content: "Welcome to the **CompeteSmart Experiment Suggestion Chatbot (n8n Tested)**! Ask me about tracking competitors, A/B testing, or suggesting strategic experiments."
      }
    ]);
  }, []);

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
      // Calling the NEW standalone test API on port 8001
      const response = await fetch("http://localhost:8001/api/n8n/chat", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          message: textToSend,
          history: messages,
          sessionId: sessionId
        }),
      });

      const data = await response.json();
      
      if (data.success) {
          setMessages((prev) => [...prev, { role: "assistant", content: data.reply }]);
      } else {
          setMessages((prev) => [...prev, { role: "assistant", content: `Error from n8n: ${data.reply}` }]);
      }
    } catch (error) {
      setMessages((prev) => [...prev, { role: "assistant", content: "Sorry, I'm having trouble connecting to the n8n test API on port 8001. Ensure it's running." }]);
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <>
      <button
        onClick={() => setIsOpen(true)}
        className="fixed bottom-8 right-8 w-16 h-16 bg-emerald-600 hover:bg-emerald-500 text-white rounded-full shadow-[0_0_30px_rgba(16,185,129,0.3)] flex items-center justify-center transition-all hover:scale-110 active:scale-95 z-50 border border-white/20 group"
      >
        <MessageSquare className="w-7 h-7 group-hover:rotate-12 transition-transform" />
        <span className="absolute -top-1 -right-1 w-4 h-4 bg-emerald-400 rounded-full border-2 border-[#050505] animate-pulse" />
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
            <div className="p-6 bg-gradient-to-r from-emerald-600/20 to-teal-600/20 border-b border-white/5 flex items-center justify-between">
              <div className="flex items-center gap-3">
                <div className="w-10 h-10 bg-emerald-600 rounded-xl flex items-center justify-center shadow-lg shadow-emerald-500/20">
                  <Bot className="w-6 h-6 text-white" />
                </div>
                <div>
                  <h3 className="text-sm font-bold text-white tracking-wide">CompeteSmart n8n Test</h3>
                  <div className="flex items-center gap-1.5">
                    <span className="w-1.5 h-1.5 bg-emerald-500 rounded-full animate-pulse" />
                    <span className="text-[10px] text-zinc-400 uppercase font-black tracking-widest">Standalone Test Instance</span>
                  </div>
                </div>
              </div>
              <button onClick={() => setIsOpen(false)} className="text-zinc-500 hover:text-white transition-colors bg-white/5 p-2 rounded-full">
                <X className="w-4 h-4" />
              </button>
            </div>

            <div ref={scrollRef} className="flex-1 overflow-y-auto p-6 space-y-6 scrollbar-thin scrollbar-thumb-white/10">
              {messages.map((msg, i) => (
                <motion.div
                  key={i}
                  initial={{ opacity: 0, y: 10 }}
                  animate={{ opacity: 1, y: 0 }}
                  className={`flex ${msg.role === "user" ? "justify-end" : "justify-start"}`}
                >
                  <div className={`flex gap-3 max-w-[90%] ${msg.role === "user" ? "flex-row-reverse" : ""}`}>
                    <div className={`w-8 h-8 rounded-lg flex-shrink-0 flex items-center justify-center ${msg.role === "user" ? "bg-zinc-800" : "bg-emerald-600/20 text-emerald-400"}`}>
                      {msg.role === "user" ? <User className="w-4 h-4" /> : <Bot className="w-4 h-4" />}
                    </div>
                    <div className="space-y-3">
                      <div className={`p-4 rounded-2xl text-[13px] leading-relaxed ${msg.role === "user" ? "bg-emerald-600 text-white rounded-tr-none shadow-lg shadow-emerald-500/10 whitespace-pre-wrap" : "bg-white/5 text-zinc-100 rounded-tl-none border border-white/5 markdown-body"}`}>
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
                              h3: ({ ...props }) => <h3 className="text-sm font-bold mt-4 mb-2 text-emerald-300" { ...props } />,
                              strong: ({ ...props }) => <strong className="font-bold text-emerald-200" { ...props } />,
                            }}
                          >
                            {msg.content}
                          </ReactMarkdown>
                        )}
                      </div>
                    </div>
                  </div>
                </motion.div>
              ))}
              {isLoading && (
                <div className="flex justify-start">
                  <div className="flex gap-3 items-center bg-white/5 px-4 py-3 rounded-2xl border border-white/5">
                    <Loader2 className="w-4 h-4 text-emerald-400 animate-spin" />
                    <span className="text-xs text-zinc-400 font-medium italic">n8n is processing your request...</span>
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
                  placeholder="Ask for an experiment suggestion..."
                  className="w-full bg-white/5 border border-white/10 rounded-2xl py-4 pl-5 pr-14 text-sm focus:outline-none focus:border-emerald-500 transition-all text-white placeholder:text-zinc-600 shadow-inner"
                />
                <button
                  onClick={() => handleSend()}
                  disabled={isLoading || !input.trim()}
                  className="absolute right-2 top-2 w-10 h-10 bg-emerald-600 hover:bg-emerald-500 disabled:opacity-50 disabled:bg-zinc-800 text-white rounded-xl flex items-center justify-center transition-all active:scale-90 shadow-lg shadow-emerald-500/20"
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
