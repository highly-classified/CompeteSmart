import { Sparkles, Download, Wand2, BookOpen, ArrowRight, Menu, Flower2 } from 'lucide-react';

const Twitter = ({ size = 24, ...props }: React.SVGProps<SVGSVGElement> & { size?: number | string }) => (
  <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" {...props}><path d="M22 4s-.7 2.1-2 3.4c1.6 10-9.4 17.3-18 11.6 2.2.1 4.4-.6 6-2C3 15.5.5 9.6 3 5c2.2 2.6 5.6 4.1 9 4-.9-4.2 4-6.6 7-3.8 1.1 0 3-1.2 3-1.2z"/></svg>
);
const Linkedin = ({ size = 24, ...props }: React.SVGProps<SVGSVGElement> & { size?: number | string }) => (
  <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" {...props}><path d="M16 8a6 6 0 0 1 6 6v7h-4v-7a2 2 0 0 0-2-2 2 2 0 0 0-2 2v7h-4v-7a6 6 0 0 1 6-6z"/><rect x="2" y="9" width="4" height="12"/><circle cx="4" cy="4" r="2"/></svg>
);
const Instagram = ({ size = 24, ...props }: React.SVGProps<SVGSVGElement> & { size?: number | string }) => (
  <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" {...props}><rect x="2" y="2" width="20" height="20" rx="5" ry="5"/><path d="M16 11.37A4 4 0 1 1 12.63 8 4 4 0 0 1 16 11.37z"/><line x1="17.5" y1="6.5" x2="17.51" y2="6.5"/></svg>
);

export default function Home() {
  return (
    <main className="relative min-h-screen w-full overflow-hidden text-white bg-black">
      {/* Background Video */}
      <video
        autoPlay
        loop
        muted
        playsInline
        className="absolute inset-0 w-full h-full object-cover z-0 opacity-90"
      >
        <source src="https://d8j0ntlcm91z4.cloudfront.net/user_38xzZboKViGWJOttwIXH07lWA1P/hf_20260315_073750_51473149-4350-4920-ae24-c8214286f323.mp4" type="video/mp4" />
      </video>

      {/* Main Content Container */}
      <div className="relative z-10 flex flex-col lg:flex-row min-h-screen w-full p-4 lg:p-6 gap-6">
        
        {/* LEFT PANEL */}
        <section className="relative w-full lg:w-[52%] min-h-[calc(100vh-2rem)] lg:min-h-[calc(100vh-3rem)] rounded-3xl flex flex-col p-8 lg:p-12 transition-all liquid-glass-strong">
          
          {/* Nav */}
          <nav className="flex items-center justify-between w-full">
            <div className="flex items-center gap-3">
              <div className="w-8 h-8 rounded-full bg-white/10 flex items-center justify-center shrink-0">
                <Flower2 size={16} className="text-white" />
              </div>
              <span className="font-semibold text-2xl tracking-tighter text-white">bloom</span>
            </div>
            
            <button className="flex items-center justify-between gap-3 pl-4 pr-1.5 py-1.5 rounded-full liquid-glass hover:scale-105 transition-transform active:scale-95 text-sm">
              <span className="font-medium">Menu</span>
              <div className="w-7 h-7 rounded-full bg-white/10 flex items-center justify-center shrink-0">
                <Menu size={14} className="text-white" />
              </div>
            </button>
          </nav>

          {/* Hero Center */}
          <div className="flex-1 flex flex-col items-center justify-center text-center max-w-2xl mx-auto w-full mt-12 mb-12">
            <div className="w-20 h-20 rounded-full liquid-glass flex items-center justify-center mb-8 shrink-0">
              <Flower2 size={36} className="text-white/80" />
            </div>
            
            <h1 className="text-6xl lg:text-7xl tracking-[-0.05em] text-white font-medium mb-10 leading-[1.1]">
              Innovating the <em className="font-serif italic text-white/80 font-normal">spirit</em> of bloom AI
            </h1>
            
            <button className="flex items-center justify-between gap-4 pl-6 pr-2 py-2 rounded-full liquid-glass-strong hover:scale-105 transition-transform active:scale-95 text-white mb-16">
              <span className="text-lg font-medium">Explore Now</span>
              <div className="w-10 h-10 rounded-full bg-white/15 flex items-center justify-center shrink-0">
                <Download size={18} />
              </div>
            </button>
            
            {/* Pills */}
            <div className="flex flex-wrap items-center justify-center gap-3">
              <div className="px-5 py-2.5 rounded-full liquid-glass text-xs text-white/80 hover:scale-105 transition-transform cursor-default">
                Artistic Gallery
              </div>
              <div className="px-5 py-2.5 rounded-full liquid-glass text-xs text-white/80 hover:scale-105 transition-transform cursor-default">
                AI Generation
              </div>
              <div className="px-5 py-2.5 rounded-full liquid-glass text-xs text-white/80 hover:scale-105 transition-transform cursor-default">
                3D Structures
              </div>
            </div>
          </div>

          {/* Bottom Quote */}
          <div className="w-full flex flex-col items-center text-center mt-auto">
            <span className="text-[10px] tracking-[0.3em] uppercase text-white/50 mb-4 font-medium">Visionary Design</span>
            <p className="text-xl lg:text-2xl text-white/90 mb-6 font-medium">
              "We imagined a <span className="font-serif italic font-normal text-white">realm</span> with no <span className="font-serif italic font-normal text-white/70">ending</span>."
            </p>
            <div className="flex items-center gap-6 text-white/50 text-[10px] tracking-[0.2em] uppercase">
              <div className="w-12 h-px bg-white/30" />
              <span>Marcus Aurelio</span>
              <div className="w-12 h-px bg-white/30" />
            </div>
          </div>
        </section>

        {/* RIGHT PANEL (Desktop Only) */}
        <section className="hidden lg:flex flex-col w-[48%] h-[calc(100vh-3rem)] relative">
          
          {/* Top Bar */}
          <div className="flex items-center justify-between w-full mb-8 pr-2">
            {/* Social Icons */}
            <div className="flex items-center gap-1 p-1.5 rounded-full liquid-glass">
              <a href="#" className="w-10 h-10 rounded-full hover:bg-white/10 flex items-center justify-center text-white transition-colors">
                <Twitter size={18} fill="currentColor" className="opacity-90 hover:opacity-100" />
              </a>
              <a href="#" className="w-10 h-10 rounded-full hover:bg-white/10 flex items-center justify-center text-white transition-colors">
                <Linkedin size={18} fill="currentColor" className="opacity-90 hover:opacity-100" />
              </a>
              <a href="#" className="w-10 h-10 rounded-full hover:bg-white/10 flex items-center justify-center text-white transition-colors">
                <Instagram size={18} className="opacity-90 hover:opacity-100" />
              </a>
              <div className="w-10 h-10 rounded-full bg-white/10 flex items-center justify-center shrink-0 ml-2">
                <ArrowRight size={18} />
              </div>
            </div>
            
            {/* Account Button */}
            <button className="w-14 h-14 rounded-full liquid-glass hover:scale-105 transition-transform active:scale-95 flex items-center justify-center">
              <Sparkles size={22} className="text-white" />
            </button>
          </div>
          
          {/* Community Card */}
          <div className="w-64 p-6 rounded-3xl liquid-glass self-end hover:scale-105 transition-transform cursor-pointer mb-8">
            <h3 className="text-lg font-medium text-white mb-2 leading-tight">Enter our<br/><em className="font-serif italic font-normal text-white/80">ecosystem</em></h3>
            <p className="text-xs text-white/60 leading-relaxed font-light">Join thousands of creators shaping the future of digital botanical design.</p>
          </div>
          
          {/* Bottom Features Section */}
          <div className="mt-auto w-full p-6 rounded-[2.5rem] liquid-glass flex flex-col gap-6">
            
            {/* Two side-by-side cards */}
            <div className="flex gap-6 h-40">
              <div className="flex-1 p-6 rounded-[2rem] liquid-glass hover:scale-105 transition-transform cursor-pointer group flex flex-col justify-between">
                <div className="w-12 h-12 rounded-full bg-white/10 flex items-center justify-center">
                  <Wand2 size={24} className="text-white/80 group-hover:text-white transition-colors" />
                </div>
                <div>
                  <h4 className="font-medium text-white text-lg">Processing</h4>
                  <p className="text-sm text-white/60 mt-1 font-light">Real-time rendering</p>
                </div>
              </div>
              
              <div className="flex-1 p-6 rounded-[2rem] liquid-glass hover:scale-105 transition-transform cursor-pointer group flex flex-col justify-between">
                <div className="w-12 h-12 rounded-full bg-white/10 flex items-center justify-center">
                  <BookOpen size={24} className="text-white/80 group-hover:text-white transition-colors" />
                </div>
                <div>
                  <h4 className="font-medium text-white text-lg">Growth Archive</h4>
                  <p className="text-sm text-white/60 mt-1 font-light">Saved structures</p>
                </div>
              </div>
            </div>
            
            {/* Bottom Card */}
            <div className="w-full p-4 rounded-[2rem] liquid-glass flex items-center gap-5 hover:scale-105 transition-transform cursor-pointer">
              <div className="w-24 h-16 rounded-xl bg-white/10 shrink-0 overflow-hidden relative flex items-center justify-center text-[10px] text-white/50">
                <Flower2 size={24} className="opacity-50" />
              </div>
              <div className="flex-1 pr-4">
                <h4 className="font-medium text-white text-base">Advanced Plant Sculpting</h4>
                <p className="text-xs text-white/60 mt-1.5 font-light leading-relaxed">Explore the latest techniques in AI-driven floral generation.</p>
              </div>
              <button className="w-12 h-12 mr-2 rounded-full bg-white/10 flex items-center justify-center shrink-0 hover:bg-white/20 transition-colors">
                <span className="text-2xl font-light mt-[-2px]">+</span>
              </button>
            </div>
            
          </div>
        </section>
      </div>
    </main>
  );
}
