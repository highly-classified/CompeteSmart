import { SimulationOrchestrator } from "@/components/simulation/SimulationOrchestrator";

// This isolates the experimental builder routing to exactly where you requested.
// You can seamlessly link to this page from anywhere in your main App dashboard using <Link href="/experiment-builder">.

export const metadata = {
    title: "Experiment Builder | CompeteSmart Engine",
    description: "Simulate and project strategic pivots against your competitors.",
};

export default function ExperimentBuilderPage() {
    return (
        <main className="bg-black/95 text-white min-h-screen overflow-x-hidden selection:bg-emerald-500/30 font-sans">
            <SimulationOrchestrator />
        </main>
    );
}
