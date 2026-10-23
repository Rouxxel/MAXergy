import { act } from 'react';
import { useResultsStore } from '@/stores/resultsStore';
import type { ForecastResult, PlanResponse, Recommendation, Scenario } from '@/types';

// Mock AsyncStorage
jest.mock('@/lib/storage', () => ({
  zustandStorage: {
    getItem: jest.fn().mockResolvedValue(null),
    setItem: jest.fn(),
    removeItem: jest.fn(),
  },
}));

const mockMonthlyCostEur = { electricity: 100, heating: 80, mobility: 50, total: 230 };
const mockShortTermForecast = [{ month: '2024-01', total_eur: 230 }];
const mockLongTermForecast = [{ year: 2024, annual_total_eur: 2760 }];
const mockComponents = { solar_pv: true, battery: true, heat_pump: false, ev_charger: false };
const mockSizing = { solar_pv_kwp: 5, battery_kwh: 10, heat_pump_kw: null };

const mockScenario: Scenario = {
  id: 'pv_battery',
  components: mockComponents,
  sizing: mockSizing,
  // Scenario total includes the loan instalment.
  monthly_cost_eur: { electricity: 40, heating: 80, mobility: 50, financing_installment: 150, total: 320 },
  monthly_saving_eur: -90,
  monthly_saving_post_payoff_eur: 60,
  self_consumption_ratio: 0.6,
  payback_month: 150,
  short_term_forecast: [{ month: '2024-01', total_eur: 320, saving_eur: -90 }],
  long_term_forecast: [
    { year: 2024, annual_total_eur: 3840, annual_saving_eur: -1080, cumulative_saving_eur: -1080 },
  ],
  financials: {
    gross_investment_eur: 13000,
    subsidy_eur: 0,
    financed_principal_eur: 13000,
    loan_term_months: 180,
    horizon_years: 20,
    cumulative_net_savings_central_eur: 2400,
    cumulative_net_savings_low_eur: 900,
    cumulative_net_savings_high_eur: 4100,
    break_even_year: 16,
  },
};

const mockForecast: ForecastResult = {
  validation_warnings: [],
  baseline: {
    monthly_cost_eur: mockMonthlyCostEur,
    short_term_forecast: mockShortTermForecast,
    long_term_forecast: mockLongTermForecast,
  },
  scenarios: [mockScenario],
};

const mockRecommendation: Recommendation = {
  selected_scenario_id: mockScenario.id,
  selected_scenario: mockScenario,
  ranked_scenarios: [{ id: mockScenario.id, score_eur: 2400, metric: 'cumulative_central' }],
  metric_used: 'cumulative_central',
  rationale: 'Test rationale',
};

describe('resultsStore', () => {
  beforeEach(() => {
    useResultsStore.setState(useResultsStore.getInitialState(), true);
  });

  it('initializes with empty state', () => {
    const state = useResultsStore.getState();
    expect(state.forecast).toBeUndefined();
    expect(state.recommendation).toBeUndefined();
  });

  it('sets forecast', () => {
    act(() => {
      useResultsStore.getState().setForecast(mockForecast);
    });
    expect(useResultsStore.getState().forecast).toEqual(mockForecast);
  });

  it('sets recommendation and selects scenario', () => {
    act(() => {
      useResultsStore.getState().setRecommendation(mockRecommendation);
    });
    const state = useResultsStore.getState();
    expect(state.recommendation).toEqual(mockRecommendation);
    expect(state.selectedScenarioId).toBe(mockScenario.id);
  });

  it('sets a plan (forecast + recommendation) and selects the recommended scenario', () => {
    const plan: PlanResponse = { forecast: mockForecast, recommendation: mockRecommendation };
    act(() => {
      useResultsStore.getState().setPlan(plan);
    });
    const state = useResultsStore.getState();
    expect(state.forecast).toEqual(mockForecast);
    expect(state.recommendation).toEqual(mockRecommendation);
    expect(state.getSelected()?.monthly_cost_eur.financing_installment).toBe(150);
  });

  it('handles a plan without any scenario', () => {
    const plan: PlanResponse = {
      forecast: { ...mockForecast, scenarios: [] },
      recommendation: {
        ...mockRecommendation,
        selected_scenario_id: null,
        selected_scenario: null,
        ranked_scenarios: [],
      },
    };
    act(() => {
      useResultsStore.getState().setPlan(plan);
    });
    expect(useResultsStore.getState().selectedScenarioId).toBeUndefined();
    expect(useResultsStore.getState().getSelected()).toBeUndefined();
  });

  it('selects scenario', () => {
    act(() => {
      useResultsStore.getState().setForecast(mockForecast);
      useResultsStore.getState().selectScenario('pv_battery');
    });
    expect(useResultsStore.getState().selectedScenarioId).toBe('pv_battery');
  });

  it('resets state', () => {
    act(() => {
      useResultsStore.getState().setForecast(mockForecast);
      useResultsStore.getState().reset();
    });
    const state = useResultsStore.getState();
    expect(state.forecast).toBeUndefined();
    expect(state.recommendation).toBeUndefined();
  });
});
