import * as React from "react";
import { View, Text } from "react-native";
import { cn } from "@/lib/utils";

interface SummaryCardProps {
  label: string;
  value: string;
  className?: string;
}

export function SummaryCard({ label, value, className }: SummaryCardProps) {
  return (
    <View
      className={cn(
        "rounded-lg border border-border bg-card p-4",
        className
      )}
    >
      <Text className="text-sm text-muted-foreground">{label}</Text>
      <Text className="font-semibold text-foreground text-base mt-1">{value}</Text>
    </View>
  );
}
