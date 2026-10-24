# Deployment (Railway)

MAXergy runs as **one Railway project with two services** built from this monorepo. The project
is defined as Infrastructure as Code in [`.railway/railway.ts`](../../.railway/railway.ts)
(Railway's replacement for the deprecated `railway.toml` config-as-code, which stops being read
on 2026-12-01).

| Service | Source | Build | Serves |
| ------- | ------ | ----- | ------ |
| `maxergy-api` | repo root | Dockerfile `backend/DOCKERFILE` (context = repo root, so the image contains `backend/`, `scripts/` and `data/`) | FastAPI backend, port 8000 |
| `maxergy-mcp` | `backend/mcp` | Railpack + uv, start `uv run --no-dev maxergy-mcp` | MCP server at `/mcp`, port 8080 |

```text
web / mobile ──HTTPS──► maxergy-api (public domain)
claude.ai    ──HTTPS──► maxergy-mcp (public domain, passphrase OAuth)

maxergy-mcp ──private──► maxergy-api   POST /plan, GET /assumptions   Bearer MAXERGY_SERVICE_TOKEN
maxergy-api ──private──► maxergy-mcp   /mcp enrichment tools          Bearer MAXERGY_MCP_TOKEN
```

Private traffic uses `http://<service>.railway.internal:<port>` (Wireguard-encrypted, no egress
cost). The frontends never call the MCP directly.

## Variables

Secrets are `preserve()` in `railway.ts`: they are set once in Railway and never committed. Each
secret lives on one service; the other service references it.

### `maxergy-api`

| Variable | Value | Notes |
| -------- | ----- | ----- |
| `PORT` | `8000` | |
| `ENVIRONMENT` | `production` | Generic 422 bodies, no field details |
| `FORWARDED_ALLOW_IPS` | `*` | Trust Railway's proxy so rate limits are per client IP |
| `ALLOWED_HOSTS` | `${{RAILWAY_PUBLIC_DOMAIN}},${{RAILWAY_PRIVATE_DOMAIN}},healthcheck.railway.app` | Add custom domains here |
| `CORS_ORIGINS` | secret-like, set manually | Comma-separated frontend origins |
| `GEMINI_API_KEY` | secret | AI advisor; without it `/advisor/chat` returns 503 (canned replies only when `ENVIRONMENT=development`). Chat onboarding also needs the MCP (`MCP_ENABLED`) for the shared onboarding script and lookups |
| `GEMINI_MODEL` | optional | Gemini model (default `gemini-3.5-flash`) |
| `MCP_ENABLED` | `true` | `false` → `/location/enrich` returns 503; everything else keeps working |
| `MCP_BASE_URL` | `http://${{maxergy-mcp.RAILWAY_PRIVATE_DOMAIN}}:8080` | |
| `MAXERGY_MCP_TOKEN` | secret | Sent to the MCP; the MCP lists it in `MAXERGY_INTERNAL_TOKENS` |
| `MAXERGY_SERVICE_TOKEN` | secret | Accepted from the MCP; grants the `service_request_limit` (300/min) |

### `maxergy-mcp`

| Variable | Value | Notes |
| -------- | ----- | ----- |
| `PORT` | `8080` | HTTP transport is selected automatically when `PORT` is set |
| `MAXERGY_AUTH_MODE` | `passphrase` | Public auth for the claude.ai connector (see `backend/mcp/README.md`) |
| `MAXERGY_AUTH_PASSPHRASE` | secret | |
| `MAXERGY_OAUTH_STATE_PATH` | `/data/oauth.json` | On the `maxergy-mcp-oauth` volume, so OAuth clients survive redeploys |
| `GOOGLE_MAPS_API_KEY` | secret | Solar API + Geocoding enabled |
| `MAXERGY_API_BASE_URL` | `http://${{maxergy-api.RAILWAY_PRIVATE_DOMAIN}}:8000` | |
| `MAXERGY_SERVICE_TOKEN` | `${{maxergy-api.MAXERGY_SERVICE_TOKEN}}` | Reference, not a copy |
| `MAXERGY_INTERNAL_TOKENS` | `${{maxergy-api.MAXERGY_MCP_TOKEN}}` | Comma-separated; accepted alongside the public mode |
| `LOG_LEVEL` | `INFO` | |

Optional: `HOST=::` on either service only for **legacy** Railway environments (created before
2025-10-16) whose private DNS is IPv6-only. Python's `::` bind is IPv6-only, so leave `HOST`
unset in newer environments (default `0.0.0.0`).

## First-time setup

Requirements: the Railway CLI (5.42.1 or newer for IaC) and Node.js.

1. **Link the project.** In the repo root:
   ```bash
   railway login
   railway link                      # select the MAXergy project + production environment
   cd .railway && npm ci && cd ..    # installs the pinned railway SDK
   ```
   Don't run `railway config pull --force` here: it overwrites `.railway/railway.ts`.
   `railway config plan` (step 4) already shows every difference from what Railway has today.
   If the project name in Railway isn't `maxergy`, either rename it or change `project("maxergy")`.
2. **Migrate the existing MCP service off config-as-code.** `backend/mcp/railway.toml` was
   removed from the repo. In the existing MCP service's **Settings**, clear the config file path
   (if set) and **rename the service to `maxergy-mcp`**. Without the rename, IaC would create a
   new `maxergy-mcp` service and plan the deletion of the old one.
3. **Set the secrets once** (generate tokens with
   `python -c "import secrets; print(secrets.token_urlsafe(32))"`):
   ```bash
   railway variables --service maxergy-api --set MAXERGY_SERVICE_TOKEN=... --set MAXERGY_MCP_TOKEN=... \
     --set CORS_ORIGINS=https://<frontend-domain> --set GEMINI_API_KEY=...
   railway variables --service maxergy-mcp --set MAXERGY_AUTH_PASSPHRASE=... --set GOOGLE_MAPS_API_KEY=...
   ```
   (`maxergy-api` must exist first; if it doesn't, run step 4, set the variables, then redeploy.)
4. **Plan, review, apply:**
   ```bash
   railway config plan               # review: no unexpected deletes
   railway config apply
   ```
5. **Domains.** Generate a Railway domain for each service in the dashboard (generated domains are
   not part of IaC). Custom domains go into `domains: [...]` in `railway.ts` and `ALLOWED_HOSTS`.

`.railway/` is evaluated by the CLI only; Railway does not read it during deploys. Type-check
changes without Railway access: `cd .railway && npx tsc --noEmit`.

## Smoke test

```bash
API=https://<maxergy-api-domain>
curl -s $API/                                                     # health
curl -s -X POST $API/plan -H "Content-Type: application/json" \
  --data @backend/tests/fixtures/model_input1.json                # recommended: full_upgrade
curl -s -X POST $API/location/enrich -H "Content-Type: application/json" \
  -d '{"postcode":"50667"}'                                       # lat/lon, roof, specific_yield (needs the Google key on the MCP)
```

In claude.ai (connector at `https://<maxergy-mcp-domain>/mcp`), run `energy_savings_overview`:
it calls `maxergy-api` over the private network. With `MCP_ENABLED=false` on the API, `/plan`
must still return 200.

## CI/CD (GitHub Actions)

| Workflow | Runs | Jobs |
| -------- | ---- | ---- |
| `backend.yml` | `backend/**` (not `backend/mcp`), `scripts/**`, `tests/**`, data and recorded fixtures | engine tests, backend API tests (incl. fixture drift: recorded `/plan`, `/benchmark`, `/assumptions` vs. the live API), contract scripts; repository guards (old product name, legacy engine, absolute paths); image build from the repo root + container `/plan` smoke test; pip-audit/Trivy (advisory) |
| `mcp.yml` | `backend/mcp/**`, `backend/src/models/**` | `uv sync --locked`; tool/auth tests; `contract.py` drift vs. the backend schemas and `PROMPT.md` drift vs. `instructions.py` |
| `frontend.yml` | `frontend/**` | type-check, lint, build (mocks); audit (advisory) |
| `mobile.yml` | `frontend-mobile/**`, backend schemas/fixtures | type-check, Jest (unit + component); **live smoke**: backend started in the job, mobile service layer without mocks |
| `security.yml` | every PR / push, weekly | gitleaks, dependency review |

Deployments are not triggered from CI: Railway builds each service on push to the connected branch
(watch patterns below). Run the smoke test above against staging before promoting.

## Rebuild triggers

Set in `railway.ts` (`watchPatterns`): `maxergy-api` rebuilds on `backend/**`, `scripts/**` and
`data/**` except `backend/mcp/**`; `maxergy-mcp` rebuilds on `backend/mcp/**`.

## Token rotation

1. Set the new value on the owning service (`maxergy-api`): `MAXERGY_SERVICE_TOKEN` or
   `MAXERGY_MCP_TOKEN`. The MCP picks it up through the reference.
2. Redeploy both services. For a zero-downtime MCP token rotation, temporarily put both tokens in
   `MAXERGY_INTERNAL_TOKENS` (comma-separated) before switching the API.

## Migrating from the pre-rename variables

The MCP reads **only** `MAXERGY_*` variables; the fallback for the old product spelling (the
`MAX…ERGY_*` names with an extra "N") was removed. **Before the next MCP deploy**, set every
`MAXERGY_*` variable listed above on `maxergy-mcp`, then delete the old-spelling variables —
otherwise the MCP starts without its auth passphrase, API URL and service token. The old public
MCP domain (old spelling, `…-production.up.railway.app`) only matters for claude.ai connectors
registered against it; keep it until those are re-registered against the new domain (decision
#11 in `API_CONTRACT.md`).

## Local Docker

```bash
docker build -f backend/DOCKERFILE -t maxergy-api .     # from the repo root
docker run -p 8000:8000 -e ENVIRONMENT=production maxergy-api
# or: cd backend && docker compose up --build
```
