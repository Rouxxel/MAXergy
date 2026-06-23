import * as React from "react";
import { View, Text } from "react-native";
import { Zap, TrendingUp, Shield, LayoutGrid, Brain, Calendar, type LucideIcon } from "lucide-react-native";
import { cn } from "@/lib/utils";

interface FeatureCardProps {
  icon: string;
  title: string;
  description: string;
  className?: string;
}

const icons: Record<string, LucideIcon> = {
  Zap,
  TrendingUp,
  Shield,
  LayoutGrid,
  Brain,
  Calendar,
};

export function FeatureCard({ icon, title, description, className }: FeatureCardProps) {
  const Icon = icons[icon] || Zap;

  return (
    <View
      className={cn(
        "rounded-lg border border-border bg-card p-6",
        className
      )}
    >
      <Icon className="h-8 w-8 text-primary" />
      <View className="space-y-1 mt-3">
        <Text className="font-semibold text-foreground text-base">{title}</Text>
        <Text className="text-sm text-muted-foreground mt-1">{description}</Text>
      </View>
    </View>
  );
}
