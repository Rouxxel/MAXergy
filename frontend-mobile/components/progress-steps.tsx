import React from "react";
import { View, Text } from "react-native";

export function ProgressSteps({ current, total }: { current: number; total: number }) {
  const pct = Math.round(((current + 1) / total) * 100);
  return (
    <View className="space-y-2">
      <View className="flex-row items-center justify-between text-xs text-muted-foreground">
        <Text className="text-xs text-muted-foreground">
          Step {current + 1} of {total}
        </Text>
        <Text className="text-xs text-muted-foreground">{pct}%</Text>
      </View>
      <View className="h-1.5 w-full bg-muted rounded-full overflow-hidden mt-1.5">
        <View
          className="h-full bg-primary rounded-full"
          style={{ width: `${pct}%` }}
        />
      </View>
    </View>
  );
}
