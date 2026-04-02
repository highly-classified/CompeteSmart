"use client";

import React, { useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { useRouter } from "next/navigation";
import { 
  Building2, 
  Mail, 
  User, 
  Plus, 
  Trash2, 
  Sparkles, 
  ArrowRight,
  ShieldCheck,
  CheckCircle2,
  Loader2,
  Globe,
  MapPin,
  ChevronDown
} from "lucide-react";

export default function SetupPage() {
  const router = useRouter();
  const [formData, setFormData] = useState({
    name: "",
    email: "admin@test.com",
    company_name: "",
    website: "",
    industry: "",
    location: "",
    business_type: "saas"
  });
  const [competitors, setCompetitors] = useState<string[]>([]);
  const [currentCompetitor, setCurrentCompetitor] = useState("");
  const [isSuggesting, setIsSuggesting] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [feedback, setFeedback] = useState<{ type: "success" | "error", message: string } | null>(null);

  const addCompetitor = (name: string) => {
    const trimmed = name.trim();
    if (!trimmed || competitors.length >= 3 || competitors.some(c => c.toLowerCase() === trimmed.toLowerCase())) {
      if (competitors.length >= 3 && trimmed) {
        setFeedback({ type: "error", message: "Maximum 3 competitors allowed." });
      }
      return;
    }
    setCompetitors([...competitors, trimmed]);
    setCurrentCompetitor("");
    setFeedback(null);
  };

  const removeCompetitor = (name: string) => {
    setCompetitors(competitors.filter(c => c !== name));
  };

  const getAiSuggestions = async () => {
    if (!formData.company_name) {
      alert("Please enter your company name first.");
      return;
    }
    setIsSuggesting(true);
    try {
      const url = new URL("http://localhost:8000/api/competitors/suggestions");
      url.searchParams.append("company_name", formData.company_name);
      if (formData.industry) url.searchParams.append("industry", formData.industry);
      if (formData.location) url.searchParams.append("location", formData.location);
      url.searchParams.append("business_type", formData.business_type);

      const response = await fetch(url.toString());
      const suggestions = await response.json();
      if (Array.isArray(suggestions)) {
        // Filter out suggestions already in the list
        const existingLower = competitors.map(c => c.toLowerCase());
        const newSuggestions = suggestions.filter(s => !existingLower.includes(s.toLowerCase()));
        setCompetitors([...competitors, ...newSuggestions]);
      }
    } catch (err) {
      console.error(err);
      alert("AI suggestions failed. Please try adding manually.");
    } finally {
      setIsSuggesting(false);
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!formData.name || !formData.company_name || competitors.length === 0) {
      setFeedback({ type: "error", message: "Please fill all fields and add at least one competitor." });
      return;
    }

    setIsSubmitting(true);
    setFeedback(null);

    const token = localStorage.getItem("token");
    try {
      const response = await fetch("http://localhost:8000/api/user/setup", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "Authorization": `Bearer ${token}`
        },
        body: JSON.stringify({
          ...formData,
          competitors
        })
      });

      if (response.ok) {
        setFeedback({ type: "success", message: "Intelligence profile updated successfully!" });
        setTimeout(() => {
          router.push("/dashboard");
        }, 1500);
      } else {
        const errorData = await response.json();
        setFeedback({ type: "error", message: errorData.detail || "Failed to save profile. Please try again." });
      }
    } catch (err) {
      setFeedback({ type: "error", message: "An error occurred. Check your connection." });
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <main className="min-h-screen bg-background flex items-center justify-center p-4 md:p-8 relative overflow-hidden font-sans text-foreground">
      {/* Dynamic Background */}
      <div className="absolute top-0 left-0 w-full h-full -z-10">
        <div className="absolute top-1/4 left-1/4 w-[500px] h-[500px] bg-purple-500/10 blur-[120px] rounded-full animate-pulse" />
        <div className="absolute bottom-1/4 right-1/4 w-[600px] h-[600px] bg-blue-500/10 blur-[140px] rounded-full" />
      </div>

      <motion.div 
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.8, ease: [0.16, 1, 0.3, 1] }}
        className="w-full max-w-4xl bg-foreground/[0.02] border border-foreground/10 rounded-[2.5rem] p-6 md:p-12 backdrop-blur-3xl shadow-[0_32px_64px_-12px_rgba(0,0,0,0.5)] relative"
      >
        <div className="flex flex-col md:flex-row gap-12">
          {/* Left Column: Form Info */}
          <div className="flex-1 space-y-10">
            <div>
              <div className="flex items-center gap-2 text-primary mb-5 px-3 py-1.5 w-fit bg-purple-500/10 rounded-full border border-purple-500/20">
                <Sparkles className="w-3.5 h-3.5 text-purple-400" />
                <span className="text-[10px] font-bold uppercase tracking-[0.2em] text-purple-400">Onboarding Phase 1</span>
              </div>
              <h1 className="text-4xl md:text-5xl font-medium tracking-tight leading-[1.1] text-foreground">
                Set Your <span className="text-transparent bg-clip-text bg-gradient-to-r from-purple-400 to-blue-400">Edge</span>
              </h1>
              <p className="mt-4 text-foreground/50 text-sm leading-relaxed max-w-sm">
                CompeteSmart needs a few details about your business to calibrate our intelligence engines for your market.
              </p>
            </div>

            <form onSubmit={handleSubmit} className="space-y-6">
              <div className="space-y-4">
                <div className="relative group">
                  <User className="absolute left-4 top-1/2 -translate-y-1/2 w-4 h-4 text-foreground/30 group-focus-within:text-purple-400 transition-colors" />
                  <input
                    type="text"
                    required
                    placeholder="Your Full Name"
                    value={formData.name}
                    onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                    className="w-full bg-background/50 border border-foreground/10 rounded-2xl py-4 pl-12 pr-4 text-sm focus:border-purple-400/50 outline-none transition-all placeholder:text-foreground/20 focus:ring-1 focus:ring-purple-400/20"
                  />
                </div>
                <div className="relative group">
                  <Mail className="absolute left-4 top-1/2 -translate-y-1/2 w-4 h-4 text-foreground/30" />
                  <input
                    type="email"
                    required
                    placeholder="Email Address"
                    value={formData.email}
                    readOnly
                    className="w-full bg-background/20 border border-foreground/5 rounded-2xl py-4 pl-12 pr-4 text-sm text-foreground/30 outline-none cursor-not-allowed italic"
                  />
                </div>
                <div className="relative group">
                  <Building2 className="absolute left-4 top-1/2 -translate-y-1/2 w-4 h-4 text-foreground/30 group-focus-within:text-blue-400 transition-colors" />
                  <input
                    type="text"
                    required
                    placeholder="Your Company Name"
                    value={formData.company_name}
                    onChange={(e) => setFormData({ ...formData, company_name: e.target.value })}
                    className="w-full bg-background/50 border border-foreground/10 rounded-2xl py-4 pl-12 pr-4 text-sm focus:border-blue-400/50 outline-none transition-all placeholder:text-foreground/20 focus:ring-1 focus:ring-blue-400/20"
                  />
                </div>
                <div className="relative group">
                  <Globe className="absolute left-4 top-1/2 -translate-y-1/2 w-4 h-4 text-foreground/30 group-focus-within:text-emerald-400 transition-colors" />
                  <input
                    type="url"
                    placeholder="Company Website (Optional)"
                    value={formData.website}
                    onChange={(e) => setFormData({ ...formData, website: e.target.value })}
                    className="w-full bg-background/50 border border-foreground/10 rounded-2xl py-4 pl-12 pr-4 text-sm focus:border-emerald-400/50 outline-none transition-all placeholder:text-foreground/20 focus:ring-1 focus:ring-emerald-400/20"
                  />
                </div>

                <div className="grid grid-cols-2 gap-4">
                  <div className="relative group">
                    <MapPin className="absolute left-4 top-1/2 -translate-y-1/2 w-4 h-4 text-foreground/30 group-focus-within:text-red-400 transition-colors" />
                    <input
                      type="text"
                      placeholder="Location (City/Country)"
                      value={formData.location}
                      onChange={(e) => setFormData({ ...formData, location: e.target.value })}
                      className="w-full bg-background/50 border border-foreground/10 rounded-2xl py-4 pl-12 pr-4 text-xs focus:border-red-400/50 outline-none transition-all placeholder:text-foreground/20"
                    />
                  </div>
                  <div className="relative group">
                    <Building2 className="absolute left-4 top-1/2 -translate-y-1/2 w-4 h-4 text-foreground/30 pointer-events-none group-focus-within:text-blue-400 transition-colors" />
                    <select
                      value={formData.business_type}
                      onChange={(e) => setFormData({ ...formData, business_type: e.target.value })}
                      className="w-full bg-background/50 border border-foreground/10 rounded-2xl py-4 pl-12 pr-8 text-xs focus:border-blue-400/50 outline-none transition-all appearance-none cursor-pointer"
                    >
                      <option value="saas">SaaS / Global</option>
                      <option value="local">Local / Area-based</option>
                    </select>
                    <ChevronDown className="absolute right-4 top-1/2 -translate-y-1/2 w-3.5 h-3.5 text-foreground/20 pointer-events-none" />
                  </div>
                </div>
              </div>
            </form>
          </div>

          {/* Right Column: Competitors */}
          <div className="flex-1 flex flex-col pt-8 md:pt-0">
            <div className="bg-foreground/[0.03] border border-foreground/10 rounded-3xl p-6 md:p-8 flex-1 flex flex-col relative overflow-hidden group/card shadow-inner">
               {/* Inner glow */}
              <div className="absolute top-0 right-0 w-24 h-24 bg-purple-500/5 blur-3xl -z-10 group-hover/card:bg-purple-500/10 transition-colors" />
              
              <div className="flex items-center justify-between mb-8">
                <div className="space-y-1">
                  <h3 className="text-xs font-bold tracking-[0.1em] uppercase text-foreground/60">Competitors</h3>
                  <p className="text-[10px] text-foreground/30 font-medium whitespace-nowrap">Who are we outperforming today?</p>
                </div>
                <button 
                  onClick={getAiSuggestions}
                  disabled={isSuggesting || competitors.length >= 3}
                  className="flex items-center gap-2 px-4 py-2 bg-purple-500/10 hover:bg-purple-500/20 border border-purple-500/30 rounded-full transition-all group/ai disabled:opacity-50 active:scale-95"
                >
                  {isSuggesting ? (
                    <Loader2 className="w-3.5 h-3.5 animate-spin text-purple-400" />
                  ) : (
                    <Sparkles className="w-3.5 h-3.5 text-purple-400 group-hover/ai:scale-110 transition-transform" />
                  )}
                  <span className="text-[10px] font-bold text-purple-400 uppercase tracking-widest">AI Suggest</span>
                </button>
              </div>

              <div className="flex gap-2 mb-6">
                <div className="relative flex-1">
                   <Plus className="absolute left-3.5 top-1/2 -translate-y-1/2 w-3.5 h-3.5 text-foreground/20" />
                  <input
                    type="text"
                    placeholder={competitors.length >= 3 ? "Limit reached (3)" : "Add competitor name..."}
                    value={currentCompetitor}
                    disabled={competitors.length >= 3}
                    onChange={(e) => setCurrentCompetitor(e.target.value)}
                    onKeyDown={(e) => e.key === "Enter" && addCompetitor(currentCompetitor)}
                    className="w-full bg-background/50 border border-foreground/10 rounded-xl py-3 pl-10 pr-4 text-xs focus:border-foreground/30 outline-none transition-all placeholder:text-foreground/20 disabled:opacity-50 italic"
                  />
                </div>
                <button 
                  onClick={() => addCompetitor(currentCompetitor)}
                  disabled={competitors.length >= 3}
                  className="px-4 bg-foreground/5 hover:bg-foreground/10 border border-foreground/10 rounded-xl transition-all active:scale-95 disabled:opacity-50"
                >
                  <Plus className="w-4 h-4 text-foreground/60" />
                </button>
              </div>

              <div className="flex-1 overflow-y-auto space-y-2 max-h-[160px] pr-2 custom-scrollbar">
                <AnimatePresence mode="popLayout">
                  {competitors.length === 0 ? (
                    <motion.div 
                      key="empty"
                      initial={{ opacity: 0 }}
                      animate={{ opacity: 1 }}
                      exit={{ opacity: 0 }}
                      className="h-full flex flex-col items-center justify-center text-center opacity-10 py-10"
                    >
                      <Building2 className="w-10 h-10 mb-3" />
                      <p className="text-[10px] font-bold uppercase tracking-[0.2em]">Manual Input Required</p>
                    </motion.div>
                  ) : (
                    competitors.map((comp) => (
                      <motion.div
                        key={comp}
                        layout
                        initial={{ opacity: 0, x: -10, scale: 0.95 }}
                        animate={{ opacity: 1, x: 0, scale: 1 }}
                        exit={{ opacity: 0, scale: 0.9, transition: { duration: 0.2 } }}
                        className="flex items-center justify-between bg-background/40 hover:bg-background/60 border border-foreground/5 rounded-xl px-4 py-3.5 group/item transition-all"
                      >
                        <span className="text-xs font-semibold text-foreground/70">{comp}</span>
                        <button 
                          onClick={() => removeCompetitor(comp)}
                          className="opacity-0 group-hover/item:opacity-100 p-1.5 hover:bg-red-500/10 rounded-lg transition-all"
                        >
                          <Trash2 className="w-3.5 h-3.5 text-red-500/40 hover:text-red-500 transition-colors" />
                        </button>
                      </motion.div>
                    ))
                  )}
                </AnimatePresence>
              </div>

              <div className="mt-8 pt-8 border-t border-foreground/5 space-y-6">
                <div className="flex items-start gap-3 p-4 bg-blue-500/[0.04] border border-blue-500/10 rounded-2xl">
                  <ShieldCheck className="w-5 h-5 text-blue-400/60 shrink-0 mt-0.5" />
                  <p className="text-[10px] text-foreground/40 leading-relaxed font-medium">
                    Data is siloed and encrypted. Your monitoring activity is invisible to the target domains.
                  </p>
                </div>

                <div className="space-y-3">
                  <button
                    onClick={handleSubmit}
                    disabled={isSubmitting}
                    className="w-full flex items-center justify-center gap-3 bg-foreground text-background py-4.5 rounded-2xl font-bold text-sm hover:opacity-90 active:scale-[0.98] transition-all disabled:opacity-50 shadow-lg shadow-background/20"
                  >
                    {isSubmitting ? (
                      <Loader2 className="w-5 h-5 animate-spin" />
                    ) : (
                      <>
                        <span>Unlock Market Intelligence</span>
                        <ArrowRight className="w-4 h-4 group-hover:translate-x-1 transition-transform" />
                      </>
                    )}
                  </button>

                  <AnimatePresence>
                    {feedback && (
                      <motion.div 
                        initial={{ opacity: 0, y: 10 }}
                        animate={{ opacity: 1, y: 0 }}
                        exit={{ opacity: 0 }}
                        className={`flex items-center gap-2 p-3.5 rounded-xl border text-[11px] font-bold uppercase tracking-wider ${
                          feedback.type === "success" 
                            ? "bg-green-500/10 border-green-500/20 text-green-400" 
                            : "bg-red-500/10 border-red-500/20 text-red-400"
                        }`}
                      >
                        <CheckCircle2 className="w-4 h-4 shrink-0" />
                        {feedback.message}
                      </motion.div>
                    )}
                  </AnimatePresence>
                </div>
              </div>
            </div>
          </div>
        </div>

        {/* Global Footer Accent */}
        <div className="absolute -bottom-[1px] left-1/2 -translate-x-1/2 w-3/4 h-[2px] bg-gradient-to-r from-transparent via-purple-400/30 to-transparent blur-[1px]" />
      </motion.div>

      <style jsx global>{`
        @import url('https://fonts.googleapis.com/css2?family=Gilda+Display&display=swap');
        
        .font-display {
          font-family: 'Gilda Display', serif;
        }

        .custom-scrollbar::-webkit-scrollbar {
          width: 4px;
        }
        .custom-scrollbar::-webkit-scrollbar-track {
          background: transparent;
        }
        .custom-scrollbar::-webkit-scrollbar-thumb {
          background: rgba(255, 255, 255, 0.05);
          border-radius: 10px;
        }
        .custom-scrollbar::-webkit-scrollbar-thumb:hover {
          background: rgba(255, 255, 255, 0.1);
        }

        input {
           caret-color: #a855f7;
        }
      `}</style>
    </main>
  );
}
