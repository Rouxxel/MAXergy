# PRODUCT.md

# Cloover – The Household Energy Transition Planner

## Product Narrative

People do not buy solar panels.

They buy lower monthly costs.

Cloover transforms complex energy upgrades into a simple financial decision.

Instead of asking:

> Do you want solar panels?

We answer:

> How much could you save every month?

## Core Product Promise

- One Household
- One Upgrade Plan
- One Monthly Number

## Key Differentiator

Traditional process:

Solar → Financing → Tariff

Cloover process:

Outcome → Upgrade Bundle

The customer sees a single monthly savings figure generated from:

- Solar production
- Battery arbitrage
- Heat pump efficiency
- EV charging optimization
- Dynamic tariffs
- Financing

## Product Principles

### Outcome First

Always lead with savings — honestly. Every result shows the same three numbers:

1. **Monthly net in year 1**, loan instalment included ("During financing: −€X/month" when the
   instalment outweighs the early savings);
2. **After payoff**: the monthly saving once the loan is repaid;
3. **N-year net**: cumulative net savings over the horizon (central prices, with a low/high range).

No unbacked trust claims ("live tariffs", "verified ROI"); results are labelled as model estimates
with their assumptions shown.

### Explainability

Every recommendation must be justified.

### Upsell Through Value

Additional upgrades are recommended only if they increase savings.

Example:

Adding a heat pump increases savings from €42/month to €88/month.

### Minimal Input

A user should complete onboarding in less than three minutes.

## Recommendation Logic

Generate:

- Solar
- Solar + Battery
- Solar + Heat Pump
- Solar + Battery + Heat Pump
- Full Bundle

Rank by:

- Cumulative net savings over the horizon (central price scenario) — default
- Monthly net savings in year 1 — available as an alternative metric

Select the highest-value scenario. Long-term ranking is the default because many bundles cost
slightly more per month while the loan runs and only pay off afterwards (decision #1 in
`API_CONTRACT.md`).

## AI Advisor Responsibilities

Generate:

- Personalized recommendation
- Savings explanation
- Financing explanation
- Upgrade justification
- Proposal-ready text

## Example Output

Example from the production engine for `documentation/data/model_input1.json` (2-person house in
Berlin, gas heating, one petrol car, 15-year loan at 4.5 %):

Recommended Plan:

Full upgrade (solar + battery + heat pump + EV charger)

During financing: −€39/month · After payoff: +€179/month · 20-year net: +€21,960

Reason:

Your household currently spends about €337/month on electricity, heating and mobility.

The upgrades cut energy costs substantially, but during the 15-year loan the instalment (€218/month)
is slightly larger than the savings, so you pay about €39/month more than today. Once the loan is
repaid you save about €179/month at today's prices. Over 20 years the cumulative net saving is
about €21,960 (€7,243 to €42,855 depending on energy prices), breaking even in year 12.

## Future Roadmap

### Phase 1

Forecasting MVP

### Phase 2

Real tariff integrations

### Phase 3

Installer CRM

### Phase 4

Checkout and financing approval

### Phase 5

Full Cloover financing workflow
