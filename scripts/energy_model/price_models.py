"""Production energy price models.

Two models serve distinct purposes:

  ConstantShortTermPriceModel  — selected for short-term (≤24 months) forecasts
      by Destatis rolling-origin backtest (see research/price_forecasting/).
      Returns the current user tariff unchanged for every month.

  ScenarioPriceModel           — long-term (multi-year) scenario projections.
      Applies configurable annual trend per scenario (low / central / high).
      Respects electricity contract lock-in until contract_end_date.

PriceModelProtocol defines the structural interface accepted by
ScenarioOrchestrator, allowing both models (or custom overrides) to be
injected for testing.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from typing import Literal, Protocol, runtime_checkable

ScenarioName = Literal["low", "central", "high"]


@dataclass(frozen=True)
class PriceConfig:
    """Long-term price trend assumptions per scenario.

    All figures are annual real-price growth rates (not CPI-adjusted).
    Source: BDEW/Destatis long-run price projections (placeholder — update
    when official projections are available).
    """

    default_electricity_arbeitspreis_eur_per_kwh: float = 0.32
    default_electricity_grundpreis_eur_per_month: float = 12.50
    default_gas_eur_per_kwh: float = 0.10
    default_oil_eur_per_litre: float = 1.05
    default_petrol_eur_per_litre: float = 1.75

    electricity_annual_trend: dict[str, float] = field(default_factory=lambda: {
        "low": 0.01, "central": 0.03, "high": 0.05,
    })
    gas_annual_trend: dict[str, float] = field(default_factory=lambda: {
        "low": 0.01, "central": 0.04, "high": 0.07,
    })
    oil_annual_trend: dict[str, float] = field(default_factory=lambda: {
        "low": 0.01, "central": 0.04, "high": 0.07,
    })
    petrol_annual_trend: dict[str, float] = field(default_factory=lambda: {
        "low": 0.01, "central": 0.03, "high": 0.05,
    })
    fixed_charge_annual_trend: dict[str, float] = field(default_factory=lambda: {
        "low": 0.005, "central": 0.02, "high": 0.03,
    })
    petrol_monthly_seasonality: tuple[float, ...] = (
        0.97, 0.97, 0.99, 1.01, 1.03, 1.04,
        1.04, 1.03, 1.01, 0.99, 0.97, 0.97,
    )
    spend_warning_threshold: float = 0.15


PRICE_CONFIG = PriceConfig()


@runtime_checkable
class PriceModelProtocol(Protocol):
    """Structural interface for price models injected into ScenarioOrchestrator."""

    def forecast_electricity_prices(
        self,
        arbeitspreis: float,
        grundpreis: float,
        start_date: date,
        months: int,
        scenario: ScenarioName,
        contract_end_date: date | None,
    ) -> tuple[list[float], list[float]]:
        """Return (unit_prices, fixed_charges), each a list of length ``months``."""
        ...

    def forecast_heating_prices(
        self,
        fuel_type: str,
        current_price_per_unit: float,
        start_date: date,
        months: int,
        scenario: ScenarioName,
    ) -> list[float]:
        """Return monthly heating fuel unit prices."""
        ...

    def forecast_petrol_prices(
        self,
        current_price: float,
        start_date: date,
        months: int,
        scenario: ScenarioName,
    ) -> list[float]:
        """Return monthly petrol prices (EUR/litre)."""
        ...

    def metadata(self) -> dict:
        """Return a dict describing the model name, version, and assumptions."""
        ...


class ConstantShortTermPriceModel:
    """Production short-term price model: constant at current user price.

    All energy prices are held fixed at the user's current tariff rate for
    every forecast month.  The electricity contract lock-in period is
    irrelevant because the post-contract assumption is also constant.

    Selected as the production short-term model based on Destatis
    rolling-origin backtesting of four energy carriers (electricity, gas,
    heating_oil, petrol).  The constant model outperformed DeterministicTrend,
    ETS, and SARIMA across all series on RMSPE.
    """

    def forecast_electricity_prices(
        self,
        arbeitspreis: float,
        grundpreis: float,
        start_date: date,
        months: int,
        scenario: ScenarioName = "central",
        contract_end_date: date | None = None,
    ) -> tuple[list[float], list[float]]:
        return [arbeitspreis] * months, [grundpreis] * months

    def forecast_heating_prices(
        self,
        fuel_type: str,
        current_price_per_unit: float,
        start_date: date,
        months: int,
        scenario: ScenarioName = "central",
    ) -> list[float]:
        return [current_price_per_unit] * months

    def forecast_petrol_prices(
        self,
        current_price: float,
        start_date: date,
        months: int,
        scenario: ScenarioName = "central",
    ) -> list[float]:
        return [current_price] * months

    def metadata(self) -> dict:
        return {
            "name": "constant_index",
            "selection_basis": "Destatis rolling-origin backtest",
            "energy_types": ["electricity", "gas", "heating_oil", "petrol"],
        }


class ScenarioPriceModel:
    """Long-term scenario price model: deterministic annual trend per scenario.

    Applies a configurable annual growth rate to the current user price.
    For electricity: price is locked to the contract rate until
    contract_end_date; trend escalation begins the month after contract expiry.

    NOT a statistical forecast.  The low/central/high bands represent
    policy-range assumptions, not confidence intervals.
    """

    def __init__(self, config: PriceConfig = PRICE_CONFIG) -> None:
        self._cfg = config

    def forecast_electricity_prices(
        self,
        arbeitspreis: float,
        grundpreis: float,
        start_date: date,
        months: int,
        scenario: ScenarioName,
        contract_end_date: date | None = None,
    ) -> tuple[list[float], list[float]]:
        ctx = {"contract_end_date": contract_end_date}
        units = self._forecast_monthly(
            "electricity_unit", arbeitspreis, start_date, months, scenario, ctx
        )
        fixed = self._forecast_monthly(
            "electricity_fixed", grundpreis, start_date, months, scenario, ctx
        )
        return units, fixed

    def forecast_heating_prices(
        self,
        fuel_type: str,
        current_price_per_unit: float,
        start_date: date,
        months: int,
        scenario: ScenarioName,
    ) -> list[float]:
        etype = "gas" if fuel_type == "gas" else "oil"
        return self._forecast_monthly(etype, current_price_per_unit, start_date, months, scenario)

    def forecast_petrol_prices(
        self,
        current_price: float,
        start_date: date,
        months: int,
        scenario: ScenarioName,
    ) -> list[float]:
        return self._forecast_monthly("petrol", current_price, start_date, months, scenario)

    def metadata(self) -> dict:
        cfg = self._cfg
        return {
            "name": "scenario_trend",
            "note": "Not a statistical forecast; bands are policy-range assumptions",
            "assumptions": {
                "electricity_annual_trend": dict(cfg.electricity_annual_trend),
                "gas_annual_trend": dict(cfg.gas_annual_trend),
                "oil_annual_trend": dict(cfg.oil_annual_trend),
                "petrol_annual_trend": dict(cfg.petrol_annual_trend),
                "fixed_charge_annual_trend": dict(cfg.fixed_charge_annual_trend),
            },
        }

    def _forecast_monthly(
        self,
        energy_type: str,
        current_price: float,
        start_date: date,
        months: int,
        scenario: ScenarioName,
        context: dict | None = None,
    ) -> list[float]:
        if current_price < 0:
            raise ValueError(f"current_price must be non-negative, got {current_price}")
        if months < 1:
            raise ValueError("months must be >= 1")

        annual_trend = self._annual_trend(energy_type, scenario)
        seasonality = self._seasonality(energy_type)
        contract_end: date | None = (context or {}).get("contract_end_date")

        result: list[float] = []
        months_post_contract = 0
        y, m = start_date.year, start_date.month

        for _ in range(months):
            month_date = date(y, m, 1)

            if contract_end is not None and month_date <= contract_end:
                price = current_price
            else:
                yrs = months_post_contract / 12
                months_post_contract += 1
                price = current_price * (1 + annual_trend) ** yrs * seasonality[m - 1]

            result.append(max(price, 0.0))
            m += 1
            if m > 12:
                m, y = 1, y + 1

        return result

    def _annual_trend(self, energy_type: str, scenario: ScenarioName) -> float:
        cfg = self._cfg
        mapping = {
            "electricity_unit": cfg.electricity_annual_trend,
            "electricity_fixed": cfg.fixed_charge_annual_trend,
            "gas": cfg.gas_annual_trend,
            "oil": cfg.oil_annual_trend,
            "petrol": cfg.petrol_annual_trend,
        }
        trends = mapping.get(energy_type)
        if trends is None:
            raise ValueError(f"Unknown energy_type '{energy_type}'")
        return trends[scenario]

    def _seasonality(self, energy_type: str) -> tuple[float, ...]:
        if energy_type == "petrol":
            return self._cfg.petrol_monthly_seasonality
        return tuple(1.0 for _ in range(12))
