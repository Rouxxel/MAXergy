import React from 'react';
import { render, fireEvent } from '@testing-library/react-native';
import { FAQItem } from '@/components/landing/FAQItem';

// Mock the trackFAQExpand function
jest.mock('@/services/analytics', () => ({
  trackFAQExpand: jest.fn(),
}));

// Mock react-native-collapsible
jest.mock('react-native-collapsible', () => ({
  __esModule: true,
  default: ({ collapsed, children }: { collapsed: boolean; children: React.ReactNode }) => (
    <>{!collapsed && children}</>
  ),
}));

describe('FAQItem component', () => {
  const testQuestion = 'Test Question?';
  const testAnswer = 'This is a test answer';

  it('renders question', async () => {
    const { getByText } = await render(
      <FAQItem question={testQuestion} answer={testAnswer} />
    );
    expect(getByText(testQuestion)).toBeTruthy();
  });

  it('toggles answer visibility when pressed', async () => {
    const { getByText, queryByText } = await render(
      <FAQItem question={testQuestion} answer={testAnswer} />
    );
    
    // Initially answer should not be visible
    expect(queryByText(testAnswer)).toBeNull();
    
    // Press to expand
    await fireEvent.press(getByText(testQuestion));
    expect(getByText(testAnswer)).toBeTruthy();
    
    // Press to collapse
    await fireEvent.press(getByText(testQuestion));
    expect(queryByText(testAnswer)).toBeNull();
  });
});
