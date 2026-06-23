import * as React from "react";
import { useState } from "react";
import { View, Text, Pressable } from "react-native";
import { ChevronDown } from "lucide-react-native";
import Collapsible from "react-native-collapsible";
import { trackFAQExpand } from "@/services/analytics";
import { cn } from "@/lib/utils";

interface FAQItemProps {
  question: string;
  answer: string;
  className?: string;
}

export function FAQItem({ question, answer, className }: FAQItemProps) {
  const [isOpen, setIsOpen] = useState(false);

  const handleToggle = () => {
    const nextState = !isOpen;
    setIsOpen(nextState);
    if (nextState) {
      trackFAQExpand(question);
    }
  };

  return (
    <View className={cn("rounded-lg border border-border bg-card overflow-hidden", className)}>
      <Pressable
        onPress={handleToggle}
        className="w-full flex-row items-center justify-between p-4"
        accessibilityRole="button"
        accessibilityState={{ expanded: isOpen }}
      >
        <Text className="font-medium text-foreground flex-1 pr-4 text-base">{question}</Text>
        <ChevronDown
          className="h-5 w-5 text-muted-foreground"
          style={{ transform: [{ rotate: isOpen ? "180deg" : "0deg" }] }}
        />
      </Pressable>
      <Collapsible collapsed={!isOpen}>
        <View className="px-4 pb-4">
          <Text className="text-sm text-muted-foreground leading-relaxed">{answer}</Text>
        </View>
      </Collapsible>
    </View>
  );
}
