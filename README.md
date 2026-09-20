<div align="center">

<img src="https://capsule-render.vercel.app/api?type=waving&color=gradient&customColorList=6,11,20&height=230&section=header&text=ReServe&fontSize=84&fontAlignY=38&desc=AI-powered%20resource%20redistribution%20%26%20rescue%20network&descAlignY=60&animation=fadeIn" alt="ReServe banner" />

<a href="https://github.com/YOUR_USERNAME/reserve">
  <img src="https://readme-typing-svg.demolab.com?font=Fira+Code&weight=600&pause=1200&color=8400FF&center=true&vCenter=true&width=760&lines=Surplus+food+%26+medical+supplies+%E2%86%92+people+who+need+them;Matched+in+seconds%2C+not+days.;Explainable+scoring.+Zero+black+boxes.;80+meals.+3+destinations.+1+truck+run." alt="Typing animation" />
</a>

<br/>

![React](https://img.shields.io/badge/React-19-61DAFB?style=for-the-badge&logo=react&logoColor=black)
![Vite](https://img.shields.io/badge/Vite-8-646CFF?style=for-the-badge&logo=vite&logoColor=white)
![Tailwind](https://img.shields.io/badge/Tailwind-4-06B6D4?style=for-the-badge&logo=tailwindcss&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-Python-009688?style=for-the-badge&logo=fastapi&logoColor=white)
![PostgreSQL](https://img.shields.io/badge/PostgreSQL-Supabase-4169E1?style=for-the-badge&logo=postgresql&logoColor=white)
![Gemini](https://img.shields.io/badge/Google-Gemini-8E75B2?style=for-the-badge&logo=googlegemini&logoColor=white)

![Tests](https://img.shields.io/badge/tests-350%2B-brightgreen?style=flat-square)
![Migrations](https://img.shields.io/badge/alembic-10%20migrations-blue?style=flat-square)
![Endpoints](https://img.shields.io/badge/API-15%20feature%20groups-8400FF?style=flat-square)

### 🚚 &nbsp;Every night, good food and medical supplies get thrown away.<br/>Every night, shelters and NGOs run short.<br/>**ReServe closes that gap.**

[**🌐 Live demo**](https://reserve-web-YOURNAME.onrender.com) &nbsp;·&nbsp; [**📖 API docs**](https://reserve-api-YOURNAME.onrender.com/docs) &nbsp;·&nbsp; [**🐛 Report a bug**](https://github.com/YOUR_USERNAME/reserve/issues)

<sub>The free backend sleeps when idle. If the demo feels slow, give it up to a minute to wake up. It only happens once.</sub>

</div>

---

## 📑 Table of contents

- [What is ReServe?](#-what-is-reserve)
- [Highlights](#-highlights)
- [How a rescue works](#-how-a-rescue-works)
- [The matching engine](#-the-matching-engine-no-black-boxes)
- [The 80-meal flagship scenario](#-the-80-meal-flagship-scenario)
- [Roles](#-roles)
- [Operation lifecycle](#-operation-lifecycle)
- [Architecture & tech stack](#-architecture--tech-stack)
- [Quick start](#-quick-start)
- [Configuration](#-configuration)
- [API](#-api)
- [Testing](#-testing)
- [Deployment](#-deployment)
- [Security](#-security)
- [Known limitations & roadmap](#-known-limitations--roadmap)

---

## 🌍 What is ReServe?

ReServe is a coordination platform that connects **organisations with surplus** (hotels, caterers, pharmacies) to **organisations in need** (NGOs, shelters, medical facilities) and to the **rescue partners** who move the goods between them.

A provider posts what they have. ReServe structures the listing with AI, **scores every possible recipient with a transparent rule-based engine**, splits the load across as many destinations as needed, dispatches a rescue partner, and tracks the whole delivery, including re-routing on the fly when a recipient drops out mid-operation.

> **Design principle:** AI describes, rules decide. Gemini structures a listing but never chooses who receives it. Every allocation decision is deterministic, reproducible, and auditable.

---

## ✨ Highlights

| | Feature | What it does |
|---|---|---|
| 🧠 | **Explainable matching** | Six-factor scoring. Every candidate, proposed *or rejected*, is stored with its full score breakdown. |
| 🤖 | **Gemini as analyst, not judge** | Turns a messy freeform listing into strict structured data. It has no power to allocate anything. |
| 🔁 | **Live reallocation** | A recipient goes unavailable mid-delivery? The allocation is superseded and the remainder is re-matched automatically. |
| 🧩 | **Partial allocation** | One donation can be split across several recipients. Over- and double-allocation are blocked. |
| 🚚 | **Operation tracking** | `PLANNED → IN_TRANSIT → DELIVERED → COMPLETED`, with a strict state machine and a full event history. |
| 🗺️ | **Network map** | Interactive Leaflet map of providers, recipients, hubs, and live routes. |
| 📊 | **Honest analytics** | Weekly supply vs. demand, deadline performance, and trends. Zeros are real zeros, never fabricated. |
| 🔮 | **Surplus forecast & alerts** | Learns *when* surplus usually appears and pings nearby rescue partners ahead of time. |
| 🔔 | **Notifications** | In-app, plus email when SMTP is configured. |
| 🍽️ | **Food-aware** | Food categories, allergens, and storage requirements (refrigerated, frozen, dry). Medical supplies too. |
| 🔐 | **Locked-down auth** | JWT access and refresh tokens, role-based access, ownership checks, and no self-registered admins. |
| 🧪 | **350+ tests** | Run against a real PostgreSQL database, not mocks. |
| 🎭 | **Mock mode** | The whole UI runs without a backend for design work and demos. |

---

## 🔄 How a rescue works

```mermaid
sequenceDiagram
    autonumber
    actor P as Provider
    participant API as FastAPI
    participant G as Gemini
    participant M as Matching engine
    actor R as Recipient or hub
    actor V as Rescue partner

    P->>API: Post surplus (food or medical)
    API->>G: Analyze and structure the listing
    G-->>API: Advisory metadata (never decides)
    P->>API: Trigger matching
    API->>M: Score every candidate on 6 factors
    M-->>API: Ranked, explained matches
    P->>API: Allocate (full or partial)
    API->>V: Create operation and notify partner
    V->>API: PLANNED, IN_TRANSIT, DELIVERED
    API->>R: Delivery confirmed
```

---

## 🧠 The matching engine (no black boxes)

The engine lives in [`backend/app/services/matching_engine.py`](backend/app/services/matching_engine.py) and is **pure**: no database, no network, no randomness, no AI. Same inputs, same score, every time.

Six factors are evaluated for every candidate:

| # | Factor | Kind | Behaviour |
|---|---|---|---|
| 1 | Resource-type compatibility | 🚧 Hard gate | Food goes to food-accepting recipients, medical to medical. |
| 2 | Recipient eligibility | 🚧 Hard gate | Platform verification, plus medical verification for medical goods. |
| 3 | Recipient availability | 🚧 Hard gate | Unavailable recipients are out. |
| 4 | Available capacity | 🎚️ Soft score | Can also hard-fail at zero capacity. |
| 5 | Distance (haversine) | 🎚️ Soft score | Scores fall to 0 at 50 km, and it hard-fails outside the recipient's own service area. |
| 6 | Urgency | 🎚️ Soft score | Adds its own score **and** changes how much distance matters. |

Fail any hard gate and a candidate is `REJECTED` with a score of `0.0`, with the reason recorded. Clear them all and it is `PROPOSED` with a weighted score in `[0, 1]`.

**The more urgent the rescue, the more proximity dominates:**

| Urgency | Capacity | Distance | Urgency |
|---|:---:|:---:|:---:|
| 🟢 LOW | 0.40 | 0.30 | 0.30 |
| 🟡 MEDIUM | 0.35 | 0.35 | 0.30 |
| 🟠 HIGH | 0.30 | 0.45 | 0.25 |
| 🔴 CRITICAL | 0.25 | **0.55** | 0.20 |

The weights are constants at the top of the file, so changing the policy is a one-line diff.

---

## 🍱 The 80-meal flagship scenario

The seed script ships with a scenario built to show the whole system in one run:

> A hotel donates **80 cooked meals**. ReServe matches, allocates, and delivers them across **two recipients and a night rescue hub in a single truck run**.

```
🏨 Hotel (80 meals)
   ├── 🤝 NGO A .................. 50 meals
   ├── 🏠 Shelter B .............. 20 meals
   └── 🌙 Night Rescue Hub ....... 10 meals
```

One extra resource is deliberately left `AVAILABLE` and unmatched so you can hit `POST /api/matching/{resource_id}` **live** during a demo and watch the engine work.

---

## 👥 Roles

| Role | Represents | Can do |
|---|---|---|
| 🏨 `PROVIDER` | Business or org with surplus | Post, edit, and analyze resources. Accept or decline requests. Trigger matching. |
| 🏠 `RECIPIENT` | NGO, shelter, community, or medical org | Create a profile and raise resource requests. |
| 🚚 `RESCUE_PARTNER` | Volunteer, transport org, or organisation | Run operations and update delivery status. |
| 🛡️ `ADMIN` | Platform administrator | Everything, including verifying recipients and partners. |

`ADMIN` accounts **cannot** be self-registered. Public sign-up only accepts the first three roles.

---

## 🚦 Operation lifecycle

Every transition is validated and written to the operation's event log, so you always get the full history, not just the current status.

```mermaid
stateDiagram-v2
    [*] --> PLANNED
    PLANNED --> IN_TRANSIT
    IN_TRANSIT --> DELIVERED
    DELIVERED --> COMPLETED
    PLANNED --> FAILED
    IN_TRANSIT --> FAILED
    DELIVERED --> FAILED
    COMPLETED --> [*]
    FAILED --> [*]
```

**Reallocation** (`POST /api/operations/{id}/reallocate`) handles "a recipient just became unavailable": the affected allocation moves to `REALLOCATED`, the same deterministic engine finds a replacement, a new allocation is created (capped by the remaining quantity and the new recipient's capacity), and a `REALLOCATED` event records exactly what changed and why.

---

## 🏗️ Architecture & tech stack

```mermaid
flowchart LR
    subgraph Client
        UI["React 19 + Vite SPA"]
    end
    subgraph Server
        API["FastAPI routers"]
        SVC["Services layer"]
        ENG["Matching engine (pure)"]
    end
    subgraph External
        DB[("PostgreSQL / Supabase")]
        ST["Supabase Storage"]
        AI["Google Gemini"]
        MAIL["SMTP (optional)"]
    end
    UI -->|"REST + JWT"| API
    API --> SVC
    SVC --> ENG
    SVC --> DB
    SVC --> ST
    SVC --> AI
    SVC --> MAIL
```

| Layer | Tech |
|---|---|
| **Frontend** | React 19, Vite 8, Tailwind CSS 4, React Router 7, Recharts, React-Leaflet, Axios, Lucide |
| **Backend** | FastAPI, SQLAlchemy, Alembic, Pydantic, python-jose (JWT), passlib (bcrypt) |
| **Database** | PostgreSQL (Supabase-compatible) |
| **AI** | Google Gemini, used only to structure listings |
| **Storage** | Supabase Storage, or local disk as a zero-setup fallback |
| **Testing** | Pytest against real PostgreSQL |

> 🛰️ Only **two** external services are ever called: Gemini and Supabase. Travel-time ETAs are computed offline from distance, with no routing or maps API.

<details>
<summary><b>📁 Project structure</b></summary>

```
reserve/
├── backend/
│   ├── app/
│   │   ├── api/          # Routers, one file per feature area
│   │   ├── core/         # Config, JWT and hashing, auth deps, error types
│   │   ├── db/           # SQLAlchemy engine and session
│   │   ├── models/       # ORM models and shared enums
│   │   ├── schemas/      # Pydantic request and response schemas
│   │   ├── services/     # Business logic (matching_engine, allocation, operations, ...)
│   │   └── main.py       # App wiring: CORS, error handlers, routers
│   ├── alembic/          # Database migrations
│   ├── scripts/          # seed_demo_data.py, verify_tables.py, clear_data.py
│   ├── tests/            # Pytest suite
│   ├── .env.example
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── pages/        # Dashboard, Rescues, Matching, Operations, Network, Analytics, ...
│   │   ├── components/   # Cards, maps, charts, trackers, UI kit
│   │   ├── services/     # API client (axios) and per-feature service modules
│   │   ├── context/      # Auth provider
│   │   ├── routes/       # Route table and protected routes
│   │   ├── layouts/      # Public and app shells
│   │   └── data/         # Mock data for offline mode
│   └── package.json
├── render.yaml           # One-click Render Blueprint
└── README.md
```

</details>

---

## 🚀 Quick start

### Prerequisites

- **Python 3.10+** (developed on 3.13)
- **Node.js 20.19+ or 22+**
- A **PostgreSQL** database: local, or a free [Supabase](https://supabase.com) project

### 1 · Backend

```bash
cd backend
python3 -m venv venv
source venv/bin/activate          # Windows: venv\Scripts\activate
pip install -r requirements.txt

cp .env.example .env              # then set DATABASE_URL and JWT_SECRET
alembic upgrade head              # create the schema
python3 scripts/verify_tables.py  # optional sanity check

uvicorn app.main:app --reload
```

API → <http://localhost:8000> · Swagger → <http://localhost:8000/docs> · Health → <http://localhost:8000/api/health>

### 2 · Seed the demo data 🌱

```bash
python3 scripts/seed_demo_data.py
```

This creates an admin, 3 providers, 3 recipients, 2 rescue partners, resources in every status, several operations, and the [80-meal scenario](#-the-80-meal-flagship-scenario). The script **prints every demo account and the shared demo password** when it finishes. Try logging in as `provider.hotel@demo.reserve.local`.

It's safe to re-run. It deletes only its own data (emails ending in `@demo.reserve.local`, names prefixed `[DEMO]`) and never touches real records.

### 3 · Frontend

```bash
cd frontend
npm install
cp .env.example .env
```

Set these in `frontend/.env`:

```ini
VITE_API_BASE_URL=http://localhost:8000/api
VITE_USE_MOCKS=false
```

```bash
npm run dev                       # → http://localhost:5173
```

> 🎭 **No backend yet?** Leave `VITE_USE_MOCKS` unset and the UI runs entirely on built-in mock data.
> ⚠️ `VITE_` values are baked in at **build time**. Change one and you must rebuild.

---

## ⚙️ Configuration

Backend settings come from environment variables (`.env` locally). The essentials:

| Variable | Purpose |
|---|---|
| `DATABASE_URL` | PostgreSQL connection string (`sslmode=require` is added automatically for Supabase hosts). |
| `JWT_SECRET` | Signing secret. **Must be 32+ random characters** in staging or production, or the app refuses to start. |
| `ENVIRONMENT` | `development`, `staging`, or `production`. |
| `GEMINI_API_KEY` / `GEMINI_MODEL` | Enable AI analysis of resources. Use a current Gemini model. |
| `SUPABASE_URL` / `SUPABASE_KEY` / `SUPABASE_STORAGE_BUCKET` | Image storage. Leave blank to use local disk instead. |
| `CORS_ORIGINS` | Comma-separated origins allowed to call the API from a browser. |
| `PUBLIC_BASE_URL` | Base URL used to build links to locally stored uploads. |

<details>
<summary><b>Full variable reference</b></summary>

| Variable | Default | Purpose |
|---|---|---|
| `APP_NAME` | `ReServe API` | Title in Swagger UI. |
| `APP_VERSION` | `0.1.0` | Shown in Swagger and `/api/health`. |
| `DEBUG` | `true` | Reserved for debug-only behaviour. |
| `JWT_ALGORITHM` | `HS256` | JWT signing algorithm. |
| `JWT_ACCESS_TOKEN_EXPIRE_MINUTES` | `1440` | Access token lifetime (24 h). |
| `JWT_REFRESH_TOKEN_EXPIRE_MINUTES` | `10080` | Refresh token lifetime (7 d). |
| `GEMINI_TIMEOUT_SECONDS` | `20` | Fails fast with `504` instead of hanging. |
| `MAX_UPLOAD_FILE_SIZE_MB` | `5` | Upload cap for both storage backends. |
| `LOCAL_UPLOAD_DIR` | `uploads` | Where files go without Supabase, served at `/static/uploads/`. |
| `LOG_LEVEL` | `INFO` | Application log level. |

See [`backend/.env.example`](backend/.env.example) for inline documentation of every setting.

</details>

---

## 📡 API

Interactive docs are served by the backend itself:

| | URL |
|---|---|
| Swagger UI | `/docs` |
| ReDoc | `/redoc` |
| OpenAPI schema | `/openapi.json` |

**Feature groups:** `Health` · `Auth` · `Users` · `Resources` · `Uploads` · `Recipients` · `Rescue Partners` · `Resource Requests` · `Matching` · `Allocations` · `Operations` · `Analytics` · `Predictions` · `Notifications` · `Admin`

Every endpoint uses one consistent envelope:

```jsonc
// ✅ Success
{ "success": true, "data": { /* ... */ }, "message": "..." }

// ❌ Error
{ "success": false, "error": { "code": "FORBIDDEN_ROLE", "message": "..." } }
```

**Auth flow:** `POST /api/auth/register` → `POST /api/auth/login` (returns access and refresh tokens) → send `Authorization: Bearer <access_token>` → `POST /api/auth/refresh` when it expires.

<details>
<summary><b>📈 Analytics endpoints</b></summary>

| Endpoint | Answers |
|---|---|
| `GET /api/analytics/overview` | Where does the platform stand right now? |
| `GET /api/analytics/trends?days=14` | How has activity moved day by day? (zero-filled, UTC-bucketed) |
| `GET /api/analytics/resource-types` | How does FOOD compare with MEDICAL? |
| `GET /api/analytics/insights` | Weekly supply vs. demand, allocation outcomes, matching time, deadline performance |
| `GET /api/analytics/surplus-forecast` | Recent food surplus, and the hour of day it usually appears |
| `POST /api/analytics/surplus-alert` | Notify nearby available rescue partners about the predicted window |

Analytics **never fabricate data**: an empty database returns zeros. `GET /api/predictions` is different and is clearly labelled `is_demo: true` when it has to fall back to demo data.

</details>

---

## 🧪 Testing

The suite runs against a **real PostgreSQL database**. SQLite isn't supported because the models use native `ENUM` and `UUID` types. Point `DATABASE_URL` at a **throwaway** database, since everything in it gets dropped:

```bash
createdb reserve_test
export DATABASE_URL=postgresql+psycopg2://postgres:postgres@localhost:5432/reserve_test
cd backend && pytest -v
```

Tables are created once per session and truncated between tests, so tests can run in any order. Verify migrations separately with `alembic upgrade head && alembic check`.

---

## ☁️ Deployment

### One-click on Render (frontend + backend)

[![Deploy to Render](https://render.com/images/deploy-to-render-button.svg)](https://render.com/deploy?repo=https://github.com/YOUR_USERNAME/reserve)

The included [`render.yaml`](render.yaml) Blueprint deploys the **FastAPI API** and the **React static site** together. Before you use it:

1. Replace `YOURNAME` in `render.yaml` with something unique.
2. Apply the Blueprint and enter the prompted secrets: `DATABASE_URL`, `SUPABASE_URL`, `SUPABASE_KEY`, `GEMINI_API_KEY`, `GEMINI_MODEL`. Render generates `JWT_SECRET` for you.
3. Check `https://<your-api>.onrender.com/api/health`. It should report `database_connected: true`.

> 💡 Render's free web services sleep when idle, so open `/api/health` a minute before a live demo. Uploads must use Supabase Storage, because the free disk is wiped on restart.

<details>
<summary><b>Other options: AWS EC2, or Netlify + Render</b></summary>

- **AWS free tier:** one EC2 instance runs Nginx, which serves the React build and proxies `/api` to Uvicorn managed by systemd, with a free Let's Encrypt certificate. It stays always-on, with no cold starts.
- **Netlify + Render:** the frontend on Netlify (`Base directory: frontend`, `Publish: frontend/dist`) and the backend on Render. Add a `_redirects` file containing `/*  /index.html  200` for React Router.

For any host: set `VITE_API_BASE_URL` to the backend's `/api` URL, set `VITE_USE_MOCKS=false`, and set the backend's `CORS_ORIGINS` to the exact frontend origin.

</details>

---

## 🔐 Security

- 🔑 **JWT with refresh-token separation.** Refresh tokens carry no role claims, so permissions are always re-checked against the database. A deactivated or demoted account can't refresh its way back in.
- 🚫 **No self-registered admins.** Public registration only accepts `PROVIDER`, `RECIPIENT`, and `RESCUE_PARTNER`.
- 🛑 **Weak secrets can't ship.** In staging or production the app refuses to start with a placeholder or short `JWT_SECRET`.
- 🧑‍⚖️ **Ownership enforced in the service layer.** Only a resource's own provider (or an admin) can edit, delete, or analyze it.
- 🖼️ **Hardened uploads.** Magic-byte sniffing, a size cap, and a strict file-id regex that blocks path traversal.
- 🗃️ **No raw SQL.** Every query goes through the ORM. Passwords are bcrypt-hashed, and no hashes or secrets appear in responses or logs.
- 🙈 **Secrets stay out of Git.** `.env` is git-ignored. Use `.env.example` as the template.

---

## 🛣️ Known limitations & roadmap

**Known limitations**

- No rate limiting or lockout on `/api/auth/login` and `/api/auth/register`. Add one (for example `slowapi` or a reverse-proxy limiter) before a real production launch.
- Travel ETAs are an offline distance-based estimate, not real road routing.
- Analytics sum quantities as recorded, so mixed units (meals, kg) are added together.

**Roadmap ideas**

- [ ] Login and registration rate limiting
- [ ] Real routing and ETA integration
- [ ] Unit-aware quantity normalisation
- [ ] Live operation tracking with driver location updates
- [ ] Multilingual UI
- [ ] Mobile-first PWA for rescue partners

<!--
📸 Screenshots: add images to docs/screenshots/ and uncomment.

## 📸 Screenshots
| Dashboard | Matching | Network map |
|---|---|---|
| ![](docs/screenshots/dashboard.png) | ![](docs/screenshots/matching.png) | ![](docs/screenshots/network.png) |
-->

---

<div align="center">

### 💜 Built so that good food and vital supplies reach people, not landfills.

**⭐ Star this repo if ReServe made you think.**

<sub>Made with FastAPI, React, and a stubborn belief that surplus should never be waste.</sub>

<img src="https://capsule-render.vercel.app/api?type=waving&color=gradient&customColorList=6,11,20&height=120&section=footer" alt="" />

</div>
