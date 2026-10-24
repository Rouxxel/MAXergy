import React from 'react';
import { render } from '@testing-library/react-native';
import { SummaryCard } from '@/components/landing/SummaryCard';

describe('SummaryCard component', () => {
  it('renders with label and value', async () => {
    const testLabel = 'Test Label';
    const testValue = 'Test Value';
    
    const { getByText } = await render(
      <SummaryCard label={testLabel} value={testValue} />
    );
    
    expect(getByText(testLabel)).toBeTruthy();
    expect(getByText(testValue)).toBeTruthy();
  });
});
