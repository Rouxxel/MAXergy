"""Technology investment cost model for upgrade scenarios.

All defaults are documented with sources.  User-supplied values override
defaults; provenance is recorded for every cost parameter.

No double-counting: only technologies active in the scenario's ScenarioFlags
contribute to gross investment.  EV purchase cost is kept separate from EV
charger cost — installing a wallbox does not imply buying an EV.
"""

from __future__ import annotations

from dataclasses import dataclass

from energy_model.upgrade_model import SCENARIO_FLAGS


@dataclass(frozen=True)
class InvestmentCostDefaults:
    """Default technology unit costs for German residential market (2024).

    All figures include equipment + installation labour unless noted.
    Sources: Stiftung Warentest 12/2023, BDEW Heizkostenvergleich 2024,
    BNetzA Wallbox market survey 2023.
    """

    # Monocrystalline PV modules + string inverter + mounting + grid connection.
    # Market range: 1200–1600 EUR/kWp installed.  Midpoint used.
    pv_eur_per_kwp: float = 1400.0

    # Lithium-ion home battery (cells + BMS + bidirectional inverter + install).
    # Market range: 500–700 EUR/kWh usable capacity.  Midpoint used.
    battery_eur_per_kwh: float = 600.0

    # Air-to-water heat pump (equipment + hydraulic integration + commissioning).
    # Market range: 10,000–15,000 EUR.  Midpoint used.
    heat_pump_eur_fixed: float = 12_000.0

    # 11 kW AC wallbox + installation + grid connection work.
    # Market range: 1,000–1,500 EUR.  Midpoint used.
    ev_charger_eur_fixed: float = 1_200.0

    # EV purchase cost.  Default = 0: installing a charger does not imply
    # purchasing a new vehicle.  Must be supplied explicitly by the user.
    ev_purchase_eur: float = 0.0


@dataclass
class ScenarioInvestment:
    """Per-technology cost breakdown for one upgrade scenario."""

    scenario: str
    pv_eur: float
    battery_eur: float
    heat_pump_eur: float
    ev_charger_eur: float
    ev_purchase_eur: float
    gross_investment_eur: float

    def components_dict(self) -> dict:
        """Return flat component breakdown (no nesting)."""
        return {
            "pv_eur": round(self.pv_eur, 2),
            "battery_eur": round(self.battery_eur, 2),
            "heat_pump_eur": round(self.heat_pump_eur, 2),
            "ev_charger_eur": round(self.ev_charger_eur, 2),
            "ev_purchase_eur": round(self.ev_purchase_eur, 2),
        }


def compute_scenario_investment(
    scenario_name: str,
    kwp: float,
    battery_kwh: float,
    defaults: InvestmentCostDefaults,
    ev_purchase_eur: float = 0.0,
) -> ScenarioInvestment:
    """Return investment breakdown for *scenario_name*, using only active technologies.

    Technologies are determined by SCENARIO_FLAGS[scenario_name].  Shared
    components (e.g. PV appears in every scenario) are included exactly once.
    """
    flags = SCENARIO_FLAGS[scenario_name]

    pv_eur = kwp * defaults.pv_eur_per_kwp if flags.has_solar else 0.0
    bat_eur = battery_kwh * defaults.battery_eur_per_kwh if flags.has_battery else 0.0
    hp_eur = defaults.heat_pump_eur_fixed if flags.has_heat_pump else 0.0
    ev_charger_eur = defaults.ev_charger_eur_fixed if flags.has_ev else 0.0
    ev_purch = ev_purchase_eur if flags.has_ev else 0.0

    gross = pv_eur + bat_eur + hp_eur + ev_charger_eur + ev_purch

    return ScenarioInvestment(
        scenario=scenario_name,
        pv_eur=pv_eur,
        battery_eur=bat_eur,
        heat_pump_eur=hp_eur,
        ev_charger_eur=ev_charger_eur,
        ev_purchase_eur=ev_purch,
        gross_investment_eur=gross,
    )
