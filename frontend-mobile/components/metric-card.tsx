import React from "react";
import { View, Text } from "react-native";
import { cn } from "@/lib/utils";

interface MetricCardProps {
  label: string;
  value: string;
  hint?: string;
  accent?: "primary" | "secondary";
  className?: string;
}

export function MetricCard({
  label,
  value,
  hint,
  accent,
  className,
}: MetricCardProps) {
  return (
    <View
      className={cn(
        "rounded-2xl border border-border bg-card p-4",
        className
      )}
    >
      <Text className="text-xs uppercase tracking-wider text-muted-foreground">
        {label}
      </Text>
      <Text
        className={cn(
          "mt-1 text-2xl font-bold text-foreground",
          accent === "primary" && "text-primary",
          accent === "secondary" && "text-secondary"
        )}
      >
        {value}
      </Text>
      {hint ? (
        <Text className="mt-1 text-xs text-muted-foreground">{hint}</Text>
      ) : null}
    </View>
  );
}
