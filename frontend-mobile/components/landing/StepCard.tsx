import * as React from "react";
import { View, Text } from "react-native";
import { cn } from "@/lib/utils";

interface StepCardProps {
  step: number;
  title: string;
  description: string;
  className?: string;
}

export function StepCard({ step, title, description, className }: StepCardProps) {
  return (
    <View className={cn("space-y-4", className)}>
      <View className="flex h-12 w-12 items-center justify-center rounded-full bg-primary">
        <Text className="text-primary-foreground font-bold text-lg">{step}</Text>
      </View>
      <View className="space-y-2 mt-3">
        <Text className="font-semibold text-foreground text-base">{title}</Text>
        <Text className="text-sm text-muted-foreground mt-1">{description}</Text>
      </View>
    </View>
  );
}
