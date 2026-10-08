# 🎵 HarmoniaAI

> **AI-powered audio stem separation — split any song into vocals, drums, bass, and instruments.**

HarmoniaAI is a full-stack, containerized platform powered by the [Demucs](https://github.com/facebookresearch/demucs) deep learning model. Upload any audio track and get back individual stems in minutes — all for free, self-hosted, with a live progress bar while you wait.

---

## ✨ Features

- 🎤 **AI Stem Separation** — Split audio into Vocals, Drums, Bass & Other using Meta's Demucs model
- ⚡ **Async Job Queue** — Celery + Redis task queue with real-time progress polling
- 📦 **S3-Compatible Storage** — MinIO locally, Cloudflare R2 in production (free tier)
- 🔐 **JWT Authentication** — Secure login with HS256 tokens via Supabase or local Postgres
- 🐳 **Fully Dockerized** — Single `docker compose up` gets the entire backend running locally
- 📊 **Flower Monitoring** — Celery task dashboard (via SSH tunnel in production)
- 🌐 **Next.js Frontend** — Modern UI with live job progress polling every 3 seconds

---

## 🏗️ Architecture

```
┌─────────────────┐     ┌──────────────┐     ┌──────────────────┐
│   Next.js UI    │────▶│  FastAPI API │────▶│  Celery Worker   │
│  (Vercel/local) │     │  (Backend)   │     │  (Demucs model)  │
└─────────────────┘     └──────┬───────┘     └────────┬─────────┘
                               │                       │
                        ┌──────▼───────┐      ┌────────▼─────────┐
                        │  PostgreSQL  │      │  Redis (broker)  │
                        │  (Supabase) │      │                  │
                        └──────────────┘      └──────────────────┘
                               │
                        ┌──────▼───────┐
                        │  S3 Storage  │
                        │(R2 / MinIO)  │
                        └──────────────┘
```

---

## 🗂️ Project Structure

```
HarmoniaAI/
├── frontend/               # Next.js UI (upload, job status, stem download)
├── backend/                # FastAPI app (REST API, auth, job dispatch)
│   └── app/
│       ├── api/v1/         # Route handlers
│       ├── auth.py         # JWT authentication
│       └── models/         # SQLAlchemy / Alembic models
├── workers/
│   └── audio/              # Celery worker — runs Demucs separation
├── infra/                  # Production infra (Caddy, Docker Compose for VM)
├── docker-compose.yml      # Local full-stack setup
├── docker-compose.nominio.yml  # Variant without MinIO
├── .env.example            # Production env template
├── .env.local.example      # Local dev env template
├── frontend.env.example    # Frontend env template
└── DEPLOY.md               # Step-by-step free deployment guide
```

---

## 🚀 Local Development Setup

### Prerequisites
- [Docker Desktop](https://www.docker.com/products/docker-desktop/) installed and running
- [Node.js 18+](https://nodejs.org/) for the frontend

### 1. Clone and configure environment

```bash
git clone https://github.com/YOUR_USERNAME/HarmoniaAI.git
cd HarmoniaAI

# Copy the local dev env file (defaults work out of the box)
cp .env.local.example .env
```

### 2. Start backend services

```bash
# Build and start Postgres, Redis, MinIO, API, and Worker
docker compose build
docker compose up -d postgres redis minio

# Run database migrations (first time only)
docker compose run --rm api alembic upgrade head

# Start all services
docker compose up -d
```

| Service | URL |
|---|---|
| FastAPI backend | http://localhost:8000 |
| API docs (Swagger) | http://localhost:8000/docs |
| MinIO console | http://localhost:9001 (minioadmin / minioadmin) |

### 3. Start the frontend

```bash
cd frontend
npm install
npm run dev
```

Frontend runs at **http://localhost:3000**

---

## 🔧 Tech Stack

| Layer | Technology |
|---|---|
| Frontend | Next.js, TypeScript |
| Backend | FastAPI (Python) |
| Task Queue | Celery + Redis |
| AI Model | Meta Demucs (audio separation) |
| Database | PostgreSQL (local) / Supabase (prod) |
| Storage | MinIO (local) / Cloudflare R2 (prod) |
| Auth | JWT (HS256) |
| Reverse Proxy | Caddy (auto HTTPS) |
| Containerization | Docker + Docker Compose |

---

## 📄 License

MIT
