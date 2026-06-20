"""Deterministic fixed-rate annuity financing model.

FinancingModel is entirely independent of energy consumption, price
forecasting, and upgrade dispatch.  It accepts a gross investment amount,
reduces it by subsidy and upfront contribution, then computes a standard
monthly annuity instalment and a full amortisation schedule.

Zero-interest loans are handled explicitly (equal principal repayments).
Payments stop after the loan term; the schedule is padded with zeros to
cover the full forecast horizon.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class FinancingInput:
    """User-supplied financing parameters with documented defaults.

    Cost overrides are optional: when None the orchestrator falls back to
    InvestmentCostDefaults.  Provenance is tracked by the caller.
    """

    # Loan terms
    loan_term_years: int = 15
    annual_rate_pct: float = 4.5

    # Subsidy / upfront — both clamp to ≥ 0 inside FinancingModel.
    # Default = 0: no subsidy is assumed without explicit user input.
    known_subsidy_eur: float = 0.0
    upfront_contribution_eur: float = 0.0

    # Technology cost overrides (None → InvestmentCostDefaults)
    pv_eur_per_kwp: float | None = None
    battery_eur_per_kwh: float | None = None
    heat_pump_eur_fixed: float | None = None
    ev_charger_eur_fixed: float | None = None

    # EV purchase cost: explicit opt-in, default = 0.
    ev_purchase_eur: float = 0.0


@dataclass
class LoanSchedule:
    """Computed annuity loan results and per-month amortisation schedule."""

    gross_investment_eur: float
    subsidy_eur: float
    upfront_contribution_eur: float
    financed_principal_eur: float

    annual_rate_pct: float
    loan_term_months: int
    monthly_instalment_eur: float
    total_repayment_eur: float
    total_interest_eur: float

    # Per-forecast-month arrays (length = total_forecast_months).
    # Both are 0.0 for months beyond the loan term.
    monthly_instalments: list[float] = field(default_factory=list)
    remaining_balances: list[float] = field(default_factory=list)

    def investment_dict(self) -> dict:
        return {
            "gross_investment_eur": round(self.gross_investment_eur, 2),
            "subsidy_eur": round(self.subsidy_eur, 2),
            "upfront_contribution_eur": round(self.upfront_contribution_eur, 2),
            "financed_principal_eur": round(self.financed_principal_eur, 2),
        }

    def financing_dict(self) -> dict:
        return {
            "annual_interest_rate_pct": self.annual_rate_pct,
            "loan_term_months": self.loan_term_months,
            "monthly_instalment_eur": round(self.monthly_instalment_eur, 2),
            "total_repayment_eur": round(self.total_repayment_eur, 2),
            "total_interest_eur": round(self.total_interest_eur, 2),
        }


class FinancingModel:
    """Computes a fixed-rate annuity loan for a given gross investment."""

    def compute(
        self,
        gross_investment_eur: float,
        financing_input: FinancingInput,
        total_forecast_months: int,
    ) -> LoanSchedule:
        """Return a fully-populated LoanSchedule.

        Parameters
        ----------
        gross_investment_eur:
            Total installed cost before subsidy / upfront payment.
        financing_input:
            Loan and subsidy parameters.
        total_forecast_months:
            Length of the monthly schedule arrays.  Payments stop at
            loan_term_months; remaining entries are 0.
        """
        subsidy = max(0.0, financing_input.known_subsidy_eur)
        upfront = max(0.0, financing_input.upfront_contribution_eur)
        net_investment = gross_investment_eur - subsidy - upfront
        principal = max(0.0, net_investment)

        n = financing_input.loan_term_years * 12
        monthly_rate = financing_input.annual_rate_pct / 100.0 / 12.0

        if principal == 0.0:
            instalment = 0.0
        elif monthly_rate > 0.0:
            factor = (1.0 + monthly_rate) ** n
            instalment = principal * monthly_rate * factor / (factor - 1.0)
        else:
            instalment = principal / n

        total_repayment = instalment * n
        total_interest = total_repayment - principal

        # Build amortisation schedule
        monthly_instalments: list[float] = []
        remaining_balances: list[float] = []
        balance = principal

        for i in range(total_forecast_months):
            payment_no = i + 1  # 1-indexed
            if payment_no <= n and principal > 0.0:
                if monthly_rate > 0.0:
                    interest_component = balance * monthly_rate
                else:
                    interest_component = 0.0
                principal_component = instalment - interest_component
                balance = max(0.0, balance - principal_component)
                # Snap to zero on the final scheduled payment to avoid
                # floating-point residual.
                if payment_no == n:
                    balance = 0.0
                monthly_instalments.append(instalment)
                remaining_balances.append(balance)
            else:
                monthly_instalments.append(0.0)
                remaining_balances.append(0.0)

        return LoanSchedule(
            gross_investment_eur=gross_investment_eur,
            subsidy_eur=subsidy,
            upfront_contribution_eur=upfront,
            financed_principal_eur=principal,
            annual_rate_pct=financing_input.annual_rate_pct,
            loan_term_months=n,
            monthly_instalment_eur=instalment,
            total_repayment_eur=total_repayment,
            total_interest_eur=total_interest,
            monthly_instalments=monthly_instalments,
            remaining_balances=remaining_balances,
        )
