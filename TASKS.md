# Implementation Tasks - MAXergy Energy Transition Planner

## Data Contract (source of truth)

The forecast/recommendation API contract is pinned by the example payloads:

- **Input:** `documentation/data/model_input_1.json` (needs to be created based on model schema)
- **Output:** `documentation/data/model_output_1.json` (exists - 1270 lines with complete forecast data)

Schemas, scenario IDs, and calculations below are derived from these files. Keep
them in sync — if the contract changes, update the example JSONs first, then the tasks.

Input is **consumption-based** (annual kWh, tariff Arbeitspreis/Grundpreis, roof
orientation/tilt/shading, heating fuel/consumption, mobility mileage/efficiency),
not simple monthly-spend inputs. Output contains a `baseline` block plus a
`scenarios[]` array, each with monthly + yearly forecast series.

**Note:** The baseline forecasting model (`scripts/run_baseline_model.py`) is already implemented and working.
The visualization script (`scripts/visualize_forecast.py`) is also implemented. These should be integrated
into the backend as services rather than reimplemented from scratch.

**Frontend Architecture Note:** The frontend is implemented as a mobile-first web shell using TanStack Start
(React 19 + Vite 7) with TanStack Router, Tailwind CSS v4, shadcn/ui, Zustand, and TanStack Query. This architecture
was chosen to enable ~80% of code (types, stores, API client, business logic) to port directly to React Native + Expo.
See `frontend/MIGRATION_TO_REACT_NATIVE.md` for the complete migration guide.

## Phase 1: Backend API Foundation

### 1.1 Project Setup
- [ ] Set up FastAPI project structure following backend/README.md template
- [ ] Configure environment variables (.env file) including GEMINI_API_KEY and MAPS_API_KEY
- [ ] Set up logging configuration
- [ ] Configure rate limiting
- [ ] Set up CORS for web app (TanStack Start) and future React Native app
- [ ] Test basic API health endpoint
- [ ] Create Python dependencies for forecasting model (numpy, pandas, matplotlib)
- [ ] Set up scripts directory structure for model execution

### 1.2 Core Schemas and Models
Mirror `documentation/data/model_input_1.json` and `model_output_1.json` exactly.
- [ ] Input — `location` (postcode, country)
- [ ] Input — `household.occupants` and `household.electricity` (annual_kwh, current_tariff_type, arbeitspreis_eur_per_kwh, grundpreis_eur_per_month, contract_end_date)
- [ ] Input — `household.roof` (available, usable_area_m2, orientation, tilt_deg, shading_factor)
- [ ] Input — `heating` (fuel_type, annual_consumption, annual_spend_eur, building.floor_area_m2, building.insulation_class)
- [ ] Input — `mobility` (vehicle_type, annual_mileage_km, fuel_consumption_l_per_100km, annual_fuel_spend_eur)
- [ ] Input — `upgrade_candidates` (booleans + nullable solar_pv_kwp / battery_kwh / heat_pump_kw overrides)
- [ ] Input — `financing` (loan_term_years, loan_rate_pct, known_subsidy_eur) and `forecast_horizon` (short_term_months, long_term_years)
- [ ] Output — `baseline` (monthly_cost_eur breakdown, short_term_forecast[], long_term_forecast[])
- [ ] Output — `scenarios[]` item (id, components, sizing, monthly_cost_eur incl. financing_installment, monthly_saving_eur, monthly_saving_post_payoff_eur, self_consumption_ratio, payback_month, short_term_forecast[], long_term_forecast[])
- [ ] Create Pydantic schemas for recommendation response (selected scenario + ranked list)
- [ ] Create Pydantic schemas for AI advisor requests/responses
- [ ] Add a contract test that validates both example JSONs against the schemas

### 1.3 API Endpoints Structure
- [ ] Create router for /assessment endpoint
- [ ] Create router for /forecast endpoint
- [ ] Create router for /recommendation endpoint
- [ ] Create router for /advisor/chat endpoint
- [ ] Register all routers in main.py
- [ ] Add input validation to all endpoints
- [ ] Add rate limiting to all endpoints

### 1.4 Baseline Forecasting Model Integration
- [ ] Integrate `scripts/run_baseline_model.py` as backend service module
- [ ] Create forecasting service in `src/services/forecasting/`
- [ ] Implement model constants configuration (specific yield, self-consumption ratios, escalation rates, equipment costs)
- [ ] Create model input validation using Pydantic schemas
- [ ] Implement model output validation against expected schema
- [ ] Add model execution endpoint or service method
- [ ] Implement seasonal heating weights calculation
- [ ] Implement amortizing payment calculation for financing
- [ ] Implement payback month calculation logic
- [ ] Add support for all 6 scenario IDs: solar_only, pv_battery, pv_heatpump, pv_ev, pv_battery_heatpump, full_upgrade
- [ ] Implement self-consumption ratio lookup table
- [ ] Add component auto-sizing logic (solar_pv_kwp, battery_kwh, heat_pump_kw)
- [ ] Create model unit tests using example input/output JSONs

### 1.5 Visualization Service Integration
- [ ] Integrate `scripts/visualize_forecast.py` as backend service module
- [ ] Create visualization service in `src/services/visualization/`
- [ ] Implement forecast chart generation (short-term 12-month, long-term 20-year)
- [ ] Add endpoint to generate forecast comparison PNG images
- [ ] Implement baseline vs scenario comparison charts
- [ ] Add loan payoff year marker visualization
- [ ] Configure chart styling (colors, labels, formatting)
- [ ] Add chart caching to avoid regenerating same forecasts
- [ ] Implement chart export in multiple formats (PNG, SVG)
- [ ] Add visualization unit tests

### 1.6 Model Configuration Management
- [ ] Create model constants configuration file (specific yield, self-consumption ratios, escalation rates, equipment costs)
- [ ] Document all placeholder constants and their intended replacements
- [ ] Create configuration schema for model parameters
- [ ] Implement environment-specific model configurations (dev, staging, prod)
- [ ] Add validation for model constant ranges and constraints
- [ ] Create model versioning system for tracking constant changes
- [ ] Document upgrade path from naive model to advanced models

## Phase 2: Frontend Foundation (TanStack Start Web Shell with React Native Migration Path)

### 2.1 TanStack Start Project Setup
- [ ] Initialize TanStack Start project (React 19 + Vite 7) following frontend/README.md
- [ ] Install dependencies: TanStack Router, Tailwind CSS v4, shadcn/ui, Zustand, TanStack Query, Zod, lucide-react
- [ ] Configure Bun as package manager
- [ ] Set up environment variables (.env file): VITE_API_BASE_URL, VITE_USE_MOCKS
- [ ] Configure Tailwind CSS v4 with design tokens (primary: #B8FF5A, secondary: #6C63FF, background: #111827)
- [ ] Set up Inter font via link tag in __root.tsx
- [ ] Configure file-based routing structure (src/routes/)
- [ ] Test basic dev server (bun run dev → http://localhost:8080)

### 2.2 Project Structure and Components
- [ ] Create file-based routes: index.tsx (onboarding), loading.tsx, results.tsx, compare.tsx, advisor.tsx
- [ ] Create app-shell component with bottom tab navigation
- [ ] Set up shadcn/ui primitives (Button, Input, Select, Switch, etc.)
- [ ] Create metric-card component for displaying data
- [ ] Create progress-steps component for onboarding wizard
- [ ] Set up __root.tsx with HTML shell, fonts, and global providers
- [ ] Configure routeTree.gen.ts (auto-generated, do not edit manually)

### 2.3 Asset Integration
- [ ] Use frontend/src/assets/tab_icon.png as the browser tab icon (favicon)
- [ ] Use frontend/src/assets/logo_64.png for small logo instances (headers, cards)
- [ ] Use frontend/src/assets/logo_128.png for medium logo instances (results screens, advisor)
- [ ] Use frontend/src/assets/logo_512.png for large logo instances (splash screens, about pages)
- [ ] Configure favicon in __root.tsx using tab_icon.png
- [ ] Add logo components that accept size prop (64, 128, 512) to use appropriate asset
- [ ] Ensure logos are used consistently throughout MAXergy branding

### 2.4 Services and API Layer
- [ ] Create apiClient.ts with fetch wrapper, retries, and USE_MOCKS flag
- [ ] Create endpoints.ts with 4 typed POST methods (/assessment, /forecast, /recommendation, /advisor/chat)
- [ ] Create mocks.ts with local fixtures for development (VITE_USE_MOCKS=true)
- [ ] Set up Zod validation for request/response types
- [ ] Implement error handling and retry logic in apiClient
- [ ] Configure CORS handling for backend communication

### 2.5 State Management (Zustand)
- [ ] Create assessmentStore.ts for onboarding draft + validation
- [ ] Create resultsStore.ts for forecast result + selected scenario
- [ ] Create uiStore.ts for global error/toast state
- [ ] Implement store patterns following create<State>()((set) => ({ ... }))
- [ ] Add store persistence if needed (localStorage for web, AsyncStorage for RN migration)

### 2.6 Type Definitions
- [ ] Create src/types/index.ts with all cross-cutting TypeScript types
- [ ] Define HouseholdAssessment type matching model_input_1.json schema
- [ ] Define ForecastResult type matching model_output_1.json schema
- [ ] Define Recommendation, AdvisorChatRequest, AdvisorChatResponse types
- [ ] Ensure types are shared between frontend and backend (contract)

### 2.7 Core Screens Implementation
- [ ] Create index.tsx route for onboarding (9-step assessment wizard)
- [ ] Create loading.tsx route for forecast generation loading state
- [ ] Create results.tsx route for savings + ROI summary dashboard
- [ ] Create compare.tsx route for scenario comparison table
- [ ] Create advisor.tsx route for AI advisor chat interface
- [ ] Implement bottom tab navigation in app-shell.tsx with MAXergy branding
- [ ] Add tab icon using frontend/src/assets/tab_icon.png
- [ ] Set up navigation between routes using TanStack Router Link component

### 2.8 API Integration Layer
- [ ] Implement assessment submission using postAssessment from endpoints.ts
- [ ] Implement forecast request using postForecast from endpoints.ts
- [ ] Implement recommendation request using postRecommendation from endpoints.ts
- [ ] Implement AI advisor chat using postAdvisorChat from endpoints.ts
- [ ] Add error handling and loading states using TanStack Query mutations
- [ ] Configure USE_MOCKS flag for development vs production
- [ ] Test both mock and real backend modes

## Phase 3: Household Assessment Flow

### 3.1 Onboarding Form (Updated for Model Input Schema)
- [ ] Design multi-step questionnaire UI in index.tsx matching `model_input_1.json` structure
- [ ] Implement location inputs (country, postal code) with validation
- [ ] Implement household inputs (occupants, electricity annual_kwh, current_tariff_type, arbeitspreis_eur_per_kwh, grundpreis_eur_per_month, contract_end_date)
- [ ] Implement roof inputs (available, usable_area_m2, orientation, tilt_deg, shading_factor)
- [ ] Implement heating inputs (fuel_type, annual_consumption, annual_spend_eur, building.floor_area_m2, building.insulation_class)
- [ ] Implement mobility inputs (vehicle_type, annual_mileage_km, fuel_consumption_l_per_100km, annual_fuel_spend_eur)
- [ ] Implement upgrade candidates (booleans for solar_pv, battery, heat_pump, ev_charger + optional overrides for solar_pv_kwp, battery_kwh, heat_pump_kw)
- [ ] Implement financing inputs (loan_term_years, loan_rate_pct, known_subsidy_eur)
- [ ] Implement forecast horizon inputs (short_term_months, long_term_years)
- [ ] Add form validation for all fields matching model schema requirements using Zod
- [ ] Implement form state management with assessmentStore (Zustand)
- [ ] Add helper text and tooltips for technical fields (arbeitspreis, grundpreis, COP, etc.)
- [ ] Use MAXergy logo (logo_64.png) in form header
- [ ] Implement progress-steps component for wizard navigation

### 3.2 Assessment Submission
- [ ] Connect onboarding form to backend /assessment endpoint using postAssessment
- [ ] Implement loading state during submission with TanStack Query mutation
- [ ] Handle submission errors gracefully using uiStore for error banners
- [ ] Store assessment data in assessmentStore
- [ ] Navigate to /loading route after successful submission using TanStack Router
- [ ] Display MAXergy logo (logo_128.png) during loading transition

## Phase 4: Recommendation Engine (Using Baseline Forecasting Model)

### 4.1 Scenario Generation Logic (Using Model)
Scenario IDs are fixed by the data contract: `solar_only`, `pv_battery`,
`pv_heatpump`, `pv_ev`, `pv_battery_heatpump`, `full_upgrade`.
- [ ] Integrate scenario generation from baseline model service
- [ ] Use model's scenario definitions (SCENARIO_DEFS) for all 6 scenarios
- [ ] Implement scenario filtering based on upgrade_candidates booleans
- [ ] Auto-size components using model logic (solar_pv_kwp = min(usable_area_m2 / 7, 10))
- [ ] Apply component sizing defaults (battery_kwh = 7.5, heat_pump_kw = 9.0)
- [ ] Add scenario filtering based on household suitability (roof availability/area, heating fuel_type, vehicle_type)

### 4.2 Cost Calculation Logic (Using Baseline Model)
- [ ] Call baseline model service for all calculations instead of manual formulas
- [ ] Use model's baseline monthly cost split (electricity / heating / mobility / total)
- [ ] Use model's short-term (monthly) forecast with seasonal heating weights
- [ ] Use model's long-term (yearly) forecast with escalation rates (electricity 3%, gas/oil 4%, fuel 3%)
- [ ] Use model's solar generation calculation (solar_pv_kwp × 1000 kWh/kWp)
- [ ] Use model's self-consumption ratio lookup table (0.30 to 0.80 based on components)
- [ ] Use model's heat pump load calculation (heating_demand_kwh / COP 3.3)
- [ ] Use model's EV load calculation (annual_mileage / 100 × 18 kWh/100km × arbeitspreis × 0.7)
- [ ] Use model's financing calculation (amortizing payment on system_cost - subsidy)
- [ ] Use model's monthly savings formula (baseline_total - scenario_total)
- [ ] Use model's monthly_saving_post_payoff_eur calculation
- [ ] Use model's payback_month calculation (financed / monthly_saving_excl_installment)
- [ ] Use model's per-scenario short-term and long-term forecast series
- [ ] Implement ROI and carbon reduction estimation (add to model output if needed)

### 4.3 Recommendation Selection
- [ ] Implement scenario ranking by monthly_saving_eur from model output
- [ ] Select top recommendation (highest monthly_saving_eur)
- [ ] Handle negative savings scenarios (show monthly_saving_post_payoff_eur)
- [ ] Apply financing constraints (loan_term_years, loan_rate_pct)
- [ ] Apply roof constraints (usable_area_m2, orientation, tilt, shading)
- [ ] Generate recommendation response object matching model output schema

### 4.4 Forecast API Endpoint
- [ ] Implement POST /forecast endpoint that calls baseline model service
- [ ] Accept household assessment data matching model_input_1.json schema
- [ ] Validate input using Pydantic schemas
- [ ] Call baseline model service to generate forecast
- [ ] Return complete model output (baseline + all scenarios)
- [ ] Add comprehensive error handling
- [ ] Add model execution timeout handling
- [ ] Cache forecast results for identical inputs

## Phase 5: Results Display

### 5.1 Results Screen UI (Matching Model Output Schema)
- [ ] Design results dashboard layout in results.tsx matching model_output_1.json structure
- [ ] Display monthly savings prominently (North Star Metric - monthly_saving_eur)
- [ ] Display baseline monthly cost breakdown (electricity, heating, mobility, total)
- [ ] Display scenario monthly cost breakdown (electricity, heating, mobility, financing_installment, total)
- [ ] Display self_consumption_ratio for recommended scenario
- [ ] Display component sizing (solar_pv_kwp, battery_kwh, heat_pump_kw)
- [ ] Display payback_month (or indicate if beyond loan term)
- [ ] Display monthly_saving_post_payoff_eur for negative savings scenarios
- [ ] Display short-term forecast chart (12 months) from short_term_forecast array
- [ ] Display long-term forecast chart (20 years) from long_term_forecast array
- [ ] Add baseline vs scenario comparison visualization
- [ ] Add loan payoff year marker on long-term chart
- [ ] Implement interactive chart selection (tap scenario to highlight)
- [ ] Add expandable forecast details (monthly/yearly breakdown)
- [ ] Use MAXergy logo (logo_128.png) in results header
- [ ] Use metric-card components for displaying key metrics

### 5.2 Scenario Comparison UI (All 6 Scenarios)
- [ ] Design scenario comparison table in compare.tsx for all 6 scenarios (solar_only, pv_battery, pv_heatpump, pv_ev, pv_battery_heatpump, full_upgrade)
- [ ] Display monthly_saving_eur for each scenario
- [ ] Display components booleans for each scenario
- [ ] Display sizing (solar_pv_kwp, battery_kwh, heat_pump_kw) for each scenario
- [ ] Display self_consumption_ratio for each scenario
- [ ] Display payback_month for each scenario
- [ ] Allow users to select different scenarios to view detailed forecast
- [ ] Update main results display based on selected scenario using resultsStore
- [ ] Add scenario details expand/collapse with full forecast data
- [ ] Highlight recommended scenario (highest monthly_saving_eur)
- [ ] Color-code scenarios by savings (positive vs negative)
- [ ] Use MAXergy logo (logo_64.png) in comparison header

### 5.3 Results Data Integration
- [ ] Connect results screen to forecast API (POST /forecast) using postForecast
- [ ] Parse and display model output data (baseline + scenarios) in resultsStore
- [ ] Handle missing or incomplete data gracefully
- [ ] Add loading states for data fetching using TanStack Query
- [ ] Add error handling and retry logic using uiStore
- [ ] Implement forecast data caching in resultsStore
- [ ] Add option to regenerate forecast with different parameters

## Phase 6: AI Advisor Integration

### 6.1 Gemini API Setup
- [ ] Set up Gemini API credentials
- [ ] Create LLM service module
- [ ] Implement Gemini client initialization
- [ ] Create prompt templates for different advisor functions
- [ ] Add API key security measures

### 6.2 AI Advisor Backend
- [ ] Implement recommendation summary generation
- [ ] Implement savings explanation generation
- [ ] Implement upsell opportunity detection
- [ ] Implement proposal-ready text generation
- [ ] Create POST /advisor/chat endpoint
- [ ] Add context management for conversations
- [ ] Add rate limiting for LLM calls

### 6.3 AI Advisor Frontend
- [ ] Design chat interface UI in advisor.tsx
- [ ] Implement message display (user and AI) using component state
- [ ] Implement chat input field with shadcn Input component
- [ ] Connect to backend /advisor/chat endpoint using postAdvisorChat
- [ ] Display AI-generated recommendations
- [ ] Display savings explanations
- [ ] Display upsell suggestions
- [ ] Add loading states for AI responses using TanStack Query mutation
- [ ] Add error handling for LLM failures using uiStore
- [ ] Use MAXergy logo (logo_128.png) in advisor header
- [ ] Implement quick question buttons for common queries

## Phase 7: Polish and User Experience

### 7.1 Loading States
- [ ] Design loading screen in loading.tsx with progress indicator
- [ ] Implement loading animation during forecast generation
- [ ] Add skeleton screens for data loading using shadcn components
- [ ] Implement optimistic UI updates where appropriate
- [ ] Display MAXergy logo (logo_128.png) during loading

### 7.2 Error Handling
- [ ] Implement global error boundary using uiStore
- [ ] Add user-friendly error messages in error banners
- [ ] Implement retry mechanisms for failed requests in apiClient
- [ ] Add offline detection and handling
- [ ] Implement form validation error display using Zod errors

### 7.3 Responsive Design
- [ ] Ensure mobile-first design works on all screen sizes
- [ ] Test on different device sizes
- [ ] Optimize touch targets
- [ ] Ensure accessibility (screen readers, contrast)

### 7.4 Performance Optimization
- [ ] Implement API response caching using TanStack Query
- [ ] Optimize image and asset loading (logo assets)
- [ ] Implement lazy loading for components using TanStack Router
- [ ] Add performance monitoring
- [ ] Optimize bundle size for web deployment

## Phase 8: Testing and Quality Assurance

### 8.1 Backend Testing
- [ ] Write unit tests for baseline forecasting model service
- [ ] Write unit tests for cost calculation logic (using model output)
- [ ] Write unit tests for scenario generation (all 6 scenarios)
- [ ] Write unit tests for recommendation selection
- [ ] Write unit tests for visualization service
- [ ] Write integration tests for API endpoints
- [ ] Test rate limiting functionality
- [ ] Test input validation against model schemas
- [ ] Test model execution with example input/output JSONs
- [ ] Test model with edge cases (zero values, missing fields, extreme values)
- [ ] Test visualization generation with different scenario combinations

### 8.2 Frontend Testing
- [ ] Write unit tests for components (shadcn primitives, metric-card, progress-steps)
- [ ] Write integration tests for user flows using TanStack Router
- [ ] Test form validation using Zod schemas
- [ ] Test API integration with both mocks and real backend
- [ ] Test error handling using uiStore
- [ ] Test navigation between routes
- [ ] Test state management with Zustand stores
- [ ] Test asset loading (logos, tab icon)

### 8.3 End-to-End Testing
- [ ] Test complete user journey from onboarding to results
- [ ] Test scenario comparison flow
- [ ] Test AI advisor interaction
- [ ] Test error scenarios
- [ ] Performance testing for API responses

## Phase 9: Documentation and Deployment

### 9.1 Documentation
- [ ] Document API endpoints with examples (using model_input_1.json and model_output_1.json)
- [ ] Document baseline forecasting model architecture and constants
- [ ] Document visualization service capabilities and endpoints
- [ ] Create frontend component documentation following frontend/README.md structure
- [ ] Write deployment guide for TanStack Start (Vite build, static hosting)
- [ ] Write React Native migration guide (update MIGRATION_TO_REACT_NATIVE.md)
- [ ] Create user guide for MAXergy app
- [ ] Document calculation formulas and assumptions (from naive_model.md)
- [ ] Document model upgrade path from naive to advanced models
- [ ] Document placeholder constants and their intended replacements
- [ ] Document asset usage (logos, tab icon) and branding guidelines

### 9.2 Backend Deployment
- [ ] Configure production environment variables
- [ ] Set up Docker containerization
- [ ] Deploy FastAPI to production server
- [ ] Configure SSL/HTTPS
- [ ] Set up monitoring and logging

### 9.3 Frontend Deployment (TanStack Start Web Shell)
- [ ] Build production Vite bundle (bun run build)
- [ ] Deploy to static hosting (Render, Railway, Vercel, or Netlify)
- [ ] Configure environment variables (VITE_API_BASE_URL, VITE_USE_MOCKS=false)
- [ ] Set up SSL/HTTPS for production domain
- [ ] Configure SPA routing (fallback to index.html for unknown paths)
- [ ] Set up monitoring and analytics
- [ ] Test deployment with real backend integration
- [ ] Document deployment process in frontend/README.md

## Phase 10: Future Enhancements (Post-MVP)

### 10.1 Advanced Forecasting Model Integration
- [ ] Replace placeholder constants with real data sources (PVGIS for solar yield, real EEG tariffs, building-specific COP)
- [ ] Integrate hourly dispatch simulation for accurate self-consumption ratios
- [ ] Add postcode-based solar generation forecasting
- [ ] Add battery optimization algorithms
- [ ] Add building-specific heat pump efficiency modeling
- [ ] Add dynamic tariff integration
- [ ] Implement macro energy price escalation models
- [ ] Add weather data integration for seasonal variations

### 10.2 Database Integration
- [ ] Design PostgreSQL schema
- [ ] Implement user management
- [ ] Implement assessment history
- [ ] Implement scenario persistence
- [ ] Add data backup and recovery
- [ ] Migrate from in-memory to database storage

### 10.3 Advanced Features
- [ ] Implement real tariff integrations
- [ ] Add installer CRM features
- [ ] Implement checkout and financing approval
- [ ] Add user accounts and authentication
- [ ] Implement sharing and export features
- [ ] Add Maps API integration for location-based services (using MAPS_API_KEY)

## Phase 11: React Native Migration (Post-Web MVP)

### 11.1 Expo Project Setup
- [ ] Bootstrap Expo app following MIGRATION_TO_REACT_NATIVE.md
- [ ] Install Expo Router, NativeWind, Zustand, TanStack Query, Zod
- [ ] Configure NativeWind v4 with Tailwind CSS v4
- [ ] Copy design tokens from web styles.css to global.css
- [ ] Set up environment variables (EXPO_PUBLIC_API_BASE_URL, EXPO_PUBLIC_USE_MOCKS)

### 11.2 Portable Code Migration
- [ ] Copy src/types/index.ts → types/index.ts (unchanged)
- [ ] Copy src/stores/*.ts → stores/*.ts (unchanged)
- [ ] Copy src/services/endpoints.ts → services/endpoints.ts (unchanged)
- [ ] Copy src/services/mocks.ts → services/mocks.ts (unchanged)
- [ ] Copy src/lib/utils.ts → lib/utils.ts (unchanged)
- [ ] Update apiClient.ts to use process.env.EXPO_PUBLIC_* instead of import.meta.env

### 11.3 Route Translation
- [ ] Translate src/routes/index.tsx → app/index.tsx (Onboarding)
- [ ] Translate src/routes/loading.tsx → app/loading.tsx
- [ ] Translate src/routes/results.tsx → app/results.tsx
- [ ] Translate src/routes/compare.tsx → app/compare.tsx
- [ ] Translate src/routes/advisor.tsx → app/advisor.tsx
- [ ] Replace HTML tags with React Native components (div→View, span/p→Text, button→Pressable)
- [ ] Replace TanStack Router with Expo Router (useNavigate→useRouter, Link href)
- [ ] Replace form inputs with TextInput and Pressable

### 11.4 Component Translation
- [ ] Replace shadcn Button with Pressable + Text wrapper
- [ ] Replace shadcn Input with TextInput styled with NativeWind
- [ ] Replace shadcn Select with @react-native-picker/picker
- [ ] Replace shadcn Switch with React Native Switch
- [ ] Translate charts to react-native-svg or victory-native
- [ ] Ensure Tailwind classes work via NativeWind className prop

### 11.5 Asset Integration (React Native)
- [ ] Add tab_icon.png to app.json for app icon
- [ ] Add logo_64.png, logo_128.png, logo_512.png to React Native assets
- [ ] Configure splash screen using logo_512.png
- [ ] Ensure MAXergy branding consistent across native app

### 11.6 Storage and Persistence
- [ ] Install @react-native-async-storage/async-storage
- [ ] Implement Zustand persist middleware with AsyncStorage adapter
- [ ] Migrate any localStorage usage to AsyncStorage

### 11.7 React Native Deployment
- [ ] Configure EAS build for TestFlight and Play Internal Testing
- [ ] Set up EXPO_PUBLIC_API_BASE_URL for production backend
- [ ] Add Sentry/Mixpanel via Expo plugins for crash reporting and analytics
- [ ] Test on iOS and Android devices
- [ ] Submit to app stores
