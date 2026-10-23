# MAXergy - Energy Transition Planner (Frontend)

MAXergy is an AI-powered home-energy upgrade planner for German households. This folder is the **mobile-first web app**: a fully navigable UI wired to the MAXergy FastAPI backend (`POST /plan`), with a mock mode that replays a recorded backend response.

The shell intentionally keeps all business logic out of components. Data fetching goes through a thin service layer, state lives in Zustand stores, and types are centralized — so swapping mocks for a real API (or porting to Expo) is a localized change.

---

## 1. Tech Stack

| Concern         | Choice                                                              |
| --------------- | ------------------------------------------------------------------- |
| Framework       | [TanStack Start](https://tanstack.com/start) v1 (React 19 + Vite 7) |
| Routing         | TanStack Router (file-based, in `src/routes/`)                      |
| Styling         | Tailwind CSS v4 (tokens in `src/styles.css`)                        |
| UI primitives   | shadcn/ui + Radix (in `src/components/ui/`)                         |
| State           | Zustand (`src/stores/`)                                             |
| Data fetching   | TanStack Query + a typed fetch wrapper                              |
| Validation      | Zod                                                                 |
| Icons           | lucide-react                                                        |
| Package manager | Bun                                                                 |

> **Note on React Native:** the original brief asked for RN. We ship a
> mobile-first PWA shell that mirrors RN structure (typed services, stores,
> screens) so the port is mechanical. See `MIGRATION_TO_REACT_NATIVE.md`.

---

## 2. Running it

```bash
bun install
cp .env.example .env       # adjust VITE_API_BASE_URL / VITE_USE_MOCKS
bun run dev                # http://localhost:8080
bun run build              # production build
bun run preview            # serve the production build locally
```

OR

```bash
npm install
cp .env.example .env       # adjust VITE_API_BASE_URL / VITE_USE_MOCKS
npm run dev                # http://localhost:8080
npm run build              # production build
npm run preview            # serve the production build locally
```

### Environment variables

| Variable            | Default                 | Purpose                                                          |
| ------------------- | ----------------------- | ---------------------------------------------------------------- |
| `VITE_API_BASE_URL` | `http://localhost:8000` | Base URL of the FastAPI backend, no trailing slash.              |
| `VITE_DEPLOYED_API_BASE_URL` | unset          | Deployed backend URL; overrides `VITE_API_BASE_URL` when set.    |
| `VITE_USE_MOCKS`    | `true` (when unset)     | When `true`, all endpoints resolve from `src/services/mocks.ts`. |

**Mock policy:** mock mode replays a real `POST /plan` response for the example household
(`documentation/data/model_input1.json`), stored in `src/services/fixtures/plan_model_input1.json`
(loaded lazily, so it is only bundled into the mock-mode chunk). It shows the same numbers as the
live backend for that household — including a negative monthly figure while the loan runs —
regardless of what was entered. Re-record the fixture when the API contract changes (POST
`backend/tests/fixtures/model_input1.json` to `/plan` and save the JSON).

Deploying to Render / Railway: set the same two env vars in the host's
dashboard. Anything prefixed `VITE_` is inlined at build time, so rebuild
after changing values.

---

## 3. Project structure

```
src/
├── routes/                  # File-based routes → URLs
│   ├── __root.tsx           # HTML shell, fonts, global providers
│   ├── index.tsx            # / — onboarding (9-step assessment)
│   ├── landing.tsx          # /landing — marketing landing page
│   ├── loading.tsx          # /loading — one POST /plan (forecast + recommendation)
│   ├── results.tsx          # /results — savings + ROI summary
│   ├── compare.tsx          # /compare — scenario comparison
│   └── advisor.tsx          # /advisor — chat with the AI advisor
├── components/
│   ├── app-shell.tsx        # Page wrapper + bottom tab nav
│   ├── landing/             # Landing page components
│   │   ├── FeatureCard.tsx
│   │   ├── StepCard.tsx
│   │   ├── SummaryCard.tsx
│   │   ├── FAQItem.tsx
│   │   └── index.ts
│   ├── metric-card.tsx
│   ├── progress-steps.tsx
│   └── ui/                  # shadcn primitives (button, slider, …)
├── services/
│   ├── apiClient.ts         # fetch wrapper, retries, USE_MOCKS flag
│   ├── endpoints.ts         # typed API methods; live responses validated with Zod
│   ├── analytics.ts         # Analytics tracking service
│   ├── validation.ts        # Zod schemas (assessment steps + every response)
│   ├── fixtures/            # Recorded backend responses for mock mode
│   └── mocks.ts             # Mock responses used when VITE_USE_MOCKS=true
├── stores/
│   ├── assessmentStore.ts   # Onboarding draft + validation
│   ├── resultsStore.ts      # Plan (forecast + recommendation) + selected scenario
│   └── uiStore.ts           # Global error/toast state
├── types/index.ts           # All cross-cutting TS types
├── styles.css               # Tailwind v4 theme tokens (MAXergy palette)
├── router.tsx               # Router bootstrap
└── routeTree.gen.ts         # AUTO-GENERATED — do not edit
```

### Design tokens

The MAXergy palette is defined as CSS variables in `src/styles.css`:

- Background `#111827`, Primary (lime) `#B8FF5A`, Secondary (violet) `#6C63FF`.
- Font: Inter, loaded via `<link>` in `src/routes/__root.tsx`.
- Never hardcode colors in components — use semantic Tailwind classes (`bg-background`, `text-primary`, etc.).

---

## 4. The data flow (how a screen gets its data)

```
 User input ──► Zustand store (draft state)
                      │
                      ▼
         services/endpoints.ts  ← single API surface
                      │
         ┌────────────┴────────────┐
         ▼                         ▼
  services/mocks.ts        services/apiClient.ts
   (USE_MOCKS=true;         (real backend fetch)
    recorded /plan)                │
                                   ▼
                          MAXergy FastAPI backend
                                   │
                                   ▼
                     services/validation.ts (Zod) → stores → screens
```

Results flow: onboarding submits `POST /assessment` (stores `assessment_id`), `/loading` calls
**`POST /plan` once** (forecast + recommendation from a single engine run) and saves both in
`resultsStore`; `/results` and `/compare` read from the store.

Screens never call `fetch` directly. They call functions from
`services/endpoints.ts` (usually through `useMutation` / `useQuery`).

---

## 5. Wiring the real backend

The app talks to these endpoints of the MAXergy backend (shapes:
[`documentation/app/API_CONTRACT.md`](../documentation/app/API_CONTRACT.md)):

| Method | Path                | Request body          | Response type         | Used by |
| ------ | ------------------- | --------------------- | --------------------- | ------- |
| GET    | `/benchmark`        | N/A                   | `BenchmarkData`       | landing (engine-computed benchmark; chart from `cumulative_series`; falls back to the recorded `fixtures/benchmark.json`) |
| POST   | `/assessment`       | `HouseholdAssessment` | `AssessmentResponse`  | onboarding (`assessment_id` → advisor context) |
| POST   | `/plan`             | `HouseholdAssessment` | `PlanResponse`        | loading → results / compare |
| POST   | `/location/enrich`  | `EnrichmentRequest`   | `EnrichmentResponse`  | `postLocationEnrich` (roof/yield pre-fill; 503 when the MCP is off) |
| POST   | `/advisor/chat`     | `AdvisorChatRequest`  | `AdvisorChatResponse` | advisor |

`postForecast` and `postRecommendation` still exist for single calls, but the results flow uses
`postPlan`. `src/types/index.ts` mirrors the backend Pydantic schemas and `src/services/validation.ts`
validates every live response with Zod, so a contract change fails with a clear error instead of
rendering `undefined`.

**Results semantics** (`src/routes/results.tsx`, wording in `src/services/savings.ts`, shared with
the mobile app and the MCP guidance):

- Hero = `monthly_saving_eur` (year-1 average, loan instalment included). Positive → "You could
  save €X per month from the start"; negative → "During financing −€X per month compared with
  today", shown in orange.
- Chips: "After payoff: +€Y/month" (`monthly_saving_post_payoff_eur`) and "N-year net: €Z"
  (`financials.cumulative_net_savings_central_eur`), with the low/high range below.
- "Modeled estimate · Assumptions" disclosure lists solar yield and its source, battery size, heat
  pump efficiency, loan terms, the price approach and every backend `validation_warning`. There are
  no "live tariffs" / "verified ROI" badges.
- Compare shows each scenario's year-1 net and after-payoff figures, the horizon net, and marks the
  backend's `selected_scenario_id` as Recommended.

Key fields: a scenario's loan instalment is `monthly_cost_eur.financing_installment` (included in
`monthly_cost_eur.total`); `monthly_saving_eur` is the average monthly net saving in year 1 with the
instalment (can be negative); `monthly_saving_post_payoff_eur` is the saving after the loan;
`financials` holds cumulative net savings and the break-even year. The recommendation provides
`selected_scenario_id` (null when no scenario is possible), `ranked_scenarios` (`{id, score_eur,
metric}`), `metric_used` and `rationale`.

### Switching mocks off

1. Start your backend (e.g. `uvicorn app:app --port 8000`).
2. In `.env`:
   ```
   VITE_API_BASE_URL=http://localhost:8000
   VITE_USE_MOCKS=false
   ```
3. Restart the dev server.

`apiClient.ts` handles JSON encoding, error parsing, and retries on network/5xx
failure. The backend's `CORS_ORIGINS` must include the frontend origin.

### Adding/changing an endpoint

1. Add or update the type in `src/types/index.ts`.
2. Add a Zod schema in `src/services/validation.ts` (`satisfies z.ZodType<FooResponse, …>`).
3. Add a mock in `src/services/mocks.ts` (so the UI keeps working offline), ideally a recorded
   backend response.
4. Add a wrapper in `src/services/endpoints.ts`:
   ```ts
   export const postFoo = (data: FooRequest): Promise<FooResponse> =>
     USE_MOCKS
       ? mockDelay(mockFoo(data))
       : apiRequest<unknown>("/foo", { method: "POST", body: data }).then(validateFoo);
   ```
5. Consume it from a screen with `useMutation` / `useQuery`.

---

## 6. Landing Page

The landing page (`/landing`) is a marketing page that showcases MAXergy's value proposition and displays benchmark data for a typical German household.

### Features

- **Hero Section**: Headline, subheadline, and CTAs linking to assessment
- **What is MAXergy**: Overview of the product and its benefits
- **How It Works**: 4-step process explanation
- **Example Output**: Benchmark data display with household details, recommended plan, and cost comparison charts
- **Features Grid**: 6 key features with icons
- **FAQ**: Accordion-style frequently asked questions
- **Analytics Integration**: Page view, CTA click, scroll depth, and FAQ expansion tracking

### Components

The landing page uses reusable components from `src/components/landing/`:

- `FeatureCard`: Display feature with icon, title, and description
- `StepCard`: Display process step with number, title, and description
- `SummaryCard`: Display key metric with label and value
- `FAQItem`: Accordion FAQ item with expand/collapse

### Benchmark Data

The landing page fetches benchmark data from the `/benchmark` endpoint using TanStack Query with 1-hour caching. If the API fails, it falls back to hardcoded data.

### Analytics

The landing page includes analytics tracking via `src/services/analytics.ts`:

- Page view tracking on mount
- CTA click tracking (primary and secondary buttons)
- Scroll depth tracking at 25%, 50%, 75%, and 100%
- Benchmark data load success/error tracking
- FAQ expansion tracking

To connect to an analytics provider, implement the `trackEvent` function in `analytics.ts` with your provider's SDK (Google Analytics, Plausible, etc.).

---

## 7. The assessment (onboarding) steps

`src/routes/assessment.tsx` collects a `HouseholdAssessment` in ten steps. Defaults come from
`ENGINE_DEFAULTS` in `src/stores/assessmentStore.ts`, which match the backend's `GET /assumptions`
(work price €0.32/kWh, base fee €12.50/month, 15-year loan at 4.5 %, all four upgrades selected), so
the web form, the mobile app and the MCP onboarding propose the same values.

| Step | What it collects | Rules |
| ---- | ---------------- | ----- |
| Country | `location.country` | Germany only; other countries shown as "coming soon" |
| Postcode | `location.postcode` | On "Continue", `POST /location/enrich` runs in the background and pre-fills the roof (see below) |
| Occupants | `household.occupants` | |
| Electricity | annual kWh, tariff type, work price, base fee | Optional "monthly payment" shortcut: kWh = (monthly € − base fee) × 12 ÷ work price |
| Roof | availability, usable area, orientation, tilt, shading | "My roof can take solar panels" off → baseline-only result. Badges show "From satellite roof scan" / "Site solar yield … kWh/kWp" when the lookup succeeded, otherwise "Estimated from region"; every value can be overridden |
| Heating | fuel, floor area, insulation, consumption, spend | Gas or oil only; other systems listed as "not modelled yet" |
| Mobility | vehicles: type, mileage, consumption, fuel spend | Types: petrol, diesel, hybrid, plug-in hybrid, electric. Mileage required per vehicle. Combustion cars are combined; electric cars are not counted (charged from household electricity) |
| Upgrades | solar, battery, heat pump, EV charger, optional sizes | |
| Financing | loan term, rate, known subsidy | |
| Horizon | short- and long-term forecast length | |

**Roof pre-fill:** the lookup (Google geocoding + Solar roof scan + PVGIS, via the backend and the
MCP service) sets `usable_area_m2`, `tilt_deg`, `orientation` and
`household.roof.specific_yield_kwh_per_kwp`. If the backend returns 503 (MCP disabled or no Google
key) or any error, it is skipped silently and the engine uses its regional yield table. The
result is stored with the postcode it belongs to, so a changed postcode triggers a new lookup.

The draft is persisted (store version 2); drafts saved by older versions restart from the defaults.

---

## 8. Adding a new page

File-based routing: the filename **is** the URL.

1. Create `src/routes/<name>.tsx`:

   ```tsx
   import { createFileRoute } from "@tanstack/react-router";
   import { AppShell } from "@/components/app-shell";

   export const Route = createFileRoute("/<name>")({
     component: MyPage,
   });

   function MyPage() {
     return (
       <AppShell title="My page">
         <h1>Hello</h1>
       </AppShell>
     );
   }
   ```

2. The route tree (`src/routeTree.gen.ts`) regenerates automatically — **do
   not edit it by hand**.
3. Link to it from anywhere:
   ```tsx
   import { Link } from "@tanstack/react-router";
   <Link to="/<name>">Go</Link>;
   ```

### Naming conventions

| File                                    | URL                          |
| --------------------------------------- | ---------------------------- |
| `index.tsx`                             | `/`                          |
| `about.tsx`                             | `/about`                     |
| `posts.$postId.tsx`                     | `/posts/:postId`             |
| `settings.tsx` + `settings.profile.tsx` | layout + `/settings/profile` |

Use dots (`a.b.c.tsx`) — not nested folders — for path segments. Use `$param`
for dynamic segments.

### Adding the page to the bottom navigation

Open `src/components/app-shell.tsx` and add to `TABS`:

```ts
const TABS = [
  { to: "/",        label: "Start",   icon: Home },
  { to: "/results", label: "Results", icon: BarChart3 },
  { to: "/compare", label: "Compare", icon: LayoutGrid },
  { to: "/advisor", label: "Advisor", icon: MessageSquare },
  // { to: "/<name>", label: "My page", icon: Sparkles },  ← add here
];
```

Pages that don't belong in the tab bar (modals, full-screen flows like
`/loading`) can pass `hideNav` to `<AppShell>`.

---

## 9. Modifying existing pages

- **Onboarding form** (`src/routes/index.tsx`): each step reads/writes the
  `assessmentStore`. To add a question, extend `HouseholdAssessment` in
  `src/types/index.ts`, add a default + validator in
  `src/stores/assessmentStore.ts`, then add the UI step.
- **Results & Compare**: read from `resultsStore`. To change visuals, only
  the JSX needs editing — the data shape is fixed by `ForecastResult`.
- **Advisor chat**: messages are local component state, sent through
  `postAdvisorChat`. To persist conversations, lift them into a new store.

---

## 10. State management cheatsheet

| Store             | Holds                                      | When to use              |
| ----------------- | ------------------------------------------ | ------------------------ |
| `assessmentStore` | Draft onboarding answers + validity        | Anywhere in the wizard   |
| `resultsStore`    | Latest plan (`forecast`, `recommendation`), selected scenario (persisted, version 2) | Results / Compare |
| `uiStore`         | Global error banner                        | Top-level error handling |

Create new stores in `src/stores/` and follow the same pattern:
`create<State>()((set) => ({ ... }))`.

---

## 11. Deployment

The output is a standard Vite build (`bun run build` → `dist/`). Any static
host works. For Render/Railway:

- Build command: `bun install && bun run build`
- Start command: `bun run preview -- --host 0.0.0.0 --port $PORT`
- Env vars: `VITE_API_BASE_URL`, `VITE_USE_MOCKS=false`

SPA deep links work out of the box when properly configured; make sure unknown
paths fall back to `index.html`.

### Security Headers

The Vite config includes security headers for dev and preview servers. However,
when deploying to production (Render/Railway/nginx/Cloudflare), you must configure
the same security headers at the host level:

- `X-Content-Type-Options: nosniff`
- `X-Frame-Options: DENY`
- `Referrer-Policy: strict-origin-when-cross-origin`
- `Permissions-Policy: camera=(), microphone=(), geolocation=()`
- `Content-Security-Policy: default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline'; img-src 'self' https: data:; font-src 'self' https:; connect-src 'self' https:; frame-ancestors 'none'`

Vite preview headers do not apply when serving from a static bucket or CDN.

---

## 12. Porting to React Native

See `MIGRATION_TO_REACT_NATIVE.md`. In short: `src/types/`, `src/stores/`,
and `src/services/` move over as-is. Only `src/routes/` and
`src/components/` need rewriting against Expo Router + NativeWind.

---

## 13. Conventions & gotchas

- **Never edit `src/routeTree.gen.ts`** — it's regenerated on every build.
- **Never import from `react-router-dom`** — this is TanStack Router.
- **Never hardcode colors** — use the design tokens from `styles.css`.
- **Mocks must stay in sync** with backend response shapes; update both when
  changing a type.
- **Bottom nav routes** must exist as route files before being added to
  `TABS`, or the build will fail (type-safe routing).

---

Happy building. ⚡
1