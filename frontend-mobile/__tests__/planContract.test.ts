import planFixture from '@/services/fixtures/plan_model_input1.json';
import benchmarkFixture from '@/services/fixtures/benchmark.json';
import { mockAdvisorReply, mockAssessmentResponse, mockBenchmark, mockPlan } from '@/services/mocks';
import {
  validateAdvisorChatResponse,
  validateAssessmentResponse,
  validateBenchmarkData,
  validatePlanResponse,
} from '@/services/validation';
import type { HouseholdAssessment } from '@/types';

const assessment = {} as HouseholdAssessment;

describe('API contract (v2) on mobile', () => {
  it('validates the recorded backend /plan response', () => {
    const plan = validatePlanResponse(planFixture);
    const selected = plan.recommendation.selected_scenario!;
    expect(plan.recommendation.selected_scenario_id).toBe('full_upgrade');
    expect(plan.recommendation.metric_used).toBe('cumulative_central');
    expect(plan.recommendation.rationale.length).toBeGreaterThan(0);
    expect(selected.monthly_cost_eur.financing_installment).toBeGreaterThan(0);
    expect(selected.financials?.break_even_year).toBe(12);
  });

  it('mock plan is the recorded response, with honest (negative) savings during the loan', () => {
    const plan = mockPlan(assessment);
    expect(plan.forecast.scenarios).toHaveLength(6);
    expect(plan.recommendation.selected_scenario!.monthly_saving_eur).toBeLessThan(0);
    expect(plan.recommendation.selected_scenario!.monthly_saving_post_payoff_eur).toBeGreaterThan(0);
  });

  it('rejects the old v1 recommendation shape', () => {
    const v1 = {
      forecast: (planFixture as { forecast: unknown }).forecast,
      recommendation: { selected_scenario: null, ranked_scenarios: [], reasoning: 'old' },
    };
    expect(() => validatePlanResponse(v1)).toThrow();
  });

  it('assessment and advisor mocks match the backend shapes', () => {
    expect(validateAssessmentResponse(mockAssessmentResponse(assessment)).assessment_id).toMatch(/^mock_/);
    expect(validateAdvisorChatResponse(mockAdvisorReply('why this?')).advisor_message.length).toBeGreaterThan(0);
  });

  it('validates the recorded engine-computed /benchmark response', () => {
    const b = validateBenchmarkData(benchmarkFixture);
    expect(b.recommendation.scenario).toBe('full_upgrade');
    expect(b.recommendation.monthly_instalment_eur).toBe(209.35);
    expect(b.recommendation.monthly_saving_eur).toBeLessThan(0);
    expect(b.cumulative_series).toHaveLength(b.projection_years);
    expect(b.cumulative_series.at(-1)?.central).toBe(b.recommendation.cumulative_savings_eur);
    expect(mockBenchmark()).toEqual(b);
  });
});
