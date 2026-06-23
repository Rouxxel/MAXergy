# Handoff: implement the shared model I/O structure from the teammate's template

You are picking up work on **MAXnergy**, a Python **FastMCP** energy-transition advisor
(MCP server). This file is a self-contained brief — the previous session built the server;
you're implementing a new data-model contract a teammate defined. Read it fully before coding.

---

## 1. Project context (what MAXnergy is)

- **Repo:** `/Users/sandbox1/maxnergy-mcp` (package `maxnergy_mcp`). Python 3.12, `uv`,
  FastMCP **3.4.2**, pydantic **v2**, httpx.
- **What it does:** an LLM advisor (the client model) runs a conversational onboarding,
  then calls MCP tools that do the credible math: roof geometry (Google Solar API),
  PV production (PVGIS, keyless), and household savings across **electricity / heating /
  mobility**. North Star = **€/month saved** vs. today, financing-anchored, shown honestly
  (cost-neutral now → saves after payoff).
- **Status:** deployed on Railway (auto-deploys on `git push` to `main`), reachable as a
  claude.ai custom connector. ~12 tools live. Supports homes **and** commercial buildings
  via a `building_type` parameter (no branching). Has request/tool/API logging.
- **Run locally:** `uv run maxnergy-mcp` (stdio). It auto-switches to HTTP when `PORT` is set.

### Files you'll touch / reuse
- `src/maxnergy_mcp/models.py` — pydantic models: `HouseholdProfile`, `Scenario`,
  `SavingsResult`, `RoofGeometry`, `Car`, `HeatingType`.
- `src/maxnergy_mcp/savings.py` — current engine: `evaluate_scenario()`,
  `FUEL_PRICE_EUR_PER_KWH`, `_self_consumption_ratio()`, `CAPEX`, annuity helper.
- `src/maxnergy_mcp/suggestions.py` — benchmarks: heating demand by building type,
  `daytime_load_fraction`, electricity price by building, battery sizing, roof-from-area.
- `src/maxnergy_mcp/providers.py` — `geocode()`, `get_roof_geometry()` (Google Solar),
  `estimate_pv_production()` (PVGIS). All log to `maxnergy.google`.
- `src/maxnergy_mcp/server.py` — tool registration (`@mcp.tool`), the `ONBOARDING_SCRIPT`,
  and existing tools incl. `compare_scenarios`, `project_savings`, `recommend_upsell`.
- `src/maxnergy_mcp/logging_setup.py` / `logging_middleware.py` — logging (reuse the loggers).

---

## 2. The task

A teammate defined the **canonical model input/output schema** the team will standardize on
(so the modeling backend and the frontend agree). Implement it in MAXnergy.

**Template files (read these first, they are the spec):**
- Input:  `/Users/sandbox1/MAXergy/documentation/data/model_input1.json`
- Output: `/Users/sandbox1/MAXergy/documentation/data/model_output_1.json`

Deliver, in order of priority:
1. **Pydantic v2 models** that exactly match the input and output JSON (field names, nesting,
   types, nullability). Put them in a new module, e.g. `src/maxnergy_mcp/model_schema.py`.
2. **An engine** that maps a validated input → the full output (baseline + the 6-scenario
   ladder + short/long-term forecasts + savings + payback). New module, e.g.
   `src/maxnergy_mcp/model_engine.py`. Reuse existing physics/heuristics where sensible.
3. **One MCP tool** that runs it and returns the output. **Naming: do NOT call it
   `recommend_upsell` or anything salesy.** Frame it positively as an *overview* — e.g.
   `energy_savings_overview` / `home_energy_overview`. (The challenge is about selling the
   *outcome*, a clear monthly number, not pushing an upsell. The existing `recommend_upsell`
   tool can stay for now, but the new structured output is the headline; prefer the positive
   framing everywhere user-facing.)

---

## 3. The template, decoded (so you don't have to reverse-engineer blind)

### Input (`model_input1.json`) — top-level keys
`location` {postcode, country} · `household` {occupants, electricity{annual_kwh,
current_tariff_type, arbeitspreis_eur_per_kwh, grundpreis_eur_per_month, contract_end_date},
roof{available, usable_area_m2, orientation, tilt_deg, shading_factor}} · `heating`
{fuel_type, annual_consumption, annual_spend_eur, building{floor_area_m2, insulation_class}} ·
`mobility` {vehicle_count, vehicles[]{vehicle_type, annual_mileage_km,
fuel_consumption_l_per_100km, annual_fuel_spend_eur}} · `upgrade_candidates`
{solar_pv, battery, heat_pump, ev_charger booleans + nullable solar_pv_kwp/battery_kwh/
heat_pump_kw overrides} · `financing` {loan_term_years, loan_rate_pct, known_subsidy_eur} ·
`forecast_horizon` {short_term_months, long_term_years}.

### Output (`model_output_1.json`)
- `baseline`: `monthly_cost_eur` {electricity, heating, mobility, total};
  `short_term_forecast[]` {month "YYYY-MM", total_eur}; `long_term_forecast[]` {year,
  annual_total_eur}.
- `scenarios[]` — fixed ladder of ids: `solar_only`, `pv_battery`, `pv_heatpump`, `pv_ev`,
  `pv_battery_heatpump`, `full_upgrade`. Each has: `components` (4 bools), `sizing`
  {solar_pv_kwp, battery_kwh?, heat_pump_kw?}, `monthly_cost_eur` {electricity, heating,
  mobility, financing_installment, total}, `monthly_saving_eur`,
  `monthly_saving_post_payoff_eur` (**only present when the now-saving is negative**),
  `self_consumption_ratio`, `short_term_forecast[]` {month, total_eur, saving_eur},
  `long_term_forecast[]` {year, annual_total_eur, annual_saving_eur}, `payback_month`.

### Mechanics I verified from the numbers (match these)
- **Baseline monthly:** electricity = `annual_kwh*arbeitspreis/12 + grundpreis`; heating =
  `annual_spend_eur/12`; mobility = `annual_fuel_spend_eur/12`. (Example: 124.5 / 120.83 /
  91.67 → total 337.0.)
- **Short-term seasonality:** the flat total is redistributed monthly via a **heating
  seasonal profile** (summer low, winter high) that **averages back to the flat annual**.
  In the example heating swings ~75 €/mo (Jul) to ~175 €/mo (Dec); electricity+mobility stay
  flat. The 12 monthly totals average exactly to 337.0. Build a German monthly heating-weight
  profile.
- **Long-term escalation:** annual totals grow ~**3.3%/yr** (energy price inflation).
- **Loan-payoff cliff:** at `loan_term_years` (here year 15 → 2041) the
  `financing_installment` ends, so `annual_saving_eur` **jumps** that year. Model the
  installment as present for `loan_term_years`, then gone.
- **Sizing derivation:** `solar_pv_kwp` ≈ `roof.usable_area_m2 / 7` (≈0.143 kWp/m²; example
  40 m² → 5.71). `heat_pump_kw` ≈ `floor_area_m2 * ~0.075` (example 120 → 9.0). `battery_kwh`
  ≈ ~1.3 kWh/kWp (example 7.5). Honor explicit overrides in `upgrade_candidates` when non-null.
- **self_consumption_ratio** is preset-ish per component combo: solar_only 0.30, +battery
  0.65, +heat_pump 0.45, +ev 0.40, +battery+heat_pump 0.75, full 0.80. (Aligns with the
  existing `daytime_load_fraction` logic — reuse/extend it rather than hardcode if clean.)
- **Financing:** annuity on capex at `loan_rate_pct` over `loan_term_years`, minus
  `known_subsidy_eur` if set. (Existing `savings.py` has `_annuity_monthly` and a `CAPEX`
  dict — note the template implies ~980 €/kWp solar; reconcile or document your capex choice.)
- **payback_month:** first month where cumulative savings ≥ cumulative outlay (or financing
  paid back). solar_only 77, pv_heatpump 144, etc.
- **monthly_saving_post_payoff_eur** appears ONLY on scenarios negative-now (the heat-pump
  ones) — the honest "cost-neutral now, saves €X after payoff" framing. Emit it conditionally.

---

## 4. Mapping the template to MAXnergy's existing model (decisions to make)

The template's input differs from `HouseholdProfile`. Decide and **state your choice in a
comment + the PR/commit**:
- **Location:** template uses `postcode`+`country`; MAXnergy uses address→geocode→lat/lon, and
  **PVGIS needs lat/lon**. Geocode the postcode (Google Geocoding via `providers.geocode`) to
  get lat/lon for PVGIS, or accept lat/lon as optional extra input. Postcode-centroid is fine
  for irradiance.
- **Tariff:** template splits `arbeitspreis`/`grundpreis` (German work/base price) vs.
  MAXnergy's single `electricity_price_eur_per_kwh`. Use the template fields as canonical.
- **Insulation:** template `insulation_class` vs. MAXnergy `building_type`/heating-demand
  table — map classes to demand or reuse `suggestions.HEATING_DEMAND_KWH_PER_M2`.
- **Canonical input:** prefer adopting the template schema as the new public contract; map to
  internal `HouseholdProfile`/`Scenario` under the hood, OR compute directly. Don't rewrite the
  existing engine if you can compose it.
- **Consolidation:** the template output supersedes what `compare_scenarios` + `project_savings`
  + `recommend_upsell` do separately. You may keep them, but the new overview tool should be the
  primary, positively-framed entry point. Don't delete working tools without reason — surface
  the question if you think they should go.

Reuse, don't reinvent: `providers` (roof/PVGIS, already logged), `suggestions` (benchmarks),
`savings` (annuity, fuel prices, self-consumption, capex), and the loggers (`maxnergy.*`).

---

## 5. Conventions & constraints

- Pydantic **v2** (`model_validate` / `model_dump`), FastMCP **3.4.2** (`@mcp.tool`,
  `mcp.add_middleware`). Match the surrounding code style, naming, and comment density.
- Keep tools' return values JSON-serializable dicts (use `.model_dump(mode="json")`).
- Reuse the existing logging — new tools are auto-logged by `ToolLoggingMiddleware`; add
  `maxnergy.*` log lines for any new external call.
- **Don't break existing tools or the deploy.** Don't change existing tool signatures.
- Keep secrets out of logs (the helpers in `logging_setup.sanitize` already do this).
- Validate against the template: round-tripping `model_input1.json` through your input model
  must succeed, and your engine's output must structurally match `model_output_1.json`
  (same keys/nesting; numeric values will differ with your assumptions — that's fine, but
  document material deltas).

## 6. Test & deploy
- **Local:** `uv venv && uv pip install -e .` then `uv run maxnergy-mcp`. Unit-test the engine
  by loading `model_input1.json` and asserting the output schema validates + key invariants
  (baseline total = sum of buckets; short-term months average to the flat annual; savings sign;
  payback present). A quick `pytest` or a `__main__` smoke script is fine.
- **MCP check:** call the new tool through an MCP client (or the existing test pattern in the
  repo's history) and confirm it returns the structured output.
- **Deploy:** commit + `git push origin main` → Railway auto-deploys (Railpack builder;
  `railway.toml`). The previous session used the Railway CLI/MCP to watch deploys; uvicorn logs
  + `maxnergy.tools`/`maxnergy.google` lines show the request story.
- **Connector (if you need to test live in the app):** it's a passphrase-gated OAuth connector
  at `https://maxnergy-production.up.railway.app/mcp`. Don't change auth.

## 7. Acceptance
- New input/output pydantic models matching both template JSONs (validate the sample input).
- An engine producing the full output (baseline + 6 scenarios + short/long forecasts +
  savings + payback + conditional post-payoff saving), with seasonality, ~3.3% escalation, and
  the loan-payoff cliff.
- One **positively-named overview** MCP tool exposing it (NOT `recommend_upsell`).
- Existing tools and the deploy still work. Document your input-mapping and capex decisions.

---

### Reference: the previous session also built (so you have the lay of the land)
Onboarding driven by a server-side `start_advisor` script (the claude.ai connector gets no
system prompt); suggest-then-confirm helpers (roof kWp, heating spend from floor area, battery
size, electricity price, roof-from-area fallback when the Solar API locks onto a small annex);
commercial support via `building_type` + load-shape self-consumption + optional peak-demand
bucket; a `project_savings` tool returning multi-line cumulative-savings chart data; and full
logging. The new template-based overview should feel consistent with that — outcome-first,
honest about cost-neutral-now-vs-saves-later, homes and businesses alike.
