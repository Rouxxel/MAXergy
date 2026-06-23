import React, { useEffect, useState } from "react";
import { View, Text, ActivityIndicator } from "react-native";
import { useRouter } from "expo-router";
import { useMutation } from "@tanstack/react-query";

import { Header } from "@/components/header";
import { useAssessmentStore } from "@/stores/assessmentStore";
import { useResultsStore } from "@/stores/resultsStore";
import { useUiStore } from "@/stores/uiStore";
import {
  postAssessment,
  postForecast,
  postRecommendation,
} from "@/services/endpoints";

const STAGES = [
  "Analyzing your household…",
  "Modeling solar yield on your roof…",
  "Pricing battery, heat pump and EV scenarios…",
  "Calculating your monthly savings…",
];

export default function LoadingScreen() {
  const router = useRouter();
  const getCompleted = useAssessmentStore((s) => s.getCompleted);
  const setForecast = useResultsStore((s) => s.setForecast);
  const setRecommendation = useResultsStore((s) => s.setRecommendation);
  const setError = useUiStore((s) => s.setError);
  const [stage, setStage] = useState(0);

  const mutation = useMutation({
    mutationFn: async () => {
      const data = getCompleted();
      if (!data) throw new Error("Assessment incomplete");
      await postAssessment(data);
      const [forecast, recommendation] = await Promise.all([
        postForecast(data),
        postRecommendation(data),
      ]);
      return { forecast, recommendation };
    },
    onSuccess: ({ forecast, recommendation }) => {
      setForecast(forecast);
      setRecommendation(recommendation);
      router.replace("/results");
    },
    onError: (err: Error) => {
      setError(err.message);
      router.replace("/landing");
    },
  });

  useEffect(() => {
    mutation.mutate();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  useEffect(() => {
    const id = setInterval(
      () => setStage((s) => Math.min(s + 1, STAGES.length - 1)),
      900,
    );
    return () => clearInterval(id);
  }, []);

  const progressPercent = ((stage + 1) / STAGES.length) * 100;

  return (
    <View className="flex-1 bg-background">
      <Header />
      
      <View className="flex-1 items-center justify-center px-6 pb-20">
        <View className="relative h-24 w-24 items-center justify-center">
          <View className="absolute inset-0 rounded-full bg-primary/20 scale-125 animate-pulse" />
          <View className="h-16 w-16 rounded-full bg-primary items-center justify-center">
            <ActivityIndicator size="small" color="#111827" />
          </View>
        </View>

        <Text className="mt-10 text-xl font-bold text-foreground text-center">
          {STAGES[stage]}
        </Text>
        <Text className="mt-2 text-sm text-muted-foreground text-center">
          This usually takes 5–10 seconds.
        </Text>

        {/* Custom Progress Bar */}
        <View className="mt-8 w-full max-w-xs h-2 bg-muted rounded-full overflow-hidden">
          <View 
            className="h-full bg-primary rounded-full" 
            style={{ width: `${progressPercent}%` }} 
          />
        </View>

        <View className="mt-12 w-full space-y-3">
          {STAGES.map((s, i) => {
            const isDoneOrActive = i <= stage;
            return (
              <View key={s} className="flex-row items-center space-x-3">
                <View 
                  className={`h-2.5 w-2.5 rounded-full ${
                    isDoneOrActive ? "bg-primary" : "bg-muted-foreground/30"
                  }`} 
                />
                <Text 
                  className={`text-sm ml-2 ${
                    isDoneOrActive ? "text-foreground font-medium" : "text-muted-foreground/50"
                  }`}
                >
                  {s}
                </Text>
              </View>
            );
          })}
        </View>
      </View>
    </View>
  );
}
