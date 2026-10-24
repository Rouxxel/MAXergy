/**
 * Live smoke test: the mobile service layer against a running backend (no mocks).
 *
 * Skipped unless MAXERGY_LIVE_SMOKE=1. CI starts the backend and runs:
 *   MAXERGY_LIVE_SMOKE=1 EXPO_PUBLIC_USE_MOCKS=false EXPO_PUBLIC_API_BASE_URL=http://127.0.0.1:8000 \
 *     npx jest __tests__/live.smoke.test.ts
 * Every response is validated with the app's own Zod schemas inside services/endpoints.ts.
 */
import assessmentFixture from '../../backend/tests/fixtures/model_input1.json';
import type { HouseholdAssessment } from '@/types';

const live = process.env.MAXERGY_LIVE_SMOKE === '1';
const describeLive = live ? describe : describe.skip;

describeLive('live backend smoke (mobile services)', () => {
  // Imported lazily so USE_MOCKS / BASE_URL are read from the env set for this run.
  const endpoints = () => require('@/services/endpoints') as typeof import('@/services/endpoints');
  const assessment = assessmentFixture as HouseholdAssessment;

  jest.setTimeout(60_000);

  it('runs with mocks disabled', () => {
    expect(require('@/services/apiClient').USE_MOCKS).toBe(false);
  });

  it('stores an assessment', async () => {
    const res = await endpoints().postAssessment(assessment);
    expect(res.assessment_id).toBeTruthy();
  });

  it('returns a plan with financing and a rationale', async () => {
    const plan = await endpoints().postPlan(assessment);
    const best = plan.recommendation.selected_scenario;
    expect(plan.recommendation.selected_scenario_id).toBe('full_upgrade');
    expect(best?.monthly_cost_eur.financing_installment).toBeGreaterThan(0);
    expect(plan.recommendation.rationale.length).toBeGreaterThan(50);
  });

  it('returns the engine-computed benchmark', async () => {
    const bench = await endpoints().getBenchmark();
    expect(bench.recommendation.scenario).toBe('full_upgrade');
    expect(bench.cumulative_series).toHaveLength(bench.projection_years);
  });
});
