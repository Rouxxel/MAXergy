import * as React from "react";
import { View } from "react-native";
import CommunitySlider from "@react-native-community/slider";
import { cn } from "@/lib/utils";

export interface SliderProps {
  value?: number[];
  onValueChange?: (value: number[]) => void;
  min?: number;
  max?: number;
  step?: number;
  className?: string;
  disabled?: boolean;
}

export function Slider({
  value = [0],
  onValueChange,
  min = 0,
  max = 100,
  step = 1,
  className,
  disabled = false,
}: SliderProps) {
  const handleValueChange = (val: number) => {
    if (onValueChange) {
      onValueChange([val]);
    }
  };

  return (
    <View className={cn("w-full py-2", className)}>
      <CommunitySlider
        value={value[0]}
        onValueChange={handleValueChange}
        minimumValue={min}
        maximumValue={max}
        step={step}
        disabled={disabled}
        minimumTrackTintColor="#B8FF5A"
        maximumTrackTintColor="rgba(255, 255, 255, 0.12)"
        thumbTintColor="#B8FF5A"
      />
    </View>
  );
}
