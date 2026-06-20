import { createFileRoute, useNavigate } from "@tanstack/react-router";
import { useEffect, useState } from "react";
import { useMutation } from "@tanstack/react-query";

import { AppShell, BrandMark } from "@/components/app-shell";
import { Progress } from "@/components/ui/progress";
import { useAssessmentStore } from "@/stores/assessmentStore";
import { useResultsStore } from "@/stores/resultsStore";
import { useUiStore } from "@/stores/uiStore";
import {
  postAssessment,
  postForecast,
  postRecommendation,
} from "@/services/endpoints";

export const Route = createFileRoute("/loading")({
  head: () => ({ meta: [{ title: "Calculating — MAXergy" }] }),
  component: LoadingScreen,
});

const STAGES = [
  "Analyzing your household…",
  "Modeling solar yield on your roof…",
  "Pricing battery, heat pump and EV scenarios…",
  "Calculating your monthly savings…",
];

function LoadingScreen() {
  const navigate = useNavigate();
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
      navigate({ to: "/results" });
    },
    onError: (err: Error) => {
      setError(err.message);
      navigate({ to: "/" });
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

  return (
    <AppShell>
      <header className="mb-12 flex items-center justify-between">
        <BrandMark />
      </header>
      <div className="flex flex-col items-center justify-center pt-12 text-center">
        <div className="relative h-24 w-24">
          <div className="absolute inset-0 animate-ping rounded-full bg-primary/20" />
          <div className="absolute inset-2 animate-pulse rounded-full bg-primary/40" />
          <div className="absolute inset-6 rounded-full bg-primary" />
        </div>
        <h1 className="mt-10 text-xl font-semibold">{STAGES[stage]}</h1>
        <p className="mt-2 text-sm text-muted-foreground">This usually takes 5–10 seconds.</p>

        <div className="mt-6 w-full max-w-xs">
          <Progress value={((stage + 1) / STAGES.length) * 100} className="h-2" />
        </div>

        <ul className="mt-10 w-full space-y-2 text-left text-sm">
          {STAGES.map((s, i) => (
            <li
              key={s}
              className={
                "flex items-center gap-2 " +
                (i <= stage ? "text-foreground" : "text-muted-foreground/60")
              }
            >
              <span
                className={
                  "inline-block h-1.5 w-1.5 rounded-full " +
                  (i <= stage ? "bg-primary" : "bg-muted-foreground/40")
                }
              />
              {s}
            </li>
          ))}
        </ul>
      </div>
    </AppShell>
  );
}