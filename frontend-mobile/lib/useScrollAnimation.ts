
import React, { useRef, useState, useEffect } from 'react';
import { View, ScrollView, Animated } from 'react-native';

export function useScrollAnimation() {
  const opacity = useRef(new Animated.Value(0)).current;
  const [hasAnimated, setHasAnimated] = useState(false);

  const triggerAnimation = () => {
    if (!hasAnimated) {
      setHasAnimated(true);
      Animated.timing(opacity, {
        toValue: 1,
        duration: 700,
        useNativeDriver: true,
      }).start();
    }
  };

  return {
    animatedStyle: {
      opacity,
      transform: [
          {
            translateY: opacity.interpolate({
            inputRange: [0, 1],
            outputRange: [20, 0],
          }),
        },
      ]
    },
    triggerAnimation,
    hasAnimated,
  };
}

export default useScrollAnimation;
