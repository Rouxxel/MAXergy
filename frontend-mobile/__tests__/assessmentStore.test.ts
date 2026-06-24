import { act } from 'react';
import { useAssessmentStore } from '@/stores/assessmentStore';

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
});
