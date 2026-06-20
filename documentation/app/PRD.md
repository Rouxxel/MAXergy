# PRD.md

# MAXergy Energy Transition Planner

## Vision

Enable homeowners to understand and purchase a complete home-energy upgrade based on one simple metric:

**Monthly Savings**

Instead of selling solar panels, batteries, heat pumps, EV chargers, financing, and tariffs separately, MAXergy presents a unified energy transition plan that minimizes total monthly household spending.

## Problem Statement

Consumers struggle to understand:

- Which energy upgrades are worth it
- How financing affects affordability
- Whether batteries or heat pumps make financial sense
- How dynamic tariffs influence savings

Current sales processes focus on hardware first and economics second.

The result is confusion and low conversion.

## Goal

Create an AI-powered advisor that:

1. Collects minimal household information
2. Models current energy spending
3. Simulates upgrade scenarios
4. Finds the highest monthly-saving configuration
5. Explains recommendations in plain language

## North Star Metric

Monthly Savings

Formula:

Monthly Savings =
Current Monthly Energy Spend
-
Future Monthly Energy Spend
-
Financing Payment

Displayed prominently throughout the experience.

## User Personas

### Homeowner

Interested in reducing energy bills.

Needs:

- Quick estimate
- Trustworthy numbers
- Simple explanations

### Energy Installer

Needs:

- Proposal-ready explanation
- Upsell opportunities
- Faster lead qualification

## User Journey

1. Open app
2. Complete household questionnaire
3. Generate savings forecast
4. View recommendation
5. Explore scenarios
6. Read AI explanation
7. Export/share proposal

## Functional Requirements

### Household Assessment

Collect:

- Country
- Postal code
- Monthly electricity spend
- Heating type
- Heating spend
- Vehicle ownership
- Fuel spend
- Roof size estimate
- Financing term

### Scenario Engine

Generate:

- Solar Only
- Solar + Battery
- Solar + Battery + Heat Pump
- Solar + Battery + EV Charger
- Full Upgrade

### Recommendation Engine

Select scenario maximizing:

Monthly Savings

Subject to:

- Household suitability
- Roof constraints
- Financing assumptions

### AI Advisor

Generate:

- Recommendation summary
- Savings explanation
- Upsell opportunities
- Proposal-ready text

### Results Dashboard

Display:

- Monthly Savings
- Current vs Future Spend
- Financing Cost
- ROI
- Payback Timeline
- Carbon Reduction

## Non Functional Requirements

- Mobile-first
- Response time < 10 seconds
- GDPR compliant
- Explainable recommendations
- API-first architecture

## Success Criteria

- User completes assessment in <3 minutes
- Forecast generated in <10 seconds
- Clear monthly savings shown
- AI recommendation generated automatically
