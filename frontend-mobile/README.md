# MAXergy mobile (Expo)

React Native / Expo Router port of the web app (`frontend/`). Types, stores and services mirror
the web app and the backend API contract
([`documentation/app/API_CONTRACT.md`](../documentation/app/API_CONTRACT.md)).

## Environment

| Variable | Purpose |
| --- | --- |
| `EXPO_PUBLIC_API_BASE_URL` | Backend base URL (default `http://localhost:8000`; use your machine's LAN IP on a device) |
| `EXPO_PUBLIC_USE_MOCKS` | `"false"` to call the backend; anything else (or unset) uses mocks |
| `EXPO_PUBLIC_ENABLE_ANALYTICS` | Analytics toggle |

Same meaning as the web app's `VITE_API_BASE_URL` / `VITE_USE_MOCKS`.

## Data flow

Onboarding posts `POST /assessment` (keeps `assessment_id` for the advisor), the loading screen
calls **`POST /plan` once** (forecast + recommendation from one engine run) and stores it with
`resultsStore.setPlan`; results and compare read from the store. Live responses are validated
with Zod (`services/validation.ts`, Zod 4). `postLocationEnrich` is available for roof/yield
pre-fill (`POST /location/enrich`).

**Mock mode** replays a recorded backend `/plan` response for the example household
(`services/fixtures/plan_model_input1.json`, same file as the web app), so mock and live numbers
match — including a negative monthly figure while the loan runs.

Persisted results use store version 2; results saved by older app versions are discarded.

**Results:** same three numbers and wording as the web app (`services/savings.ts`, tested in
`__tests__/savings.test.ts`): year-1 monthly net with the loan ("During financing" when negative),
after-payoff saving, horizon net with range, and an "Assumptions" panel instead of trust badges.

**Advisor:** same as the web app — sends the current `plan` and the last 20 messages; without a
plan the advisor onboards in chat and a returned `plan` is stored ("See your results").

**Assessment:** same steps, defaults (`ENGINE_DEFAULTS` = backend `GET /assumptions`) and rules as
the web app (`frontend/README.md` §7): Germany only, gas/oil heating only (other options are hidden
because the mobile `Select` has no disabled items), canonical vehicle types with required mileage,
monthly-bill shortcut, "roof can take solar panels" switch, and roof/site-yield pre-fill from
`POST /location/enrich` after the postcode step (skipped silently on 503).
`__tests__/assessmentStore.test.ts` checks the defaults against the recorded `/assumptions`
response and the pre-fill logic.

## Tests

```bash
npx jest                     # unit + component tests (__tests__/); Detox e2e tests are excluded
npx tsc --noEmit             # type-check (tsconfig sets "ignoreDeprecations": "6.0" for TS 6)
```

- `__tests__/planContract.test.ts` validates the recorded `/plan` and `/benchmark` responses and the
  mocks against the Zod schemas and rejects the old v1 recommendation shape.
- `__tests__/resultsStore.test.ts` covers `setPlan`, selection and the no-scenario case;
  `assessmentStore.test.ts` the engine defaults and roof pre-fill; `savings.test.ts` the wording.
- Component tests (`Button`, `FAQItem`, `FeatureCard`, `StepCard`, `SummaryCard`) use
  `@testing-library/react-native` 14, whose `render` and `fireEvent` are **async** (`await`). It needs
  its peer `test-renderer` (dev dependency); `react-test-renderer` is pinned to the React version
  (19.2.3). `jest.setup.js` mocks `react-native` (incl. `StyleSheet.flatten`, `Pressable`).
- `__tests__/live.smoke.test.ts` runs the service layer against a real backend; skipped unless
  `MAXERGY_LIVE_SMOKE=1` (CI job `Mobile / live-smoke`):
  `MAXERGY_LIVE_SMOKE=1 EXPO_PUBLIC_USE_MOCKS=false EXPO_PUBLIC_API_BASE_URL=http://127.0.0.1:8000 npx jest __tests__/live.smoke.test.ts`
- Jest uses `tsconfig.jest.json` (JSX `react-jsx`).
- Lockfile: CI installs with `npm ci` from `package-lock.json`; `bun.lock` is not kept in sync.
- Detox e2e: `e2e/jest.config.js` (needs a built app and a simulator/emulator; not run in CI).

## Commands used to set up the project

```bash
    npx expo install expo-router react-native-safe-area-context react-native-screens
    bun add nativewind tailwindcss zustand @tanstack/react-query zod
    bun add lucide-react-native
    bun add @react-native-async-storage/async-storage
    bun add @react-native-community/netinfo
    bun add react-native-svg react-native-chart-kit
    bun add react-native-reanimated react-native-intersection-observer
    bun add react-native-collapsible
    bun add expo-router
```
