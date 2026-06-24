import React from 'react';
import { render, fireEvent } from '@testing-library/react-native';
import { Button } from '../components/ui/Button';

describe('Button component', () => {
  it('renders correctly', () => {
    const { getByText } = render(<Button>Test Button</Button>) as any;
    expect(getByText('Test Button')).toBeTruthy();
  });

  it('calls onPress when pressed', () => {
    const onPress = jest.fn();
    const { getByText } = render(<Button onPress={onPress}>Press Me</Button>) as any;
    fireEvent.press(getByText('Press Me'));
    expect(onPress).toHaveBeenCalledTimes(1);
  });
});
