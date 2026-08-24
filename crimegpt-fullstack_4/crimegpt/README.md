# CrimeGPT — Full-Stack Setup

`frontend/` — the pre-built final UI you uploaded, compiled from source and served as-is (no redesign)
`backend/` — Python FastAPI server: API, database, auth, AI assistant, location-based access control

## 1. One-time setup (Windows / VS Code)

```
cd backend
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env
```

## 2. Create the database and run migrations

The database schema is now managed by **Alembic** (real, version-controlled migrations
— not just `create_all()`). Run this once:

```
alembic upgrade head
```

This creates `backend\crimegpt.db` with all 8 tables (see below), including the two
new lookup tables — `roles` and `locations` — with real foreign-key constraints from
`users.role` → `roles.name`, `users.officeLocation` → `locations.name`, and
`cases.district` → `locations.name`. SQLite's foreign-key enforcement is explicitly
turned on in code (`database.py`), so these constraints are actually enforced, not
just declared — verified by testing: attempting to file a case under a nonsense
location returns a clean `400` error, not silent corruption.

## 3. Seed demo data

Seeding happens **automatically** the first time you start the server (next step) —
no separate script to run. It only seeds if the `users` table is empty, so it never
overwrites real data on restart.

## 4. Start the backend

```
uvicorn app.main:app --reload
```

Watch for this line confirming the seed ran:
```
Seeded database: 10 original users + 4 demo city users, 8 original cases + 6 demo city cases, ...
```

## 5. Start the frontend

Not needed separately — the backend serves the pre-built frontend directly.

## 6. Verify the database is working

```
python -c "import sqlite3; c = sqlite3.connect('crimegpt.db'); print(c.execute(\"SELECT name FROM sqlite_master WHERE type='table'\").fetchall())"
```
Should list: `roles`, `locations`, `users`, `victims`, `criminals`, `cases`,
`evidence`, `audit_logs`, `alembic_version`.

Or just open http://127.0.0.1:8000/docs and try `GET /api/cases` after logging in —
real data comes back, not a mock array.

- **App**: http://127.0.0.1:8000
- **Swagger API docs**: http://127.0.0.1:8000/docs

---

## Database - full technical answer to your 7 questions

1. **Currently configured**: SQLite (kept — see recommendation below)
2. **SQLAlchemy configured?**: Yes, and now properly wired to Alembic too
3. **Models before this change**: `User`, `Case`, `Criminal`, `Victim`, `Evidence`,
   `AuditLog` — location/role were plain unconstrained strings
4. **Alembic**: Was not configured — **now fully set up** (`alembic/` folder,
   `alembic.ini`, one initial migration covering all 8 tables)
5. **Seed script**: Existed (`seed_service.py`), **now extended** with dedicated
   lookup-table seeding (`seed_lookup_tables`) plus new demo data for Mysuru,
   Mangaluru, Belagavi, and Tumakuru
6. **DATABASE_URL**: Was hardcoded — **now reads from `.env`**, defaulting to
   local SQLite if not set
7. **Physical storage**: `backend\crimegpt.db`, single file

### Why SQLite over PostgreSQL for this submission

Kept SQLite deliberately. For a local, single-user (or few-user) Windows demo, SQLite
means: no service to install or start, no connection string to debug, the entire
database is one file you can copy/backup/delete-and-reseed trivially. PostgreSQL
would add a real install + running-service step for no practical benefit at this
scale. `DATABASE_URL` is now environment-configurable specifically so this decision
isn't locked in — switching later is a one-line `.env` change plus
`pip install psycopg2-binary`, not a rewrite.

### Tables (all 8, with real relationships)

| Table | Purpose | Key relationships |
|---|---|---|
| `roles` | Lookup: Admin/Investigator/Analyst/Supervisor | `users.role` → this |
| `locations` | Lookup: every valid district/city + real lat/lng | `users.officeLocation` and `cases.district` → this |
| `users` | Accounts | FK to `roles`, FK to `locations` |
| `victims` | Victim records | referenced by `cases.victimId` |
| `criminals` | Criminal profiles | referenced by `cases.criminalIds` (JSON list — see note below) |
| `cases` | FIRs | FK to `locations`, FK to `victims` |
| `evidence` | Evidence attached to a case | FK to `cases.firNumber` |
| `audit_logs` | Action history | no FK (intentionally freeform, matches original design) |

**One honest limitation**: `cases.criminalIds` is still a JSON array column, not a
proper many-to-many association table. SQLite/most databases can't put a real FK
constraint on values inside a JSON array. A fully "correct" schema would add a
`case_criminals` junction table — I didn't do that this round since it would ripple
into every case-detail response shape the frontend already expects; flagging it as a
known architectural simplification rather than silently leaving it unmentioned.

### Location-based data flow (test-verified again after these changes)

Login as `kavya` (Mysuru) → JWT carries `officeLocation: "Mysuru"` → every
subsequent `/api/cases`, `/api/analytics/trends`, `/api/chatbot` request is filtered
server-side to Mysuru only. Verified: `kavya` sees exactly 2 cases (`FIR-2026-5001`,
`FIR-2026-5002`), both `district: "Mysuru"`; `admin` sees all 14 across every city.

## Test login credentials

| Username | Password | Role | Location |
|---|---|---|---|
| admin | admin123 | Admin | All |
| vinay | investigator123 | Investigator | Central District |
| sneha | analyst123 | Analyst | South District |
| satish | supervisor123 | Supervisor | District C |
| siva | siva | Investigator | District E |
| **kavya** | **kavya123** | Investigator | **Mysuru** *(new)* |
| **arjun** | **arjun123** | Investigator | **Mangaluru** *(new)* |
| **meera** | **meera123** | Analyst | **Belagavi** *(new)* |
| **rakesh** | **rakesh123** | Investigator | **Tumakuru** *(new)* |



---

## What changed / what was built

### Files created
Everything under `backend/app/` — this is a new backend built specifically for your final
uploaded frontend (`api.ts`/`server.ts` were used as the exact contract to match).

### Database

- **Type**: SQLite — **File location**: `backend/crimegpt.db` (auto-created on first run)
- **Tables**: `users`, `cases`, `criminals`, `victims`, `evidence`, `audit_logs`
- **Seed source**: `backend/db_seed.json` (your uploaded `db.json`), imported once on first startup only

### New/modified API endpoints (matching `api.ts` exactly)

| Method | Endpoint | Purpose |
|---|---|---|
| POST | `/api/auth/login` | Login — blocks `Pending`/`Suspended` accounts |
| POST | `/api/auth/register` | Register — new accounts default to `Pending` (need Admin approval) |
| GET/PUT | `/api/user/profile` | My Profile — real data, editable |
| PUT | `/api/user/settings` | Account Settings — username/email/language/notifications |
| PUT | `/api/user/password` | Security Settings — password change, 2FA toggle, login-notification toggle |
| GET | `/api/cases` | List/search/filter cases — **location-scoped** |
| GET/PUT/POST | `/api/cases/...` | Case detail, update, create, evidence, suspects — **location-scoped** |
| GET/POST | `/api/criminals` | Criminal profiles (not location-scoped, matching your source) |
| GET | `/api/analytics/trends` | Dashboard KPIs/charts/hotspots — **location-scoped** |
| GET/DELETE/PUT | `/api/users/...` | Admin user management, incl. new `PUT /api/users/:id/status` |
| GET | `/api/audit-logs` | Audit trail (Admin/Supervisor) |
| POST | `/api/chatbot`, `/api/assistant/...` | AI Assistant — **location-scoped** context |

## How location filtering works

This matches your uploaded frontend's actual design: there's no location selector on the
*login* screen — location (`officeLocation`) is chosen once, at **registration**, and then
permanently tied to that account. It's embedded in the JWT on every login, so:

- **Non-Admin users** are automatically locked to their own `officeLocation` on every request —
  cases, criminals-in-context, analytics, hotspots, and the AI assistant's data all silently
  filter to just their district. This is enforced **in the backend** (verified by testing: a
  non-admin gets a 403 trying to view another district's case directly by ID, even without a
  matching UI button).
- **Admins** (`officeLocation: "All"`) see everything, and can pass `?district=X` to filter
  when useful.

I flagged one thing worth knowing: an earlier request in this conversation asked for a location
*dropdown on the login screen* (with Bengaluru/Mysuru/etc. as options). Your actual final
frontend doesn't have that — it captures location once at registration instead. Since you said
to treat this upload as the source of truth and not add UI that isn't there, I built the backend
to match what's actually in your code, not the earlier spec. If you do want a login-time location
switcher after all, that's a small, well-scoped addition I can make on request.

## Profile / Account / Security — status

All three are fully implemented and tested, not simulated:

- **My Profile**: loads real data from `/api/user/profile`, edits save via `PUT`
- **Account Settings**: username/email/language/notification toggles save via `PUT /api/user/settings`
- **Security Settings**: password change verifies your current password (bcrypt) before accepting
  a new one; 2FA and login-notification toggles persist independently. Verified: wrong current
  password → rejected; correct → old password stops working, new one works, survives a restart.

One honest gap: the "Active Sessions" table in Security Settings is still frontend-only mock data
(hardcoded array in `SecuritySettingsView.tsx`) — there's no real multi-session tracking in this
backend. Implementing that would need session/device tracking infrastructure beyond what a single
JWT-per-login supports; flagging it rather than pretending it's live.

## AI Assistant

- Uses Gemini if `GEMINI_API_KEY` is set in `.env`; otherwise a local rule-based fallback engine
  (real code, not a stub) searches your actual location-scoped case/criminal data by FIR number,
  crime type, district keywords, or free text.
- **Not implemented**: server-side text-to-speech (`/api/assistant/speak` returns
  `{"clientFallback": true}`, same as your reference `server.ts` does when no TTS key is
  configured) — the frontend already handles this by using the browser's own speech synthesis.

## Test checklist (all verified working during build)

1. Login without an approved account → blocked ✅
2. Login as `vinay` → only Central District cases visible ✅
3. Login as `admin` → all districts visible ✅
4. Direct case-ID access to another district → 403 ✅
5. Dashboard KPIs differ correctly between `vinay` and `admin` ✅
6. My Profile loads and displays real data ✅
7. Account Settings save persists (language, notifications) ✅
8. Security Settings: wrong password rejected, correct one changes it, restart-persistent ✅
9. 2FA toggle persists independently of password change ✅
10. Register new account → `Pending` → login blocked → Admin approves via status endpoint → login succeeds ✅
11. AI Assistant (fallback engine) returns real, location-scoped data ✅
12. All error responses use `{"error": "..."}` shape your frontend expects ✅
