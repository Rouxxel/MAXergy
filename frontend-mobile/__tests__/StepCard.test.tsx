import React from 'react';
import { render } from '@testing-library/react-native';
import { StepCard } from '@/components/landing/StepCard';

describe('StepCard component', () => {
  it('renders with step number, title and description', async () => {
    const testStep = 1;
    const testTitle = 'Test Step';
    const testDescription = 'This is a test step description';
    
    const { getByText } = await render(
      <StepCard step={testStep} title={testTitle} description={testDescription} />
    );
    
    expect(getByText(String(testStep))).toBeTruthy();
    expect(getByText(testTitle)).toBeTruthy();
    expect(getByText(testDescription)).toBeTruthy();
  });
});
