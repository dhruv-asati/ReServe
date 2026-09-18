# ReServe Backend — Stages 1-4: Foundation + Models + Auth + Resources

AI-Powered Resource Redistribution & Rescue Network.

**Stage 1** set up the project skeleton, DB connection, CORS, health check,
logging, and Swagger docs.

**Stage 2** added all 12 SQLAlchemy models, Postgres enum types,
relationships, constraints, and the initial Alembic migration.

**Stage 3** added authentication: register / login / current user, bcrypt
password hashing, JWT issuing + verification, and role-protected endpoint
dependencies.

**Stage 4** adds resource management: full CRUD for FOOD and MEDICAL
surplus resources, owner-based permissions, and role restrictions on top
of Stage 3's auth. No new migration needed — the `Resource` table from
Stage 2 already had every field this stage uses.

**Profile management** adds `GET /api/users/me`, `PUT /api/users/me`, and
`GET /api/users/{user_id}`, so any authenticated user can view and edit
their own profile — name, phone, organization name/description, profile
image URL, address, and latitude/longitude. Migration `8f1c2a4e9b3d` adds
the six new columns to `users`.

**File uploads** adds `POST /api/uploads/resource-image` and
`DELETE /api/uploads/{file_id}`, backed by Supabase Storage when
configured, falling back automatically to local disk otherwise so uploads
work in local development with no Supabase project set up at all. No new
migration — `resources.image_url` already existed from an earlier update.

**Gemini AI analysis** (this update) adds
`POST /api/resources/{resource_id}/analyze`: a reusable Gemini service
(`app/services/gemini_service.py`) that turns a resource's freeform
fields into a strict, structured analysis — category/subtype, extracted
quantity, urgency, a recommended rescue window, notable attributes,
storage requirements, eligibility notes, warnings, and a confidence
score — stored in `ai_analysis` (see §8's "AI analysis" section). No new
migration — `resources.ai_analysis` already existed as a JSON column.
Gemini only analyzes and structures information; it never makes or
implies an allocation decision, and the tests mock it entirely so the
suite needs no `GEMINI_API_KEY` or network access to run.

## Project structure

```
reserve-backend/
  app/
    main.py                  # FastAPI app, CORS, error handlers, router wiring
    api/
      health.py               # GET /api/health
      auth.py                  # POST /register, POST /login, GET /me
      users.py                  # GET/PUT /api/users/me, GET /api/users/{id}
      resources.py              # Resource CRUD
      recipients.py              # Recipient CRUD
      rescue_partners.py          # Rescue partner CRUD
    core/
      config.py                # Pydantic Settings (reads .env)
      logging_config.py        # Logging setup
      security.py               # Password hashing + JWT create/decode
      errors.py                 # AppError — consistent business-error type
      deps.py                    # get_current_user, require_roles(...)
    db/
      database.py              # SQLAlchemy engine, session, Base
    models/
      enums.py                  # All Postgres/Python enums (roles, statuses, types)
      mixins.py                 # UUIDPrimaryKeyMixin, TimestampMixin
      user.py
      resource.py
      recipient.py
      rescue_partner.py
      rescue_hub.py
      rescue_request.py
      match.py
      allocation.py
      operation.py               # RescueOperation + OperationEvent
      notification.py
      prediction.py
    schemas/
      common.py                 # Shared success/error response envelope
      auth.py                    # RegisterRequest, LoginRequest, UserPublic, TokenData
      resource.py                 # ResourceCreate, ResourceUpdate, ResourceOut, ResourceListData
      recipient.py                 # RecipientCreate, RecipientUpdate, RecipientOut, RecipientListData
      rescue_partner.py             # PartnerCreate, PartnerUpdate, PartnerOut, PartnerListData
      analysis.py                  # ResourceAnalysis, ResourceAnalysisResult (Gemini output schema)
    services/                   # (empty — future stages)
      auth_service.py            # register_user, authenticate_user
      resource_service.py         # Resource CRUD + ownership/status rules + analyze_resource
      recipient_service.py         # Recipient CRUD + ownership/verification rules
      rescue_partner_service.py     # Rescue partner CRUD + ownership/verification rules
      gemini_service.py            # Reusable Gemini client: prompt building, call, validation
    utils/                       # (empty)
  alembic/
    env.py                       # Wired to Settings.DATABASE_URL + Base.metadata
    script.py.mako
    versions/
      34a01cac6ded_initial_models.py  # Creates all 12 tables + enums
  alembic.ini
  scripts/
    verify_tables.py             # Confirms every expected table exists
  requirements.txt
  .env.example
  .gitignore
```

## Data model overview

| Model             | Purpose                                                                 |
|--------------------|--------------------------------------------------------------------------|
| `User`             | Login identity for all roles: PROVIDER, RECIPIENT, RESCUE_PARTNER, ADMIN |
| `Resource`         | Surplus (FOOD/MEDICAL) posted by a provider, with quantity/urgency/expiry/location |
| `Recipient`        | NGO/shelter/etc. profile (1:1 with a RECIPIENT user), capacity + availability |
| `RescuePartner`    | Volunteer/transport profile (1:1 with a RESCUE_PARTNER user), capacity + availability |
| `RescueHub`        | Fallback drop point (e.g. night hub) when normal recipients are unavailable |
| `RescueRequest`    | The coordination record the matching engine operates on, created per Resource |
| `Match`            | Every candidate (Recipient or RescueHub) the engine considered, with a score + machine-readable `reasons` JSON |
| `Allocation`       | A confirmed quantity committed to one recipient/hub — what reallocation creates/cancels |
| `RescueOperation`  | End-to-end execution of a RescueRequest: partner + status lifecycle + its allocations |
| `OperationEvent`   | Append-only audit log per operation (status changes, reallocation old/new state) |
| `Notification`     | Per-user notification tied optionally to an operation |
| `Prediction`       | Seeded/demo surplus forecast, always flagged `is_simulated=True` for the hackathon |

Key relationships: `User` 1—1 `Recipient`/`RescuePartner` (via role-specific
profile tables), `User` 1—N `Resource` (as provider), `Resource` 1—N
`RescueRequest`, `RescueRequest` 1—N `Match` and 1—N `Allocation` and 1—1
`RescueOperation`, `RescueOperation` 1—N `Allocation` and 1—N
`OperationEvent`. `Match` and `Allocation` each point to **either** a
`Recipient` **or** a `RescueHub`, enforced with a Postgres `CHECK`
constraint (`..._target_xor`) — never both, never neither.

All primary keys are UUIDs (generated client-side via `uuid.uuid4()`), so
IDs are safe to expose in URLs without leaking row counts.

**Design assumption (please confirm):** `latitude`/`longitude` fields were
added as plain nullable floats on `Resource`, `Recipient`, `RescuePartner`
(current position), and `RescueHub` — no distance calculation logic exists
yet at the model layer. This keeps the schema ready for either a real
haversine calculation or a simplified distance model once the matching
engine (Stage 7) is built, without a schema change either way.

## 1. Prerequisites

- Python 3.11+ (3.12 recommended)
- A Supabase project (or any PostgreSQL 14+ instance — the code works with
  either, but the steps below assume Supabase)

### Setting up Supabase

1. **Create a project**: go to [supabase.com](https://supabase.com), sign
   in, click **New project**, pick an organization, name it (e.g.
   `reserve`), set a strong **database password** (save it — you'll need
   it for `DATABASE_URL`), pick a region close to you, and click
   **Create new project**. Takes 1-2 minutes to provision.
2. **Get the database connection string**: in your project, go to
   **Project Settings** (gear icon) -> **Database** -> **Connection
   string** -> select the **URI** tab. Copy it. It looks like:
   `postgresql://postgres:[YOUR-PASSWORD]@db.xxxxxxxx.supabase.co:5432/postgres`
   Replace `[YOUR-PASSWORD]` with your actual database password.
3. **Get the Supabase URL and API key**: go to **Project Settings** ->
   **API**. `Project URL` is your `SUPABASE_URL`; the `anon` `public` key
   under **Project API keys** is your `SUPABASE_KEY`. Not needed until
   Stage 5+ (file storage) — fine to leave blank for now.

## 2. Install

```bash
cd reserve-backend

# Create and activate a virtual environment
python3 -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

## 3. Configure environment variables

```bash
cp .env.example .env
```

Then edit `.env`:

| Variable | What to put | Can it stay empty for now? |
|---|---|---|
| `DATABASE_URL` | Your Supabase connection string from step 1.2 above, with `postgresql://` changed to `postgresql+psycopg2://` and `[YOUR-PASSWORD]` replaced with your real password | No |
| `JWT_SECRET` | Any long random string, e.g. output of `python3 -c "import secrets; print(secrets.token_hex(32))"` | No |
| `JWT_ALGORITHM`, `JWT_ACCESS_TOKEN_EXPIRE_MINUTES` | Leave the defaults | No (defaults are fine) |
| `GEMINI_API_KEY` | — | Yes, until Stage 5 |
| `SUPABASE_URL`, `SUPABASE_KEY` | Your project URL / anon key from step 1.3 above | Yes, until file storage is built (Stage 5+) |
| `CORS_ORIGINS`, `LOG_LEVEL`, everything under General | Leave the defaults | Yes |

The backend automatically adds `sslmode=require` to Supabase connection
strings if you forget it — Supabase requires SSL, so this avoids a common
"connection refused"-looking error.

Never commit your real `.env` file — `.gitignore` already excludes it.

## 4. Run the server

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

You should see log output like:

```
2026-09-17 12:00:00 | INFO     | app.main | ReServe API v0.1.0 starting up in 'development' mode.
2026-09-17 12:00:00 | INFO     | app.main | CORS origins allowed: ['http://localhost:5173', 'http://localhost:3000']
INFO:     Uvicorn running on http://0.0.0.0:8000
```

## 5. Verify it works

**Health check:**

```bash
curl http://localhost:8000/api/health
```

Expected response:

```json
{
  "success": true,
  "data": {
    "status": "ok",
    "environment": "development",
    "version": "0.1.0",
    "database_connected": true
  },
  "message": "ReServe API is running."
}
```

If `database_connected` is `false`, the server itself is still up and
`/api/health` still returns `200 OK` — it just means Postgres isn't
reachable with the current `DATABASE_URL`. Check that Postgres is running
and the credentials/host/port in `.env` are correct.

**Swagger UI (interactive docs):**

Open in a browser: `http://localhost:8000/docs`

**ReDoc (alternative docs view):**

Open in a browser: `http://localhost:8000/redoc`

**Raw OpenAPI schema:**

`http://localhost:8000/openapi.json`

## 6. Run the migration and verify the tables

`alembic upgrade head` now runs the full chain of migrations added across
every stage so far — the initial 12-table schema, user profile fields,
resource image/available-time fields, food-specific resource fields, and
(this stage) recipient/rescue-partner profile fields. With your `.env`
pointing at a real Postgres database:

```bash
alembic upgrade head
```

Expected output ends with something like:

```
INFO  [alembic.runtime.migration] Running upgrade  -> 34a01cac6ded, initial models
```

**Verify all tables were created** — either via the included script:

```bash
python3 scripts/verify_tables.py
```

which prints an OK/MISSING line per table and exits non-zero if anything's
missing, or manually via `psql`:

```bash
psql "$DATABASE_URL" -c "\dt"
```

You should see all 12 tables: `users`, `resources`, `recipients`,
`rescue_partners`, `rescue_hubs`, `rescue_requests`, `matches`,
`allocations`, `rescue_operations`, `operation_events`, `notifications`,
`predictions` (plus Alembic's own `alembic_version` bookkeeping table).

You can also just open the **Table Editor** in your Supabase project
dashboard and see the same tables listed there — no `psql` required.

To confirm the enum types were created too:

```bash
psql "$DATABASE_URL" -c "\dT"
```

**Rolling back**, if needed:

```bash
alembic downgrade base
```

**Future migrations** — once you add or change a model, this same
workflow generates the diff automatically (the hand-authored initial
migration above was written to match the models exactly, so autogenerate
should produce an empty/near-empty diff right now):

```bash
alembic revision --autogenerate -m "describe your change"
alembic upgrade head
```

## 7. Authentication

Four endpoints, all under `/api/auth`:

| Method | Path | Auth required? | Purpose |
|---|---|---|---|
| POST | `/api/auth/register` | No | Create an account with a role (`PROVIDER`, `RECIPIENT`, `RESCUE_PARTNER`, `ADMIN`) |
| POST | `/api/auth/login` | No | Exchange email + password for an access token + refresh token |
| GET | `/api/auth/me` | Yes (access token) | Return the profile of whoever the token belongs to |
| POST | `/api/auth/refresh` | No (needs a refresh token in the body instead) | Exchange a refresh token for a new access/refresh pair |

- Passwords are hashed with **bcrypt** (via `passlib`) — plaintext is
  never stored, never logged.
- Tokens are signed **JWTs** (via `python-jose`). Every token carries a
  `type` claim (`"access"` or `"refresh"`) so the two can never be used
  interchangeably — e.g. `GET /api/auth/me` rejects a refresh token even
  if it's otherwise valid, and `/api/auth/refresh` rejects an access
  token.
- **Access tokens** expire after `JWT_ACCESS_TOKEN_EXPIRE_MINUTES`
  (default 24h) and carry the user's id + role, so most requests don't
  need a DB round trip to check the role.
- **Refresh tokens** expire after `JWT_REFRESH_TOKEN_EXPIRE_MINUTES`
  (default 7 days) and carry no role — `/refresh` always re-fetches the
  user from the database before minting a new access token, so a stale
  refresh token can't "lock in" a role or active-status the user no
  longer has. Each call to `/refresh` returns a new refresh token too;
  worth knowing this is stateless JWT rotation (no server-side token
  store), so the old refresh token isn't force-invalidated, only meant to
  be discarded by a well-behaved client — see the docstring in
  `auth_service.refresh_access_token` for the honest limitation and what
  true revocation would need.
- `app/core/deps.py` exposes `get_current_user` (any logged-in user) and
  `require_roles(UserRole.PROVIDER, ...)` (restrict to specific roles) —
  the resource endpoints (§8) already use these, and later stages'
  matching/operations endpoints will too.
- Every response — success or error — uses the same envelope. Errors
  raised as `AppError` (e.g. duplicate email, wrong password, expired
  token, wrong role) come back as
  `{"success": false, "error": {"code": "...", "message": "..."}}`
  with an appropriate status code (401, 403, 409, etc.), not a generic 500.

### Testing in Swagger

1. Start the server (`uvicorn app.main:app --reload`) and open
   `http://localhost:8000/docs`.

**1. Register a user**

2. Expand `POST /api/auth/register` -> **Try it out** -> use the
   pre-filled example body (or your own), e.g.:
   ```json
   {
     "email": "hotel.manager@example.com",
     "password": "strongpassword123",
     "full_name": "Asha Rao",
     "phone": "+91-9876543210",
     "role": "PROVIDER"
   }
   ```
   **Execute**. Expect `201` and the new user's public profile (no
   password hash in the response).
3. Execute the exact same request again — expect
   `409 EMAIL_ALREADY_REGISTERED`, confirming duplicate emails are
   blocked.
4. Register one or two more users with different emails and
   `"role": "RECIPIENT"` / `"RESCUE_PARTNER"` / `"ADMIN"` — you'll want
   at least one non-PROVIDER account for the role-restriction test below.

**2. Log in**

5. Expand `POST /api/auth/login` -> **Try it out** -> the first user's
   email/password -> **Execute**. Expect `200` with `access_token`,
   `refresh_token`, and the user's profile. Copy both tokens. Try a wrong
   password — expect `401 INVALID_CREDENTIALS`.

**3. Access /api/auth/me**

6. Click the green **Authorize** button (top right), paste the
   `access_token` into the value field (no `Bearer` prefix needed —
   Swagger adds it), **Authorize**, then **Close**.
7. Expand `GET /api/auth/me` -> **Try it out** -> **Execute**. Expect
   `200` with the same user's profile back.

**4. Test an unauthorized request**

8. Click **Authorize** again -> **Logout** -> **Close** (this clears the
   token Swagger sends). Call `GET /api/auth/me` again — expect
   `401 NOT_AUTHENTICATED`.
9. Re-**Authorize** with the access token again, then try
   `POST /api/auth/refresh` with that *access* token pasted into the
   `refresh_token` field of the request body (not the Authorize field) —
   expect `401 INVALID_REFRESH_TOKEN`, confirming an access token can't
   be used as a refresh token.
10. Now call `POST /api/auth/refresh` correctly — body
    `{"refresh_token": "<the real refresh_token from step 5>"}` —
    expect `200` with a new `access_token` and `refresh_token`.
    Re-Authorize Swagger with the new access token and confirm
    `GET /api/auth/me` still works.

**5. Test role restrictions**

11. This is easiest to see against the resource endpoints from §8, since
    `/api/auth/*` itself has no role-restricted routes. **Authorize**
    with the PROVIDER's access token and call `POST /api/resources`
    (§8 step 1) — expect `201`.
12. Log in as the RECIPIENT (or RESCUE_PARTNER) account from step 4,
    re-Authorize with *their* access token, and call
    `POST /api/resources` again with the same body — expect
    `403 FORBIDDEN_ROLE`, confirming role-based permission dependencies
    are enforced, not just authentication.

## 8. Resource management

Six endpoints, all under `/api/resources`, all requiring authentication:

| Method | Path | Who can call it |
|---|---|---|
| POST | `/api/resources` | PROVIDER or ADMIN |
| GET | `/api/resources` | Any authenticated user |
| GET | `/api/resources/{id}` | Any authenticated user |
| PUT | `/api/resources/{id}` | The resource's own provider, or ADMIN |
| DELETE | `/api/resources/{id}` | The resource's own provider, or ADMIN |
| POST | `/api/resources/{id}/analyze` | The resource's own provider, or ADMIN |

Notes on behavior:

- `resource_type` is `FOOD` or `MEDICAL`. Posting a `MEDICAL` resource
  automatically forces `requires_medical_verification: true`, regardless
  of what you send — the stricter check the spec calls for isn't
  optional.
- `provider_id` is never taken from the request body — it's always the
  logged-in user, so no one can post a resource under someone else's name.
- `GET /api/resources` supports filtering (`resource_type`, `status`,
  `provider_id`, or `mine=true` for "just my own resources") and
  pagination (`skip`, `limit`), returning `{items, total, skip, limit}`.
- `PUT` only allows `status` to move to `AVAILABLE` or `CANCELLED`
  directly — every other status (`MATCHING`, `ALLOCATED`, `IN_TRANSIT`,
  `DELIVERED`, `EXPIRED`) is set automatically once the matching/
  operations engine (Stages 7-8) exists, not by hand-editing a resource.
- Once a resource reaches `ALLOCATED`, `IN_TRANSIT`, or `DELIVERED`, both
  `PUT` and `DELETE` are locked (`409 RESOURCE_LOCKED`) — those states
  mean a recipient/partner already has commitments riding on the data.
- `DELETE` is a hard delete (cascades to any related rescue requests —
  harmless right now since nothing populates those tables until Stage 7).
- `image_url` (optional) and `available_time` (optional — when the
  resource actually becomes ready, distinct from `pickup_window_start`)
  are accepted on create/update and returned on every response.

### Testing the full CRUD flow in Swagger

Assumes you already have a `PROVIDER` account and are logged in (see
§7 above) with Swagger's **Authorize** button holding a valid token.

1. **Create**: `POST /api/resources` -> **Try it out** -> use one of the
   two pre-filled examples (FOOD or MEDICAL) -> **Execute**. Expect `201`
   with the full resource, including a generated `id` and
   `status: "AVAILABLE"`. For the MEDICAL example, confirm
   `requires_medical_verification` came back `true` even though the
   example didn't set it. Copy the `id` for the next steps.
2. **List**: `GET /api/resources` -> **Try it out** -> leave filters
   blank -> **Execute**. Expect `200` with your new resource inside
   `data.items`. Try again with `mine=true` — same result, filtered to
   just your resources. Try `resource_type=MEDICAL` — filtered
   accordingly.
3. **Get one**: `GET /api/resources/{resource_id}` -> paste the id from
   step 1 -> **Execute**. Expect `200` with that resource. Try a random
   UUID — expect `404 RESOURCE_NOT_FOUND`.
4. **Update**: `PUT /api/resources/{resource_id}` -> paste the id ->
   body `{"quantity": 60, "urgency": "CRITICAL"}` -> **Execute**. Expect
   `200` with the updated fields changed and everything else untouched.
   Try `{"status": "ALLOCATED"}` — expect `422` (rejected: not a
   client-settable status).
5. **Check ownership enforcement**: register a second account with a
   *different* email and role `RECIPIENT`, log in as them, click
   **Authorize**, swap in their token, then try `PUT` or `DELETE` on the
   first user's resource — expect `403 NOT_RESOURCE_OWNER`. Re-authorize
   back with the original provider's token afterward.
6. **Delete**: `DELETE /api/resources/{resource_id}` -> paste the id ->
   **Execute**. Expect `200`. Call `GET` on the same id again — expect
   `404`.
7. **Check role restriction on create**: log in as the `RECIPIENT`
   account from step 5, re-authorize with their token, try
   `POST /api/resources` — expect `403 FORBIDDEN_ROLE`.

### AI analysis (Gemini)

`POST /api/resources/{resource_id}/analyze` reads a resource's fields —
title, description, category, quantity/unit, dates, and (for FOOD)
`food_category`/`allergen_info`/`storage_requirements`/`packaging_info` —
and asks Gemini to return a strict, structured analysis: `resource_category`,
`resource_subtype`, `extracted_quantity` (Gemini's own parse of the
quantity, cross-checked against what you posted), `urgency_level`,
`rescue_window` (a recommended pickup-by window with reasoning),
`important_attributes`, `storage_requirements`, `eligibility_info`,
`warnings`, and a `confidence_score` (0-1). The result is stored in
`ai_analysis` and returned in every resource response from then on
(`GET`/`PUT`/create all include it). Re-running it simply overwrites the
previous result — there's no history kept of past analyses.

**Boundary that's enforced, not just documented:** Gemini only analyzes
and structures information here. It never decides allocation, matching,
or acceptance — the response schema (`ResourceAnalysis`) has no field
that could represent that kind of decision, the system prompt sent to
Gemini explicitly forbids it, and the service function that stores the
result only ever writes to `ai_analysis` — it never touches `status` or
creates a `RescueRequest`/`Match`/`Allocation`.

Setup:

- Requires `GEMINI_API_KEY` in `.env` (get one from
  [Google AI Studio](https://aistudio.google.com/apikey)). Without it,
  the endpoint returns `503 AI_ANALYSIS_NOT_CONFIGURED` rather than
  failing in some more confusing way.
- `GEMINI_MODEL` (default `gemini-1.5-flash`) and
  `GEMINI_TIMEOUT_SECONDS` (default `20`) are also configurable — see
  `.env.example`.
- The API key is only ever read server-side from the environment
  (`app/core/config.py`) — it's never included in any response, and
  nothing about it reaches the frontend.

Error handling: a Gemini timeout returns `504 AI_ANALYSIS_TIMEOUT`; any
other call failure (auth error, rate limit, model error) returns
`502 AI_ANALYSIS_FAILED`; a response that isn't valid JSON, or is JSON
but doesn't match the `ResourceAnalysis` schema (e.g. `confidence_score`
out of the 0-1 range), returns `502 AI_ANALYSIS_INVALID_RESPONSE`.
Failures are logged with the resource id and exception type only —
never the raw exception text or the prompt, since some Gemini SDK/
transport errors embed the request URL, which historically includes the
API key as a query parameter.

**Testing in Swagger** (needs a real `GEMINI_API_KEY` configured):

1. Using a resource id from the CRUD flow above, `POST
   /api/resources/{resource_id}/analyze` -> **Try it out** -> **Execute**
   (no request body). Expect `200` with `ai_analysis` populated —
   `analysis` (the structured fields above), `model`, and `analyzed_at`.
2. Create a second, `MEDICAL`-type resource (see §8 step 1) and analyze
   it too — expect a medical-appropriate `resource_category`/
   `resource_subtype` (e.g. "Pharmaceutical" / "Antibiotic") and
   `eligibility_info` filled in instead of `null`.
3. Call it again on the same resource — expect `200` with a fresh
   `analyzed_at` timestamp, overwriting the previous `ai_analysis`.
4. Re-authorize as a different provider and try analyzing the first
   provider's resource — expect `403 NOT_RESOURCE_OWNER`.
5. Temporarily blank out `GEMINI_API_KEY` in `.env` and restart the
   server, then try again — expect `503 AI_ANALYSIS_NOT_CONFIGURED`.

**Testing without a Gemini API key at all:** `tests/test_resource_analysis.py`
mocks Gemini entirely (`gemini_service.call_gemini_model` is monkeypatched
to return a canned JSON string), so the full request/response/error-handling
flow — including both a FOOD and a MEDICAL example — can be exercised with
`pytest` and no API key or network access:

```bash
export DATABASE_URL=postgresql+psycopg2://postgres:postgres@localhost:5432/reserve_test
pytest tests/test_resource_analysis.py -v
```

## 9. Profile management

Three endpoints, all under `/api/users`, all requiring authentication:

| Method | Path | Who can call it |
|---|---|---|
| GET | `/api/users/me` | Any authenticated user (their own profile) |
| PUT | `/api/users/me` | Any authenticated user (their own profile only) |
| GET | `/api/users/{user_id}` | The user themself, or ADMIN |

Editable fields (all optional on `PUT` — only what you send is changed):
`full_name`, `phone`, `organization_name`, `organization_description`,
`profile_image_url`, `address`, `latitude`, `longitude`.

Notes on behavior:

- There's no `user_id` in the `PUT /me` body or path — it's always taken
  from the logged-in token, so there's no way to edit someone else's
  profile by id.
- `GET /api/users/{user_id}` returns `403 FORBIDDEN` for a non-admin
  requesting anyone but themself.
- `phone` must look like a phone number (7-20 digits, optional leading
  `+`, spaces/hyphens allowed) — anything else is rejected with `422`.
- `profile_image_url` must be an `http://` or `https://` URL.
- `latitude`/`longitude` must be provided together (both or neither), and
  are range-checked (`-90..90`, `-180..180`).
- Responses (`UserProfileOut`) never include `hashed_password` or any
  other auth internals — the schema only lists the fields meant to be
  public, so nothing new added to the `User` model in the future can leak
  by accident.

### Testing in Swagger

Assumes you're already logged in (see §7) with Swagger's **Authorize**
button holding a valid access token.

1. **Get my profile**: `GET /api/users/me` -> **Try it out** ->
   **Execute**. Expect `200` with your profile — organization fields will
   be `null` until you set them.
2. **Update my profile**: `PUT /api/users/me` -> **Try it out** -> body
   e.g. `{"organization_name": "Grand Plaza Hotel", "address": "MG Road, Bengaluru", "latitude": 12.9716, "longitude": 77.5946}`
   -> **Execute**. Expect `200` with those fields updated and everything
   else unchanged. Try `{"latitude": 12.9716}` alone — expect `422`
   (latitude/longitude must be provided together). Try
   `{"phone": "not-a-phone"}` — expect `422`.
3. **Get another user's profile as a non-admin**: copy your own `id`
   from step 1, register/login as a second, different-role account,
   re-authorize with their token, then `GET /api/users/{that id}` ->
   expect `403 FORBIDDEN`. `GET /api/users/{their own id}` still works.
4. **Get another user's profile as ADMIN**: register/login with
   `role: "ADMIN"`, re-authorize with that token, `GET /api/users/{any id}`
   -> expect `200`.

## 10. File uploads

Two endpoints, both under `/api/uploads`:

| Method | Path | Who can call it |
|---|---|---|
| POST | `/api/uploads/resource-image` | PROVIDER or ADMIN |
| DELETE | `/api/uploads/{file_id}` | The file's own uploader, or ADMIN |

### Storage backend

Storage is fully abstracted behind `app/services/storage_service.py`,
picked automatically per request — nothing else in the app (or the
client calling it) needs to know which one is active:

- **Supabase Storage**, used whenever both `SUPABASE_URL` and
  `SUPABASE_KEY` are set in `.env`. Files are uploaded to the bucket
  named by `SUPABASE_STORAGE_BUCKET` (default `resource-images` — create
  this bucket in your Supabase project first, with public read access,
  or uploads will fail).
- **Local disk**, used automatically whenever Supabase isn't configured
  — the default out of the box. Files are written under `LOCAL_UPLOAD_DIR`
  (default `uploads/`) and served back at
  `{PUBLIC_BASE_URL}/static/uploads/{file_id}`, a route mounted directly
  in `app/main.py`. This is what makes the upload endpoint fully testable
  with zero Supabase setup.

Switching between the two is just editing `.env` and restarting — no code
changes, no migration.

### Validation

- **File type**: accepts JPEG, PNG, GIF, and WEBP. Judged from the file's
  actual bytes (its magic-number signature), never from the filename or
  the declared `Content-Type` — both are trivial for a client to fake.
  Anything else is rejected with `422 UNSUPPORTED_FILE_TYPE`.
- **File size**: capped at `MAX_UPLOAD_FILE_SIZE_MB` (default 5MB),
  enforced while streaming the upload rather than after buffering it
  fully into memory — oversized files are rejected mid-read with
  `413 FILE_TOO_LARGE`.
- **Empty files**: rejected with `422 EMPTY_FILE`.

### Ownership and security

There's no separate uploaded-files database table. Instead, each
`file_id` is `<uploader's user id, hex>__<random hex>.<ext>` — the owner
is baked into the id itself. `DELETE /api/uploads/{file_id}`:

1. Checks `file_id` against a strict pattern before doing anything else
   with it (used to build a filesystem path or a storage object key) —
   this is what stops path-traversal attempts (`../../etc/passwd`, etc.)
   from ever reaching disk or the Supabase API. A malformed id is reported
   as `404 FILE_NOT_FOUND`.
2. Compares the id's embedded owner against the caller — anyone else
   (other than an ADMIN) gets `403 NOT_FILE_OWNER`.

Deleting a file does **not** automatically clear it from any resource's
`image_url` — that's a separate `PUT /api/resources/{id}` call if needed.

### Connecting an upload to a resource

`Resource.image_url` (see §8) already exists as a plain string column —
uploads don't add a foreign key to it, they just produce a URL that fits
the same `image_url` field `POST`/`PUT /api/resources` already accepts
(and validates as an absolute `http(s)://` URL). The flow is:

1. `POST /api/uploads/resource-image` -> copy the returned `url`.
2. `POST /api/resources` or `PUT /api/resources/{id}` with
   `"image_url": "<that url>"`.

### Testing upload and deletion in Swagger

Assumes you're logged in as a `PROVIDER` (see §7) with Swagger's
**Authorize** button holding a valid token, and no Supabase credentials
configured (i.e. testing the local-disk fallback — the flow is identical
either way, only where the file physically lands differs).

1. **Upload**: `POST /api/uploads/resource-image` -> **Try it out** ->
   under `file`, choose any small `.jpg`/`.png`/`.gif`/`.webp` from your
   machine -> **Execute**. Expect `201` with `file_id`, `url`,
   `content_type`, and `size_bytes`. Paste `url` into a browser tab —
   it should load the image you just uploaded (served from
   `/static/uploads/...`). Copy `file_id` for later.
2. **Reject a non-image file**: repeat step 1 but choose a `.txt` or
   `.pdf` file instead — expect `422 UNSUPPORTED_FILE_TYPE`, even if you
   rename it to end in `.png` first (validation reads the actual bytes).
3. **Reject an oversized file**: repeat step 1 with a file larger than
   `MAX_UPLOAD_FILE_SIZE_MB` (5MB by default) — expect
   `413 FILE_TOO_LARGE`.
4. **Attach it to a resource**: `POST /api/resources` with the example
   FOOD payload, but set `"image_url"` to the `url` from step 1 ->
   **Execute**. Expect `201` with `image_url` echoed back unchanged.
5. **Check ownership enforcement**: register/login a second `PROVIDER`
   account, re-authorize with their token, then
   `DELETE /api/uploads/{file_id}` using the `file_id` from step 1 —
   expect `403 NOT_FILE_OWNER`. Re-authorize back to the original
   provider afterward.
6. **Check role restriction on upload**: log in as a `RECIPIENT` account,
   re-authorize, try step 1 again — expect `403 FORBIDDEN_ROLE`.
7. **Delete**: back on the original provider's token,
   `DELETE /api/uploads/{file_id}` with the id from step 1 -> **Execute**.
   Expect `200`. Reload the `url` from step 1 in a browser tab — it
   should now 404 (the file is gone from disk/Supabase). Note that the
   resource created in step 4 still shows the old `image_url` — deleting
   the file doesn't touch it.

## 11. Recipients and rescue partners

Two mirrored sets of endpoints — a Recipient (NGO/shelter/community/
medical-recipient org) and a RescuePartner (volunteer/transport org) are
both one-to-one profile extensions of a User, the same pattern as
`/api/users/me` for basic profile info, but with the domain-specific
fields the matching engine (Stage 7+) will need.

| Method | Path | Who can call it |
|---|---|---|
| POST | `/api/recipients` | RECIPIENT (self) or ADMIN (on behalf of a RECIPIENT user) |
| GET | `/api/recipients` | Any authenticated user |
| GET | `/api/recipients/{id}` | Any authenticated user |
| PUT | `/api/recipients/{id}` | That recipient's own account, or ADMIN |
| POST | `/api/partners` | RESCUE_PARTNER (self) or ADMIN (on behalf of a RESCUE_PARTNER user) |
| GET | `/api/partners` | Any authenticated user |
| GET | `/api/partners/{id}` | Any authenticated user |
| PUT | `/api/partners/{id}` | That partner's own account, or ADMIN |

Stored fields (both): organization name, contact phone, address,
latitude/longitude (validated -90..90 / -180..180, and must be provided
together — never a half-updated coordinate pair), capacity (must be > 0
if set), accepted resource types (`accepts_food` / `accepts_medical`),
operating hours (validated as `24/7` or `HH:MM-HH:MM`), current
availability, verification status (`is_verified` — admin-only to change),
and a service area radius in km (`service_area_km` for recipients,
`service_radius_km` for partners — same concept, named to match each
table's existing convention). RescuePartner additionally has
`vehicle_type` and `capacity` as its transportation-capability fields,
and a `rating` that's read-only here (not client-settable at all — it's
meant to be computed/assigned elsewhere later).

Notes on behavior:

- **One profile per account.** A second `POST` for the same user fails
  with `409 RECIPIENT_PROFILE_EXISTS` / `409 PARTNER_PROFILE_EXISTS`.
- **Self-service vs. admin creation.** A RECIPIENT/RESCUE_PARTNER account
  always creates their own profile — any `user_id` they send is ignored.
  An ADMIN must supply `user_id` (the target user), which is validated to
  exist and have the matching role before the profile is created — handy
  for seeding demo data as ADMIN without needing to log in as each
  provider/recipient/partner individually.
- **`is_verified` is admin-gated, not silently dropped.** If a non-admin
  includes `is_verified` in a `PUT` body, the whole request is rejected
  with `403 ADMIN_ONLY_FIELD` rather than quietly ignoring just that
  field — so a client never mistakenly believes verification changed
  when it didn't.
- **Filtering**: `resource_type=FOOD` or `MEDICAL` maps to
  `accepts_food`/`accepts_medical`; `recipient_type`/`partner_type` filter
  by the org-type enum; `current_availability`/`is_available` filter by
  live status; `location` is a text search (`ILIKE`) across the address
  and organization name fields — not a geospatial radius query. A true
  "recipients within N km" search needs distance math against real
  coordinates, which is deliberately deferred to the matching engine
  (Stage 7+) rather than duplicated ad hoc here; the still-unresolved
  question from earlier stages (real haversine vs. a simplified distance
  model) applies here too.
- **`GET` is open to any authenticated user**, not just admins — a
  provider posting a resource, or a partner deciding whether to accept a
  job, needs to see recipient/partner directory info, not just their own.
- Availability changes go through the same `PUT` as everything else —
  there's no separate toggle endpoint, since `current_availability` /
  `is_available` are ordinary optional fields on the update schema.

### Testing with sample data in Swagger

Assumes the server is running and you're on `http://localhost:8000/docs`.

**Recipients:**

1. Register a `RECIPIENT` account (§7) if you don't have one, log in, and
   **Authorize** with its access token.
2. `POST /api/recipients` -> **Try it out** -> use the pre-filled example
   (Hope Community Shelter) -> **Execute**. Expect `201`.
3. Execute the same request again — expect
   `409 RECIPIENT_PROFILE_EXISTS`.
4. `GET /api/recipients` -> **Execute** -> confirm it's in `data.items`.
   Try `?resource_type=FOOD`, `?recipient_type=SHELTER`,
   `?location=Church` — confirm each filters correctly.
5. `GET /api/recipients/{id}` with the id from step 2 -> expect `200`.
   Try a random UUID -> expect `404 RECIPIENT_NOT_FOUND`.
6. `PUT /api/recipients/{id}` -> body
   `{"current_availability": false, "capacity": 100}` -> expect `200`
   with both fields changed. Try
   `{"latitude": 12.97}` alone (no longitude) -> expect `422` (must be
   provided together). Try `{"is_verified": true}` -> expect
   `403 ADMIN_ONLY_FIELD`.
7. **Ownership check**: register a second, different `RECIPIENT` account,
   log in as them, re-Authorize, try `PUT` on the first recipient's
   profile -> expect `403 NOT_RECIPIENT_OWNER`.
8. **Admin path**: log in as an `ADMIN` account, re-Authorize,
   `PUT /api/recipients/{id}` with `{"is_verified": true}` -> expect
   `200` this time. `POST /api/recipients` with
   `{"user_id": "<the second recipient user's id>", ...}` for a user who
   already has a profile -> expect `409`.

**Rescue partners:** same flow, swapped:

9. Register a `RESCUE_PARTNER` account, log in, **Authorize**.
10. `POST /api/partners` -> the pre-filled example (QuickRelief
    Logistics) -> `201`.
11. `GET /api/partners?resource_type=MEDICAL&is_available=true` -> confirm
    filtering.
12. `PUT /api/partners/{id}` -> `{"operating_hours": "not-a-time"}` ->
    expect `422` with a clear validation message. Then
    `{"operating_hours": "08:00-20:00"}` -> expect `200`.
13. Confirm ownership and admin-gating the same way as steps 7-8.

## Running Stage 3 (auth) and Stage 4 (resources) together

They're not separate servers or separate setup steps — Stage 4 is built
directly on top of Stage 3 in the same app, so there's exactly one
install and one server to run:

```bash
cd reserve-backend
python3 -m venv .venv && source .venv/bin/activate   # skip if already set up
pip install -r requirements.txt                       # picks up everything, both stages
cp .env.example .env                                   # skip if you already have one — don't overwrite it
alembic upgrade head                                    # picks up the profile-fields migration too
uvicorn app.main:app --reload
```

Then open `http://localhost:8000/docs`. You'll see five route groups —
**Health**, **Auth**, **Users**, **Resources**, **Uploads**. The end-to-end flow that
exercises everything together is §7, then §8, then §9:

1. Register (§7 step 2) -> Login (§7 step 4) -> Authorize in Swagger (§7
   step 5). That's Stage 3.
2. With that same token still authorized, go straight into §8's Create ->
   List -> Get -> Update -> Delete flow. That's Stage 4, using the
   identity Stage 3 just gave you.

There's nothing to reconfigure or restart between them — one running
server, one Swagger tab, one token, both stages tested back to back.

## What's intentionally NOT in this stage

- No rescue-hub CRUD API endpoints — the `RescueHub` table exists but has
  no dedicated endpoints yet (a future stage; hubs are largely
  admin/system-managed fallback locations rather than something
  providers/recipients/partners register themselves)
- No matching/allocation engine logic — Stage 7 (the `Match`/`Allocation`
  tables exist now, but nothing populates them yet; Gemini's analysis
  output is advisory input for that future engine, not a replacement for it)
- No geospatial "within N km" search for recipients/partners — location
  filtering here is text search only; real distance math is deferred to
  the matching engine
- No seed data — Stage 10
- No frontend code of any kind — this repo is backend-only

Everything above is wired to be extended, not rebuilt: routers get added to
`app/main.py` via `include_router()`, models get added under `app/models/`
and imported into `alembic/env.py`, and the response envelope in
`app/schemas/common.py` is reused everywhere.
