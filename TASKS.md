# Implementation Tasks - Cloover Energy Transition Planner

## Data Contract (source of truth)

The forecast/recommendation API contract is pinned by the example payloads:

- **Input:** `documentation/data/model_input_1.json`
- **Output:** `documentation/data/model_output_1.json`

Schemas, scenario IDs, and calculations below are derived from these files. Keep
them in sync — if the contract changes, update the example JSONs first, then the tasks.

Input is **consumption-based** (annual kWh, tariff Arbeitspreis/Grundpreis, roof
orientation/tilt/shading, heating fuel/consumption, mobility mileage/efficiency),
not simple monthly-spend inputs. Output contains a `baseline` block plus a
`scenarios[]` array, each with monthly + yearly forecast series.

## Phase 1: Backend API Foundation

### 1.1 Project Setup
- [ ] Set up FastAPI project structure following backend/README.md template
- [ ] Configure environment variables (.env file)
- [ ] Set up logging configuration
- [ ] Configure rate limiting
- [ ] Set up CORS for React Native app
- [ ] Test basic API health endpoint

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

## Phase 2: Frontend Foundation

### 2.1 React Native Setup
- [ ] Initialize React Native project with Expo
- [ ] Configure TypeScript
- [ ] Set up NativeWind for styling
- [ ] Install and configure Zustand for state management
- [ ] Install and configure TanStack Query for API calls
- [ ] Set up navigation structure

### 2.2 Core Screens Structure
- [ ] Create Onboarding screen component
- [ ] Create Loading screen component
- [ ] Create Results screen component
- [ ] Create Scenario Comparison screen component
- [ ] Create AI Advisor Chat screen component
- [ ] Set up navigation between screens

### 2.3 API Integration Layer
- [ ] Create API client service for backend communication
- [ ] Implement assessment submission function
- [ ] Implement forecast request function
- [ ] Implement recommendation request function
- [ ] Implement AI advisor chat function
- [ ] Add error handling and loading states

## Phase 3: Household Assessment Flow

### 3.1 Onboarding Form
- [ ] Design multi-step questionnaire UI
- [ ] Implement country selection dropdown
- [ ] Implement postal code input with validation
- [ ] Implement monthly electricity spend input
- [ ] Implement heating type selection (electric, gas, oil, etc.)
- [ ] Implement heating spend input
- [ ] Implement vehicle ownership toggle
- [ ] Implement fuel spend input (conditional on vehicle ownership)
- [ ] Implement roof size estimation input
- [ ] Implement financing term selection
- [ ] Add form validation for all fields
- [ ] Implement form state management with Zustand

### 3.2 Assessment Submission
- [ ] Connect onboarding form to backend /assessment endpoint
- [ ] Implement loading state during submission
- [ ] Handle submission errors gracefully
- [ ] Store assessment data in local state
- [ ] Navigate to loading screen after successful submission

## Phase 4: Recommendation Engine (Without Forecasting Model)

### 4.1 Scenario Generation Logic
Scenario IDs are fixed by the data contract: `solar_only`, `pv_battery`,
`pv_battery_heatpump`, `full_upgrade` (EV charging is folded into `full_upgrade`,
not a standalone scenario).
- [ ] Implement scenario generation based on household data
- [ ] Create `solar_only` scenario configuration
- [ ] Create `pv_battery` scenario configuration
- [ ] Create `pv_battery_heatpump` scenario configuration
- [ ] Create `full_upgrade` scenario configuration (solar + battery + heat pump + EV charger)
- [ ] Auto-size components when input overrides are null (solar_pv_kwp, battery_kwh, heat_pump_kw)
- [ ] Add scenario filtering based on household suitability (roof availability/area, heating fuel_type, vehicle_type)

### 4.2 Cost Calculation Logic (Manual Calculations)
- [ ] Implement baseline monthly cost split (electricity / heating / mobility / total)
- [ ] Implement baseline short-term (monthly) and long-term (yearly, with price escalation) forecast series
- [ ] Implement solar production estimation from roof orientation/tilt/shading + kWp (simplified formula)
- [ ] Implement battery savings and `self_consumption_ratio` calculation (simplified formula)
- [ ] Implement heat pump savings — replaces heating spend, adds electricity load (simplified formula)
- [ ] Implement EV charging savings — shifts mobility from fuel to electricity (simplified formula)
- [ ] Implement financing installment from loan_term_years, loan_rate_pct, known_subsidy_eur
- [ ] Implement monthly savings = baseline_total − (future_total + financing_installment)
- [ ] Implement `monthly_saving_post_payoff_eur` (savings after loan is paid off)
- [ ] Implement `payback_month` calculation (0 when immediately cash-flow positive)
- [ ] Implement per-scenario short-term and long-term forecast series (with saving_eur deltas)
- [ ] Implement ROI and carbon reduction estimation

### 4.3 Recommendation Selection
- [ ] Implement scenario ranking by monthly savings
- [ ] Select top recommendation
- [ ] Apply financing constraints
- [ ] Apply roof constraints
- [ ] Generate recommendation response object

### 4.4 Recommendation API Endpoint
- [ ] Implement POST /recommendation endpoint
- [ ] Accept household assessment data
- [ ] Generate all scenarios
- [ ] Calculate costs for each scenario
- [ ] Rank and select best scenario
- [ ] Return recommendation with all scenario data
- [ ] Add comprehensive error handling

## Phase 5: Results Display

### 5.1 Results Screen UI
- [ ] Design results dashboard layout
- [ ] Display monthly savings prominently (North Star Metric)
- [ ] Display current vs future spend comparison
- [ ] Display financing cost breakdown
- [ ] Display ROI and payback timeline
- [ ] Display carbon reduction metrics
- [ ] Display recommended upgrade bundle and self-consumption ratio
- [ ] Plot short-term (monthly) baseline-vs-scenario cost chart from `short_term_forecast`
- [ ] Plot long-term (yearly) savings chart from `long_term_forecast`
- [ ] Surface payback month and post-payoff monthly savings
- [ ] Add visual charts/graphs for data visualization

### 5.2 Scenario Comparison UI
- [ ] Design scenario comparison table
- [ ] Display all generated scenarios
- [ ] Show monthly savings for each scenario
- [ ] Show upgrade components for each scenario
- [ ] Allow users to select different scenarios
- [ ] Update results based on selected scenario
- [ ] Add scenario details expand/collapse

### 5.3 Results Data Integration
- [ ] Connect results screen to recommendation API
- [ ] Parse and display recommendation data
- [ ] Handle missing or incomplete data gracefully
- [ ] Add loading states for data fetching
- [ ] Add error handling and retry logic

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
- [ ] Design chat interface UI
- [ ] Implement message display (user and AI)
- [ ] Implement chat input field
- [ ] Connect to backend /advisor/chat endpoint
- [ ] Display AI-generated recommendations
- [ ] Display savings explanations
- [ ] Display upsell suggestions
- [ ] Add loading states for AI responses
- [ ] Add error handling for LLM failures

## Phase 7: Polish and User Experience

### 7.1 Loading States
- [ ] Design loading screen with progress indicator
- [ ] Implement loading animation during forecast generation
- [ ] Add skeleton screens for data loading
- [ ] Implement optimistic UI updates where appropriate

### 7.2 Error Handling
- [ ] Implement global error boundary
- [ ] Add user-friendly error messages
- [ ] Implement retry mechanisms for failed requests
- [ ] Add offline detection and handling
- [ ] Implement form validation error display

### 7.3 Responsive Design
- [ ] Ensure mobile-first design works on all screen sizes
- [ ] Test on different device sizes
- [ ] Optimize touch targets
- [ ] Ensure accessibility (screen readers, contrast)

### 7.4 Performance Optimization
- [ ] Implement API response caching where appropriate
- [ ] Optimize image and asset loading
- [ ] Implement lazy loading for components
- [ ] Add performance monitoring

## Phase 8: Testing and Quality Assurance

### 8.1 Backend Testing
- [ ] Write unit tests for cost calculation logic
- [ ] Write unit tests for scenario generation
- [ ] Write unit tests for recommendation selection
- [ ] Write integration tests for API endpoints
- [ ] Test rate limiting functionality
- [ ] Test input validation

### 8.2 Frontend Testing
- [ ] Write unit tests for components
- [ ] Write integration tests for user flows
- [ ] Test form validation
- [ ] Test API integration
- [ ] Test error handling
- [ ] Test navigation

### 8.3 End-to-End Testing
- [ ] Test complete user journey from onboarding to results
- [ ] Test scenario comparison flow
- [ ] Test AI advisor interaction
- [ ] Test error scenarios
- [ ] Performance testing for API responses

## Phase 9: Documentation and Deployment

### 9.1 Documentation
- [ ] Document API endpoints with examples
- [ ] Create frontend component documentation
- [ ] Write deployment guide
- [ ] Create user guide for the app
- [ ] Document calculation formulas and assumptions

### 9.2 Backend Deployment
- [ ] Configure production environment variables
- [ ] Set up Docker containerization
- [ ] Deploy FastAPI to production server
- [ ] Configure SSL/HTTPS
- [ ] Set up monitoring and logging

### 9.3 Frontend Deployment
- [ ] Build production React Native bundle
- [ ] Deploy to app stores (TestFlight first)
- [ ] Set up crash reporting
- [ ] Configure analytics
- [ ] Set up app update mechanism

## Phase 10: Future Enhancements (Post-MVP)

### 10.1 Forecasting Model Integration
- [ ] Integrate real energy forecasting models
- [ ] Replace simplified calculations with ML models
- [ ] Add solar generation forecasting
- [ ] Add battery optimization algorithms
- [ ] Add heat pump efficiency modeling
- [ ] Add dynamic tariff integration

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
