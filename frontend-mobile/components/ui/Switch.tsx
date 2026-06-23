import * as React from "react";
import { Pressable, View } from "react-native";
import { cn } from "@/lib/utils";

export interface SwitchProps {
  checked?: boolean;
  onCheckedChange?: (checked: boolean) => void;
  disabled?: boolean;
  className?: string;
}

export function Switch({
  checked = false,
  onCheckedChange,
  disabled = false,
  className,
}: SwitchProps) {
  const handlePress = () => {
    if (disabled) return;
    if (onCheckedChange) {
      onCheckedChange(!checked);
    }
  };

  return (
    <Pressable
      disabled={disabled}
      onPress={handlePress}
      className={cn(
        "flex h-7 w-12 shrink-0 flex-row items-center rounded-full border-2 border-transparent p-0.5 transition-colors",
        checked ? "bg-primary" : "bg-muted",
        disabled && "opacity-50",
        className
      )}
    >
      <View
        className={cn(
          "h-5 w-5 rounded-full bg-background shadow",
          checked ? "translate-x-5" : "translate-x-0"
        )}
      />
    </Pressable>
  );
}
