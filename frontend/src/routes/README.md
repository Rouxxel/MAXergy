# Routes

TanStack Start uses **file-based routing**. Every `.tsx` file in this directory
is a route. Do **not** create `src/pages/`, `src/routes/_app/index.tsx`, or
`app/layout.tsx` — those are Next.js / Remix conventions. The only root layout
is `src/routes/__root.tsx`.

## Conventions

| File | URL |
| --- | --- |
| `index.tsx` | `/` |
| `about.tsx` | `/about` |
| `users/index.tsx` | `/users` |
| `users/$id.tsx` | `/users/:id` (dynamic — bare `$`, no curly braces) |
| `posts/{-$category}.tsx` | `/posts/:category?` (optional segment) |
| `files/$.tsx` | `/files/*` (splat — read via `_splat` param, never `*`) |
| `_layout.tsx` | layout route (renders children via `<Outlet />`) |
| `__root.tsx` | app shell — wraps every page; preserve `<Outlet />` |

`routeTree.gen.ts` is auto-generated. Don't edit it by hand.

## MAXergy flow

| Route | What it does |
| --- | --- |
| `assessment.tsx` | Onboarding steps; on submit `POST /assessment` → stores `assessment_id`, then navigates to `/loading` |
| `loading.tsx` | One `POST /plan` (forecast + recommendation from a single engine run) → `resultsStore.setPlan` → `/results`; errors go back to `/` with the message |
| `results.tsx` | Selected (or recommended) scenario: monthly net saving incl. loan instalment (negative while the loan costs more than it saves), saving after payoff, `financials`, backend `rationale`; handles "no scenario available" |
| `compare.tsx` | All scenarios; "Recommended" = backend `selected_scenario_id`; select a bundle for `/results` |
| `advisor.tsx` | `POST /advisor/chat` with the forecast and `assessment_id` as context |
