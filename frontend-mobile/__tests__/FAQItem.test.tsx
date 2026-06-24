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

  it('renders question', () => {
    const { getByText } = render(
      <FAQItem question={testQuestion} answer={testAnswer} />
    ) as any;
    expect(getByText(testQuestion)).toBeTruthy();
  });

  it('toggles answer visibility when pressed', () => {
    const { getByText, queryByText } = render(
      <FAQItem question={testQuestion} answer={testAnswer} />
    ) as any;
    
    // Initially answer should not be visible
    expect(queryByText(testAnswer)).toBeNull();
    
    // Press to expand
    fireEvent.press(getByText(testQuestion));
    expect(getByText(testAnswer)).toBeTruthy();
    
    // Press to collapse
    fireEvent.press(getByText(testQuestion));
    expect(queryByText(testAnswer)).toBeNull();
  });
});
