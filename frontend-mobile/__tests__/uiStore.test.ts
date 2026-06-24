import { act } from 'react';
import { useUiStore } from '@/stores/uiStore';

describe('uiStore', () => {
  beforeEach(() => {
    useUiStore.setState(useUiStore.getInitialState(), true);
  });

  it('sets globalError', () => {
    const testError = 'Test error message';
    act(() => {
      useUiStore.getState().setError(testError);
    });
    expect(useUiStore.getState().globalError).toBe(testError);
  });

  it('clears globalError when undefined is passed', () => {
    act(() => {
      useUiStore.getState().setError('Test error');
      useUiStore.getState().setError(undefined);
    });
    expect(useUiStore.getState().globalError).toBeUndefined();
  });
});
