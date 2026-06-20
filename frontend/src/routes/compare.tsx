import { createFileRoute, Link } from "@tanstack/react-router";
import { useMemo, useState } from "react";
import { ArrowLeft, Check, ArrowDownUp } from "lucide-react";

import { AppShell, BrandMark } from "@/components/app-shell";
import { Button } from "@/components/ui/button";
import { useResultsStore } from "@/stores/resultsStore";
import type { Scenario } from "@/types";

export const Route = createFileRoute("/compare")({
  head: () => ({ meta: [{ title: "Compare scenarios — Cloover" }] }),
  component: Compare,
});

const euro = (n: number) => `€${n.toLocaleString()}`;

function Compare() {
  const { forecast, selectedScenarioId, selectScenario } = useResultsStore();
  const [sortDesc, setSortDesc] = useState(true);
  const [openId, setOpenId] = useState<string | undefined>(selectedScenarioId);

  const sorted = useMemo(() => {
    if (!forecast) return [] as Scenario[];
    return [...forecast.scenarios].sort((a, b) =>
      sortDesc
        ? b.monthlySavings - a.monthlySavings
        : a.monthlySavings - b.monthlySavings,
    );
  }, [forecast, sortDesc]);

  if (!forecast) {
    return (
      <AppShell>
        <header className="mb-6 flex items-center justify-between">
          <BrandMark />
        </header>
        <div className="rounded-2xl border border-border bg-card p-6 text-center">
          <h1 className="text-lg font-semibold">Nothing to compare yet</h1>
          <p className="mt-2 text-sm text-muted-foreground">
            Finish the onboarding to generate scenarios you can compare.
          </p>
          <Link
            to="/"
            className="mt-5 inline-flex items-center justify-center rounded-full bg-primary px-4 py-2 text-sm font-semibold text-primary-foreground"
          >
            Start onboarding
          </Link>
        </div>
      </AppShell>
    );
  }

  return (
    <AppShell>
      <header className="mb-6 flex items-center justify-between">
        <Link
          to="/results"
          className="inline-flex items-center gap-1.5 text-sm text-muted-foreground hover:text-foreground"
        >
          <ArrowLeft className="h-4 w-4" /> Back
        </Link>
        <BrandMark />
      </header>

      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold tracking-tight">Compare scenarios</h1>
        <button
          onClick={() => setSortDesc((v) => !v)}
          className="inline-flex items-center gap-1.5 rounded-full border border-border bg-card px-3 py-1.5 text-xs text-muted-foreground hover:text-foreground"
        >
          <ArrowDownUp className="h-3.5 w-3.5" />
          {sortDesc ? "Highest savings" : "Lowest savings"}
        </button>
      </div>
      <p className="mt-1 text-sm text-muted-foreground">
        Tap any bundle to see details and select it.
      </p>

      <ul className="mt-5 space-y-3">
        {sorted.map((s) => {
          const selected = selectedScenarioId === s.id;
          const open = openId === s.id;
          return (
            <li
              key={s.id}
              className={
                "overflow-hidden rounded-2xl border bg-card transition " +
                (selected ? "border-primary" : "border-border")
              }
            >
              <button
                onClick={() => setOpenId(open ? undefined : s.id)}
                className="flex w-full items-center justify-between gap-3 p-4 text-left"
              >
                <div className="min-w-0">
                  <div className="flex items-center gap-2">
                    <span className="truncate font-semibold">{s.name}</span>
                    {s.recommended ? (
                      <span className="rounded-full bg-secondary/20 px-2 py-0.5 text-[10px] font-semibold uppercase tracking-wider text-secondary">
                        Recommended
                      </span>
                    ) : null}
                  </div>
                  <div className="mt-1 truncate text-xs text-muted-foreground">
                    {s.components.join(" · ")}
                  </div>
                </div>
                <div className="text-right">
                  <div className="text-lg font-bold text-primary tabular-nums">
                    {euro(s.monthlySavings)}
                  </div>
                  <div className="text-[10px] uppercase tracking-wider text-muted-foreground">
                    /month
                  </div>
                </div>
              </button>

              {open ? (
                <div className="border-t border-border p-4">
                  <div className="grid grid-cols-3 gap-3 text-center">
                    <Stat label="Upfront" value={euro(s.upfrontCost)} />
                    <Stat label="Financing" value={`${euro(s.financingCost)}/mo`} />
                    <Stat label="Payback" value={`${s.paybackYears.toFixed(1)} yr`} />
                  </div>
                  <div className="mt-3 text-center text-xs text-muted-foreground">
                    Cuts {Math.round(s.carbonReductionKg).toLocaleString()} kg CO₂e / year
                  </div>
                  <Button
                    onClick={() => selectScenario(s.id)}
                    className="mt-4 h-11 w-full bg-primary text-primary-foreground hover:bg-primary/90"
                  >
                    {selected ? (
                      <>
                        <Check className="mr-1.5 h-4 w-4" /> Selected
                      </>
                    ) : (
                      "Select this bundle"
                    )}
                  </Button>
                </div>
              ) : null}
            </li>
          );
        })}
      </ul>
    </AppShell>
  );
}

function Stat({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-xl border border-border bg-background/40 p-2">
      <div className="text-[10px] uppercase tracking-wider text-muted-foreground">
        {label}
      </div>
      <div className="mt-0.5 text-sm font-semibold tabular-nums">{value}</div>
    </div>
  );
}