"use client";

import React, { useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { ArrowLeft } from "lucide-react";
import Link from "next/link";

export default function AuthPage() {
  const [isLogin, setIsLogin] = useState(true);
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [neonUrl, setNeonUrl] = useState("");

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    // Placeholder for actual backend auth integration
    console.log("Submitting Auth payload:", { isLogin, email, password, neonUrl });
  };

  return (
    <main className="min-h-screen w-full bg-background flex flex-col items-center justify-center relative p-6 font-sans overflow-hidden">
      {/* Background Accent */}
      <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[90vw] md:w-[60vw] h-[90vw] md:h-[60vw] bg-[hsl(220,70%,78%)] opacity-[0.04] blur-[120px] rounded-full pointer-events-none z-0" />

      {/* Back to Home Navigation */}
      <Link href="/" className="absolute top-8 left-6 md:left-10 z-20 flex items-center gap-2 text-foreground/60 hover:text-foreground transition-colors">
        <ArrowLeft className="w-5 h-5" />
        <span className="text-sm tracking-widest uppercase">Back to Home</span>
      </Link>

      <motion.div 
        initial={{ opacity: 0, scale: 0.95, y: 10 }}
        animate={{ opacity: 1, scale: 1, y: 0 }}
        transition={{ duration: 0.6, ease: [0.25, 1, 0.5, 1] }}
        className="w-full max-w-md bg-foreground/[0.02] border border-foreground/10 rounded-3xl p-8 relative z-10 backdrop-blur-md shadow-2xl"
      >
        <div className="flex flex-col items-center mb-8 text-center pt-2">
          <span className="text-3xl md:text-4xl font-bungee tracking-wider text-foreground drop-shadow-md mb-3">
            competeSmart
          </span>
          <p className="text-foreground/60 text-sm px-4">
            {isLogin ? "Welcome back to your intelligence dashboard" : "Join the next generation of market intelligence"}
          </p>
        </div>

        {/* Toggle Login/Signup */}
        <div className="flex bg-foreground/5 rounded-full p-1.5 mb-8">
          <button
            type="button"
            onClick={() => setIsLogin(true)}
            className={`flex-1 py-2.5 rounded-full text-sm font-medium transition-all duration-300 ${isLogin ? "bg-foreground text-background shadow-md" : "text-foreground/70 hover:text-foreground hover:bg-foreground/5"}`}
          >
            Log In
          </button>
          <button
            type="button"
            onClick={() => setIsLogin(false)}
            className={`flex-1 py-2.5 rounded-full text-sm font-medium transition-all duration-300 ${!isLogin ? "bg-foreground text-background shadow-md" : "text-foreground/70 hover:text-foreground hover:bg-foreground/5"}`}
          >
            Sign Up
          </button>
        </div>

        <form onSubmit={handleSubmit} className="flex flex-col gap-4">
          <div className="flex flex-col gap-1.5">
            <label className="text-xs font-semibold uppercase tracking-widest text-foreground/70 pl-2">Email Address</label>
            <input
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              className="w-full bg-background/60 border border-foreground/15 rounded-xl px-4 py-3.5 text-foreground focus:outline-none focus:border-foreground/40 focus:ring-1 focus:ring-foreground/20 transition-all"
              placeholder="name@company.com"
              required
            />
          </div>

          {/* Animated Neon DB URL Input (exclusively for Signup) */}
          <AnimatePresence mode="popLayout">
            {!isLogin && (
              <motion.div
                initial={{ opacity: 0, height: 0, scaleY: 0.8 }}
                animate={{ opacity: 1, height: "auto", scaleY: 1 }}
                exit={{ opacity: 0, height: 0, scaleY: 0.8 }}
                transition={{ duration: 0.35, ease: "easeInOut" }}
                className="flex flex-col gap-1.5 overflow-hidden origin-top"
              >
                <div className="pt-2 flex flex-col gap-1.5 pb-2">
                  <label className="text-xs font-semibold uppercase tracking-widest text-foreground/70 pl-2 flex items-center justify-between">
                    Neon Database URL
                    <span className="text-[10px] text-[hsl(220,70%,78%)] tracking-normal lowercase border border-[hsl(220,70%,78%)]/30 rounded px-1.5 py-0.5">Required</span>
                  </label>
                  <input
                    type="text"
                    value={neonUrl}
                    onChange={(e) => setNeonUrl(e.target.value)}
                    className="w-full bg-background/60 border border-foreground/15 rounded-xl px-4 py-3.5 text-foreground focus:outline-none focus:border-[hsl(220,70%,78%)] focus:ring-1 focus:ring-[hsl(220,70%,78%)]/30 transition-all"
                    placeholder="postgres://user:password@endpoint..."
                    required={!isLogin}
                  />
                  <p className="text-[10px] text-foreground/40 pl-2 pr-2 mt-1 leading-snug">
                    Provide your Neon connection string to directly sync competitor intelligence datasets with your infrastructure.
                  </p>
                </div>
              </motion.div>
            )}
          </AnimatePresence>

          <div className="flex flex-col gap-1.5 mb-2 mt-1">
            <label className="text-xs font-semibold uppercase tracking-widest text-foreground/70 pl-2 flex justify-between">
              Password
              {isLogin && <a href="#" className="text-foreground/40 hover:text-foreground text-[10px] tracking-normal capitalize underline-offset-4 hover:underline">Forgot?</a>}
            </label>
            <input
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              className="w-full bg-background/60 border border-foreground/15 rounded-xl px-4 py-3.5 text-foreground focus:outline-none focus:border-foreground/40 focus:ring-1 focus:ring-foreground/20 transition-all font-mono tracking-widest text-lg"
              placeholder="••••••••"
              required
            />
          </div>

          <button
            type="submit"
            className="w-full bg-foreground text-background font-semibold tracking-wide py-3.5 rounded-xl hover:opacity-90 hover:scale-[1.01] active:scale-[0.98] transition-all mt-3"
          >
            {isLogin ? "Sign In Securely" : "Create Account"}
          </button>
        </form>

        <div className="flex items-center gap-4 my-7">
          <div className="flex-1 h-[1px] bg-foreground/10" />
          <span className="text-[10px] uppercase text-foreground/40 tracking-widest font-semibold">Or continue with</span>
          <div className="flex-1 h-[1px] bg-foreground/10" />
        </div>

        <button
          type="button"
          onClick={() => console.log("Google Sign In trigger")}
          className="w-full flex items-center justify-center gap-3 bg-foreground/5 border border-foreground/15 text-foreground py-3.5 rounded-xl hover:bg-foreground/10 transition-colors"
        >
          <svg className="w-5 h-5" viewBox="0 0 24 24">
            <path d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z" fill="#4285F4"/>
            <path d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z" fill="#34A853"/>
            <path d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z" fill="#FBBC05"/>
            <path d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z" fill="#EA4335"/>
          </svg>
          <span className="font-medium tracking-wide">Google</span>
        </button>
      </motion.div>
    </main>
  );
}
