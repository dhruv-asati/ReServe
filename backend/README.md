# ReServe Backend

AI-powered resource redistribution & rescue network — backend API only.
Built with FastAPI + SQLAlchemy + PostgreSQL (Supabase-compatible).

This README covers local setup, environment variables, and authentication/roles.
For the full endpoint reference, run the server and open **`/docs`** (Swagger UI) —
every endpoint there has a summary and description, grouped by feature area.

## Contents

- [Requirements](#requirements)
- [Installation & running locally](#installation--running-locally)
- [Environment variables](#environment-variables)
- [Authentication & roles](#authentication--roles)
- [Analytics](#analytics)
- [API documentation (Swagger)](#api-documentation-swagger)
- [Project structure](#project-structure)
- [Tests](#tests)

## Requirements

- Python 3.10+
- A PostgreSQL database (a local Postgres instance, or a free [Supabase](https://supabase.com) project)

## Installation & running locally

1. **Clone the repo and move into the backend folder**

   ```bash
   cd backend
   ```

2. **Create and activate a virtual environment**

   ```bash
   python3 -m venv venv
   source venv/bin/activate      # Windows: venv\Scripts\activate
   ```

3. **Install dependencies**

   ```bash
   pip install -r requirements.txt
   ```

4. **Configure environment variables**

   ```bash
   cp .env.example .env
   ```

   Then edit `.env` — at minimum set `DATABASE_URL` and `JWT_SECRET`.
   See [Environment variables](#environment-variables) below for what each one does.

5. **Run database migrations**

   ```bash
   alembic upgrade head
   ```

   Optionally verify every expected table was created:

   ```bash
   python3 scripts/verify_tables.py
   ```

6. **Start the API**

   ```bash
   uvicorn app.main:app --reload
   ```

   The API is now running at `http://localhost:8000`. Open
   `http://localhost:8000/docs` for interactive Swagger UI, or
   `http://localhost:8000/api/health` to confirm the server and database are up.

## Demo preparation

Before a live demo, seed the database with sample data:

```bash
python3 scripts/seed_demo_data.py
```

This creates a full set of demo accounts (admin, 3 providers, 3 recipients, 2
rescue partners), sample resources across every status, and several rescue
operations — including the flagship **80-meal rescue scenario**: a single
80-meal hotel donation matched, allocated, and delivered across two
recipients and a night rescue hub in one truck run (NGO A: 50, Shelter B:
20, Night Rescue Hub: 10). It also leaves one resource `AVAILABLE` and
unmatched so you can trigger `POST /api/matching/{resource_id}` live during
the demo.

The script prints every demo account's email/role and the shared demo
password when it finishes — keep that output handy for logging in during
the demo. All seeded data is clearly labeled so it's never confused with
real data:

- Every demo user's email ends in `@demo.reserve.local`.
- Every demo organization/resource/hub name is prefixed `[DEMO]`.

It's safe to re-run at any time (e.g. right before the demo, to reset to a
clean state) — it deletes its own previously-seeded data first and never
touches non-demo data.

### Pre-demo checklist

1. `alembic upgrade head` has been run against the demo database.
2. `python3 scripts/verify_tables.py` reports no missing tables.
3. `python3 scripts/seed_demo_data.py` completes and prints the account summary.
4. `uvicorn app.main:app` starts with no errors, and `GET /api/health`
   returns `"database_connected": true`.
5. `/docs` loads and `POST /api/auth/login` with a seeded account (e.g.
   `provider.hotel@demo.reserve.local`) returns a token.

## Environment variables

All configuration is read from environment variables (via `.env` locally — see
`app/core/config.py`). `.env.example` documents every variable inline; the table
below is a quick-reference summary.

| Variable | Default | Purpose |
|---|---|---|
| `APP_NAME` | `ReServe API` | Shown as the title in Swagger UI. |
| `APP_VERSION` | `0.1.0` | Shown in Swagger UI and `/api/health`. |
| `ENVIRONMENT` | `development` | `development` \| `staging` \| `production`. Logged on startup. |
| `DEBUG` | `true` | Reserved for future use in debug-only behavior. |
| `DATABASE_URL` | `postgresql+psycopg2://postgres:postgres@localhost:5432/reserve_db` | PostgreSQL connection string. Works with any Postgres instance, including Supabase (direct or pooled connection — see comments in `.env.example`). `sslmode=require` is added automatically for Supabase hosts. |
| `JWT_SECRET` | `CHANGE_ME_IN_PRODUCTION` | Secret used to sign/verify JWTs. **Must** be changed to a long random value outside local dev. |
| `JWT_ALGORITHM` | `HS256` | JWT signing algorithm. |
| `JWT_ACCESS_TOKEN_EXPIRE_MINUTES` | `1440` (24h) | Access token lifetime. |
| `JWT_REFRESH_TOKEN_EXPIRE_MINUTES` | `10080` (7d) | Refresh token lifetime. |
| `GEMINI_API_KEY` | *(empty)* | API key for Google Gemini, used by `POST /api/resources/{id}/analyze`. |
| `GEMINI_MODEL` | `gemini-1.5-flash` | Gemini model used for resource analysis. |
| `GEMINI_TIMEOUT_SECONDS` | `20` | Per-request timeout for Gemini calls; fails fast (`504`) instead of hanging. |
| `SUPABASE_URL` | *(empty)* | Supabase project base URL, for Supabase Storage. Leave blank to use local-disk storage instead. |
| `SUPABASE_KEY` | *(empty)* | Supabase service/anon key. |
| `SUPABASE_STORAGE_BUCKET` | `resource-images` | Storage bucket resource images are uploaded to; must already exist with public read access. |
| `MAX_UPLOAD_FILE_SIZE_MB` | `5` | Max upload size, enforced for both storage backends. |
| `LOCAL_UPLOAD_DIR` | `uploads` | Where files are written when Supabase Storage isn't configured. |
| `PUBLIC_BASE_URL` | `http://localhost:8000` | Base URL used to build links to locally-stored uploads. |
| `CORS_ORIGINS` | `http://localhost:5173,http://127.0.0.1:5173,http://localhost:3000` | Comma-separated list of origins allowed to call the API from a browser. |
| `LOG_LEVEL` | `INFO` | Application log level. |

**Note on file storage:** if `SUPABASE_URL`/`SUPABASE_KEY` are left blank, uploads
are written to `LOCAL_UPLOAD_DIR` on disk and served back at `/static/uploads/...`.
This means uploads work out of the box with no Supabase project set up.

## Authentication & roles

Authentication is JWT-based (`python-jose`), with two token types issued from
the **Auth** endpoints:

- **Access token** — short-lived (`JWT_ACCESS_TOKEN_EXPIRE_MINUTES`, default 24h).
  Sent as `Authorization: Bearer <access_token>` on every protected request.
- **Refresh token** — long-lived (`JWT_REFRESH_TOKEN_EXPIRE_MINUTES`, default 7d).
  Exchanged for a new token pair via `POST /api/auth/refresh` without logging in
  again. It carries no role claims, so a user's permissions are always re-checked
  against the database when it's used — a deactivated or role-changed account
  can't refresh its way back into old permissions.

**Typical flow:**

1. `POST /api/auth/register` — create an account with a `role`.
2. `POST /api/auth/login` — get back `access_token` + `refresh_token`.
3. Call any protected endpoint with `Authorization: Bearer <access_token>`.
   In Swagger UI: click **Authorize** and paste the access token.
4. When the access token expires, `POST /api/auth/refresh` with the refresh
   token to get a new pair.

### Roles

Every account has exactly one role (`app/models/enums.py: UserRole`). `POST
/api/auth/register` only accepts `PROVIDER`, `RECIPIENT`, or `RESCUE_PARTNER` —
`ADMIN` accounts cannot be self-registered and must be created directly in the
database (or by promoting an existing user), so a public request can never
grant itself platform-admin access:

| Role | Represents |
|---|---|
| `PROVIDER` | An org/business posting surplus resources (food, medical supplies). |
| `RECIPIENT` | An org that requests and receives resources. |
| `RESCUE_PARTNER` | An org that handles pickup/delivery logistics. |
| `ADMIN` | Platform administrator — full access everywhere. |

`ADMIN` can do everything below in addition to what's listed; it's omitted
from the "Allowed roles" column for brevity except where it's the *only*
allowed role.

| Area | Rule | Enforced by |
|---|---|---|
| Register / Login / Refresh / `GET /me` | Any authenticated (or anonymous, for register/login) user. | `app/api/auth.py` |
| Create a resource | `PROVIDER` (+ `ADMIN`). | `require_roles` dependency |
| Edit / delete / analyze a resource | Only that resource's own `PROVIDER`, or `ADMIN`. | Service-layer ownership check |
| Upload/delete a resource image | `PROVIDER` (+ `ADMIN`). | `require_roles` dependency |
| Create a recipient profile | `RECIPIENT` (+ `ADMIN`). | `require_roles` dependency |
| Verify a recipient / rescue-partner profile | `ADMIN` only. | Service-layer check |
| Create a resource request | `RECIPIENT` (+ `ADMIN`). | `require_roles` dependency |
| Accept/decline a resource request | The resource's own `PROVIDER`, or `ADMIN`. | Service-layer check |
| Create a rescue-partner profile | `RESCUE_PARTNER` (+ `ADMIN`). | `require_roles` dependency |
| Update operation/allocation status | The resource's own `PROVIDER`, the assigned `RESCUE_PARTNER`, or `ADMIN`. | Service-layer check |
| View/update another user's account | Only `ADMIN` (users can always view/update their own). | Service-layer check |
| Notifications | Only the notification's own recipient, or `ADMIN`. | Service-layer check |
| All `/api/admin/*` endpoints | `ADMIN` only. | `require_roles` dependency |

A request from an authenticated user without the required role gets
`403 FORBIDDEN_ROLE`; a missing/invalid/expired token gets `401`.

## Analytics

Read-only, platform-wide endpoints (plus one notification-only write, below). Every figure is computed fresh
from real aggregate queries on each call — no caching, no sampling, and
no estimates. They require authentication but no particular role,
the same as viewing resources or operations, and none of them can
influence matching, allocation, or any resource's status.

| Endpoint | What it answers |
| --- | --- |
| `GET /api/analytics/overview` | Where does the platform stand right now? |
| `GET /api/analytics/trends` | How has activity moved day by day? |
| `GET /api/analytics/resource-types` | How does FOOD compare with MEDICAL? |
| `GET /api/analytics/insights` | Weekly supply vs. demand, allocation outcomes, matching time, deadline performance, operation outcomes |
| `GET /api/analytics/surplus-forecast` | Recent daily food surplus, and the hour of day it usually appears in |
| `POST /api/analytics/surplus-alert` | Notify available rescue partners about the predicted window (the one endpoint here that writes — notifications only) |

### `GET /api/analytics/overview`

Current-state snapshot: total resources posted, how many are `AVAILABLE`
and `ALLOCATED`, how many operations are `COMPLETED` and `PLANNED`
(pending), and `total_quantity_rescued` — the sum of `allocated_quantity`
across every `DELIVERED` allocation, i.e. quantity that actually reached
a recipient or rescue hub, not merely committed.

### `GET /api/analytics/trends`

Basic day-by-day resource and operation activity.

```
GET /api/analytics/trends?days=14
```

`days` defaults to **14** and accepts **1–90**; anything outside that
range is rejected with `422`. The window counts back from today
inclusive.

Each entry in `daily` reports, for one calendar day:

| Field | Meaning |
| --- | --- |
| `resources_posted` / `quantity_posted` | Resources created that day, by `Resource.created_at` |
| `operations_started` | Operations created that day, by `RescueOperation.created_at` |
| `operations_completed` | Operations that reached `COMPLETED`, by `completed_at` |
| `quantity_delivered` | `DELIVERED` allocations whose operation was marked delivered that day |

Notes worth knowing before you chart it:

- **Every day in the window is present**, zero-filled. There are no gaps
  to patch client-side, and `daily` always has exactly `window_days`
  entries, oldest first.
- **Days are bucketed in UTC explicitly**, not by casting timestamps in
  whatever timezone the database session happens to be set to — so the
  same row always lands in the same bucket regardless of server config.
- **`quantity_delivered` is keyed off `RescueOperation.delivered_at`.**
  An `Allocation` has no delivery timestamp of its own, so an allocation
  not linked to an operation has no date to bucket by and is not counted
  here — even though it still counts toward the overview's
  `total_quantity_rescued`. The two figures are allowed to differ for
  that reason.
- **Quantities are summed as recorded**, so mixed units (meals, kg)
  are added together.

### `GET /api/analytics/resource-types`

Per-type breakdown. For each `ResourceType` (`FOOD`, `MEDICAL`):
`resource_count`, `total_quantity`, `share_percent` (of all resources by
count), the current `available_count` / `allocated_count` /
`delivered_count`, and `quantity_rescued` — using the same "`DELIVERED`
allocations only" definition as the overview endpoint, joined back to
each allocation's resource.

**Every type is always listed**, zero-filled when nothing of that type
exists yet, so a client rendering FOOD and MEDICAL side by side never has
to handle a missing key — and a type with nothing posted reads as a real
zero rather than as absent data.

### `GET /api/analytics/insights`

Feeds the Analytics page's weekly and outcome charts in one call. `weeks`
(default 4, max 12) sets the window; weeks start on Monday (UTC) and the
last one is the current, still-in-progress week. Returns, per week,
supply vs. demand quantity, delivered vs. cancelled allocations, average
matching time (rescue request created → first allocation) and completed
vs. at-risk operations, plus window totals for deadline performance
(arrived on time / late / no deadline recorded) and operation completion
(completed / in progress / failed). Weeks with nothing to average report
`avg_minutes: null`, never `0`. See `app/services/analytics_logic.py` for
the exact definitions (an operation is judged against its rescue
request's deadline, falling back to the resource's `expiry_time`).

### `GET /api/analytics/surplus-forecast` and `POST /api/analytics/surplus-alert`

The forecast returns the last 7 days of FOOD surplus (by
`available_time`, else `created_at`) and, **only when the history
supports one**, `prediction`: the local hour of day in which surplus
appeared on at least 3 different days of the last 28, with the smallest
and largest per-day amount seen. Pass the browser's UTC offset as
`tz_offset_minutes` (e.g. `330` for India). With too little history
`prediction` is `null` — there is no demo fallback.

The alert re-computes that forecast server-side (409
`NO_SURPLUS_FORECAST` when there is none) and creates a real in-app
notification (plus an email if SMTP is configured) for each active,
available, food-accepting rescue partner other than the caller. If the
caller has a saved location, only partners within their own
`service_radius_km` (default 25 km) are alerted (`scope: "nearby"`);
otherwise every available partner is (`scope: "all_available"`). Partners
alerted within the last hour are skipped. `partners_notified` is the true
count and is `0` when there is nobody to notify. Requires the `PROVIDER`,
`RESCUE_PARTNER` or `ADMIN` role.

### Analytics vs. predictions

`/api/analytics/*` and `/api/predictions` behave differently on a quiet
database, and the difference is deliberate:

- **Analytics never fabricates anything.** An empty database returns
  zeros.
- **`GET /api/predictions` substitutes clearly-labelled demo data** when
  there isn't enough recorded activity to forecast from, flagged by
  `is_demo: true` and `data_source: "DEMO"`.

Don't read a zero from analytics as "not enough data" — it means exactly
zero.

## API documentation (Swagger)

With the server running, interactive docs are available at:

- **Swagger UI:** `http://localhost:8000/docs`
- **ReDoc:** `http://localhost:8000/redoc`
- **Raw OpenAPI schema:** `http://localhost:8000/openapi.json`

Endpoints are grouped into tags matching the feature areas below (see
`app/main.py` for the tag descriptions shown in Swagger UI):

`Health` · `Auth` · `Users` · `Resources` · `Uploads` · `Recipients` ·
`Rescue Partners` · `Resource Requests` · `Matching` · `Allocations` ·
`Operations` · `Analytics` · `Predictions` · `Notifications` · `Admin`

Every endpoint has a `summary` (one line) and `description` (full detail,
including which role(s) can call it) visible in Swagger UI — expand any
endpoint there for specifics rather than reading route code directly.

All responses use one consistent JSON envelope:

```jsonc
// Success
{ "success": true, "data": { ... }, "message": "..." }

// Error
{ "success": false, "error": { "code": "...", "message": "..." } }
```

## Project structure

```
backend/
├── app/
│   ├── api/          # FastAPI routers (one file per feature area)
│   ├── core/          # config, security (JWT/password hashing), auth deps, error types
│   ├── db/            # SQLAlchemy engine/session setup
│   ├── models/        # SQLAlchemy models + shared enums
│   ├── schemas/        # Pydantic request/response schemas
│   ├── services/       # Business logic, called from the routers
│   ├── utils/
│   └── main.py         # App wiring: CORS, error handlers, router mounting
├── alembic/            # Database migrations
├── scripts/            # One-off operational scripts (e.g. verify_tables.py)
├── tests/              # Pytest test suite
├── .env.example
├── alembic.ini
└── requirements.txt
```

## Security notes

A basic security review covered JWT auth, role-based permissions, resource
ownership, API-key protection, input validation, and sensitive-data exposure.
Findings:

- **Fixed — privilege escalation at registration.** `POST /api/auth/register`
  previously accepted `role: ADMIN` from any unauthenticated caller, letting
  anyone create a full-admin account. Self-registration is now restricted to
  `PROVIDER`, `RECIPIENT`, and `RESCUE_PARTNER`.
- **Fixed — weak JWT secret could reach production.** `JWT_SECRET` had a
  hardcoded placeholder default (`CHANGE_ME_IN_PRODUCTION`) with nothing
  stopping the app from actually running with it. `Settings` now refuses to
  start when `ENVIRONMENT` is `staging`/`production` and `JWT_SECRET` is
  still the placeholder or under 32 characters, so a forgeable secret can't
  silently ship.
- **Fixed — no `.gitignore`.** The repo had no `.gitignore` at all, so a
  real `.env` (JWT secret, DB credentials, Gemini/Supabase keys) could easily
  be committed by accident. Added one that excludes `.env`, local uploads,
  and other generated files.
- **Reviewed, already solid:** password hashing (bcrypt via `passlib`),
  access/refresh token separation and type-checking, ownership checks on
  resources/uploads/requests/profiles (service-layer, consistent across
  routes), upload validation (magic-byte sniffing + size cap + a strict
  file-id regex that blocks path traversal), no raw SQL (all queries go
  through the ORM), and no password hashes or secrets in any API response
  or log line.
- **Not fixed (out of scope — would be a new feature):** there's no
  rate-limiting/lockout on `/api/auth/login` or `/api/auth/register`, so
  brute-force and credential-stuffing attempts aren't throttled. Worth
  adding (e.g. via a reverse-proxy rate limiter or `slowapi`) before a real
  production deployment.

## Tests

The suite runs against a **real PostgreSQL database**. SQLite is not a
supported test backend — the models use Postgres-specific column types
(native `ENUM`, `UUID`), so the schema will not build on SQLite.

Point `DATABASE_URL` at a throwaway database before running; everything
in it will be dropped and truncated:

```bash
createdb reserve_test
export DATABASE_URL=postgresql+psycopg2://postgres:postgres@localhost:5432/reserve_test
pytest -v
```

If `DATABASE_URL` is unset, `tests/conftest.py` falls back to
`postgresql+psycopg2://postgres:postgres@localhost:5432/reserve_test`.

Fixture behaviour (`tests/conftest.py`):

- Tables are created once per session and dropped at the end.
- Every table is `TRUNCATE ... RESTART IDENTITY CASCADE`'d between tests,
  so tests can run in any order without leaking state.
- `client` overrides the `get_db` dependency so the app and the test both
  use the same session.
- The `make_*` factory helpers take keyword overrides for any field —
  e.g. `make_resource(db, provider, quantity=200, category="bakery")`.

Migrations are **not** applied by the test suite; it builds the schema
straight from the models via `Base.metadata.create_all`. Verify
migrations separately against a scratch database:

```bash
alembic upgrade head
alembic check          # should report no new operations
```
