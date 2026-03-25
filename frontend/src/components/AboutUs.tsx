"use client";

import React from "react";
import { motion } from "framer-motion";
import { Target, Zap, Shield } from "lucide-react";

export default function AboutUs() {
  const pillars = [
    {
      icon: <Zap className="w-8 h-8 mb-4 text-[hsl(220,70%,78%)]" />,
      title: "Intelligence Layer",
      description:
        "Continuously ingest and process vast amounts of market data. We instantly transform raw competitor signals into structured, readable intelligence.",
    },
    {
      icon: <Target className="w-8 h-8 mb-4 text-[hsl(40,80%,82%)]" />,
      title: "Decision Layer",
      description:
        "Bridge the gap between data and action. Our decision engine recommends strategic prioritizations and experimental pathways for maximum impact.",
    },
    {
      icon: <Shield className="w-8 h-8 mb-4 text-foreground/80" />,
      title: "Trust Layer",
      description:
        "Operate with absolute certainty. We provide comprehensive risk assessments and full traceability to ensure every strategic move is securely vetted.",
    },
  ];

  return (
    <section id="about-us" className="relative w-full bg-background text-foreground py-24 md:py-32 px-6 md:px-10 overflow-hidden">
      {/* Background Accent */}
      <div className="absolute top-0 right-0 w-[50vw] h-[50vw] bg-[hsl(220,70%,78%)] opacity-5 blur-[120px] rounded-full pointer-events-none" />

      <div className="max-w-7xl mx-auto flex flex-col items-center">
        <motion.div
          initial={{ opacity: 0, y: 30 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true, margin: "-100px" }}
          transition={{ duration: 0.8 }}
          className="text-center mb-16 md:mb-24 max-w-3xl"
        >
          <h2 className="text-[clamp(1.5rem,4vw,3rem)] font-light tracking-[-0.02em] mb-6">
            Pioneering the future of <br />
            <span className="font-display">market intelligence</span>
          </h2>
          <p className="text-foreground/70 text-lg md:text-xl leading-relaxed">
            CompeteSmart is a next-generation integrated Market Intelligence System. 
            By seamlessly combining distinct Intelligence, Decision, and Trust layers 
            into a single continuous pipeline, we empower organizations to confidently 
            navigate risks, execute data-backed experiments, and maintain an uncompromising 
            competitive edge.
          </p>
        </motion.div>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-10 md:gap-16 w-full">
          {pillars.map((pillar, idx) => (
            <motion.div
              key={idx}
              initial={{ opacity: 0, y: 30 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true, margin: "-100px" }}
              transition={{ duration: 0.8, delay: idx * 0.2 }}
              className="flex flex-col items-start p-8 rounded-2xl border border-foreground/10 bg-foreground/[0.02] hover:bg-foreground/[0.04] transition-colors"
            >
              {pillar.icon}
              <h3 className="text-xl font-medium tracking-wide mb-3">
                {pillar.title}
              </h3>
              <p className="text-foreground/60 leading-relaxed text-sm">
                {pillar.description}
              </p>
            </motion.div>
          ))}
        </div>
      </div>
    </section>
  );
}
