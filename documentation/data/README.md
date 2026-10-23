# Data files

| Path | What it is |
| ---- | ---------- |
| `model_input1.json` | Example `HouseholdAssessment` (API request; also `backend/tests/fixtures/model_input1.json`) |
| `model_output_v2.json` | API `ForecastResult` for `model_input1.json` from the production engine |
| `model_output.json`, `model_output_forecast.json`, `model_output_upgrade_comparison.json` | Raw production-engine outputs (`scripts/energy_model`) |
| `model_output_legacy.json` | Output of the retired legacy engine (`research/legacy/`); optimistic, reference only |
| `test_profiles/` | Three household profiles (see below) |
| `test_outputs/` | Engine outputs and the summary (`model_test_summary.json` / `.md`) for the three profiles |

## Test profiles

`test_profiles/average_german_household.json`, `low_benefit_household.json` and
`high_benefit_household.json` are **full `HouseholdAssessment` documents** (same shape as the
web/mobile apps and the MCP send to `POST /plan`), plus a `_profile_notes` block that documents
where each value comes from (the API ignores it).

- `roof.available: true`, `current_tariff_type: "fixed"`, `heating.building` (floor area and
  insulation from the notes; not used by the engine), `mobility.vehicles` with one car,
  `upgrade_candidates` all `true`.
- Converting them from the earlier flat engine format did not change the engine output: the
  engine reads them as-is (CLI, `tests/test_profile_runs.py`) and the API path
  (validation → normalizer → engine) gives the same result.
- `backend/tests/test_profiles.py` runs each profile through the API path and `/plan` and checks
  the best plan and its monthly loan instalment against `test_outputs/model_test_summary.json`.

**Run-date dependence:** the engine starts its forecast in the month after the run date, so the
first year's seasonal mix — and the cumulative totals that build on it — change with the date a
profile is run. Example: the average household's 20-year central net saving is €24,828 in the
stored July-start run and about €24,500 for a November start. Loan instalments, scenario sizes and
the best plan do not depend on the run date.

## Recorded API responses used by tests and mocks

`backend/mcp/tests/fixtures/plan_model_input1.json` (POST `/plan` for `model_input1.json`) is also
used by the web and mobile mock modes; `backend/mcp/tests/fixtures/assumptions.json` (GET
`/assumptions`) is also checked by the mobile defaults test. Re-record both when the API contract or
the engine defaults change.
