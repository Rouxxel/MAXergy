import { createFileRoute, Link } from "@tanstack/react-router";
import { useMemo, useState } from "react";
import { ArrowLeft, Check, ArrowDownUp } from "lucide-react";

import { AppShell, BrandMark } from "@/components/app-shell";
import { Button } from "@/components/ui/button";
import { useResultsStore } from "@/stores/resultsStore";
import type { Scenario } from "@/types";

export const Route = createFileRoute("/compare")({
  head: () => ({ meta: [{ title: "Compare scenarios — MAXergy" }] }),
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
        ? b.monthly_saving_eur - a.monthly_saving_eur
        : a.monthly_saving_eur - b.monthly_saving_eur,
    );
  }, [forecast, sortDesc]);

  const recommendedId = useMemo(() => {
    if (!forecast) return undefined;
    const top = [...forecast.scenarios].sort((a, b) => b.monthly_saving_eur - a.monthly_saving_eur)[0];
    return top?.id;
  }, [forecast]);

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
          const recommended = recommendedId === s.id;
          const components = [
            s.components.solar_pv && "Solar PV",
            s.components.battery && "Battery",
            s.components.heat_pump && "Heat Pump",
            s.components.ev_charger && "EV Charger",
          ].filter(Boolean);
          const isNegativeSavings = s.monthly_saving_eur < 0;
          return (
            <li
              key={s.id}
              className={
                "overflow-hidden rounded-2xl border bg-card transition " +
                (selected ? "border-primary" : isNegativeSavings ? "border-orange-500/30" : "border-border")
              }
            >
              <button
                onClick={() => setOpenId(open ? undefined : s.id)}
                className="flex w-full items-center justify-between gap-3 p-4 text-left"
              >
                <div className="min-w-0">
                  <div className="flex items-center gap-2">
                    <span className="truncate font-semibold">Scenario {s.id}</span>
                    {recommended && (
                      <span className="rounded-full bg-primary/20 px-2 py-0.5 text-[10px] font-semibold uppercase tracking-wider text-primary">
                        Recommended
                      </span>
                    )}
                    {selected ? (
                      <span className="rounded-full bg-secondary/20 px-2 py-0.5 text-[10px] font-semibold uppercase tracking-wider text-secondary">
                        Selected
                      </span>
                    ) : null}
                  </div>
                  <div className="mt-1 truncate text-xs text-muted-foreground">
                    {components.join(" · ")}
                  </div>
                </div>
                <div className="text-right">
                  <div className={`text-lg font-bold tabular-nums ${isNegativeSavings ? "text-orange-500" : "text-primary"}`}>
                    {euro(s.monthly_saving_eur)}
                  </div>
                  <div className="text-[10px] uppercase tracking-wider text-muted-foreground">
                    /month
                  </div>
                </div>
              </button>

              {open ? (
                <div className="border-t border-border p-4">
                  <div className="mb-3 space-y-2">
                    <div className="text-xs uppercase tracking-wider text-muted-foreground">
                      Component sizing
                    </div>
                    <div className="grid grid-cols-3 gap-2 text-xs">
                      {s.sizing.solar_pv_kwp && <div className="rounded-lg bg-background/40 p-2 text-center">Solar: {s.sizing.solar_pv_kwp} kWp</div>}
                      {s.sizing.battery_kwh && <div className="rounded-lg bg-background/40 p-2 text-center">Battery: {s.sizing.battery_kwh} kWh</div>}
                      {s.sizing.heat_pump_kw && <div className="rounded-lg bg-background/40 p-2 text-center">Heat Pump: {s.sizing.heat_pump_kw} kW</div>}
                    </div>
                  </div>
                  <div className="grid grid-cols-3 gap-3 text-center">
                    <Stat label="Monthly payment" value={euro(s.financing_installment_eur)} />
                    <Stat label="Self-consumption" value={`${(s.self_consumption_ratio * 100).toFixed(0)}%`} />
                    <Stat label="Payback" value={s.payback_month ? `${(s.payback_month / 12).toFixed(1)} yr` : "N/A"} />
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