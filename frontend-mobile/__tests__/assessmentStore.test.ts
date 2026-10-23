import { act } from 'react';
import { ENGINE_DEFAULTS, useAssessmentStore } from '@/stores/assessmentStore';
import { validateHouseholdAssessment } from '@/services/validation';
import type { EnrichmentResponse } from '@/types';
// GET /assumptions as recorded from the backend (shared with the MCP tests)
import assumptions from '../../backend/mcp/tests/fixtures/assumptions.json';

// Mock AsyncStorage
jest.mock('@/lib/storage', () => ({
  zustandStorage: {
    getItem: jest.fn().mockResolvedValue(null),
    setItem: jest.fn(),
    removeItem: jest.fn(),
  },
}));

describe('assessmentStore', () => {
  beforeEach(() => {
    // Reset store state before each test
    useAssessmentStore.setState(useAssessmentStore.getInitialState(), true);
  });

  it('initializes with default state', () => {
    const state = useAssessmentStore.getState();
    expect(state.step).toBe(0);
    expect(state.submitting).toBe(false);
    expect(state.draft).toBeDefined();
  });

  it('updates a field with setField', () => {
    const testPostcode = '12345';
    act(() => {
      useAssessmentStore.getState().setField('location', { postcode: testPostcode, country: 'DE' });
    });
    expect(useAssessmentStore.getState().draft.location?.postcode).toBe(testPostcode);
  });

  it('updates step with setStep', () => {
    const testStep = 2;
    act(() => {
      useAssessmentStore.getState().setStep(testStep);
    });
    expect(useAssessmentStore.getState().step).toBe(testStep);
  });

  it('resets to initial state with reset', () => {
    // First modify some fields
    act(() => {
      useAssessmentStore.getState().setStep(3);
      useAssessmentStore.getState().setSubmitting(true);
    });
    
    // Reset
    act(() => {
      useAssessmentStore.getState().reset();
    });
    
    const state = useAssessmentStore.getState();
    expect(state.step).toBe(0);
    expect(state.submitting).toBe(false);
  });

  it('proposes the engine defaults from GET /assumptions', () => {
    expect(ENGINE_DEFAULTS.arbeitspreis_eur_per_kwh).toBe(assumptions.tariff.arbeitspreis_eur_per_kwh);
    expect(ENGINE_DEFAULTS.grundpreis_eur_per_month).toBe(assumptions.tariff.grundpreis_eur_per_month);
    expect(ENGINE_DEFAULTS.loan_term_years).toBe(assumptions.financing.loan_term_years);
    expect(ENGINE_DEFAULTS.loan_rate_pct).toBe(assumptions.financing.loan_rate_pct);
    const { draft } = useAssessmentStore.getState();
    expect(draft.household?.electricity.arbeitspreis_eur_per_kwh).toBe(0.32);
    expect(draft.financing?.loan_term_years).toBe(15);
    expect(draft.upgrade_candidates).toMatchObject({ solar_pv: true, battery: true, heat_pump: true, ev_charger: true });
  });

  it('default draft with a postcode is a valid assessment', () => {
    act(() => {
      useAssessmentStore.getState().setField('location', { postcode: '10115', country: 'DE' });
    });
    const completed = useAssessmentStore.getState().getCompleted();
    expect(completed).not.toBeNull();
    expect(() => validateHouseholdAssessment(completed)).not.toThrow();
  });

  it('pre-fills the roof from a location lookup until reset', () => {
    const enrichment: EnrichmentResponse = {
      lat: 50.94,
      lon: 6.96,
      roof: { usable_area_m2: 38, tilt_deg: 35, azimuth_deg: 170, orientation: 'south', max_array_kwp: 7.2, low_confidence: false },
      specific_yield_kwh_per_kwp: 1012,
      source: { roof: 'google_solar', pv_yield: 'pvgis' },
      warnings: [],
    };
    act(() => {
      useAssessmentStore.getState().applyEnrichment('50667', enrichment);
    });
    const state = useAssessmentStore.getState();
    expect(state.enrichedPostcode).toBe('50667');
    expect(state.draft.household?.roof).toMatchObject({
      available: true,
      usable_area_m2: 38,
      tilt_deg: 35,
      orientation: 'south',
      shading_factor: 0.1,
      specific_yield_kwh_per_kwp: 1012,
    });
    act(() => {
      useAssessmentStore.getState().reset();
    });
    expect(useAssessmentStore.getState().enrichment).toBeUndefined();
    expect(useAssessmentStore.getState().draft.household?.roof.specific_yield_kwh_per_kwp).toBeNull();
  });

  it('keeps the user roof when the lookup has no roof data', () => {
    act(() => {
      useAssessmentStore.getState().applyEnrichment('20095', {
        lat: 53.55,
        lon: 9.99,
        roof: null,
        specific_yield_kwh_per_kwp: null,
        source: { roof: 'unavailable', pv_yield: 'unavailable' },
        warnings: ['Roof geometry unavailable'],
      });
    });
    expect(useAssessmentStore.getState().draft.household?.roof).toMatchObject({ usable_area_m2: 40, tilt_deg: 30 });
  });
});
