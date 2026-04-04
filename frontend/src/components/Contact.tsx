"use client";

import React from "react";
import { motion } from "framer-motion";
import { Mail, MessageCircle, Send, MapPin, Phone } from "lucide-react";

export default function Contact() {
  return (
    <section id="contact" className="relative w-full bg-background py-24 md:py-32 px-6 md:px-10 overflow-hidden">
      {/* Background Accents */}
      <div className="absolute top-1/2 left-0 w-[40vw] h-[40vw] bg-[hsl(40,80%,82%)] opacity-[0.03] blur-[100px] rounded-full pointer-events-none -translate-y-1/2" />
      <div className="absolute bottom-0 right-0 w-[30vw] h-[30vw] bg-[hsl(220,70%,78%)] opacity-[0.03] blur-[100px] rounded-full pointer-events-none translate-y-1/2" />

      <div className="max-w-7xl mx-auto">
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-16 lg:gap-24 items-start">
          
          {/* Left Column: Heading & Info */}
          <motion.div
            initial={{ opacity: 0, x: -30 }}
            whileInView={{ opacity: 1, x: 0 }}
            viewport={{ once: true, margin: "-100px" }}
            transition={{ duration: 0.8 }}
          >
            <h2 className="text-[clamp(2.5rem,5vw,4.5rem)] font-light tracking-[-0.04em] leading-[1.1] mb-8">
              Let's build the <br />
              <span className="font-display">intelligent future</span>
            </h2>
            <p className="text-foreground/60 text-lg md:text-xl leading-relaxed max-w-md mb-12">
              Ready to redefine your market strategy? Reach out to our 
              intelligence team to integrate CompeteSmart into your pipeline.
            </p>

            <div className="space-y-8">
              <div className="flex items-center gap-6 group">
                <div className="w-12 h-12 rounded-full border border-foreground/10 bg-foreground/[0.02] flex items-center justify-center text-foreground/40 group-hover:text-foreground group-hover:border-foreground/30 transition-all duration-300">
                  <Mail className="w-5 h-5" />
                </div>
                <div>
                  <h4 className="text-[10px] uppercase tracking-[0.2em] text-foreground/40 mb-1">Email Us</h4>
                  <p className="text-foreground/80 font-medium tracking-wide">contact@competesmart.ai</p>
                </div>
              </div>

              <div className="flex items-center gap-6 group">
                <div className="w-12 h-12 rounded-full border border-foreground/10 bg-foreground/[0.02] flex items-center justify-center text-foreground/40 group-hover:text-foreground group-hover:border-foreground/30 transition-all duration-300">
                  <MapPin className="w-5 h-5" />
                </div>
                <div>
                  <h4 className="text-[10px] uppercase tracking-[0.2em] text-foreground/40 mb-1">Headquarters</h4>
                  <p className="text-foreground/80 font-medium tracking-wide">San Francisco, CA</p>
                </div>
              </div>
            </div>
          </motion.div>

          {/* Right Column: Contact Form */}
          <motion.div
            initial={{ opacity: 0, y: 30 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true, margin: "-100px" }}
            transition={{ duration: 0.8, delay: 0.2 }}
            className="p-8 md:p-12 rounded-[2.5rem] border border-foreground/10 bg-foreground/[0.01] backdrop-blur-xl shadow-2xl relative"
          >
            {/* Form Background Pattern */}
            <div className="absolute inset-0 opacity-[0.02] pointer-events-none overflow-hidden rounded-[2.5rem]">
              <div className="absolute top-0 right-0 w-full h-full bg-[radial-gradient(circle_at_100%_0%,hsl(var(--foreground)/0.2),transparent_70%)]" />
            </div>

            <form className="space-y-8 relative z-10" onSubmit={(e) => e.preventDefault()}>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
                <div className="space-y-2">
                  <label className="text-[10px] uppercase tracking-[0.2em] text-foreground/40 ml-1">Full Name</label>
                  <input 
                    type="text" 
                    placeholder="John Doe"
                    className="w-full bg-foreground/[0.03] border border-foreground/10 rounded-2xl px-6 py-4 text-foreground placeholder:text-foreground/20 focus:outline-none focus:ring-1 focus:ring-foreground/20 focus:border-foreground/20 transition-all"
                  />
                </div>
                <div className="space-y-2">
                  <label className="text-[10px] uppercase tracking-[0.2em] text-foreground/40 ml-1">Work Email</label>
                  <input 
                    type="email" 
                    placeholder="john@company.com"
                    className="w-full bg-foreground/[0.03] border border-foreground/10 rounded-2xl px-6 py-4 text-foreground placeholder:text-foreground/20 focus:outline-none focus:ring-1 focus:ring-foreground/20 focus:border-foreground/20 transition-all"
                  />
                </div>
              </div>

              <div className="space-y-2">
                <label className="text-[10px] uppercase tracking-[0.2em] text-foreground/40 ml-1">Message</label>
                <textarea 
                  rows={4}
                  placeholder="How can we help your brand grow?"
                  className="w-full bg-foreground/[0.03] border border-foreground/10 rounded-2xl px-6 py-4 text-foreground placeholder:text-foreground/20 focus:outline-none focus:ring-1 focus:ring-foreground/20 focus:border-foreground/20 transition-all resize-none"
                />
              </div>

              <button 
                type="submit"
                className="w-full group relative overflow-hidden rounded-2xl bg-foreground text-background font-bold py-5 px-8 transition-transform active:scale-95 shadow-xl"
              >
                <span className="relative z-10 flex items-center justify-center gap-3 tracking-widest uppercase text-sm">
                  Initialize Transmission
                  <Send className="w-4 h-4 group-hover:translate-x-1 group-hover:-translate-y-1 transition-transform" />
                </span>
                <div className="absolute inset-0 bg-gradient-to-r from-[hsl(220,70%,78%)] to-[hsl(40,80%,82%)] opacity-0 group-hover:opacity-100 transition-opacity" />
              </button>
            </form>
          </motion.div>

        </div>
      </div>
    </section>
  );
}
