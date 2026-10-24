import '@testing-library/jest-native/extend-expect';

jest.mock('react-native', () => {
  const React = require('react');
  return {
    View: 'View',
    Text: 'Text',
    TouchableOpacity: 'TouchableOpacity',
    Pressable: 'Pressable',
    ActivityIndicator: 'ActivityIndicator',
    StyleSheet: {
      create: jest.fn(obj => obj),
      // Used by @testing-library/react-native to check accessibility (display: none etc.)
      flatten: (style) =>
        Array.isArray(style)
          ? Object.assign({}, ...style.flat(Infinity).filter(Boolean))
          : style || {},
    },
    Animated: {
      View: 'Animated.View',
      Value: jest.fn(() => ({
        interpolate: jest.fn(),
      })),
      timing: jest.fn(() => ({
        start: jest.fn()
      }))
    },
    Dimensions: {
      get: jest.fn(() => ({ width: 375, height: 667 }))
    },
    ScrollView: 'ScrollView',
  };
});

jest.mock('react-native-reanimated', () => {
  return {
    useAnimatedScrollHandler: jest.fn(),
    useSharedValue: jest.fn(() => 0),
    withTiming: jest.fn(),
    withSpring: jest.fn(),
    useAnimatedStyle: jest.fn(() => {}),
    ScrollView: 'Animated.ScrollView',
  };
});

jest.mock('react-native-svg', () => {
  return {
    Svg: 'Svg',
    Path: 'Path',
    Circle: 'Circle',
    Rect: 'Rect',
    Line: 'Line',
    G: 'G',
    Text: 'Text',
  };
});

jest.mock('expo-router', () => ({
  Link: 'Link',
  useRouter: () => ({
    push: jest.fn(),
    replace: jest.fn(),
    back: jest.fn()
  }),
  useLocalSearchParams: jest.fn()
}));
