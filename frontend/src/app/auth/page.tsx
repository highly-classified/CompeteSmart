"use client";

import React, { useState } from "react";
import { motion } from "framer-motion";
import { ArrowLeft } from "lucide-react";
import Link from "next/link";
import { useRouter } from "next/navigation";

export default function AuthPage() {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const router = useRouter();

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();

    if (email === "admin@test.com" && password === "password") {
      localStorage.setItem("token", "dummy_token");
      router.push("/dashboard");
    } else {
      alert("Invalid test credentials. Please use admin@test.com / password");
    }
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
            Test Admin Login
          </p>
        </div>

        <form onSubmit={handleSubmit} className="flex flex-col gap-4">
          <div className="flex flex-col gap-1.5">
            <label className="text-xs font-semibold uppercase tracking-widest text-foreground/70 pl-2">Email Address</label>
            <input
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              className="w-full bg-background/60 border border-foreground/15 rounded-xl px-4 py-3.5 text-foreground focus:outline-none focus:border-foreground/40 focus:ring-1 focus:ring-foreground/20 transition-all"
              placeholder="admin@test.com"
              required
            />
          </div>

          <div className="flex flex-col gap-1.5 mb-2 mt-1">
            <label className="text-xs font-semibold uppercase tracking-widest text-foreground/70 pl-2 flex justify-between">
              Password
            </label>
            <input
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              className="w-full bg-background/60 border border-foreground/15 rounded-xl px-4 py-3.5 text-foreground focus:outline-none focus:border-foreground/40 focus:ring-1 focus:ring-foreground/20 transition-all font-mono tracking-widest text-lg"
              placeholder="password"
              required
            />
          </div>

          <button
            type="submit"
            className="w-full bg-foreground text-background font-semibold tracking-wide py-3.5 rounded-xl hover:opacity-90 hover:scale-[1.01] active:scale-[0.98] transition-all mt-3"
          >
            Log In Securely
          </button>
        </form>
      </motion.div>
    </main>
  );
}
