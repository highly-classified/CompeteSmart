import Hero from "@/components/Hero";
import AboutUs from "@/components/AboutUs";
import Contact from "@/components/Contact";
import Footer from "@/components/Footer";

export default function Home() {
  return (
    <main className="min-h-screen bg-background w-full selection:bg-violet-500/30">
      <Hero />
      <AboutUs />
      <Contact />
      <Footer />
    </main>
  );
}
