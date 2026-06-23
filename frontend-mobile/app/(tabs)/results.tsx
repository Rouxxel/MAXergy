import React from "react";
import { View, Text } from "react-native";
import { Header } from "@/components/header";

export default function ResultsScreen() {
  return (
    <View className="flex-1 bg-background">
      <Header />
      <View className="flex-1 items-center justify-center p-5">
        <Text className="text-foreground text-xl font-bold">Results Screen</Text>
        <Text className="text-muted-foreground text-sm text-center mt-2">
          This is a placeholder for the savings summary and charts.
        </Text>
      </View>
    </View>
  );
}
