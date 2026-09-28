<div align="center">

# 🎯 Career Platform

### AI-Powered Career Guidance for Students & Junior Professionals

[![FastAPI](https://img.shields.io/badge/FastAPI-0.111-009688?style=flat-square&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com)
[![React](https://img.shields.io/badge/React-19-61DAFB?style=flat-square&logo=react&logoColor=black)](https://react.dev)
[![Python](https://img.shields.io/badge/Python-3.11+-3776AB?style=flat-square&logo=python&logoColor=white)](https://python.org)
[![TypeScript](https://img.shields.io/badge/TypeScript-5.8-3178C6?style=flat-square&logo=typescript&logoColor=white)](https://typescriptlang.org)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-Supabase-4169E1?style=flat-square&logo=postgresql&logoColor=white)](https://supabase.com)
[![License](https://img.shields.io/badge/License-MIT-green?style=flat-square)](LICENSE)

**Career Platform** bridges the gap between student skills and job market expectations using a hybrid AI pipeline — RAG with ChromaDB, Google Gemini, and semantic NLP with spaCy.

[Features](#-features) · [Architecture](#-architecture) · [Quick Start](#-quick-start) · [API Reference](#-api-reference) · [Deployment](#-deployment)

</div>

---

## 📋 Table of Contents

- [Overview](#-overview)
- [Features](#-features)
- [Architecture](#-architecture)
- [Tech Stack](#-tech-stack)
- [Project Structure](#-project-structure)
- [Quick Start](#-quick-start)
- [Environment Variables](#-environment-variables)
- [API Reference](#-api-reference)
- [AI Modules](#-ai-modules)
- [Database Schema](#-database-schema)
- [Data Pipeline & Scraping](#-data-pipeline--scraping)
- [Deployment](#-deployment)
- [Running Tests](#-running-tests)
- [Contributing](#-contributing)

---

## 🌟 Overview

Career Platform solves three core problems faced by students entering the job market:

| Problem | Solution |
|---------|----------|
| "I don't know what skills I'm missing" | **Gap Analysis** — CV vs. job market or a specific offer |
| "My CV gets rejected before a human sees it" | **ATS Optimizer** — semantic scoring with spaCy NLP |
| "I have no way to practice real interviews" | **Interview Simulator** — Gemini-powered chatbot anchored to the actual job offer |

The platform also generates a **personalized weekly learning roadmap** using a hybrid RAG pipeline (ChromaDB + SentenceTransformers + Gemini AI), enriched with real market data scraped from multiple job sources.

---

## ✨ Features

### Core Modules

- **📄 CV Upload & Parsing** — Supports PDF (PyMuPDF) and DOCX (python-docx); extracted text is persisted for all downstream analyses
- **📊 Gap Analysis** — Two modes: *market* (seeded job skill requirements) or *specific offer* (paste any job description); produces an employability score (0–100) with per-skill breakdown (`missing` / `partial` / `acquired`)
- **🗺️ Personalized Roadmap** — Weekly plan generated via a 3-layer pipeline: rule-based prerequisite resolution → ChromaDB semantic retrieval → Gemini enrichment with real course links and practical tips
- **✅ ATS Optimizer** — Weighted scoring engine (65% keywords · 20% completeness · 15% format) with spaCy semantic matching (cosine similarity threshold 0.75)
- **🎤 Interview Simulator** — Conversational chatbot powered by Gemini; generates 6–8 offer-anchored questions (≥70% technical), mixing MCQ and open-ended formats, with an end-of-session scored report
- **📈 Progress Tracker** — Mark roadmap steps as complete and track your employability score over time
- **🔍 Job Offers** — Browse scraped offers or paste a custom job description for targeted analysis

### Technical Highlights

- **Hybrid RAG pipeline** with persistent ChromaDB vector store (cosine distance, HNSW index)
- **3-level fallback** system: Gemini multi-model cascade → rule-based engine → local heuristics — the platform never fully fails
- **Recursive prerequisite resolution** — automatically schedules foundational skills (e.g., Python + SQL) before advanced ones (e.g., Spark)
- **Multi-source scraper** covering Adzuna, RemoteOK, and Jobicy for 8 tech job profiles
- **Auto-documented REST API** via FastAPI's built-in OpenAPI / Swagger UI

---

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        FRONTEND (Vercel)                        │
│          React 19 · TanStack Router · shadcn/ui · Vite          │
└───────────────────────────┬─────────────────────────────────────┘
                            │ HTTPS / REST
┌───────────────────────────▼─────────────────────────────────────┐
│                        BACKEND (Render)                         │
│                  FastAPI · SQLAlchemy · Alembic                  │
│                                                                  │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────────────┐   │
│  │   Auth   │ │    CV    │ │   Gap    │ │     Roadmap      │   │
│  │  Router  │ │  Router  │ │  Router  │ │  RAG Pipeline    │   │
│  └──────────┘ └──────────┘ └──────────┘ └──────────────────┘   │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐                        │
│  │   ATS    │ │Interview │ │  Offers  │                        │
│  │  Router  │ │  Router  │ │  Router  │                        │
│  └──────────┘ └──────────┘ └──────────┘                        │
│                                                                  │
│  ┌────────────────────────────────────────────────────────┐     │
│  │                    AI / ML Layer                       │     │
│  │  spaCy NLP │ SentenceTransformers │ Gemini 2.5 Flash  │     │
│  └────────────────────────────────────────────────────────┘     │
└──────────┬──────────────────────────────────────┬───────────────┘
           │                                      │
┌──────────▼──────────┐              ┌────────────▼───────────────┐
│  PostgreSQL          │              │  ChromaDB (local)          │
│  (Supabase)          │              │  all-MiniLM-L6-v2          │
│  17 tables           │              │  HNSW · cosine distance    │
└─────────────────────┘              └────────────────────────────┘
```

### Roadmap Generation Pipeline

```
Gap Skills
    │
    ▼
Rule Engine ──── Recursive prerequisite resolution (DFS)
    │            Sort skills by priority & category
    │            Distribute across N weeks
    ▼
ChromaDB ──────── Semantic search (top-3 docs per skill)
    │             Sources: knowledge base + scraped offers
    │             Model: all-MiniLM-L6-v2 · cosine distance
    ▼
Gemini Flash ──── JSON enrichment: description · tip · resource link
    │             Temperature 0.3 · market_insight field
    │
    └─ fallback ── Rule-based roadmap (no LLM enrichment)
```

---

## 🛠️ Tech Stack

### Backend

| Category | Technology |
|----------|------------|
| Framework | FastAPI 0.111 + uvicorn |
| ORM | SQLAlchemy 2.0 |
| Migrations | Alembic |
| Auth | python-jose (JWT HS256) + passlib (bcrypt) |
| Validation | Pydantic v2 |
| PDF Parsing | PyMuPDF (fitz) 1.24 |
| DOCX Parsing | python-docx 1.1 |
| NLP | spaCy 3.7 (`en_core_web_md`) |
| Embeddings | sentence-transformers 3.0 (`all-MiniLM-L6-v2`) |
| Vector DB | ChromaDB 0.5 |
| LLM | Google Gemini 2.5 Flash (via httpx) |
| Scraping | requests + BeautifulSoup4 |
| Testing | pytest + pytest-asyncio |

### Frontend

| Category | Technology |
|----------|------------|
| Framework | React 19 + TypeScript 5.8 |
| Routing | TanStack Router (file-based, fully type-safe) |
| Data Fetching | TanStack Query v5 |
| UI Components | shadcn/ui (Radix primitives) |
| Styling | TailwindCSS 4 |
| Charts | Recharts |
| Forms | React Hook Form + Zod |
| HTTP Client | Axios |
| Build Tool | Vite 7 |

### Infrastructure

| Service | Purpose |
|---------|---------|
| Vercel | Frontend hosting (Node.js 20 runtime) |
| Render | Backend API hosting |
| Supabase | Managed PostgreSQL |
| GitHub | Source control + auto-deploy triggers |

---

## 📁 Project Structure

```
career-platform/
│
├── backend/
│   ├── app/
│   │   ├── config.py                # Pydantic settings (reads .env)
│   │   ├── main.py                  # App factory, CORS middleware, startup hooks
│   │   ├── db/
│   │   │   ├── database.py          # SQLAlchemy engine & session factory
│   │   │   ├── models.py            # ORM table definitions (17 tables)
│   │   │   ├── seed.py              # Idempotent reference data seeder
│   │   │   └── import_jobs.py       # Bulk offer import utility
│   │   ├── models/                  # Pydantic request/response schemas
│   │   │   ├── user.py
│   │   │   ├── cv.py
│   │   │   ├── skill.py
│   │   │   ├── offer.py
│   │   │   └── interview_chat.py
│   │   ├── routers/                 # HTTP endpoint handlers
│   │   │   ├── auth.py              # POST /auth/register · login · GET /me
│   │   │   ├── cv.py                # POST /cv/upload · GET /cv/list
│   │   │   ├── gap.py               # POST /gap/analyze · GET /gap/history
│   │   │   ├── roadmap.py           # POST /roadmap/generate · PATCH progress
│   │   │   ├── ats.py               # POST /ats/analyze
│   │   │   ├── interview.py         # POST /interview/start · /chat
│   │   │   └── offers.py            # GET /offers/list · POST /offers/paste
│   │   └── services/
│   │       ├── ats_service.py       # Keyword + semantic scoring engine
│   │       ├── gap_service.py       # Employability score calculation
│   │       ├── cv_service.py        # PDF / DOCX text extraction
│   │       ├── offer_service.py     # Offer ingestion & skill extraction
│   │       ├── interview_chat_service.py  # Gemini conversation manager
│   │       └── roadmap/
│   │           ├── roadmap_service.py     # Pipeline orchestrator
│   │           ├── rule_based_engine.py   # Prerequisite resolver + scheduler
│   │           ├── gemini_engine.py       # LLM enrichment prompts & calls
│   │           ├── knowledge_base.py      # Curated skill → courses + projects
│   │           └── rag/
│   │               ├── vector_store.py    # ChromaDB singleton + CRUD
│   │               ├── document_loader.py # KB + scraper → documents
│   │               └── retriever.py       # Semantic query interface
│   ├── alembic/
│   │   └── versions/                # 6 versioned migration scripts
│   ├── chroma_db/                   # Persisted vector index (gitignored in prod)
│   ├── tests/                       # pytest suite
│   ├── requirements.txt             # Full dependency set
│   ├── requirements-render-free.txt # Lightweight set for 512 MB RAM constraint
│   └── alembic.ini
│
├── frontend/
│   └── src/
│       ├── components/
│       │   ├── app-sidebar.tsx
│       │   ├── topbar.tsx
│       │   └── ui/                  # shadcn/ui component library
│       ├── lib/
│       │   ├── api/                 # Typed Axios clients per domain
│       │   │   ├── auth.ts · cv.ts · gap.ts
│       │   │   ├── roadmap.ts · ats.ts · interview.ts
│       │   │   └── client.ts        # Axios instance + auth interceptor
│       │   ├── auth-context.tsx     # JWT storage + React auth provider
│       │   └── theme.tsx
│       └── routes/                  # TanStack file-based routes
│           ├── _app.dashboard.tsx
│           ├── _app.upload.tsx
│           ├── _app.gap.tsx
│           ├── _app.roadmap.tsx
│           ├── _app.cv-optimization.tsx
│           ├── _app.interview.tsx
│           ├── _app.jobs.tsx
│           ├── _app.progress.tsx
│           ├── login.tsx
│           └── register.tsx
│
└── data/
    ├── scraper/
    │   ├── job_scraper.py           # Multi-source scraper (Adzuna, RemoteOK, Jobicy)
    │   ├── scheduler.py             # APScheduler periodic jobs
    │   └── wtj_scraper.py           # Welcome to the Jungle scraper
    └── parser/
        └── cv_parser.py             # Standalone CV extraction utilities
```

---

## 🚀 Quick Start

### Prerequisites

- **Python** 3.11+
- **Node.js** 20+
- **PostgreSQL** 14+ (or a free [Supabase](https://supabase.com) project)
- **Google AI API key** — free at [aistudio.google.com](https://aistudio.google.com)

---

### Backend Setup

```bash
# 1. Clone the repository
git clone https://github.com/your-org/career-platform.git
cd career-platform/backend

# 2. Create and activate a virtual environment
python -m venv venv
source venv/bin/activate          # Windows: venv\Scripts\activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Download the spaCy language model
python -m spacy download en_core_web_md

# 5. Configure environment variables
cp .env.example .env
# Edit .env with your values (see Environment Variables section)

# 6. Apply database migrations
alembic upgrade head

# 7. Start the development server
uvicorn app.main:app --reload --port 8000
```

The API is available at **`http://localhost:8000`**
Interactive docs (Swagger UI): **`http://localhost:8000/docs`**

> **First startup note:** ChromaDB initializes automatically by indexing the knowledge base and any scraped offers. This takes ~30–60 seconds. Set `SKIP_CHROMA_INIT=true` to skip (rule-based fallback will be used instead).

---

### Frontend Setup

```bash
cd frontend
npm install
npm run dev
```

The app is available at **`http://localhost:5173`**

---

## 🔐 Environment Variables

### Backend — `backend/.env`

```env
# ── Database ───────────────────────────────────────────────────
DATABASE_URL=postgresql://user:password@host:5432/career_guidance

# ── Security ───────────────────────────────────────────────────
SECRET_KEY=your-random-secret-key-min-32-chars
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=1440

# ── Google Gemini ──────────────────────────────────────────────
LLM_API_KEY=your-google-ai-api-key
LLM_MODEL=gemini-2.5-flash-lite
LLM_FALLBACK_MODELS=gemini-2.5-flash-lite,gemini-2.0-flash,gemini-2.5-flash
LLM_BASE_URL=https://generativelanguage.googleapis.com/v1beta

# ── CORS ───────────────────────────────────────────────────────
# Comma-separated list of allowed frontend origins
ALLOWED_ORIGINS=http://localhost:5173,https://your-app.vercel.app

# ── File Uploads ───────────────────────────────────────────────
UPLOAD_DIR=uploads
MAX_FILE_SIZE_MB=10

# ── ChromaDB ───────────────────────────────────────────────────
# Set to true on memory-constrained environments (Render free tier)
SKIP_CHROMA_INIT=false
```

### Frontend — `frontend/.env`

```env
VITE_API_URL=http://localhost:8000
```

---

## 📡 API Reference

All endpoints except `/auth/register` and `/auth/login` require:
```
Authorization: Bearer <access_token>
```

### Authentication

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/auth/register` | Create account — returns JWT + user profile |
| `POST` | `/auth/login` | Login via OAuth2 form — returns JWT + user profile |
| `GET` | `/auth/me` | Get current authenticated user |

### CV Management

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/cv/upload` | Upload a PDF or DOCX file; extracts and stores text |
| `GET` | `/cv/list` | List the authenticated user's CVs |
| `DELETE` | `/cv/{id}` | Delete a CV and cascade-remove associated data |

### Gap Analysis

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/gap/analyze` | Run gap analysis (market mode or offer mode) |
| `GET` | `/gap/history` | Retrieve past gap analyses |
| `GET` | `/gap/jobs` | List available target job profiles |
| `POST` | `/gap/target-job` | Set or update the user's active target job |

### Roadmap

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/roadmap/generate` | Generate a personalized roadmap from a gap analysis |
| `GET` | `/roadmap/list` | List the user's generated roadmaps |
| `PATCH` | `/roadmap/steps/{id}/progress` | Update step status (`not_started` / `in_progress` / `completed`) |

### ATS Optimizer

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/ats/analyze` | Score a CV against a job description text |

### Interview Simulator

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/interview/start` | Generate interview questions for a target job |
| `POST` | `/interview/chat` | Submit an answer; receive feedback + next question |

### Offers

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/offers/list` | Browse scraped job offers |
| `POST` | `/offers/paste` | Submit a custom job description |

> Full interactive documentation is auto-generated at `/docs` (Swagger UI) and `/redoc`.

---

## 🤖 AI Modules

### 1. ATS Scoring Engine

Scores how well a CV matches a job description using a weighted formula:

```
ATS Score = 0.65 × Keyword Score
          + 0.20 × Completeness Score
          + 0.15 × Format Score
```

**Keyword matching** uses a two-pass approach:
1. Exact match after stopword removal
2. spaCy semantic similarity (`en_core_web_md` word vectors, threshold `0.75`) — detects equivalences like *"machine learning"* ↔ *"apprentissage automatique"*

**Completeness** checks for 6 standard CV sections: `experience`, `education`, `skills`, `projects`, `certification`, `summary`.

**Format** validates presence of email address, phone number, and adequate bullet-point usage.

Returns: overall score, matched keywords, missing keywords, formatting warnings, and actionable suggestions.

---

### 2. RAG Pipeline (Roadmap Generation)

A three-layer pipeline ensures personalized, market-grounded roadmaps:

**Layer 1 — Rule Engine**
- Resolves skill prerequisites recursively using DFS (e.g., Python → SQL → Spark)
- Sorts skills by category and importance score
- Distributes learning steps across weeks

**Layer 2 — ChromaDB Retrieval**
- Embeds each skill query with `all-MiniLM-L6-v2` (~80 MB, ~22 ms/batch)
- Retrieves the top-3 most relevant documents per skill via cosine similarity
- Sources: curated `SKILL_KNOWLEDGE_BASE` + scraped real job postings

**Layer 3 — Gemini Enrichment**
- Injects the RAG context into a structured prompt (temperature 0.3)
- Outputs a JSON object with: `description`, `tip`, `resource_link`, `market_insight`
- Graceful degradation: returns rule-based roadmap if Gemini is unavailable

---

### 3. Interview Simulator

- User pastes a full job offer text
- Gemini analyzes the offer and generates 6–8 questions anchored to its specific technologies, missions, and requirements
- Question mix: ≥70% technical, alternating between MCQ (4 plausible choices) and open-ended scenario questions
- Immediate feedback after each answer with correct/incorrect verdict
- Final report: score (0–100), label (e.g., "Bon potentiel"), overall advice, and per-question corrections

---

### Fallback Strategy

| Level | Trigger | Behavior |
|-------|---------|----------|
| 1 | Gemini 503 / rate limit | Retry with next model in `LLM_FALLBACK_MODELS` |
| 2 | All Gemini models unavailable | Return rule-based roadmap without enrichment |
| 3 | ChromaDB unavailable | `SKIP_CHROMA_INIT=true` → rule-based only |
| 4 | spaCy vectors not loaded | ATS falls back to exact keyword matching |

---

## 🗄️ Database Schema

17 PostgreSQL tables organized around the user's career lifecycle:

```
users
 ├── cvs
 │    └── cv_skills ──────────────────── skills
 ├── user_target_jobs ──────────── target_jobs
 │    │                                 └── job_skills ── skills
 │    ├── career_gap_analyses
 │    │    ├── gap_details ──────────────── skills
 │    │    └── roadmaps
 │    │         └── roadmap_steps ──────── skills
 │    └── interview_sessions
 │         └── interview_questions ────── skills
 └── user_skill_progress ── skills · roadmap_steps

offers ── offer_skills ─────────── skills
      └── career_gap_analyses
      └── interview_sessions
      └── cv_optimizations ──────── cvs
```

**Key design decisions:**
- Cascade deletes on all user-owned data (`ON DELETE CASCADE`)
- Idempotent seeder — `seed_if_empty()` only inserts reference data on first run
- Unique constraints on `(cv_id, skill_id)`, `(offer_id, skill_id)`, and offer `url`
- Check constraints enforce valid enum values (`status`, `source_type`, etc.)

---

## 🕷️ Data Pipeline & Scraping

The `data/scraper/` module collects real job postings from three sources:

| Source | Method | Coverage |
|--------|--------|---------|
| [Adzuna](https://www.adzuna.com) | REST API | All 8 profiles |
| [RemoteOK](https://remoteok.com) | JSON API | All 8 profiles |
| [Jobicy](https://jobicy.com) | BeautifulSoup | All 8 profiles |

**Supported job profiles:** Data Engineer · Data Scientist · Data Analyst · ML Engineer · Cloud Engineer · DevOps Engineer · Backend Developer · Fullstack Developer

### Running the scraper

```bash
cd data/scraper

# Scrape all profiles once
python job_scraper.py --profile all

# Scrape a specific profile
python job_scraper.py --profile "data engineer"

# Run on a schedule (APScheduler)
python scheduler.py
```

Scraped offers are automatically:
1. Deduplicated on `url` (SQL unique constraint — no duplicates on re-runs)
2. Stored in the `offers` and `offer_skills` tables
3. Indexed in ChromaDB for downstream RAG retrieval

---

## 🚢 Deployment

### Frontend — Vercel

```bash
cd frontend
vercel deploy --prod
```

Set in the Vercel dashboard → Environment Variables:
```
VITE_API_URL=https://your-backend.onrender.com
```

`vercel.json` is pre-configured with the correct build command and Node.js 20 runtime.

---

### Backend — Render

1. Connect your GitHub repository in the Render dashboard
2. **Build command:** `pip install -r requirements-render-free.txt`
3. **Start command:** `uvicorn app.main:app --host 0.0.0.0 --port $PORT`
4. Add all environment variables from the [Environment Variables](#-environment-variables) section
5. Add `SKIP_CHROMA_INIT=true` on the free tier (512 MB RAM limit)

> **Free tier note:** Render's free plan spins down after 15 minutes of inactivity — the first request after sleep may take ~30 seconds. `requirements-render-free.txt` strips out `chromadb` and `sentence-transformers` to stay within the RAM limit; the rule-based roadmap fallback activates automatically.

---

### Database — Supabase

1. Create a project at [supabase.com](https://supabase.com)
2. Copy the connection string from **Settings → Database → Connection string**
3. Set `DATABASE_URL` in your backend environment
4. Run: `alembic upgrade head`

---

## 🧪 Running Tests

```bash
cd backend

# Run all tests
pytest

# Run with coverage report
pytest --cov=app --cov-report=term-missing

# Run a specific test file
pytest tests/test_ats.py -v
```

| Test file | Coverage area |
|-----------|--------------|
| `test_ats.py` | ATS scoring engine (keyword extraction, semantic match, scoring) |
| `test_auth.py` | Registration, login, JWT validation |
| `test_db_connexion.py` | Database connectivity |
| `test_gap.py` | Gap analysis and employability score |
| `test_roadmap.py` | Roadmap generation pipeline |

---

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch: `git checkout -b feat/your-feature`
3. Commit your changes following [Conventional Commits](https://www.conventionalcommits.org): `git commit -m "feat: add your feature"`
4. Push the branch: `git push origin feat/your-feature`
5. Open a Pull Request against `main`

---

## 📄 License

This project is licensed under the **MIT License** — see the [LICENSE](LICENSE) file for details.

---

<div align="center">

Built with ❤️ by a team of 4 students · 2026

</div>
