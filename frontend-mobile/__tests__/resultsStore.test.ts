import { act } from 'react';
import { useResultsStore } from '@/stores/resultsStore';

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

const mockScenario = {
  id: 'scenario-1',
  components: mockComponents,
  sizing: mockSizing,
  monthly_cost_eur: mockMonthlyCostEur,
  financing_installment_eur: 150,
  monthly_saving_eur: 80,
  monthly_saving_post_payoff_eur: 120,
  self_consumption_ratio: 0.6,
  payback_month: 48,
  short_term_forecast: mockShortTermForecast,
  long_term_forecast: mockLongTermForecast,
};

const mockBaseline = {
  monthly_cost_eur: mockMonthlyCostEur,
  short_term_forecast: mockShortTermForecast,
  long_term_forecast: mockLongTermForecast,
};

const mockForecast = {
  baseline: mockBaseline,
  scenarios: [mockScenario],
};

const mockRecommendation = {
  selected_scenario: mockScenario,
  ranked_scenarios: [mockScenario],
  reasoning: 'Test reasoning',
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

  it('selects scenario', () => {
    act(() => {
      useResultsStore.getState().setForecast(mockForecast);
      useResultsStore.getState().selectScenario('scenario-1');
    });
    expect(useResultsStore.getState().selectedScenarioId).toBe('scenario-1');
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
