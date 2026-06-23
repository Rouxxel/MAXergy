import * as React from "react";
import { Pressable, Text } from "react-native";
import { useRouter } from "expo-router";
import { ArrowLeft } from "lucide-react-native";
import { cn } from "@/lib/utils";

interface BackButtonProps {
  className?: string;
  textClassName?: string;
  label?: string;
}

export function BackButton({ className, textClassName, label = "Back" }: BackButtonProps) {
  const router = useRouter();

  return (
    <Pressable
      onPress={() => {
        if (router.canGoBack()) {
          router.back();
        }
      }}
      className={cn("flex-row items-center py-2 active:opacity-75", className)}
      accessibilityRole="button"
      accessibilityLabel={label}
    >
      <ArrowLeft size={20} className="text-muted-foreground" />
      {label ? (
        <Text className={cn("text-sm font-medium text-muted-foreground ml-1.5", textClassName)}>
          {label}
        </Text>
      ) : null}
    </Pressable>
  );
}
