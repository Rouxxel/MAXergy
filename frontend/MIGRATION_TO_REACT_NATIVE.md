# Migrating MAXergy to React Native + Expo

MAXergy's frontend is built as a mobile-first **web** app using TanStack Start (React 19 + Vite 7). The architecture was designed so that ~80% of the code (types, stores, API client, business logic) ports directly to React Native. This document is the migration recipe.

## Why the web shell is portable

| Layer | Web (current) | React Native target | Port effort |
|---|---|---|---|
| Types | `src/types/index.ts` (TS) | Same file, unchanged | **None** |
| State | Zustand stores | Zustand | **None** |
| Data fetching | TanStack Query | TanStack Query | **None** |
| API client | `fetch` wrapper in `src/services/apiClient.ts` | Same (RN has `fetch`) | **None** |
| Endpoints | `src/services/endpoints.ts` | Same | **None** |
| Mocks | `src/services/mocks.ts` | Same | **None** |
| Analytics | `src/services/analytics.ts` | Same (with RN analytics SDK) | Low |
| Styling | Tailwind CSS v4 utility classes | **NativeWind** (same class names) | Low |
| Routing | TanStack Router file routes | **Expo Router** file routes | Low |
| Storage | `localStorage` | `@react-native-async-storage/async-storage` | Trivial |
| Primitives | shadcn/ui (Radix + Tailwind) | RN core + react-native-reusables | Medium |
| Images | Module imports | RN `require()` or `expo-image` | Low |

## Current Project Structure

```
frontend/src/
├── routes/
│   ├── __root.tsx           # HTML shell, fonts, global providers
│   ├── index.tsx            # / — redirects to assessment
│   ├── landing.tsx          # /landing — marketing landing page
│   ├── assessment.tsx       # /assessment — 9-step onboarding
│   ├── loading.tsx          # /loading — forecast generation
│   ├── results.tsx          # /results — savings summary
│   ├── compare.tsx          # /compare — scenario comparison
│   └── advisor.tsx          # /advisor — AI advisor chat
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
│   └── ui/                  # shadcn primitives
├── services/
│   ├── apiClient.ts         # fetch wrapper
│   ├── endpoints.ts         # 5 typed API methods
│   ├── analytics.ts         # Analytics tracking service
│   └── mocks.ts             # Mock data
├── stores/
│   ├── assessmentStore.ts   # Onboarding draft + validation
│   ├── resultsStore.ts      # Forecast result + selected scenario
│   └── uiStore.ts           # Global error/toast state
├── types/index.ts           # TypeScript types
├── assets/                  # Image files
│   ├── cumulative_net_savings.png
│   ├── average_german_household_comparison.png
│   ├── high_benefit_household_comparison.png
│   └── low_benefit_household_comparison.png
└── styles.css               # Tailwind v4 theme tokens
```

## Step-by-step Migration

### 1. Bootstrap the Expo app

```bash
npx create-expo-app maxergy-mobile -t expo-template-blank-typescript
cd maxergy-mobile
npx expo install expo-router react-native-safe-area-context react-native-screens
bun add nativewind tailwindcss zustand @tanstack/react-query zod lucide-react-native
bun add @react-native-async-storage/async-storage
bun add expo-image @react-native-community/netinfo
```

Follow the NativeWind v4 + Expo setup guide to wire `metro.config.js`, `babel.config.js`, and a `global.css`. Copy the `@theme` block and `:root` color tokens from `frontend/src/styles.css` into `global.css` — the tokens (`--primary`, `--background`, etc.) and their utility classes (`bg-primary`, `text-primary`) work identically.

### 2. Copy these files verbatim

- `frontend/src/types/index.ts` → `types/index.ts`
- `frontend/src/services/apiClient.ts` → `services/apiClient.ts` (replace `import.meta.env` with Expo's `process.env.EXPO_PUBLIC_*`)
- `frontend/src/services/endpoints.ts` → `services/endpoints.ts`
- `frontend/src/services/mocks.ts` → `services/mocks.ts`
- `frontend/src/services/analytics.ts` → `services/analytics.ts` (update analytics provider SDK for RN)
- `frontend/src/stores/*.ts` → `stores/*.ts` (unchanged)
- `frontend/src/lib/utils.ts` (`cn` helper) → `lib/utils.ts` (if exists)

Only diff in `apiClient.ts`:

```ts
// web
const BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000";
const USE_MOCKS = import.meta.env.VITE_USE_MOCKS !== "false";

// react native
const BASE_URL = process.env.EXPO_PUBLIC_API_BASE_URL ?? "http://localhost:8000";
const USE_MOCKS = process.env.EXPO_PUBLIC_USE_MOCKS !== "false";
```

### 3. Translate the routes

| Web route | Expo Router file |
|---|---|
| `src/routes/__root.tsx` | `app/_layout.tsx` (app shell) |
| `src/routes/index.tsx` | `app/index.tsx` (redirect to assessment) |
| `src/routes/landing.tsx` | `app/landing.tsx` |
| `src/routes/assessment.tsx` | `app/assessment.tsx` |
| `src/routes/loading.tsx` | `app/loading.tsx` |
| `src/routes/results.tsx` | `app/results.tsx` |
| `src/routes/compare.tsx` | `app/compare.tsx` |
| `src/routes/advisor.tsx` | `app/advisor.tsx` |

Per file:

- Replace `<div>` → `<View>`, `<span>`/`<p>` → `<Text>`, `<button>` → `<Pressable>`.
- Replace `<Link to="/foo">` → `<Link href="/foo">` from `expo-router`.
- Replace `useNavigate()` → `useRouter()` from `expo-router`.
- Replace `<input>`/`<form>` with `TextInput` and a submit `Pressable`.
- Replace `useScrollAnimation` (Intersection Observer) with `react-native-reanimated` or `react-native-intersection-observer`.
- Replace image imports: `import img from "@/assets/foo.png"` → `<Image source={require('@/assets/foo.png')} />`.
- Tailwind class names (`flex flex-col`, `bg-primary`, `text-2xl font-bold`) work as-is via NativeWind's `className` prop.
- The mutation hooks, store hooks, types, and mock data require **zero changes**.

### 4. Replace shadcn primitives

The web app uses shadcn `Button`, `Input`, `Select`, `Switch`, `Slider`. In RN, swap them with:

- `Button` → small wrapper around `Pressable` + `Text` with the same variants.
- `Input` → `TextInput` styled with NativeWind.
- `Select` → `@react-native-picker/picker` or a sheet from `@gorhom/bottom-sheet`.
- `Switch` → React Native's built-in `Switch`.
- `Slider` → React Native's built-in `Slider` or `@react-native-community/slider`.

Keep the same prop names so the route files barely change.

### 5. Port landing page components

The landing page uses reusable components from `components/landing/`:

- `FeatureCard.tsx` → Port to RN with `<View>`, `<Text>`, and NativeWind styling
- `StepCard.tsx` → Port to RN with same approach
- `SummaryCard.tsx` → Port to RN with same approach
- `FAQItem.tsx` → Replace accordion logic with `react-native-collapsible` or `react-native-reanimated`

### 6. Handle images

Web uses module imports:
```ts
import cumulativeNetSavings from "@/assets/cumulative_net_savings.png";
<img src={cumulativeNetSavings} />
```

React Native uses `require()`:
```ts
<Image source={require('@/assets/cumulative_net_savings.png')} />
```

Copy all images from `frontend/src/assets/` to the Expo project's `assets/` directory.

### 7. Analytics integration

The web app uses a custom analytics service (`src/services/analytics.ts`). For React Native:

- Keep the same function signatures (`trackPageView`, `trackCTAClick`, etc.)
- Replace the implementation with RN-compatible analytics SDK:
  - Firebase Analytics: `@react-native-firebase/analytics`
  - Mixpanel: `mixpanel-react-native`
  - Plausible: Custom HTTP calls (same as web)
  - Google Analytics: `@react-native-firebase/app` + analytics

### 8. Storage and persistence

Wherever you would use `localStorage` (currently nowhere — state is in-memory Zustand), use `AsyncStorage` and `zustand/middleware`'s `persist` with a custom storage adapter.

### 9. Charts

The web app uses inline SVG bars in `results.tsx`. In RN, swap to:
- `react-native-svg` (same JSX shape)
- `victory-native`
- `react-native-chart-kit`

### 10. Scroll animations

The web app uses Intersection Observer for scroll animations (`useScrollAnimation` hook). In RN, use:
- `react-native-intersection-observer`
- `react-native-reanimated` with `useAnimatedScrollHandler`

### 11. Environment & deployment

- Set `EXPO_PUBLIC_API_BASE_URL=https://your-backend.onrender.com` in `.env`.
- `eas build` for TestFlight / Play Internal Testing.
- Add Sentry / Mixpanel via their Expo plugins.
- Configure app.json with proper app name, bundle identifier, and permissions.

### 12. Bottom navigation

The web app uses `app-shell.tsx` with bottom tab navigation. In RN, use:
- `expo-router`'s Tabs layout: `app/(tabs)/_layout.tsx`
- Or `react-navigation`'s `createBottomTabNavigator`

## What lives where

```
frontend/src/              →  Expo project/
├── types/                 →  types/           ← portable, copy as-is
├── stores/                →  stores/          ← portable, copy as-is
├── services/              →  services/        ← portable, change env vars
│   ├── apiClient.ts       →  apiClient.ts     ← change 2 lines
│   ├── endpoints.ts       →  endpoints.ts     ← unchanged
│   ├── analytics.ts       →  analytics.ts     ← update SDK
│   └── mocks.ts           →  mocks.ts         ← unchanged
├── lib/utils.ts           →  lib/utils.ts     ← portable, copy as-is
├── components/            →  components/
│   ├── landing/           →  components/landing/  ← port to RN
│   ├── app-shell.tsx      →  components/app-shell.tsx  ← rewrite for RN
│   ├── metric-card.tsx    →  components/metric-card.tsx  ← port to RN
│   ├── progress-steps.tsx →  components/progress-steps.tsx  ← port to RN
│   └── ui/                →  components/ui/  ← replace with RN primitives
├── routes/                →  app/             ← rewrite JSX tags, keep logic
├── assets/                →  assets/          ← copy images
└── styles.css             →  global.css       ← copy token block
```

If you keep the same folder names in the Expo project, every `import` path stays identical and the diff is mechanical.

## Key Differences to Note

### Landing Page
- The web app has a marketing landing page at `/landing` with scroll animations
- In RN, consider making this the onboarding flow or a separate tab
- Scroll animations need RN-compatible implementation

### Assessment Flow
- 9-step onboarding form with progress tracking
- Form validation with Zod
- In RN, use `react-hook-form` or `formik` with NativeWind-styled inputs

### Benchmark Data
- Web fetches from `/api/v1/maxergy/benchmark` endpoint
- Same endpoint works in RN (TanStack Query handles it)
- Fallback to hardcoded data if API fails

### Analytics
- Web logs to console in development
- RN should use proper analytics SDK for production
- Keep the same event structure for consistency

## Testing Strategy

1. **Unit tests**: Port existing tests (if any) to RN-compatible testing framework
2. **E2E tests**: Use Detox for RN instead of Playwright
3. **Manual testing**: Test on iOS Simulator and Android Emulator
4. **Device testing**: Test on actual devices before deployment

## Deployment

### iOS
- Configure `app.json` with iOS bundle identifier
- Set up Apple Developer account
- Use EAS Build for TestFlight
- Submit to App Store for review

### Android
- Configure `app.json` with Android package name
- Set up Google Play Console account
- Use EAS Build for internal testing
- Submit to Play Store for review

## Estimated Effort

- **Logic layer**: 2-3 days (types, stores, services)
- **UI primitives**: 3-4 days (shadcn replacements)
- **Route translation**: 5-7 days (all 7 routes)
- **Landing page**: 2-3 days (scroll animations, components)
- **Testing**: 2-3 days
- **Polish**: 2-3 days

**Total**: ~16-23 days for a single developer

## Conclusion

The MAXergy web app is well-architected for React Native migration. The separation of concerns (types, stores, services, components) means most business logic ports unchanged. The main work is translating JSX to React Native primitives and replacing web-specific APIs (Intersection Observer, localStorage) with RN equivalents.