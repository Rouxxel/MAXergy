import * as React from "react";
import { View, Text } from "react-native";
import { Logo } from "./logo";
import { cn } from "@/lib/utils";

interface HeaderProps {
  className?: string;
}

export function Header({ className }: HeaderProps) {
  return (
    <View className={cn("flex-row items-center justify-between py-4 border-b border-border bg-background px-5", className)}>
      <View className="flex-row items-center">
        <Logo size={64} className="h-9 w-9" />
        <Text className="text-lg font-bold tracking-tight text-foreground ml-2">MAXergy</Text>
      </View>
    </View>
  );
}
