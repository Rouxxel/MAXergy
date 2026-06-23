import React from "react";
import { Tabs } from "expo-router";
import { Home, BarChart3, LayoutGrid, MessageSquare } from "lucide-react-native";

export default function TabLayout() {
  return (
    <Tabs
      screenOptions={{
        headerShown: false,
        tabBarActiveTintColor: "#B8FF5A",
        tabBarInactiveTintColor: "#9CA3AF",
        tabBarStyle: {
          backgroundColor: "#111827",
          borderTopColor: "rgba(255, 255, 255, 0.1)",
          paddingBottom: 8,
          paddingTop: 8,
          height: 64,
        },
        tabBarLabelStyle: {
          fontSize: 11,
          fontWeight: "500",
        },
      }}
    >
      <Tabs.Screen
        name="assessment"
        options={{
          title: "Start",
          tabBarIcon: ({ color, size }) => <Home color={color} size={size || 20} />,
        }}
      />
      <Tabs.Screen
        name="results"
        options={{
          title: "Results",
          tabBarIcon: ({ color, size }) => <BarChart3 color={color} size={size || 20} />,
        }}
      />
      <Tabs.Screen
        name="compare"
        options={{
          title: "Compare",
          tabBarIcon: ({ color, size }) => <LayoutGrid color={color} size={size || 20} />,
        }}
      />
      <Tabs.Screen
        name="advisor"
        options={{
          title: "Advisor",
          tabBarIcon: ({ color, size }) => <MessageSquare color={color} size={size || 20} />,
        }}
      />
    </Tabs>
  );
}
