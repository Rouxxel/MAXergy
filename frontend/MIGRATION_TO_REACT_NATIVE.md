# Migrating Cloover to React Native + Expo

This shell is built as a mobile-first **web** app. The architecture was chosen so that ~80% of the code (types, stores, API client, business logic) ports directly. This document is the recipe.

## Why the web shell is portable

| Layer | Web (here) | React Native target | Port effort |
|---|---|---|---|
| Types | `src/types/index.ts` (TS) | Same file, unchanged | **None** |
| State | Zustand | Zustand | **None** |
| Data fetching | TanStack Query | TanStack Query | **None** |
| API client | `fetch` wrapper in `src/services/apiClient.ts` | Same (RN has `fetch`) | **None** |
| Mocks | `src/services/mocks.ts` | Same | **None** |
| Styling | Tailwind v4 utility classes | **NativeWind** (same class names) | Low |
| Routing | TanStack Router file routes | **Expo Router** file routes | Low |
| Storage | `localStorage` | `@react-native-async-storage/async-storage` | Trivial |
| Primitives | shadcn/ui (Radix + Tailwind) | RN core + react-native-reusables | Medium |

## Step-by-step

### 1. Bootstrap the Expo app

```bash
npx create-expo-app cloover-mobile -t expo-template-blank-typescript
cd cloover-mobile
npx expo install expo-router react-native-safe-area-context react-native-screens
bun add nativewind tailwindcss zustand @tanstack/react-query zod
bun add @react-native-async-storage/async-storage
```

Follow the NativeWind v4 + Expo setup guide to wire `metro.config.js`, `babel.config.js`, and a `global.css`. Copy the `@theme` block and `:root` color tokens from `src/styles.css` into `global.css` — the tokens (`--primary`, `--background`, etc.) and their utility classes (`bg-primary`, `text-primary`) work identically.

### 2. Copy these files verbatim

- `src/types/index.ts` → `types/index.ts`
- `src/services/apiClient.ts` → `services/apiClient.ts` (replace `import.meta.env` with Expo's `process.env.EXPO_PUBLIC_*`)
- `src/services/endpoints.ts` → `services/endpoints.ts`
- `src/services/mocks.ts` → `services/mocks.ts`
- `src/stores/*.ts` → `stores/*.ts` (unchanged)
- `src/lib/utils.ts` (`cn` helper) → `lib/utils.ts`

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
| `src/routes/index.tsx` | `app/index.tsx` (Onboarding) |
| `src/routes/loading.tsx` | `app/loading.tsx` |
| `src/routes/results.tsx` | `app/results.tsx` |
| `src/routes/compare.tsx` | `app/compare.tsx` |
| `src/routes/advisor.tsx` | `app/advisor.tsx` |

Per file:

- Replace `<div>` → `<View>`, `<span>`/`<p>` → `<Text>`, `<button>` → `<Pressable>`.
- Replace `<Link to="/foo">` → `<Link href="/foo">` from `expo-router`.
- Replace `useNavigate()` → `useRouter()` from `expo-router`.
- Replace `<input>`/`<form>` with `TextInput` and a submit `Pressable`.
- Tailwind class names (`flex flex-col`, `bg-primary`, `text-2xl font-bold`) work as-is via NativeWind's `className` prop.
- The mutation hooks, store hooks, types, and mock data require **zero changes**.

### 4. Replace shadcn primitives

The shell uses shadcn `Button`, `Input`, `Select`, `Switch`. In RN, swap them with:

- `Button` → small wrapper around `Pressable` + `Text` with the same variants.
- `Input` → `TextInput` styled with NativeWind.
- `Select` → `@react-native-picker/picker` or a sheet from `@gorhom/bottom-sheet`.
- `Switch` → React Native's built-in `Switch`.

Keep the same prop names so the route files barely change.

### 5. Storage and persistence

Wherever you would use `localStorage` (currently nowhere — state is in-memory Zustand), use `AsyncStorage` and `zustand/middleware`'s `persist` with a custom storage adapter.

### 6. Charts

The web shell uses inline SVG bars in `results.tsx`. In RN, swap to `react-native-svg` (same JSX shape) or `victory-native`.

### 7. Environment & deployment

- Set `EXPO_PUBLIC_API_BASE_URL=https://your-backend.onrender.com` in `.env`.
- `eas build` for TestFlight / Play Internal Testing.
- Add Sentry / Mixpanel via their Expo plugins.

## What lives where

```
src/
  types/             ← portable, copy as-is
  stores/            ← portable, copy as-is
  services/          ← portable, change 2 lines in apiClient.ts
  lib/utils.ts       ← portable, copy as-is
  components/        ← rewrite primitives, keep logic
  routes/            ← rewrite JSX tags, keep hooks/state/mutations
  styles.css         ← copy token block into global.css
```

If you keep the same folder names in the Expo project, every `import` path stays identical and the diff is mechanical.