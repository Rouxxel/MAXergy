# MAXergy Landing Page - Phase 1 Design and Content Strategy

**Status:** Phase 1 - Design and Content Strategy  
**Date:** 2026-06-21  
**Version:** 1.0

---

## 1. Page Structure Planning

### 1.1 Section Definition

The landing page will consist of the following sections, ordered from top to bottom:

| Section | Purpose | Content Type | Priority |
|---------|---------|--------------|----------|
| **Hero** | Capture attention, communicate value proposition, primary CTA | Headline, subheadline, CTA buttons, hero illustration | High |
| **What is MAXergy** | Explain the app's purpose and target audience | Text explanation, key statistics, visual element | High |
| **How It Works** | Show the user journey from assessment to results | 5-step process with icons and descriptions | High |
| **Example Output** | Demonstrate real results using benchmark data | Savings figure, household summary, recommended plan, simplified chart | High |
| **Features & Benefits** | Highlight key differentiators and capabilities | Feature cards with icons | Medium |
| **FAQ** | Address common questions and concerns | Accordion-style Q&A | Medium |
| **Footer** | Navigation, legal, contact information | Links, copyright, social media | Low |

### 1.2 Mobile-First Wireframe

**Mobile Layout (320px - 768px):**

```
┌─────────────────────────────┐
│  [Logo]                     │  Header (sticky)
├─────────────────────────────┤
│                             │
│  HERO SECTION               │
│  ┌───────────────────────┐  │
│  │ Headline (H1)         │  │
│  │ Subheadline           │  │
│  │ [Primary CTA]         │  │
│  │ [Secondary CTA]       │  │
│  │ Hero Illustration     │  │
│  └───────────────────────┘  │
│                             │
│  WHAT IS MAXERGY            │
│  ┌───────────────────────┐  │
│  │ Icon + Text           │  │
│  │ Key Stats (2x1 grid)  │  │
│  └───────────────────────┘  │
│                             │
│  HOW IT WORKS               │
│  ┌───────────────────────┐  │
│  │ Step 1: Icon + Text  │  │
│  │ Step 2: Icon + Text  │  │
│  │ Step 3: Icon + Text  │  │
│  │ Step 4: Icon + Text  │  │
│  │ Step 5: Icon + Text  │  │
│  └───────────────────────┘  │
│                             │
│  EXAMPLE OUTPUT             │
│  ┌───────────────────────┐  │
│  │ Benchmark Badge       │  │
│  │ Savings Figure (H2)   │  │
│  │ Household Summary     │  │
│  │ Recommended Plan      │  │
│  │ Mini Chart            │  │
│  │ [Get Your Estimate]   │  │
│  └───────────────────────┘  │
│                             │
│  FEATURES                    │
│  ┌───────────────────────┐  │
│  │ Feature 1: Icon+Text  │  │
│  │ Feature 2: Icon+Text  │  │
│  │ Feature 3: Icon+Text  │  │
│  │ Feature 4: Icon+Text  │  │
│  │ Feature 5: Icon+Text  │  │
│  │ Feature 6: Icon+Text  │  │
│  └───────────────────────┘  │
│                             │
│  FAQ                         │
│  ┌───────────────────────┐  │
│  │ Q1 (expandable)       │  │
│  │ Q2 (expandable)       │  │
│  │ Q3 (expandable)       │  │
│  │ Q4 (expandable)       │  │
│  │ Q5 (expandable)       │  │
│  └───────────────────────┘  │
│                             │
│  FOOTER                      │
│  ┌───────────────────────┐  │
│  │ Logo + Tagline        │  │
│  │ Navigation Links      │  │
│  │ Copyright             │  │
│  └───────────────────────┘  │
└─────────────────────────────┘
```

**Desktop Layout (1024px+):**

- Hero: Side-by-side layout (text left, illustration right)
- How It Works: Horizontal row of 5 steps
- Example Output: Two-column layout (stats left, chart right)
- Features: 3-column grid
- FAQ: 2-column grid

### 1.3 Responsive Breakpoints

| Breakpoint | Width Range | Layout Changes |
|------------|-------------|----------------|
| Mobile | 320px - 768px | Single column, stacked sections |
| Tablet | 768px - 1024px | Some sections use 2-column grid |
| Desktop | 1024px+ | Multi-column layouts, side-by-side hero |

### 1.4 Component Hierarchy

```
LandingPage
├── Header
│   ├── Logo
│   └── Navigation (desktop only)
├── HeroSection
│   ├── Headline
│   ├── Subheadline
│   ├── PrimaryCTA
│   ├── SecondaryCTA
│   └── HeroIllustration
├── WhatIsMaxergySection
│   ├── Description
│   ├── KeyStats (StatCard[])
│   └── VisualElement
├── HowItWorksSection
│   ├── SectionTitle
│   └── StepCards (StepCard[])
├── ExampleOutputSection
│   ├── BenchmarkBadge
│   ├── HeadlineSavings
│   ├── HouseholdSummaryCards
│   ├── RecommendedPlanCard
│   ├── CumulativeSavingsMiniChart
│   └── PersonalEstimateCTA
├── FeaturesSection
│   ├── SectionTitle
│   └── FeatureCards (FeatureCard[])
├── FAQSection
│   ├── SectionTitle
│   └── FAQItems (FAQItem[])
└── Footer
    ├── Logo
    ├── Tagline
    ├── NavigationLinks
    ├── SocialLinks
    └── Copyright
```

### 1.5 User Flow

```
Landing Page (/)
    │
    ├─→ User clicks "Start Your Assessment" (Primary CTA)
    │   └─→ Redirects to /assessment (current index.tsx)
    │
    ├─→ User clicks "Learn More" (Secondary CTA)
    │   └─→ Smooth scroll to "What is MAXergy" section
    │
    └─→ User clicks "Get Your Personal Estimate" (Example Output CTA)
        └─→ Redirects to /assessment
```

---

## 2. Content Development

### 2.1 Hero Section

**Headline (H1):**
> Plan your energy upgrade with confidence

**Subheadline:**
> AI-powered analysis for German households. See how solar, batteries, heat pumps, and EV charging could save you money over 20 years.

**Primary CTA:**
> Start Your Assessment

**Secondary CTA:**
> Learn More

**Hero Illustration Concept:**
- Modern home with solar panels
- Subtle energy flow visualization
- Clean, minimalist style
- Uses MAXergy brand colors (lime primary, violet secondary)

### 2.2 What is MAXergy

**Section Title (H2):**
> What is MAXergy?

**Description:**
> MAXergy is an AI-powered home energy upgrade planner designed specifically for German households. We help you understand the financial impact of energy efficiency upgrades like solar PV, battery storage, heat pumps, and EV charging.

**Key Statistics (Stat Cards):**

| Stat | Value | Label |
|------|-------|-------|
| Scenarios Analyzed | 6 | Upgrade options compared |
| Projection Horizon | 20 years | Long-term cost analysis |
| Market Specific | ✓ | German tariffs & subsidies |
| AI-Powered | ✓ | Personalized recommendations |

**German Market Context:**
> Built for the German energy market with current tariffs (Arbeitspreis, Grundpreis), EEG feed-in tariffs, and subsidy considerations.

### 2.3 How It Works

**Section Title (H2):**
> How it works

**Step 1: Tell us about your home**
- Complete a 9-step assessment
- Share your energy usage, building characteristics, and upgrade preferences
- Takes approximately 5-10 minutes

**Step 2: We analyze your energy use**
- Baseline forecast calculates your current energy costs
- Uses your actual tariffs and consumption patterns
- Accounts for seasonal variations

**Step 3: See upgrade scenarios**
- Compare 6 different upgrade options
- Solar only, solar + battery, heat pump, EV charging, and combinations
- View costs, savings, and ROI for each scenario

**Step 4: Get personalized recommendations**
- AI selects the optimal scenario based on your situation
- See break-even timing and long-term projections
- Understand financing options

**Step 5: Chat with AI advisor**
- Ask questions about your results
- Get explanations of savings calculations
- Explore what-if scenarios

### 2.4 What You'll Get

**Section Title (H2):**
> What you'll get

**Output Types:**

| Output | Description |
|--------|-------------|
| **Cost Breakdown** | Monthly and annual energy costs for baseline and each upgrade scenario |
| **Savings Analysis** | Net savings calculations with break-even timing |
| **20-Year Projections** | Long-term cost projections under low, central, and high price scenarios |
| **Scenario Comparison** | Side-by-side comparison of all 6 upgrade options |
| **Financing Analysis** | Monthly instalments, total repayment, and payback timeline |
| **AI Recommendations** | Personalized advice and explanations |

### 2.5 Why MAXergy

**Section Title (H2):**
> Why MAXergy?

**Key Benefits:**

| Benefit | Description |
|---------|-------------|
| **German Market Specific** | Built for German tariffs, subsidies, and regulations |
| **Data-Driven** | All calculations based on your actual input, not generic assumptions |
| **Transparent** | Clear methodology, visible assumptions, no hidden fees |
| **Comprehensive** | Analyzes 6 scenarios across electricity, heating, and mobility |
| **AI-Powered** | Intelligent recommendations and personalized advice |
| **Future-Proof** | 20-year projections help you make long-term decisions |

### 2.6 FAQ Section

**Section Title (H2):**
> Frequently Asked Questions

**Q1: How accurate are the savings estimates?**
> A: Our estimates are based on your actual energy consumption, current tariffs, and German market conditions. The 20-year projections use different price scenarios (low, central, high) to show sensitivity to energy price trends. Short-term estimates (12 months) use constant prices validated against historical data. All calculations follow a documented methodology.

**Q2: What data do I need to provide?**
> A: You'll need information about your household (occupants, location), energy usage (electricity bills, heating fuel), building characteristics (roof area, orientation), and mobility (vehicle type, annual mileage). The assessment takes about 5-10 minutes to complete.

**Q3: How long does the assessment take?**
> A: The 9-step assessment typically takes 5-10 minutes. Once submitted, your personalized results are generated immediately.

**Q4: Is my data secure?**
> A: Yes. Your data is processed securely and is not shared with third parties. We use industry-standard security practices to protect your information.

**Q5: Can I save my results?**
> A: Yes. After completing the assessment, you can save your results and return to them later. Your personalized analysis remains available for future reference.

**Q6: What if I don't have a roof suitable for solar?**
> A: MAXergy analyzes all scenarios, including those that don't require solar panels (e.g., heat pump only, EV charging only). The recommendation engine will suggest the best option for your specific situation.

### 2.7 Footer Content

**Logo + Tagline:**
> MAXergy
> Plan your energy upgrade with confidence

**Navigation Links:**
- About
- Contact
- Privacy Policy
- Terms of Service
- Imprint (Impressum)

**Copyright:**
> © 2026 MAXergy. All rights reserved.

**Contact:**
> contact@maxergy.de

---

## 3. Visual Design Assets

### 3.1 Hero Illustration

**Style:** Modern, clean, minimalist  
**Elements:** Home with solar panels, energy flow visualization  
**Colors:** MAXergy brand palette (background #111827, primary lime #B8FF5A, secondary violet #6C63FF)  
**Format:** SVG for scalability, fallback PNG for older browsers  
**Alt Text:** "Modern home with solar panels and energy flow visualization showing MAXergy's energy upgrade planning capabilities"

### 3.2 Feature Icons

**Icon Set:** Lucide React (already in use in frontend)  
**Icons per section:**

| Section | Icons |
|---------|-------|
| How It Works | Home, Calculator, LayoutGrid, Sparkles, MessageSquare |
| Features | Zap, Battery, Thermometer, Car, TrendingUp, Shield |
| Stats | Users, Calendar, CheckCircle, Brain |

### 3.3 Example Output Mockup

**Components:**
- Savings headline: Large number display with Euro symbol
- Household summary: Card-based layout with key metrics
- Recommended plan: Highlighted card with scenario details
- Cumulative savings chart: Simplified line chart showing 20-year projection

**Design Reference:** Use the dashboard design from `documentation/figures/design/maxergy_dashboard_reference_v1_mobile.png` as visual guidance, but adapt for landing page context (simplified, less detailed).

### 3.4 CTA Button Styles

**Primary CTA:**
- Background: MAXergy lime (#B8FF5A)
- Text: Dark (#111827)
- Hover: Slightly lighter lime with subtle shadow
- Active: Pressed state with darker lime
- Border radius: 8px
- Padding: 12px 24px
- Font weight: 600

**Secondary CTA:**
- Background: Transparent
- Text: MAXergy lime (#B8FF5A)
- Border: 2px solid lime
- Hover: Lime background with dark text
- Border radius: 8px
- Padding: 12px 24px
- Font weight: 600

### 3.5 Loading States and Animations

**Scroll Effects:**
- Fade-in on scroll (using Intersection Observer)
- Staggered animation for cards and steps
- Smooth scroll for anchor links
- Respects `prefers-reduced-motion` media query

**Loading States:**
- Skeleton loaders for dynamic content
- Spinner for async data fetching
- Progressive image loading with blur-up effect

---

## 4. Copywriting Guidelines

### 4.1 Tone of Voice

**Primary Attributes:**
- **Helpful:** Clear, supportive language that guides users
- **Clear:** Avoid jargon, explain technical terms when necessary
- **Pragmatic:** Focus on actionable information and realistic expectations
- **Trustworthy:** Transparent about assumptions and limitations
- **Professional:** Appropriate for financial/energy decisions

**Voice Examples:**

| Instead of | Use |
|------------|-----|
| "Revolutionize your home" | "Plan your energy upgrade with confidence" |
| "Amazing savings guaranteed" | "See projected savings based on your situation" |
| "Cutting-edge AI technology" | "AI-powered analysis for personalized recommendations" |
| "Don't miss out" | "Understand your options before you decide" |

### 4.2 German Market Context

**Key Terms to Include:**
- **Arbeitspreis:** Energy unit price (€/kWh)
- **Grundpreis:** Monthly standing charge
- **EEG feed-in tariff:** Solar feed-in compensation
- **Subsidies:** Mention KfW, BAFA, and other German subsidy programs
- **Tariffs:** Reference current German energy market tariffs
- **Regulations:** Acknowledge German energy transition (Energiewende) context

**Context Statements:**
- "Built for the German energy market"
- "Accounts for German tariffs and regulations"
- "Considers subsidy eligibility where applicable"
- "Aligned with Energiewende goals"

### 4.3 Technical Terms Glossary

| Term | Definition | When to Use |
|------|------------|-------------|
| **Arbeitspreis** | The variable price per kilowatt-hour of energy consumed | When explaining electricity costs |
| **Grundpreis** | The fixed monthly charge for energy service | When explaining electricity costs |
| **SCOP** | Seasonal Coefficient of Performance - heat pump efficiency metric | When discussing heat pumps |
| **kWp** | Kilowatt peak - solar system capacity rating | When discussing solar panels |
| **Feed-in tariff** | Rate paid for solar energy fed into the grid | When discussing solar economics |
| **Break-even** | Point where cumulative savings equal investment costs | When explaining ROI |
| **Cumulative savings** | Total savings over time, accounting for financing | When showing long-term results |

### 4.4 Accessibility Alt Text

**Guidelines:**
- Describe the content and function of the image
- Include relevant context for the user's task
- Keep concise (typically under 125 characters)
- Use "decorative" for purely visual elements

**Examples:**

| Image | Alt Text |
|-------|----------|
| Hero illustration | "Modern home with solar panels showing energy upgrade planning" |
| Step 1 icon | "Icon representing home assessment" |
| Savings chart | "Line chart showing 20-year cumulative savings projection" |
| Feature icon (solar) | "Icon representing solar panel system" |

### 4.5 German-Language Readiness

**Formatting Considerations:**
- Number formatting: Use German locale (de-DE)
  - Decimal separator: comma (,) not period (.)
  - Thousand separator: period (.) or space
  - Example: €24.828,00 or €24 828,00
- Date formatting: DD.MM.YYYY
- Currency: Always Euro (€) symbol before amount
- Time: 24-hour format

**Translation Notes:**
- All copy should be translatable to German
- Avoid idioms that don't translate well
- Keep sentences relatively short and direct
- Use formal address (Sie) for German version

**Locale Configuration:**
- Set `de-DE` as default locale for German version
- Use `Intl.NumberFormat` with `de-DE` for currency
- Use `Intl.DateTimeFormat` with `de-DE` for dates

---

## 5. Benchmark Data Integration

### 5.1 Data Source

**Input File:** `documentation/data/test_profiles/average_german_household.json`  
**Output File:** `documentation/data/test_outputs/average_german_household_output.json`

### 5.2 Key Benchmark Values

**Household Profile:**
- Location: Cologne (50667)
- Occupants: 3
- Electricity: 3,500 kWh/yr @ €0.31/kWh
- Heating: Gas, 14,000 kWh/yr
- Mobility: Petrol, 12,000 km/yr
- Roof: 35 m², south-facing, 32° tilt

**Recommended Scenario:** Full Upgrade (solar + battery + heat pump + EV)

**Key Results (from model output):**
- 20-year cumulative savings: €24,828 (central scenario)
- Break-even: Year 8
- Monthly instalment: €209.35
- Year 1 net savings: -€297 (negative due to financing)

### 5.3 Display Requirements

**Mandatory Attribution:**
> "These figures describe a typical German household benchmark. They are not yet personalised for your home."

**CTA Context:**
> "See what the estimate could look like for your own home."

---

## 6. Success Criteria for Phase 1

Phase 1 is complete when:

- [x] Landing page sections are defined and documented
- [ ] Mobile-first wireframe is created
- [ ] Responsive breakpoints are specified
- [ ] Component hierarchy is planned
- [ ] User flow from landing to assessment is defined
- [ ] All section copy is written
- [ ] Tone of voice guidelines are established
- [ ] German market context is defined
- [ ] Technical glossary is created
- [ ] Accessibility guidelines are documented
- [ ] German-language readiness is ensured
- [ ] Visual design assets are specified
- [ ] Benchmark data integration is planned

---

## 7. Next Steps (Phase 2)

Once Phase 1 is approved, proceed to:

1. Create visual wireframes/mockups
2. Develop design system components
3. Set up TanStack Start landing route
4. Implement Hero section component
5. Implement remaining section components
6. Integrate benchmark data API
7. Test responsive design
8. Optimize performance

---

**Document Status:** Draft  
**Next Review:** After visual wireframes are created  
**Approvals:** Pending
