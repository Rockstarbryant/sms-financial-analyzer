# SMS Financial Analyzer

A local-first personal finance analyzer that parses M-Pesa and Airtel
Money SMS messages into structured transactions and shows them in a
mobile-first web dashboard. Runs entirely on-device via Termux — no
cloud database, no Docker, no PC required.

**Phases 1, 2, and 3 are done:** a tested FastAPI backend, a React
dashboard, and real SMS sync via Termux:API — all reusing the exact same
parsing pipeline. Demo mode still works too, for trying the app without
SMS access. Export/backup/reset are the last phase.

## What's here

### Backend (Phase 1)

- FastAPI + SQLite backend
- Contextual M-Pesa and Airtel Money parsers with a HIGH/MEDIUM/UNKNOWN
  confidence system — amounts are never fabricated
- `amount`, `fee`, and `balance` are always extracted as independent
  fields, never inferred from one another
- Deterministic SMS fingerprinting so re-importing/re-syncing never
  creates duplicate transactions
- A demo-mode endpoint that runs fully synthetic sample SMS through the
  exact same pipeline real SMS will use later
- 40 automated tests covering parsing, dedup, and the API

### Frontend (Phase 2)

- React + TypeScript + Vite + Tailwind, mobile-first with bottom nav
- Dashboard, Transactions (search/filter/paginate), Analytics (charts),
  People & Services (counterparty drill-down), and Settings pages
- First-run onboarding screen that imports demo data with one tap — no
  SMS permission needed for any of this phase
- A **ledger/receipt design system**: every amount in the app renders in
  tabular monospace "till receipt" digits, and cards use a torn-perforation
  edge as the visual signature tying the whole app together
- Self-hosted fonts (no runtime CDN calls) so the UI works offline once
  installed
- Typechecked (`tsc`), linted (`oxlint`), and production-build verified
- Route-based code-splitting (Analytics/recharts loads on demand)

### Real SMS sync (Phase 3)

- `POST /api/sync` retrieves SMS from the device via `termux-sms-list`
  and runs them through the **exact same parsing pipeline** as demo mode
  — same confidence system, same amount/fee/balance independence, same
  dedup fingerprint
- The Termux:API call is isolated in `app/services/termux_sms.py`:
  invoked via an argument list (never `shell=True`), with a 60s timeout
  and defensive timestamp parsing
- Clear, specific errors: a 503 with an actionable message when
  Termux:API isn't installed, a 403 when SMS permission was denied, and
  one malformed device SMS entry is skipped rather than aborting the
  whole retrieval
- A real **Sync SMS** button in Settings and on first-run onboarding,
  alongside the existing demo-data import
- 15 additional tests (mocked `termux-sms-list`, no device required):
  dedup across repeated syncs, permission-denied and unavailable error
  paths, malformed-entry containment, and a confirmed command-injection
  guard (asserts the call is argument-list based, never shell)

## Requirements

- Python 3.10+ (3.12 used in development)
- Node.js 18+ and npm
- On a real device: [Termux:API](https://wiki.termux.com/wiki/Termux:API)
  (both the Termux:API package and the companion Android app), for
  Phase 3's real SMS sync. Not required for demo mode.

On a Termux/Android setup:

```bash
pkg update
pkg install python nodejs termux-api
```

Also install the **Termux:API** app from F-Droid or Google Play (the
`pkg install termux-api` package alone isn't enough — it's a thin CLI
that talks to the separate Android app, which is what actually holds the
SMS permission).

## Install

```bash
cd backend
pip install -r requirements.txt --break-system-packages

cd ../frontend
npm install
```

(`--break-system-packages` is typically needed on Termux; drop it if
you're using a virtualenv elsewhere.)

## Configuration

- Copy `backend/.env.example` to `backend/.env` if you want to override
  any backend default (database path, port, sample data location).
- Copy `frontend/.env.example` to `frontend/.env` if the backend isn't
  running at the default `http://127.0.0.1:8000`.

Both work out of the box with no `.env` file at all.

## Android SMS permission

The first time you tap **Sync SMS**, Android will prompt Termux:API for
SMS read access (this is a device permission dialog, not something the
app can skip). If you tap "Deny," the sync will fail with a clear
in-app error — reopen it from Android's app settings
(Settings → Apps → Termux:API → Permissions → SMS) and try again.

## Run it

**Two Termux sessions (recommended on Termux):**

```bash
# session 1
./scripts/run_backend.sh

# session 2
./scripts/run_frontend.sh
```

**Or, if backgrounding works fine on your setup:**

```bash
./scripts/run_all.sh
```

Then open `http://127.0.0.1:5173` in Chrome. You'll see an onboarding
screen with two options:

- **Sync my SMS** — reads your real M-Pesa/Airtel Money messages via
  Termux:API (requires the Termux:API app + SMS permission, see above)
- **Import demo data** — loads synthetic transactions with no permission
  needed, useful for trying the app first

Either way you'll land on the full dashboard, transactions list,
analytics charts, and counterparty breakdown. Both are available again
any time from the Settings tab.

For the raw API, `http://127.0.0.1:8000/docs` has interactive Swagger
docs, and:

```bash
curl -X POST http://127.0.0.1:8000/api/sync           # real device SMS
curl -X POST http://127.0.0.1:8000/api/demo/import     # synthetic demo data
curl http://127.0.0.1:8000/api/dashboard
curl http://127.0.0.1:8000/api/transactions
curl http://127.0.0.1:8000/api/counterparties
```

Both `/api/sync` and `/api/demo/import` are idempotent — call them as
many times as you like; neither will ever create duplicate transactions.

## Run tests

```bash
cd backend
python -m pytest tests/ -v
```

All 55 tests should pass. They cover:
- M-Pesa and Airtel Money parsing for every transaction type
- Contextual bundle detection (not fooled by the word "data" appearing
  incidentally in a message)
- amount/fee/balance staying independent fields
- Ambiguous/promotional/balance-only messages ending up UNKNOWN and
  excluded from totals
- Malformed messages never crashing a batch import
- Duplicate prevention, including 10x repeated imports and 10x repeated
  syncs
- Full API round-trips (demo import → dashboard → transactions →
  counterparties)
- Termux:API adapter: mocked `termux-sms-list` responses, permission-
  denied and unavailable error paths, malformed device entries, and a
  command-injection guard (confirms argument-list invocation, never shell)

## API endpoints

```
GET  /api/health
POST /api/demo/import
POST /api/sync
GET  /api/transactions
GET  /api/transactions/{id}
GET  /api/dashboard
GET  /api/analytics/categories
GET  /api/analytics/providers
GET  /api/analytics/monthly
GET  /api/analytics/counterparties
GET  /api/counterparties
GET  /api/counterparties/{name}
```

No endpoint ever returns a raw SMS body.

## Project structure

```
sms-financial-analyzer/
├── backend/
│   ├── app/
│   │   ├── main.py            FastAPI app + router wiring
│   │   ├── config.py          Settings (env-driven, local-first defaults)
│   │   ├── database.py        SQLAlchemy engine/session/Base
│   │   ├── models/
│   │   │   └── transaction.py Transaction ORM model + enums
│   │   ├── schemas/
│   │   │   └── transaction.py Pydantic request/response models
│   │   ├── api/                Route handlers (health, demo, sync, transactions, analytics)
│   │   ├── services/
│   │   │   ├── parsing_pipeline.py  Detect → parse → dedupe → insert
│   │   │   ├── analytics.py         Dashboard/breakdown queries
│   │   │   ├── demo_data.py         Loads sample_data/ fixtures
│   │   │   └── termux_sms.py        termux-sms-list adapter (Phase 3)
│   │   ├── parsers/
│   │   │   ├── base.py              Parser interface + ParsedTransaction
│   │   │   ├── provider_config.py   Sender-address → provider mapping
│   │   │   ├── mpesa.py
│   │   │   └── airtel_money.py
│   │   └── utils/
│   │       ├── hashing.py     Deterministic SMS fingerprint
│   │       └── logging.py     PII-safe structured logging
│   ├── tests/
│   ├── requirements.txt
│   └── .env.example
├── frontend/
│   ├── src/
│   │   ├── main.tsx / App.tsx       Router + onboarding gate
│   │   ├── components/
│   │   │   ├── AppShell.tsx         Header + bottom nav
│   │   │   ├── SummaryCards.tsx     Receipt-hero, provider cards
│   │   │   ├── TransactionList.tsx  Receipt-line rows
│   │   │   ├── Onboarding.tsx       First-run demo import screen
│   │   │   └── StateViews.tsx       Loading/error/empty states
│   │   ├── pages/                   Dashboard, Transactions, Analytics,
│   │   │                            Counterparties, Settings
│   │   ├── services/
│   │   │   ├── api.ts               Typed fetch wrapper for the backend
│   │   │   └── format.ts            Currency/date/label formatting
│   │   ├── hooks/useApiData.ts      Loading/error/refetch data hook
│   │   └── types/index.ts           Mirrors backend Pydantic schemas
│   ├── package.json
│   ├── vite.config.ts
│   ├── tailwind.config.js
│   └── .env.example
├── scripts/
│   ├── run_backend.sh
│   ├── run_frontend.sh
│   └── run_all.sh
├── sample_data/
│   ├── sample_mpesa.json      Synthetic M-Pesa fixtures
│   └── sample_airtel.json     Synthetic Airtel Money fixtures
├── .gitignore
└── README.md
```

## Design system (frontend)

The dashboard uses a **ledger/receipt** visual language grounded in the
actual paper transaction slips M-Pesa and Airtel Money agents print:

- Every amount renders in tabular monospace digits (IBM Plex Mono) —
  consistent, receipt-like alignment everywhere money appears
- Cards use a torn-perforation bottom edge as the app's signature motif
- M-Pesa green and Airtel red are used functionally, to encode which
  provider a card or line belongs to — not as decoration
- Warm paper background, deep ink text, restrained hairline dividers

## Privacy & security notes (apply from this phase onward)

- Backend binds to `127.0.0.1` only — never exposed beyond the device
- No SMS content or transaction data is ever sent to an external API
- Logs never include full SMS bodies, phone numbers, transaction IDs,
  personal names, or balances
- All queries go through the ORM (no raw SQL string building)
- Sample data is entirely synthetic — no real SMS data is used anywhere
  in this repository
- The frontend never renders raw SMS bodies (the API never returns them
  in the first place)
- Fonts are self-hosted (no Google Fonts CDN calls at runtime) so the UI
  works offline once installed
- The Termux:API shell-out uses an argument list, never `shell=True` —
  no command-injection surface
- One malformed device SMS entry is skipped, never aborts the whole sync

## What's next

- **Phase 4:** CSV export, backup/restore, data reset, and packaging
  into a distributable zip

## Cloud multi-user mode (companion Android app)

The backend now supports a **cloud multi-user** path so non-technical users
can use a normal web dashboard while an Android companion app reads SMS
on-device and uploads them.

### New endpoints

| Method | Path | Auth | Purpose |
|--------|------|------|---------|
| POST | `/api/auth/register` | No | Create account (email + password) |
| POST | `/api/auth/login` | No | Get JWT |
| GET | `/api/auth/me` | Bearer JWT | Current user |
| POST | `/api/v1/sync` | Bearer JWT | Upload SMS batch from Android app |

### Cloud sync request body

```json
{
  "messages": [
    {
      "sender": "MPESA",
      "body": "…full SMS text…",
      "timestamp": "2026-08-01T09:12:00+03:00"
    }
  ]
}
```

Response shape is identical to the existing demo/Termux sync
(`scanned`, `recognized`, `inserted`, `duplicates`, `unknown`).

### Behaviour notes

- Transactions are scoped per user (`user_id`). Deduplication is also
  per-user, so two accounts can independently sync the same SMS text.
- Local-first mode is unchanged: `/api/sync` (Termux) and `/api/demo/import`
  still work without auth and store rows with `user_id = NULL`.
- Query endpoints (`/api/transactions`, `/api/dashboard`, analytics) return
  the authenticated user's data when a JWT is present; without a token they
  return only local/demo rows.
- Set `SMS_ANALYZER_JWT_SECRET` to a long random value in production.
- Set `SMS_ANALYZER_CORS_ORIGINS` (comma-separated) for your web app domain.
- For cloud hosting bind with `SMS_ANALYZER_HOST=0.0.0.0`.

### Still to build

- Android companion app (reads SMS, logs in, calls `/api/v1/sync`)
- Frontend login / signup UI and token storage
- Production deployment (PostgreSQL recommended for multi-user)

## Android companion app

See [`android/README.md`](android/README.md) for the Kotlin companion app that:

- Signs in with the same account as the web dashboard
- Requests SMS permission
- Uploads M-Pesa / Airtel Money messages to `POST /api/v1/sync`

Open the `android/` folder in Android Studio to build and run.
