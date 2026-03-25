"use client";

import React, { useState, useEffect } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { ArrowRight, X } from "lucide-react";
import Link from "next/link";

export default function Hero() {
  const [menuOpen, setMenuOpen] = useState(false);
  const [progress, setProgress] = useState(0);

  // Scroll lock when menu is open
  useEffect(() => {
    if (menuOpen) {
      document.body.style.overflow = "hidden";
    } else {
      document.body.style.overflow = "";
    }
    return () => {
      document.body.style.overflow = "";
    };
  }, [menuOpen]);

  // SVG Progress animation after mount
  useEffect(() => {
    const timer = setTimeout(() => {
      setProgress(75);
    }, 500);
    return () => clearTimeout(timer);
  }, []);

  const menuLinks = [
    { title: "Home", href: "#" },
    { title: "About Us", href: "#about-us" },
    { title: "Projects", href: "#" },
    { title: "Contact", href: "#" },
  ];

  const featureItems = [
    "Real-Time Tracking",
    "AI-Driven Insights",
    "Trend Analysis",
    "Strategic Prioritization",
    "Risk Assessment",
    "Actionable Intel",
    "Data Integration",
  ];
  // Duplicated twice for seamless loop
  const marqueeItems = [...featureItems, ...featureItems, ...featureItems];

  return (
    <div className="relative w-full h-screen min-h-screen overflow-hidden flex flex-col font-sans">
      {/* Video Background */}
      <video
        autoPlay
        muted
        loop
        playsInline
        className="absolute inset-0 w-full h-full object-cover object-[37%_center] z-0"
      >
        <source
          src="https://ik.imagekit.io/5tp4o5nk1m/8188999-uhd_3840_2160_25fps.mp4"
          type="video/mp4"
        />
      </video>

      {/* Navigation Bar */}
      <nav className="fixed top-0 left-0 z-[60] w-full flex items-center justify-between px-6 py-4 md:px-10 bg-black/30 backdrop-blur-md border-b border-white/10 transition-all duration-300">
        <button
          onClick={() => setMenuOpen(true)}
          className="flex items-center gap-3 px-5 py-2.5 rounded-full border border-white/20 hover:bg-white/10 transition-colors uppercase tracking-widest text-xs font-medium text-white shadow-xl"
        >
          Menu
          <div className="flex flex-col gap-[4px]">
            <span className="w-7 h-[2px] bg-white block" />
            <span className="w-7 h-[2px] bg-white block" />
          </div>
        </button>

        <div className="absolute left-1/2 -translate-x-1/2 hidden sm:block md:static md:translate-x-0 lg:absolute lg:left-1/2 lg:-translate-x-1/2">
          <span className="font-bungee tracking-wider text-white drop-shadow-[0_2px_10px_rgba(0,0,0,0.5)] flex items-baseline select-none">
            <span className="text-3xl md:text-5xl">C</span>
            <span className="text-xl md:text-3xl">OMPETE</span>
            <span className="text-3xl md:text-5xl">S</span>
            <span className="text-xl md:text-3xl">MART</span>
          </span>
        </div>

        <div className="hidden md:flex items-center gap-3">
          <a href="#about-us" className="px-6 py-2.5 rounded-full border border-white/30 hover:bg-white/10 transition-colors text-sm text-white font-medium">
            About Us
          </a>
          <Link href="/auth" className="px-6 py-2.5 rounded-full bg-gradient-to-r from-[hsl(220,70%,78%)] to-[hsl(40,80%,82%)] text-black uppercase tracking-wide text-sm font-bold hover:scale-105 transition-transform text-center flex items-center shadow-lg">
            Get Started
          </Link>
        </div>
      </nav>

      {/* Main Content Area */}
      <main className="relative z-10 flex-1 flex flex-col justify-start pt-6 px-6 pb-2 md:justify-end md:pt-0 md:px-10 md:pb-16 w-full">
        <div className="flex items-center gap-2 mb-6">
          <ArrowRight className="w-4 h-4 text-foreground" />
          <span className="text-xs font-medium tracking-[0.25em] uppercase text-foreground">
            CompeteSmart
          </span>
        </div>

        <div className="flex flex-col lg:flex-row lg:items-end justify-between w-full h-full lg:h-auto gap-8">
          {/* Heading */}
          <div className="flex-1">
            <h1 className="flex flex-col text-[clamp(2rem,6vw,5rem)] leading-[0.9] tracking-[-0.02em]">
              <span className="font-light">Mastering the</span>
              <span className="font-light">art of market</span>
              <span className="font-display">intelligence</span>
            </h1>
          </div>

          {/* Stats/Progress Circle */}
          <div className="mt-8 md:mt-0 lg:max-w-xs flex flex-col items-start lg:items-start lg:text-left lg:pb-4">
            <div className="relative w-[120px] h-[120px] mb-4">
              <svg
                className="w-full h-full transform -rotate-90"
                viewBox="0 0 120 120"
              >
                <circle
                  cx="60"
                  cy="60"
                  r="54"
                  fill="none"
                  stroke="hsl(var(--foreground) / 0.15)"
                  strokeWidth="3"
                />
                <circle
                  cx="60"
                  cy="60"
                  r="54"
                  fill="none"
                  stroke="hsl(var(--foreground))"
                  strokeWidth="3"
                  strokeLinecap="round"
                  strokeDasharray={2 * Math.PI * 54}
                  strokeDashoffset={2 * Math.PI * 54 * (1 - progress / 100)}
                  className="transition-all duration-1000 ease-out"
                />
              </svg>
              <div className="absolute inset-0 flex items-center justify-center">
                <span className="text-foreground text-lg font-medium">75%</span>
              </div>
            </div>
            <p className="text-foreground/70 text-sm leading-relaxed">
              Guiding organizations toward lasting competitive advantage
              through actionable intelligence and data-driven decisions.
            </p>
          </div>
        </div>
      </main>

      {/* Platform Features Marquee Bar */}
      <div className="relative z-10 w-full mt-auto mb-0 md:mb-6 px-6 md:px-10 pb-6 md:pb-0">
        <div className="flex justify-between items-center mb-4">
          <span className="text-xs font-medium tracking-[0.2em] uppercase text-foreground">
            Core Features
          </span>
          <span className="hidden md:block text-xs font-medium tracking-[0.2em] uppercase text-foreground">
            Empowering Strategic Decisions
          </span>
        </div>
        <div className="border-t border-foreground/10 overflow-hidden py-5 flex">
          <div className="flex whitespace-nowrap animate-marquee gap-16 pr-16">
            {marqueeItems.map((brand, idx) => (
              <span
                key={idx}
                className="text-foreground/50 text-lg font-medium tracking-wide"
              >
                {brand}
              </span>
            ))}
          </div>
        </div>
      </div>

      {/* Full-Screen Menu Overlay */}
      <AnimatePresence>
        {menuOpen && (
          <motion.div
            initial={{ clipPath: "circle(0% at 80px 40px)" }}
            animate={{ clipPath: "circle(150% at 80px 40px)" }}
            exit={{ clipPath: "circle(0% at 80px 40px)" }}
            transition={{ duration: 0.7, ease: [0.76, 0, 0.24, 1] }}
            className="fixed inset-0 z-50 bg-foreground flex flex-col"
          >
            {/* Overlay Header */}
            <div className="flex items-center justify-between px-6 py-6 md:px-10">
              <button
                onClick={() => setMenuOpen(false)}
                className="flex items-center gap-3 px-5 py-2.5 rounded-full border border-background/30 hover:bg-background/10 transition-colors uppercase tracking-widest text-xs font-medium text-background"
              >
                Close
                <X className="w-5 h-5 text-background" />
              </button>

              <div className="absolute left-1/2 -translate-x-1/2 hidden sm:block md:static md:translate-x-0 lg:absolute lg:left-1/2 lg:-translate-x-1/2">
                <span className="font-bungee tracking-wider text-background drop-shadow-md flex items-baseline">
                  <span className="text-3xl md:text-5xl">C</span>
                  <span className="text-xl md:text-3xl">OMPETE</span>
                  <span className="text-3xl md:text-5xl">S</span>
                  <span className="text-xl md:text-3xl">MART</span>
                </span>
              </div>
              <div className="w-[100px]" /* Spacer */></div>
            </div>

            {/* Overlay Links */}
            <div className="flex-1 flex flex-col justify-center px-6 md:px-20 lg:px-40">
              {menuLinks.map((link, i) => (
                <motion.a
                  key={link.title}
                  href={link.href}
                  onClick={() => setMenuOpen(false)}
                  initial={{ opacity: 0, x: -60 }}
                  animate={{ opacity: 1, x: 0 }}
                  transition={{
                    delay: 0.15 + i * 0.08,
                    ease: [0.25, 1, 0.5, 1],
                  }}
                  className="group flex items-center justify-between py-6 md:py-8 border-b border-background/10 text-background hover:text-background/80 transition-colors"
                >
                  <span className="text-[clamp(2rem,5vw,4.5rem)] font-light tracking-[-0.06em] group-hover:translate-x-1 transition-transform duration-300">
                    {link.title}
                  </span>
                  <ArrowRight className="w-8 h-8 md:w-12 md:h-12 opacity-0 group-hover:opacity-100 group-hover:translate-x-2 transition-all duration-300" />
                </motion.a>
              ))}
            </div>

            {/* Overlay Footer */}
            <div className="flex items-center justify-between px-6 py-8 md:px-10">
              <span className="text-background/40 text-[10px] md:text-xs tracking-[0.2em] uppercase">
                CompeteSmart
              </span>
              <span className="text-background/40 text-[10px] md:text-xs tracking-[0.2em] uppercase">
                © 2026
              </span>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}
