import { createFileRoute, Link } from "@tanstack/react-router";
import { MessageSquare, LineChart, Leaf, Clock, TrendingUp } from "lucide-react";

import { AppShell, BrandMark } from "@/components/app-shell";
import { MetricCard } from "@/components/metric-card";
import { Button } from "@/components/ui/button";
import { useResultsStore } from "@/stores/resultsStore";

export const Route = createFileRoute("/results")({
  head: () => ({ meta: [{ title: "Your savings — Cloover" }] }),
  component: Results,
});

const euro = (n: number) =>
  `€${n.toLocaleString(undefined, { maximumFractionDigits: 0 })}`;

function Results() {
  const { forecast, recommendation } = useResultsStore();
  if (!forecast || !recommendation) {
    return (
      <AppShell>
        <header className="mb-6 flex items-center justify-between">
          <BrandMark />
        </header>
        <div className="rounded-2xl border border-border bg-card p-6 text-center">
          <h1 className="text-lg font-semibold">No results yet</h1>
          <p className="mt-2 text-sm text-muted-foreground">
            Complete the quick onboarding to see your monthly savings forecast.
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

  const futurePct = Math.max(
    8,
    Math.round((forecast.futureSpend / forecast.currentSpend) * 100),
  );

  return (
    <AppShell>
      <header className="mb-6 flex items-center justify-between">
        <BrandMark />
        <Link
          to="/advisor"
          className="inline-flex items-center gap-1.5 rounded-full border border-border bg-card px-3 py-1.5 text-xs font-medium text-muted-foreground hover:text-foreground"
        >
          <MessageSquare className="h-3.5 w-3.5" /> Advisor
        </Link>
      </header>

      <section className="rounded-3xl border border-primary/30 bg-gradient-to-b from-primary/15 to-transparent p-6 text-center">
        <div className="text-xs uppercase tracking-widest text-primary">
          You could save
        </div>
        <div className="mt-2 text-6xl font-extrabold tracking-tight text-primary tabular-nums">
          {euro(forecast.monthlySavings)}
        </div>
        <div className="mt-1 text-sm text-muted-foreground">every month</div>
      </section>

      <section className="mt-6 space-y-3">
        <div className="rounded-2xl border border-border bg-card p-4">
          <div className="text-xs uppercase tracking-wider text-muted-foreground">
            Today vs after upgrade
          </div>
          <div className="mt-3 space-y-3">
            <Bar label="Now" amount={forecast.currentSpend} pct={100} tone="muted" />
            <Bar
              label="After"
              amount={forecast.futureSpend}
              pct={futurePct}
              tone="primary"
            />
          </div>
        </div>

        <div className="grid grid-cols-2 gap-3">
          <MetricCard
            label="ROI"
            value={`${forecast.roi.toFixed(1)}%`}
            accent="secondary"
            hint="Annualized"
          />
          <MetricCard
            label="Payback"
            value={`${forecast.paybackTimeline.toFixed(1)} yrs`}
          />
          <MetricCard
            label="Financing"
            value={`${euro(forecast.financingCost)}/mo`}
          />
          <MetricCard
            label="CO₂ saved"
            value={`${(forecast.carbonReduction / 1000).toFixed(1)} t`}
            hint="per year"
          />
        </div>

        <div className="rounded-2xl border border-border bg-card p-4">
          <div className="flex items-center gap-2 text-xs uppercase tracking-wider text-muted-foreground">
            <TrendingUp className="h-3.5 w-3.5" /> Recommended bundle
          </div>
          <div className="mt-2 text-lg font-semibold">
            {recommendation.scenario.name}
          </div>
          <div className="mt-3 flex flex-wrap gap-2">
            {recommendation.scenario.components.map((c) => (
              <span
                key={c}
                className="rounded-full bg-primary/10 px-3 py-1 text-xs font-medium text-primary"
              >
                {c}
              </span>
            ))}
          </div>
          <p className="mt-3 text-sm text-muted-foreground">
            {recommendation.reasoning}
          </p>
        </div>

        <div className="grid grid-cols-3 gap-2 pt-2 text-xs text-muted-foreground">
          <Detail icon={<LineChart className="h-3.5 w-3.5" />} label="Modeled" />
          <Detail icon={<Clock className="h-3.5 w-3.5" />} label="Live tariffs" />
          <Detail icon={<Leaf className="h-3.5 w-3.5" />} label="Verified ROI" />
        </div>
      </section>

      <div className="mt-8 flex flex-col gap-3">
        <Button asChild className="h-12 bg-primary text-primary-foreground hover:bg-primary/90">
          <Link to="/compare">Compare scenarios</Link>
        </Button>
        <Button asChild variant="outline" className="h-12">
          <Link to="/advisor">Ask the AI advisor</Link>
        </Button>
      </div>
    </AppShell>
  );
}

function Bar({
  label,
  amount,
  pct,
  tone,
}: {
  label: string;
  amount: number;
  pct: number;
  tone: "primary" | "muted";
}) {
  return (
    <div>
      <div className="mb-1 flex justify-between text-sm">
        <span className="text-muted-foreground">{label}</span>
        <span className="font-semibold tabular-nums">{euro(amount)}/mo</span>
      </div>
      <div className="h-2.5 w-full overflow-hidden rounded-full bg-muted">
        <div
          className={
            "h-full rounded-full " +
            (tone === "primary" ? "bg-primary" : "bg-muted-foreground/40")
          }
          style={{ width: `${pct}%` }}
        />
      </div>
    </div>
  );
}

function Detail({ icon, label }: { icon: React.ReactNode; label: string }) {
  return (
    <div className="flex items-center justify-center gap-1.5 rounded-lg border border-border bg-card/50 px-2 py-1.5">
      {icon}
      <span>{label}</span>
    </div>
  );
}