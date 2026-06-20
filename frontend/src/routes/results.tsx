import { createFileRoute, Link } from "@tanstack/react-router";
import { MessageSquare, LineChart, Leaf, Clock, TrendingUp, Zap, Flame, Car, DollarSign } from "lucide-react";
import { LineChart as RechartsLineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from "recharts";

import { AppShell, BrandMark } from "@/components/app-shell";
import { MetricCard } from "@/components/metric-card";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { useResultsStore } from "@/stores/resultsStore";

export const Route = createFileRoute("/results")({
  head: () => ({ meta: [{ title: "Your savings — MAXergy" }] }),
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

  const baselineTotal = forecast.baseline.monthly_cost_eur.total;
  const selectedScenario = recommendation.selected_scenario;
  const scenarioTotal = selectedScenario.monthly_cost_eur.total;
  const monthlySavings = baselineTotal - scenarioTotal;
  const futurePct = Math.max(8, Math.round((scenarioTotal / baselineTotal) * 100));

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
          {euro(monthlySavings)}
        </div>
        <div className="mt-1 text-sm text-muted-foreground">every month</div>
      </section>

      <section className="mt-6 space-y-3">
        <div className="rounded-2xl border border-border bg-card p-4">
          <div className="text-xs uppercase tracking-wider text-muted-foreground">
            Today vs after upgrade
          </div>
          <div className="mt-3 space-y-3">
            <Bar label="Now" amount={baselineTotal} pct={100} tone="muted" />
            <Bar
              label="After"
              amount={scenarioTotal}
              pct={futurePct}
              tone="primary"
            />
          </div>
        </div>

        <div className="rounded-2xl border border-border bg-card p-4">
          <div className="text-xs uppercase tracking-wider text-muted-foreground">
            Baseline monthly costs
          </div>
          <div className="mt-3 space-y-2">
            <CostRow icon={<Zap className="h-4 w-4" />} label="Electricity" value={euro(forecast.baseline.monthly_cost_eur.electricity)} />
            <CostRow icon={<Flame className="h-4 w-4" />} label="Heating" value={euro(forecast.baseline.monthly_cost_eur.gas_oil)} />
            <CostRow icon={<Car className="h-4 w-4" />} label="Mobility" value={euro(forecast.baseline.monthly_cost_eur.fuel)} />
            <div className="mt-2 border-t border-border pt-2">
              <CostRow icon={<DollarSign className="h-4 w-4" />} label="Total" value={euro(forecast.baseline.monthly_cost_eur.total)} bold />
            </div>
          </div>
        </div>

        <div className="rounded-2xl border border-border bg-card p-4">
          <div className="text-xs uppercase tracking-wider text-muted-foreground">
            Scenario monthly costs
          </div>
          <div className="mt-3 space-y-2">
            <CostRow icon={<Zap className="h-4 w-4" />} label="Electricity" value={euro(selectedScenario.monthly_cost_eur.electricity)} />
            <CostRow icon={<Flame className="h-4 w-4" />} label="Heating" value={euro(selectedScenario.monthly_cost_eur.gas_oil)} />
            <CostRow icon={<Car className="h-4 w-4" />} label="Mobility" value={euro(selectedScenario.monthly_cost_eur.fuel)} />
            <CostRow icon={<DollarSign className="h-4 w-4" />} label="Financing" value={euro(selectedScenario.financing_installment_eur)} />
            <div className="mt-2 border-t border-border pt-2">
              <CostRow icon={<DollarSign className="h-4 w-4" />} label="Total" value={euro(selectedScenario.monthly_cost_eur.total)} bold />
            </div>
          </div>
        </div>

        <div className="grid grid-cols-2 gap-3">
          <MetricCard
            label="Monthly payment"
            value={euro(selectedScenario.financing_installment_eur)}
            hint="Financing"
          />
          <MetricCard
            label="Self-consumption"
            value={`${(selectedScenario.self_consumption_ratio * 100).toFixed(0)}%`}
            hint="Solar used directly"
          />
          <MetricCard
            label="Payback"
            value={selectedScenario.payback_month ? `${(selectedScenario.payback_month / 12).toFixed(1)} yrs` : "N/A"}
          />
          <MetricCard
            label="Monthly saving"
            value={euro(selectedScenario.monthly_saving_eur)}
            accent="primary"
          />
        </div>

        <div className="rounded-2xl border border-border bg-card p-4">
          <div className="flex items-center gap-2 text-xs uppercase tracking-wider text-muted-foreground">
            <TrendingUp className="h-3.5 w-3.5" /> Recommended bundle
          </div>
          <div className="mt-2 text-lg font-semibold">
            Scenario {selectedScenario.id}
          </div>
          <div className="mt-3 flex flex-wrap gap-2">
            {selectedScenario.components.solar_pv && (
              <span className="rounded-full bg-primary/10 px-3 py-1 text-xs font-medium text-primary">
                Solar PV ({selectedScenario.sizing.solar_pv_kwp} kWp)
              </span>
            )}
            {selectedScenario.components.battery && (
              <span className="rounded-full bg-primary/10 px-3 py-1 text-xs font-medium text-primary">
                Battery ({selectedScenario.sizing.battery_kwh} kWh)
              </span>
            )}
            {selectedScenario.components.heat_pump && (
              <span className="rounded-full bg-primary/10 px-3 py-1 text-xs font-medium text-primary">
                Heat Pump ({selectedScenario.sizing.heat_pump_kw} kW)
              </span>
            )}
            {selectedScenario.components.ev_charger && (
              <span className="rounded-full bg-primary/10 px-3 py-1 text-xs font-medium text-primary">
                EV Charger
              </span>
            )}
          </div>
          <p className="mt-3 text-sm text-muted-foreground">
            {recommendation.reasoning}
          </p>
        </div>

        <div className="rounded-2xl border border-border bg-card p-4">
          <div className="text-xs uppercase tracking-wider text-muted-foreground">
            Short-term forecast (12 months)
          </div>
          <div className="mt-3 h-48">
            <ResponsiveContainer width="100%" height="100%">
              <RechartsLineChart data={selectedScenario.short_term_forecast}>
                <CartesianGrid strokeDasharray="3 3" className="stroke-muted" />
                <XAxis dataKey="month" tick={{ fontSize: 10 }} />
                <YAxis tick={{ fontSize: 10 }} />
                <Tooltip />
                <Line type="monotone" dataKey="cost_eur" stroke="hsl(var(--primary))" strokeWidth={2} dot={false} name="Scenario" />
                <Line type="monotone" dataKey="cost_eur" stroke="hsl(var(--muted-foreground))" strokeWidth={2} dot={false} name="Baseline" data={forecast.baseline.short_term_forecast} />
              </RechartsLineChart>
            </ResponsiveContainer>
          </div>
        </div>

        <div className="rounded-2xl border border-border bg-card p-4">
          <div className="text-xs uppercase tracking-wider text-muted-foreground">
            Long-term forecast (20 years)
          </div>
          <div className="mt-3 h-48">
            <ResponsiveContainer width="100%" height="100%">
              <RechartsLineChart data={selectedScenario.long_term_forecast}>
                <CartesianGrid strokeDasharray="3 3" className="stroke-muted" />
                <XAxis dataKey="year" tick={{ fontSize: 10 }} />
                <YAxis tick={{ fontSize: 10 }} />
                <Tooltip />
                <Line type="monotone" dataKey="cost_eur" stroke="hsl(var(--primary))" strokeWidth={2} dot={false} name="Scenario" />
                <Line type="monotone" dataKey="cost_eur" stroke="hsl(var(--muted-foreground))" strokeWidth={2} dot={false} name="Baseline" data={forecast.baseline.long_term_forecast} />
              </RechartsLineChart>
            </ResponsiveContainer>
          </div>
          {selectedScenario.payback_month && (
            <div className="mt-2 text-center text-xs text-muted-foreground">
              Payoff: Year {Math.ceil(selectedScenario.payback_month / 12)}
            </div>
          )}
        </div>

        {selectedScenario.monthly_saving_eur < 0 && (
          <div className="rounded-2xl border border-border bg-card p-4">
            <div className="text-xs uppercase tracking-wider text-muted-foreground">
              Post-payoff savings
            </div>
            <div className="mt-2 text-lg font-semibold text-primary">
              {euro(selectedScenario.monthly_saving_post_payoff_eur)}/month
            </div>
            <p className="mt-1 text-xs text-muted-foreground">
              After loan is paid off
            </p>
          </div>
        )}

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

function CostRow({ icon, label, value, bold = false }: { icon: React.ReactNode; label: string; value: string; bold?: boolean }) {
  return (
    <div className={`flex items-center justify-between ${bold ? "font-semibold" : ""}`}>
      <div className="flex items-center gap-2 text-sm text-muted-foreground">
        {icon}
        <span>{label}</span>
      </div>
      <span className="tabular-nums">{value}</span>
    </div>
  );
}