import planFixture from '@/services/fixtures/plan_model_input1.json';
import { describeAssumptions, euro, signedEuro, summarizeSavings } from '@/services/savings';
import { validatePlanResponse } from '@/services/validation';

const plan = validatePlanResponse(planFixture);
const byId = (id: string) => plan.forecast.scenarios.find((s) => s.id === id)!;

describe('savings wording (shared by web, mobile and the MCP guidance)', () => {
  it('formats euros with and without sign', () => {
    expect(euro(1234.6)).toBe('€1,235');
    expect(signedEuro(-39.18)).toBe('−€39');
    expect(signedEuro(179.1)).toBe('+€179');
    expect(euro(null)).toBe('–');
  });

  it('negative year-1 net: "During financing" with after-payoff and long-term numbers', () => {
    const s = summarizeSavings(byId('full_upgrade'));
    expect(s.savesFromStart).toBe(false);
    expect(s.primaryLabel).toBe('During financing');
    expect(s.primaryValue).toBe('−€39');
    expect(s.afterPayoff).toBe('After payoff: +€179/month');
    expect(s.longTerm).toBe('20-year net: +€21,960');
    expect(s.sentence).toBe('Costs €39/month more during the 15-year loan, then saves €179/month; 20-year net +€21,960.');
  });

  it('positive year-1 net: "You could save"', () => {
    const s = summarizeSavings(byId('pv_ev'));
    expect(s.savesFromStart).toBe(true);
    expect(s.primaryLabel).toBe('You could save');
    expect(s.primaryValue).toBe('€39');
    expect(s.sentence).toMatch(/^Saves €39\/month from the start \(loan included\)/);
  });

  it('lists the assumptions behind the forecast', () => {
    const items = describeAssumptions(plan.forecast.assumptions_used);
    expect(items[0]).toMatch(/Solar yield 950 kWh per kWp per year \(regional average\)/);
    expect(items).toContain('Loan 15 years at 4.5 %');
  });
});
