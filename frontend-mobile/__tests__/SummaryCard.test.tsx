import React from 'react';
import { render } from '@testing-library/react-native';
import { SummaryCard } from '@/components/landing/SummaryCard';

describe('SummaryCard component', () => {
  it('renders with label and value', () => {
    const testLabel = 'Test Label';
    const testValue = 'Test Value';
    
    const { getByText } = render(
      <SummaryCard label={testLabel} value={testValue} />
    ) as any;
    
    expect(getByText(testLabel)).toBeTruthy();
    expect(getByText(testValue)).toBeTruthy();
  });
});
