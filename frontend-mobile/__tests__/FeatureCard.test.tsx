import React from 'react';
import { render } from '@testing-library/react-native';
import { FeatureCard } from '@/components/landing/FeatureCard';

describe('FeatureCard component', () => {
  it('renders with title and description', async () => {
    const testTitle = 'Test Feature';
    const testDescription = 'This is a test feature description';
    
    const { getByText } = await render(
      <FeatureCard icon="Zap" title={testTitle} description={testDescription} />
    );
    
    expect(getByText(testTitle)).toBeTruthy();
    expect(getByText(testDescription)).toBeTruthy();
  });
});
