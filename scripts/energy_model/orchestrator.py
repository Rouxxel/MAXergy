"""ScenarioOrchestrator: baseline + all 6 upgrade scenarios across 3 price scenarios.

Short-term forecast (monthly records):
  • Uses ConstantShortTermPriceModel — prices held constant at user's current tariff.
  • Central scenario only (constant model is scenario-agnostic).

Long-term projection (annual aggregates):
  • Uses ScenarioPriceModel — deterministic annual trend per scenario.
  • All three scenarios (low / central / high), nested by key.

Financing is deterministic (independent of price scenario).  Investment costs
and loan schedules are computed once per upgrade scenario and injected into
both the short-term and long-term sections of the output.
"""

from __future__ import annotations

from datetime import date

from energy_model.consumption import CONSUMPTION_CONFIG, ConsumptionModel
from energy_model.financing import FinancingInput, FinancingModel, LoanSchedule
from energy_model.input_validator import (
    EnergyCostCalculator,
    ParsedInput,
    _iter_months,
)
from energy_model.investment_costs import (
    InvestmentCostDefaults,
    ScenarioInvestment,
    compute_scenario_investment,
)
from energy_model.price_models import (
    ConstantShortTermPriceModel,
    PriceModelProtocol,
    ScenarioPriceModel,
)
from energy_model.setup_models import (
    PRICE_SCENARIOS,
    UPGRADE_SCENARIO_NAMES,
    AnnualUpgradeRecord,
    MonthlyUpgradeRecord,
    UpgradeInput,
)
from energy_model.solar import feed_in_tariff, resolve_kwp
from energy_model.upgrade_model import SCENARIO_FLAGS, UpgradeEnergyModel


def _forecast_start() -> date:
    today = date.today()
    sm, sy = today.month + 1, today.year
    if sm > 12:
        sm, sy = 1, sy + 1
    return date(sy, sm, 1)


class ScenarioOrchestrator:
    """Wires ConsumptionModel, price models, UpgradeEnergyModel, and FinancingModel.

    Accepts optional constructor overrides for testability.

    st_price_model  — used for the short-term constant-price forecast.
    lt_price_model  — used for the long-term scenario projections.
    """

    def __init__(
        self,
        consumption_model: ConsumptionModel | None = None,
        st_price_model: PriceModelProtocol | None = None,
        lt_price_model: PriceModelProtocol | None = None,
        calculator: EnergyCostCalculator | None = None,
    ) -> None:
        self._cons = consumption_model or ConsumptionModel()
        self._st_price = st_price_model or ConstantShortTermPriceModel()
        self._lt_price = lt_price_model or ScenarioPriceModel()
        self._calc = calculator or EnergyCostCalculator()

    # ── Public entry point ────────────────────────────────────────────────────

    def run(
        self,
        inp: ParsedInput,
        upgrade: UpgradeInput,
        financing: FinancingInput | None = None,
    ) -> dict:
        """Return the full comparison output dict (all 3 price scenarios).

        When *financing* is None a default FinancingInput() is used and a
        warning is added to the output.
        """
        if financing is None:
            financing = FinancingInput()

        start_date = _forecast_start()
        st_n = inp.short_term_months
        lt_n = inp.long_term_years
        lt_months = lt_n * 12
        schedule_months = max(st_n, lt_months)

        # Resolve upgrade sizing; record provenance in upgrade object
        upgrade, kwp, fit = self._resolve_upgrade(inp, upgrade)
        bat_kwh = self._resolve_battery_kwh(upgrade)

        # ── Investment cost defaults (merge user overrides) ──────────────────
        _d = InvestmentCostDefaults()
        inv_defaults = InvestmentCostDefaults(
            pv_eur_per_kwp=financing.pv_eur_per_kwp if financing.pv_eur_per_kwp is not None else _d.pv_eur_per_kwp,
            battery_eur_per_kwh=financing.battery_eur_per_kwh if financing.battery_eur_per_kwh is not None else _d.battery_eur_per_kwh,
            heat_pump_eur_fixed=financing.heat_pump_eur_fixed if financing.heat_pump_eur_fixed is not None else _d.heat_pump_eur_fixed,
            ev_charger_eur_fixed=financing.ev_charger_eur_fixed if financing.ev_charger_eur_fixed is not None else _d.ev_charger_eur_fixed,
            ev_purchase_eur=financing.ev_purchase_eur,
        )

        # ── Per-scenario investment and financing ────────────────────────────
        fin_model = FinancingModel()
        scenario_investments: dict[str, ScenarioInvestment] = {}
        loan_schedules: dict[str, LoanSchedule] = {}

        for sn in UPGRADE_SCENARIO_NAMES:
            inv = compute_scenario_investment(
                sn, kwp, bat_kwh, inv_defaults, financing.ev_purchase_eur
            )
            scenario_investments[sn] = inv
            loan_schedules[sn] = fin_model.compute(
                inv.gross_investment_eur, financing, schedule_months
            )

        _prov_sources = {
            "pv_eur_per_kwp": "user" if financing.pv_eur_per_kwp is not None else f"default:{_d.pv_eur_per_kwp} EUR/kWp",
            "battery_eur_per_kwh": "user" if financing.battery_eur_per_kwh is not None else f"default:{_d.battery_eur_per_kwh} EUR/kWh",
            "heat_pump_eur_fixed": "user" if financing.heat_pump_eur_fixed is not None else f"default:{_d.heat_pump_eur_fixed} EUR",
            "ev_charger_eur_fixed": "user" if financing.ev_charger_eur_fixed is not None else f"default:{_d.ev_charger_eur_fixed} EUR",
            "ev_purchase_eur": f"user:{financing.ev_purchase_eur} EUR" if financing.ev_purchase_eur > 0 else "default:0 EUR (charger only, no EV purchase)",
            "known_subsidy_eur": "user" if financing.known_subsidy_eur > 0 else "default:0 EUR (no subsidy assumed)",
            "upfront_contribution_eur": "user" if financing.upfront_contribution_eur > 0 else "default:0 EUR",
            "loan_term_years": "user",
            "annual_rate_pct": "user",
        }

        # ── Short-term: constant prices (central, st_n months) ───────────────
        eu_st, ef_st = self._st_price.forecast_electricity_prices(
            arbeitspreis=inp.arbeitspreis_eur_per_kwh,
            grundpreis=inp.grundpreis_eur_per_month,
            start_date=start_date,
            months=st_n,
            scenario="central",
            contract_end_date=inp.contract_end_date,
        )
        hp_st = self._st_price.forecast_heating_prices(
            fuel_type=inp.fuel_type,
            current_price_per_unit=inp.heating_eur_per_unit,
            start_date=start_date,
            months=st_n,
            scenario="central",
        )
        pp_st = self._st_price.forecast_petrol_prices(
            current_price=inp.effective_petrol_eur_per_litre,
            start_date=start_date,
            months=st_n,
            scenario="central",
        )

        baseline_months_st = self._compute_baseline_months(
            inp, start_date, st_n, eu_st, ef_st, hp_st, pp_st
        )
        upgrade_months_st: dict[str, list[MonthlyUpgradeRecord]] = {}
        for sn in UPGRADE_SCENARIO_NAMES:
            upgrade_months_st[sn] = self._compute_upgrade_months(
                inp, upgrade, sn, kwp, bat_kwh, fit, start_date, st_n,
                eu_st, ef_st, hp_st, pp_st, baseline_months_st
            )

        # ── Long-term: scenario prices (all 3 scenarios, lt_months months) ───
        baseline_months_lt: dict[str, list[dict]] = {}
        upgrade_months_lt: dict[str, dict[str, list[MonthlyUpgradeRecord]]] = {
            ps: {} for ps in PRICE_SCENARIOS
        }

        for ps in PRICE_SCENARIOS:
            eu_lt, ef_lt = self._lt_price.forecast_electricity_prices(
                arbeitspreis=inp.arbeitspreis_eur_per_kwh,
                grundpreis=inp.grundpreis_eur_per_month,
                start_date=start_date,
                months=lt_months,
                scenario=ps,
                contract_end_date=inp.contract_end_date,
            )
            hp_lt = self._lt_price.forecast_heating_prices(
                fuel_type=inp.fuel_type,
                current_price_per_unit=inp.heating_eur_per_unit,
                start_date=start_date,
                months=lt_months,
                scenario=ps,
            )
            pp_lt = self._lt_price.forecast_petrol_prices(
                current_price=inp.effective_petrol_eur_per_litre,
                start_date=start_date,
                months=lt_months,
                scenario=ps,
            )

            baseline_months_lt[ps] = self._compute_baseline_months(
                inp, start_date, lt_months, eu_lt, ef_lt, hp_lt, pp_lt
            )
            for sn in UPGRADE_SCENARIO_NAMES:
                upgrade_months_lt[ps][sn] = self._compute_upgrade_months(
                    inp, upgrade, sn, kwp, bat_kwh, fit, start_date, lt_months,
                    eu_lt, ef_lt, hp_lt, pp_lt, baseline_months_lt[ps]
                )

        # ── Assemble ST output ───────────────────────────────────────────────
        baseline_st = [self._fmt_baseline_month(b) for b in baseline_months_st]

        upgrade_st: dict[str, list[dict]] = {}
        for sn in UPGRADE_SCENARIO_NAMES:
            schedule = loan_schedules[sn]
            monthly_dicts = [r.to_dict(scenario=sn) for r in upgrade_months_st[sn]]
            cum_net = 0.0
            for i, m_dict in enumerate(monthly_dicts):
                instalment = schedule.monthly_instalments[i]
                energy_red = m_dict["cost_eur"]["energy_cost_reduction"]
                net = energy_red - instalment
                cum_net += net
                m_dict["financial_result"] = {
                    "energy_cost_reduction_eur": round(energy_red, 2),
                    "financing_instalment_eur": round(instalment, 2),
                    "net_monthly_savings_eur": round(net, 2),
                    "cumulative_net_savings_eur": round(cum_net, 2),
                }
            upgrade_st[sn] = monthly_dicts

        # ── Assemble LT output ───────────────────────────────────────────────
        baseline_lt: dict[str, list[dict]] = {
            ps: self._aggregate_baseline(baseline_months_lt[ps], lt_n)
            for ps in PRICE_SCENARIOS
        }

        upgrade_lt: dict[str, dict[str, list[dict]]] = {}
        for sn in UPGRADE_SCENARIO_NAMES:
            upgrade_lt[sn] = {}
            schedule = loan_schedules[sn]
            for ps in PRICE_SCENARIOS:
                anns = self._aggregate_upgrades(
                    upgrade_months_lt[ps][sn],
                    baseline_months_lt[ps],
                    lt_n,
                )
                ann_dicts = [a.to_dict() for a in anns]
                cum_net_lt = 0.0
                for yr_idx, ann_dict in enumerate(ann_dicts):
                    m_start = yr_idx * 12
                    m_end = (yr_idx + 1) * 12
                    ann_fin = sum(schedule.monthly_instalments[m_start:m_end])
                    ann_energy_red = ann_dict["cost_eur"]["energy_cost_reduction"]
                    ann_net = ann_energy_red - ann_fin
                    cum_net_lt += ann_net
                    bal_idx = m_end - 1
                    rem_bal = (
                        schedule.remaining_balances[bal_idx]
                        if bal_idx < len(schedule.remaining_balances)
                        else 0.0
                    )
                    ann_dict["financial_result"] = {
                        "annual_energy_cost_reduction_eur": round(ann_energy_red, 2),
                        "annual_financing_payments_eur": round(ann_fin, 2),
                        "annual_net_savings_eur": round(ann_net, 2),
                        "cumulative_net_savings_eur": round(cum_net_lt, 2),
                        "remaining_loan_balance_eur": round(rem_bal, 2),
                    }
                upgrade_lt[sn][ps] = ann_dicts

        # ── Investment cost assumptions provenance ───────────────────────────
        inv_assumptions = {
            "pv_eur_per_kwp": inv_defaults.pv_eur_per_kwp,
            "battery_eur_per_kwh": inv_defaults.battery_eur_per_kwh,
            "heat_pump_eur_fixed": inv_defaults.heat_pump_eur_fixed,
            "ev_charger_eur_fixed": inv_defaults.ev_charger_eur_fixed,
            "ev_purchase_eur": inv_defaults.ev_purchase_eur,
            "known_subsidy_eur": financing.known_subsidy_eur,
            "upfront_contribution_eur": financing.upfront_contribution_eur,
            "loan_term_years": financing.loan_term_years,
            "annual_rate_pct": financing.annual_rate_pct,
            "provenance": _prov_sources,
        }

        # ── Final output ─────────────────────────────────────────────────────
        return {
            "model": {
                "name": "energy_cost_comparison",
                "version": "4.0",
                "price_scenarios": PRICE_SCENARIOS,
            },
            "price_models": {
                "short_term": self._st_price.metadata(),
                "long_term": self._lt_price.metadata(),
            },
            "input_summary": {
                "postcode": inp.postcode,
                "country": inp.country,
                "occupants": inp.occupants,
                "annual_electricity_kwh": inp.annual_kwh,
                "arbeitspreis_eur_per_kwh": inp.arbeitspreis_eur_per_kwh,
                "grundpreis_eur_per_month": inp.grundpreis_eur_per_month,
                "contract_end_date": (
                    inp.contract_end_date.isoformat() if inp.contract_end_date else None
                ),
                "fuel_type": inp.fuel_type,
                "heating_annual_value": inp.heating_annual_value,
                "heating_unit": inp.heating_unit,
                "effective_heating_eur_per_unit": inp.heating_eur_per_unit,
                "vehicle_type": inp.vehicle_type,
                "annual_mileage_km": inp.annual_mileage_km,
                "fuel_consumption_l_per_100km": inp.fuel_consumption_l_per_100km,
                "effective_petrol_eur_per_litre": inp.effective_petrol_eur_per_litre,
                "forecast_start": start_date.isoformat(),
                "short_term_months": st_n,
                "long_term_years": lt_n,
            },
            "assumptions_used": {
                "solar_kwp": round(kwp, 3),
                "feed_in_tariff_eur_per_kwh": fit,
                "battery_usable_kwh": bat_kwh,
                "heat_pump_scop": upgrade.heat_pump_assumptions.heat_pump_scop,
                "existing_heating_efficiency": upgrade.heat_pump_assumptions.existing_heating_efficiency,
                "ev_kwh_per_100km": upgrade.ev_assumptions.kwh_per_100km,
                "ev_charging_efficiency": upgrade.ev_assumptions.charging_efficiency,
                "ev_home_charging_share": upgrade.ev_assumptions.home_charging_share,
                "pv_annual_degradation_pct": upgrade.solar_assumptions.annual_degradation_pct,
                "daytime_demand_fraction": 0.35,
                "roof_orientation": upgrade.roof_orientation,
                "roof_tilt_deg": upgrade.roof_tilt_deg,
                "shading_factor": upgrade.shading_factor,
                "investment_costs": inv_assumptions,
                "defaults": [
                    {"field": k, "source": v}
                    for k, v in upgrade.provenance.items()
                    if not v.startswith("user")
                ],
            },
            "validation_warnings": upgrade.warnings_list,
            "baseline": {
                "short_term_forecast": baseline_st,
                "long_term_projection": baseline_lt,
            },
            "upgrade_scenarios": {
                sn: {
                    "investment": {
                        "components": scenario_investments[sn].components_dict(),
                        **loan_schedules[sn].investment_dict(),
                    },
                    "financing": loan_schedules[sn].financing_dict(),
                    "short_term_forecast": upgrade_st[sn],
                    "long_term_projection": upgrade_lt[sn],
                }
                for sn in UPGRADE_SCENARIO_NAMES
            },
        }

    # ── Private helpers ───────────────────────────────────────────────────────

    def _resolve_upgrade(
        self, inp: ParsedInput, upgrade: UpgradeInput
    ) -> tuple[UpgradeInput, float, float]:
        from dataclasses import replace

        prov = dict(upgrade.provenance)
        warns = list(upgrade.warnings_list)

        if upgrade.solar_kwp is not None:
            kwp = float(upgrade.solar_kwp)
            prov["solar_kwp"] = "user"
        elif upgrade.usable_roof_area_m2 is not None:
            kwp, note = resolve_kwp(None, upgrade.usable_roof_area_m2, upgrade.solar_assumptions)
            prov["solar_kwp"] = f"default:{note}"
            warns.append(
                f"solar_kwp not provided; estimated {kwp:.2f} kWp from "
                f"{upgrade.usable_roof_area_m2} m² roof"
            )
        else:
            kwp = 0.0
            prov["solar_kwp"] = "default:0 kWp (no roof data)"
            warns.append("No solar_kwp or usable_roof_area_m2 provided; PV set to 0 kWp")

        if upgrade.battery_kwh is not None:
            prov["battery_kwh"] = "user"
        else:
            prov["battery_kwh"] = (
                f"default:{upgrade.battery_assumptions.default_usable_kwh} kWh "
                "(BatteryAssumptions default)"
            )
            warns.append(
                f"battery_kwh not specified; using default "
                f"{upgrade.battery_assumptions.default_usable_kwh} kWh"
            )

        if upgrade.ev_kwh_per_100km is not None:
            prov["ev_kwh_per_100km"] = "user"
        else:
            prov["ev_kwh_per_100km"] = (
                f"default:{upgrade.ev_assumptions.kwh_per_100km} kWh/100km"
            )

        fit = feed_in_tariff(kwp, upgrade.solar_assumptions)
        prov["feed_in_tariff_eur_per_kwh"] = (
            f"default:EEG2024 {fit:.4f} for {kwp:.1f} kWp"
        )

        return replace(upgrade, provenance=prov, warnings_list=warns), kwp, fit

    @staticmethod
    def _resolve_battery_kwh(upgrade: UpgradeInput) -> float:
        if upgrade.battery_kwh is not None:
            return float(upgrade.battery_kwh)
        return upgrade.battery_assumptions.default_usable_kwh

    def _compute_baseline_months(
        self,
        inp: ParsedInput,
        start_date: date,
        n_months: int,
        elec_units: list[float],
        elec_fixed: list[float],
        heat_prices: list[float],
        petrol_prices: list[float],
    ) -> list[dict]:
        result = []
        for i, (y, m) in enumerate(_iter_months(start_date.year, start_date.month, n_months)):
            elec_kwh = inp.annual_kwh * self._cons.electricity_fraction(y, m)
            heat_val = inp.heating_annual_value * self._cons.heating_fraction(m, inp.postcode)
            mob_km = inp.annual_mileage_km * self._cons.mobility_fraction(m)
            mob_litres = mob_km / 100.0 * inp.fuel_consumption_l_per_100km

            e_cost = self._calc.electricity_cost(elec_kwh, elec_units[i], elec_fixed[i])
            h_cost = self._calc.heating_cost(heat_val, heat_prices[i])
            m_cost = self._calc.mobility_cost(mob_litres, petrol_prices[i])

            result.append({
                "year": y, "month": m,
                "month_str": f"{y:04d}-{m:02d}",
                "electricity_kwh": elec_kwh,
                "heating_value": heat_val,
                "heating_unit": inp.heating_unit,
                "mileage_km": mob_km,
                "petrol_litres": mob_litres,
                "elec_unit": elec_units[i],
                "elec_fixed": elec_fixed[i],
                "heat_price": heat_prices[i],
                "petrol_price": petrol_prices[i],
                "electricity_cost": e_cost,
                "heating_cost": h_cost,
                "mobility_cost": m_cost,
                "total_cost": e_cost + h_cost + m_cost,
            })
        return result

    def _compute_upgrade_months(
        self,
        inp: ParsedInput,
        upgrade: UpgradeInput,
        sn: str,
        kwp: float,
        bat_kwh: float,
        fit: float,
        start_date: date,
        n_months: int,
        elec_units: list[float],
        elec_fixed: list[float],
        heat_prices: list[float],
        petrol_prices: list[float],
        baseline_months: list[dict],
    ) -> list[MonthlyUpgradeRecord]:
        flags = SCENARIO_FLAGS[sn]
        model = UpgradeEnergyModel(
            flags,
            kwp=kwp,
            postcode=inp.postcode,
            orientation=upgrade.roof_orientation,
            tilt_deg=upgrade.roof_tilt_deg,
            shading_factor=upgrade.shading_factor,
            solar_assumptions=upgrade.solar_assumptions,
            battery_usable_kwh=bat_kwh,
            battery_assumptions=upgrade.battery_assumptions,
            heat_pump_assumptions=upgrade.heat_pump_assumptions,
            fuel_type=inp.fuel_type,
            oil_kwh_per_litre=CONSUMPTION_CONFIG.oil_kwh_per_litre,
            ev_assumptions=upgrade.ev_assumptions,
            feed_in_tariff_eur_per_kwh=fit,
        )
        records: list[MonthlyUpgradeRecord] = []
        for i, (y, m) in enumerate(_iter_months(start_date.year, start_date.month, n_months)):
            b = baseline_months[i]
            rec = model.compute_month(
                baseline_electricity_kwh=b["electricity_kwh"],
                baseline_heating_value=b["heating_value"],
                baseline_petrol_litres=b["petrol_litres"],
                monthly_mileage_km=b["mileage_km"],
                year=y,
                month=m,
                year_index=i // 12,
                elec_unit_eur_per_kwh=elec_units[i],
                elec_fixed_eur=elec_fixed[i],
                heating_price_per_unit=heat_prices[i],
                petrol_price_eur_per_litre=petrol_prices[i],
                baseline_electricity_cost_eur=b["electricity_cost"],
                baseline_heating_cost_eur=b["heating_cost"],
                baseline_mobility_cost_eur=b["mobility_cost"],
            )
            records.append(rec)
        return records

    @staticmethod
    def _fmt_baseline_month(b: dict) -> dict:
        return {
            "month": b["month_str"],
            "consumption": {
                "electricity_kwh": round(b["electricity_kwh"], 3),
                "heating_value": round(b["heating_value"], 3),
                "heating_unit": b["heating_unit"],
                "mobility_km": round(b["mileage_km"], 2),
                "mobility_fuel_litres": round(b["petrol_litres"], 3),
            },
            "prices": {
                "electricity_eur_per_kwh": round(b["elec_unit"], 5),
                "electricity_fixed_eur": round(b["elec_fixed"], 4),
                "heating_eur_per_unit": round(b["heat_price"], 5),
                "petrol_eur_per_litre": round(b["petrol_price"], 4),
            },
            "cost_eur": {
                "electricity": round(b["electricity_cost"], 2),
                "heating": round(b["heating_cost"], 2),
                "mobility": round(b["mobility_cost"], 2),
                "total": round(b["total_cost"], 2),
            },
        }

    @staticmethod
    def _aggregate_baseline(months: list[dict], years: int) -> list[dict]:
        result = []
        for yr_idx in range(years):
            block = months[yr_idx * 12: yr_idx * 12 + 12]
            if not block:
                break
            annual_total = sum(b["total_cost"] for b in block)
            result.append({
                "year_label": f"Year {yr_idx + 1}",
                "first_month": block[0]["month_str"],
                "last_month": block[-1]["month_str"],
                "consumption": {
                    "electricity_kwh": round(sum(b["electricity_kwh"] for b in block), 2),
                    "heating_value": round(sum(b["heating_value"] for b in block), 2),
                    "heating_unit": block[0]["heating_unit"],
                    "mobility_fuel_litres": round(sum(b["petrol_litres"] for b in block), 2),
                },
                "cost_eur": {
                    "electricity": round(sum(b["electricity_cost"] for b in block), 2),
                    "heating": round(sum(b["heating_cost"] for b in block), 2),
                    "mobility": round(sum(b["mobility_cost"] for b in block), 2),
                    "total": round(annual_total, 2),
                },
            })
        return result

    @staticmethod
    def _aggregate_upgrades(
        records: list[MonthlyUpgradeRecord],
        baseline_months: list[dict],
        years: int,
    ) -> list[AnnualUpgradeRecord]:
        result: list[AnnualUpgradeRecord] = []
        cumulative = 0.0

        def s(attr: str) -> float:
            return sum(getattr(r, attr) for r in block)

        for yr_idx in range(years):
            start_i = yr_idx * 12
            block = records[start_i: start_i + 12]
            base_block = baseline_months[start_i: start_i + 12]
            if not block:
                break

            annual_red = sum(r.energy_cost_reduction_eur for r in block)
            cumulative += annual_red

            ann = AnnualUpgradeRecord(
                year_label=f"Year {yr_idx + 1}",
                first_month=block[0].month,
                last_month=block[-1].month,
                baseline_household_electricity_kwh=s("baseline_household_electricity_kwh"),
                pv_generation_kwh=s("pv_generation_kwh"),
                pv_direct_self_consumption_kwh=s("pv_direct_self_consumption_kwh"),
                battery_charge_kwh=s("battery_charge_kwh"),
                battery_discharge_kwh=s("battery_discharge_kwh"),
                battery_loss_kwh=s("battery_loss_kwh"),
                grid_import_kwh=s("grid_import_kwh"),
                grid_export_kwh=s("grid_export_kwh"),
                heat_pump_electricity_kwh=s("heat_pump_electricity_kwh"),
                remaining_heating_fuel=s("remaining_heating_fuel"),
                ev_charging_home_kwh=s("ev_charging_home_kwh"),
                remaining_petrol_litres=s("remaining_petrol_litres"),
                grid_electricity_cost_eur=s("grid_electricity_cost_eur"),
                solar_export_revenue_eur=s("solar_export_revenue_eur"),
                remaining_heating_fuel_cost_eur=s("remaining_heating_fuel_cost_eur"),
                remaining_mobility_fuel_cost_eur=s("remaining_mobility_fuel_cost_eur"),
                total_upgraded_cost_eur=s("total_upgraded_cost_eur"),
                baseline_total_cost_eur=s("baseline_total_cost_eur"),
                energy_cost_reduction_eur=annual_red,
                baseline_electricity_cost_eur=sum(b["electricity_cost"] for b in base_block),
                baseline_heating_cost_eur=sum(b["heating_cost"] for b in base_block),
                baseline_mobility_cost_eur=sum(b["mobility_cost"] for b in base_block),
                cumulative_energy_cost_reduction_eur=cumulative,
            )
            result.append(ann)
        return result
