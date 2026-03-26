# CompeteSmart

**CompeteSmart** is a cutting-edge market intelligence and strategic simulation platform. It empowers businesses to monitor competitive landscapes, analyze market trends, and simulate strategic pivots before real-world execution.

---

## 🚀 Key Features

### 1. Market Intelligence Dashboard
- **Dynamic Trends:** Real-time visualization of market category trajectories.
- **Competitor Analysis:** Deep-dive into competitor strengths, positioning, and whitespace gaps.
- **Live KPIs:** Monitor "Signal Resonance" and "Persona Drift" to capture shifting consumer sentiment.

### 2. Strategic Experiment Builder
- **Simulation Engine:** Apply hypothetical strategies (e.g., messaging pivots, pricing changes) and project their impact over time.
- **Outcome Projection:** AI-driven success/failure verdicts based on historical data and market saturation models.
- **Experiment History:** A Google Drive-style gallery to store, retrieve, and analyze past simulation results with high-fidelity charts.

### 3. AI Execution Copilot
- **Context-Aware Chat:** An integrated AI assistant that understands your market data.
- **Strategic Advice:** Get instantly generated suggestions for your next market move.
- **Markdown Support:** Clean, structured responses with actionable bullet points and bold highlights.

---

## 🛠️ Tech Stack

### Frontend (Next.js)
- **Framework:** Next.js 15+ (App Router)
- **Styling:** Vanilla CSS & Tailwind CSS
- **Animations:** Framer Motion (premium micro-interactions)
- **Visualizations:** Recharts (high-performance SVG charts)
- **Icons:** Lucide React

### Backend (FastAPI)
- **Language:** Python 3.10+
- **API Framework:** FastAPI (high performance)
- **Database:** PostgreSQL with `pgvector` (for semantic intelligence)
- **AI/ML:** OpenAI & Google Generative AI (Gemini)
- **Scraping:** BeautifulSoup (bs4) for real-time market data extraction
- **Pipeline:** Custom modular architecture with Intelligence, Decision, and Trust layers.

---

## 📦 Installation & Setup

### Prerequisites
- Node.js 18+
- Python 3.10+
- PostgreSQL (with `pgvector` extension)

### 1. Clone the Repository
```bash
git clone https://github.com/shruthi/CompeteSmart.git
cd CompeteSmart
```

### 2. Backend Setup
```bash
cd backend
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
```
Create a `.env` file in the `backend` directory with your API keys:
```env
OPENAI_API_KEY=your_key
GEMINI_API_KEY=your_key
DATABASE_URL=postgresql://user:pass@localhost/db
```
Start the backend server:
```bash
uvicorn api:app --reload
```

### 3. Frontend Setup
```bash
cd ../frontend
npm install
```
Create a `.env` file in the `frontend` directory:
```env
NEXT_PUBLIC_API_URL=http://localhost:8000
```
Start the development server:
```bash
npm run dev
```

---

## 📂 Project Structure

```text
CompeteSmart/
├── frontend/                # Next.js Application
│   ├── src/app/             # App Router pages (Dashboard, Builder)
│   ├── src/components/      # UI components (Simulation, Copilot, Charts)
│   └── src/utils/           # API helpers & Mock data
├── backend/                 # FastAPI Service
│   ├── src/intelligence/    # Market analysis logic
│   ├── src/auth/            # Token-based authentication
│   ├── api.py               # Main API routes
│   └── decision_layer.py    # Strategic AI logic
└── README.md
```

---

## 📄 License
Internal use only. Copyright © 2026 CompeteSmart Team.