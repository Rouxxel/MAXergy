# Cloover — Energy Transition Planner (Frontend Shell)

Cloover is an AI-powered home-energy upgrade planner. This repository is the
**mobile-first web shell** of the product: a fully navigable UI built with
mocked data, ready to be wired to a real backend and later ported to React
Native.

The shell intentionally keeps all business logic out of components. Data
fetching goes through a thin service layer, state lives in Zustand stores,
and types are centralized — so swapping mocks for a real API (or porting to
Expo) is a localized change.

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

### Environment variables

| Variable            | Default                 | Purpose                                                          |
| ------------------- | ----------------------- | ---------------------------------------------------------------- |
| `VITE_API_BASE_URL` | `http://localhost:8000` | Base URL of the FastAPI (or any) backend, no trailing slash.     |
| `VITE_USE_MOCKS`    | `true`                  | When `true`, all endpoints resolve from `src/services/mocks.ts`. |

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
│   ├── loading.tsx          # /loading — runs forecast mutation
│   ├── results.tsx          # /results — savings + ROI summary
│   ├── compare.tsx          # /compare — scenario comparison
│   └── advisor.tsx          # /advisor — chat with the AI advisor
├── components/
│   ├── app-shell.tsx        # Page wrapper + bottom tab nav
│   ├── metric-card.tsx
│   ├── progress-steps.tsx
│   └── ui/                  # shadcn primitives (button, slider, …)
├── services/
│   ├── apiClient.ts         # fetch wrapper, retries, USE_MOCKS flag
│   ├── endpoints.ts         # 4 typed POST methods (the API surface)
│   └── mocks.ts             # Local fixtures used when VITE_USE_MOCKS=true
├── stores/
│   ├── assessmentStore.ts   # Onboarding draft + validation
│   ├── resultsStore.ts      # Forecast result + selected scenario
│   └── uiStore.ts           # Global error/toast state
├── types/index.ts           # All cross-cutting TS types
├── styles.css               # Tailwind v4 theme tokens (Cloover palette)
├── router.tsx               # Router bootstrap
└── routeTree.gen.ts         # AUTO-GENERATED — do not edit
```

### Design tokens

The Cloover palette is defined as CSS variables in `src/styles.css`:

- Background `#111827`, Primary (lime) `#B8FF5A`, Secondary (violet) `#6C63FF`.
- Font: Inter, loaded via `<link>` in `src/routes/__root.tsx`.
- Never hardcode colors in components — use semantic Tailwind classes
  (`bg-background`, `text-primary`, etc.).

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
   (USE_MOCKS=true)         (real backend fetch)
                                   │
                                   ▼
                          FastAPI / your backend
```

Screens never call `fetch` directly. They call functions from
`services/endpoints.ts` (usually through `useMutation` / `useQuery`).

---

## 5. Wiring the real backend

The shell talks to four endpoints. Implement them in your backend and the UI
lights up — no component changes required.

| Method | Path              | Request body          | Response type         |
| ------ | ----------------- | --------------------- | --------------------- |
| POST   | `/assessment`     | `HouseholdAssessment` | `AssessmentResponse`  |
| POST   | `/forecast`       | `HouseholdAssessment` | `ForecastResult`      |
| POST   | `/recommendation` | `HouseholdAssessment` | `Recommendation`      |
| POST   | `/advisor/chat`   | `AdvisorChatRequest`  | `AdvisorChatResponse` |

All request/response shapes live in `src/types/index.ts` — treat that file as
the contract between FE and BE.

### Switching mocks off

1. Start your backend (e.g. `uvicorn app:app --port 8000`).
2. In `.env`:
   ```
   VITE_API_BASE_URL=http://localhost:8000
   VITE_USE_MOCKS=false
   ```
3. Restart the dev server.

`apiClient.ts` handles JSON encoding, error parsing, and one retry on network
failure. CORS must be enabled on the backend for the frontend origin.

### Adding/changing an endpoint

1. Add or update the type in `src/types/index.ts`.
2. Add a mock in `src/services/mocks.ts` (so the UI keeps working offline).
3. Add a wrapper in `src/services/endpoints.ts`:
   ```ts
   export const postFoo = (data: FooRequest): Promise<FooResponse> =>
     USE_MOCKS
       ? mockDelay(mockFoo(data))
       : apiRequest<FooResponse>("/foo", { method: "POST", body: data });
   ```
4. Consume it from a screen with `useMutation` / `useQuery`.

---

## 6. Adding a new page

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

## 7. Modifying existing pages

- **Onboarding form** (`src/routes/index.tsx`): each step reads/writes the
  `assessmentStore`. To add a question, extend `HouseholdAssessment` in
  `src/types/index.ts`, add a default + validator in
  `src/stores/assessmentStore.ts`, then add the UI step.
- **Results & Compare**: read from `resultsStore`. To change visuals, only
  the JSX needs editing — the data shape is fixed by `ForecastResult`.
- **Advisor chat**: messages are local component state, sent through
  `postAdvisorChat`. To persist conversations, lift them into a new store.

---

## 8. State management cheatsheet

| Store             | Holds                                      | When to use              |
| ----------------- | ------------------------------------------ | ------------------------ |
| `assessmentStore` | Draft onboarding answers + validity        | Anywhere in the wizard   |
| `resultsStore`    | Latest `ForecastResult`, selected scenario | Results / Compare        |
| `uiStore`         | Global error banner                        | Top-level error handling |

Create new stores in `src/stores/` and follow the same pattern:
`create<State>()((set) => ({ ... }))`.

---

## 9. Deployment

The output is a standard Vite build (`bun run build` → `dist/`). Any static
host works. For Render/Railway:

- Build command: `bun install && bun run build`
- Start command: `bun run preview -- --host 0.0.0.0 --port $PORT`
- Env vars: `VITE_API_BASE_URL`, `VITE_USE_MOCKS=false`

SPA deep links work out of the box when properly configured; make sure unknown
paths fall back to `index.html`.

---

## 10. Porting to React Native

See `MIGRATION_TO_REACT_NATIVE.md`. In short: `src/types/`, `src/stores/`,
and `src/services/` move over as-is. Only `src/routes/` and
`src/components/` need rewriting against Expo Router + NativeWind.

---

## 11. Conventions & gotchas

- **Never edit `src/routeTree.gen.ts`** — it's regenerated on every build.
- **Never import from `react-router-dom`** — this is TanStack Router.
- **Never hardcode colors** — use the design tokens from `styles.css`.
- **Mocks must stay in sync** with backend response shapes; update both when
  changing a type.
- **Bottom nav routes** must exist as route files before being added to
  `TABS`, or the build will fail (type-safe routing).

---

Happy building. ⚡
