"use client";

import React from "react";
import { Mail, ArrowUpRight } from "lucide-react";
import { motion } from "framer-motion";

export default function Footer() {
  const currentYear = new Date().getFullYear();

  const footerLinks = [
    {
      title: "Platform",
      links: [
        { name: "Intelligence Layer", href: "#" },
        { name: "Decision Engine", href: "#" },
        { name: "Strategic Experiments", href: "#" },
        { name: "Risk Assessment", href: "#" },
      ],
    },
    {
      title: "Company",
      links: [
        { name: "About Us", href: "#about-us" },
        { name: "Our Methodology", href: "#" },
        { name: "Privacy Protocol", href: "#" },
        { name: "Contact", href: "#" },
      ],
    },
    {
      title: "Resources",
      links: [
        { name: "Case Studies", href: "#" },
        { name: "Insight Archive", href: "#" },
        { name: "API Documentation", href: "#" },
        { name: "System Status", href: "#" },
      ],
    },
  ];

  return (
    <footer className="relative w-full bg-[#050505] pt-24 pb-12 px-6 md:px-10 overflow-hidden border-t border-white/5">
      {/* Background Accent */}
      <div className="absolute bottom-0 left-1/2 -translate-x-1/2 w-[60vw] h-[60vw] bg-[hsl(220,70%,78%)] opacity-[0.02] blur-[120px] rounded-full pointer-events-none" />

      <div className="max-w-7xl mx-auto relative z-10">
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-5 gap-12 lg:gap-8 mb-20">
          
          {/* Logo & Vision Block */}
          <div className="lg:col-span-2 flex flex-col items-start max-w-sm">
            <span className="font-bungee tracking-wider text-white drop-shadow-[0_2px_10px_rgba(0,0,0,0.5)] flex items-baseline select-none mb-6">
              <span className="text-2xl md:text-3xl">C</span>
              <span className="text-lg md:text-xl">OMPETE</span>
              <span className="text-2xl md:text-3xl">S</span>
              <span className="text-lg md:text-xl">MART</span>
            </span>
            <p className="text-foreground/40 text-sm leading-relaxed mb-8">
              Pioneering autonomous market intelligence by integrating heavy-data ingestion
              with AI-driven decision layers. CompeteSmart transforms reactive monitoring
              into proactive strategic dominance.
            </p>
          </div>

          {/* Nav Sections */}
          {footerLinks.map((section, idx) => (
            <div key={idx} className="flex flex-col items-start">
              <h4 className="text-[10px] font-bold uppercase tracking-[0.2em] text-white/40 mb-6">
                {section.title}
              </h4>
              <ul className="space-y-4">
                {section.links.map((link, lIdx) => (
                  <li key={lIdx}>
                    <a 
                      href={link.href} 
                      className="group flex items-center gap-2 text-sm text-foreground/40 hover:text-white transition-colors"
                    >
                      {link.name}
                      <ArrowUpRight className="w-3 h-3 opacity-0 group-hover:opacity-100 -translate-y-1 translate-x-1 group-hover:translate-x-0 group-hover:translate-y-0 transition-all duration-300" />
                    </a>
                  </li>
                ))}
              </ul>
            </div>
          ))}
        </div>

        {/* Bottom Bar */}
        <div className="pt-8 border-t border-white/5 flex flex-col md:flex-row justify-between items-center gap-6">
          <div className="flex items-center gap-2">
            <div className="w-1.5 h-1.5 bg-emerald-500 rounded-full animate-pulse" />
            <span className="text-[10px] font-bold uppercase tracking-[0.2em] text-emerald-500/60">
              System Live: Status Nominal
            </span>
          </div>
          <div className="flex flex-col md:flex-row items-center gap-4 md:gap-8 order-last md:order-none">
            <span className="text-[10px] uppercase tracking-[0.2em] text-foreground/20">
              © {currentYear} CompeteSmart Protocol
            </span>
            <div className="flex items-center gap-6">
              <a href="#" className="text-[10px] uppercase tracking-[0.2em] text-foreground/20 hover:text-white transition-colors">Terms</a>
              <a href="#" className="text-[10px] uppercase tracking-[0.2em] text-foreground/20 hover:text-white transition-colors">Privacy</a>
              <a href="#" className="text-[10px] uppercase tracking-[0.2em] text-foreground/20 hover:text-white transition-colors">Legal</a>
            </div>
          </div>
          <div className="flex items-center gap-2 text-foreground/20 hover:text-white/40 transition-colors cursor-pointer group">
            <span className="text-[10px] uppercase tracking-[0.2em] font-bold">Contact Intelligence</span>
            <Mail className="w-3 h-3 group-hover:scale-110 transition-transform" />
          </div>
        </div>
      </div>
    </footer>
  );
}
