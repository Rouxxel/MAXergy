import React from "react";
import { ScrollView, View, Text, Pressable, Dimensions } from "react-native";
import { useRouter } from "expo-router";
import { MessageSquare, LineChart as LineChartIcon, Leaf, Clock, TrendingUp, Zap, Flame, Car, DollarSign } from "lucide-react-native";
import { LineChart as RNLineChart } from "react-native-chart-kit";

import { Header } from "@/components/header";
import { MetricCard } from "@/components/metric-card";
import { Button } from "@/components/ui/Button";
import { useResultsStore } from "@/stores/resultsStore";
import { useAssessmentStore } from "@/stores/assessmentStore";

const euro = (n: number | undefined | null) =>
  n !== undefined && n !== null
    ? `€${n.toLocaleString(undefined, { maximumFractionDigits: 0 })}`
    : "€0";

const scenarioNames: Record<string, string> = {
  solar_only: "Solar Only",
  pv_battery: "Solar + Battery",
  pv_heatpump: "Solar + Heat Pump",
  pv_ev: "Solar + EV Charger",
  pv_battery_heatpump: "Solar + Battery + Heat Pump",
  full_upgrade: "Full Upgrade (All Components)",
};

export default function Results() {
  const router = useRouter();
  const { forecast, recommendation } = useResultsStore();
  const reset = useAssessmentStore((state) => state.reset);

  const handleCreateNewScenario = () => {
    reset();
    router.replace("/assessment");
  };

  if (!forecast || !recommendation) {
    return (
      <View className="flex-1 bg-background">
        <Header />
        <View className="flex-1 items-center justify-center p-6 text-center space-y-4">
          <Text className="text-lg font-semibold text-foreground">No results yet</Text>
          <Text className="text-sm text-muted-foreground text-center">
            Complete the quick onboarding to see your monthly savings forecast.
          </Text>
          <Button
            onPress={() => router.replace("/assessment")}
            className="bg-primary text-primary-foreground mt-4"
          >
            Start onboarding
          </Button>
        </View>
      </View>
    );
  }

  const baselineTotal = forecast.baseline.monthly_cost_eur.total;
  const selectedScenario = recommendation.selected_scenario;
  const scenarioTotal = selectedScenario.monthly_cost_eur.total;
  const monthlySavings = baselineTotal - scenarioTotal;
  const futurePct = Math.max(8, Math.round((scenarioTotal / baselineTotal) * 100));

  return (
    <View className="flex-1 bg-background">
      <Header />
      <ScrollView className="flex-1 px-5 pt-4">
        {/* Top Control Header */}
        <View className="flex-row items-center justify-between pb-4 border-b border-border mb-4">
          <Button
            onPress={handleCreateNewScenario}
            variant="outline"
            size="sm"
            className="h-8 px-3"
            textClassName="text-xs"
          >
            New Scenario
          </Button>
          
          <Pressable
            onPress={() => router.push("/advisor")}
            className="flex-row items-center space-x-1.5 rounded-full border border-border bg-card px-3 py-1.5 active:opacity-75"
          >
            <MessageSquare size={14} className="text-muted-foreground" />
            <Text className="text-xs font-semibold text-muted-foreground ml-1">Advisor</Text>
          </Pressable>
        </View>

        {/* You could save card */}
        <View className="rounded-3xl border border-primary/30 bg-gradient-to-b from-primary/10 to-transparent p-6 items-center mb-6">
          <Text className="text-xs uppercase tracking-widest text-primary font-bold">
            You could save
          </Text>
          <Text className="mt-2 text-5xl font-extrabold tracking-tight text-primary">
            {euro(monthlySavings)}
          </Text>
          <Text className="mt-1 text-sm text-muted-foreground">every month</Text>
        </View>

        {/* Now vs After Bars */}
        <View className="space-y-4">
          <View className="rounded-2xl border border-border bg-card p-4">
            <Text className="text-xs uppercase tracking-wider text-muted-foreground font-semibold mb-3">
              Today vs after upgrade
            </Text>
            <View className="space-y-4">
              <Bar label="Now" amount={baselineTotal} pct={100} tone="muted" />
              <View className="mt-3">
                <Bar
                  label="After"
                  amount={scenarioTotal}
                  pct={futurePct}
                  tone="primary"
                />
              </View>
            </View>
          </View>

          {/* Baseline monthly costs */}
          <View className="rounded-2xl border border-border bg-card p-4">
            <Text className="text-xs uppercase tracking-wider text-muted-foreground font-semibold mb-3">
              Baseline monthly costs
            </Text>
            <View className="space-y-2.5">
              <CostRow icon={<Zap size={15} className="text-muted-foreground" />} label="Electricity" value={euro(forecast.baseline.monthly_cost_eur.electricity)} />
              <CostRow icon={<Flame size={15} className="text-muted-foreground" />} label="Heating" value={euro(forecast.baseline.monthly_cost_eur.heating)} />
              <CostRow icon={<Car size={15} className="text-muted-foreground" />} label="Mobility" value={euro(forecast.baseline.monthly_cost_eur.mobility)} />
              <View className="mt-2 border-t border-border pt-2">
                <CostRow icon={<DollarSign size={15} className="text-foreground" />} label="Total" value={euro(forecast.baseline.monthly_cost_eur.total)} bold />
              </View>
            </View>
          </View>

          {/* Scenario monthly costs */}
          <View className="rounded-2xl border border-border bg-card p-4">
            <Text className="text-xs uppercase tracking-wider text-muted-foreground font-semibold mb-3">
              Scenario monthly costs
            </Text>
            <View className="space-y-2.5">
              <CostRow icon={<Zap size={15} className="text-muted-foreground" />} label="Electricity" value={euro(selectedScenario.monthly_cost_eur.electricity)} />
              <CostRow icon={<Flame size={15} className="text-muted-foreground" />} label="Heating" value={euro(selectedScenario.monthly_cost_eur.heating)} />
              <CostRow icon={<Car size={15} className="text-muted-foreground" />} label="Mobility" value={euro(selectedScenario.monthly_cost_eur.mobility)} />
              <CostRow icon={<DollarSign size={15} className="text-muted-foreground" />} label="Financing" value={euro(selectedScenario.financing_installment_eur)} />
              <View className="mt-2 border-t border-border pt-2">
                <CostRow icon={<DollarSign size={15} className="text-foreground" />} label="Total" value={euro(selectedScenario.monthly_cost_eur.total)} bold />
              </View>
            </View>
          </View>

          {/* Metric cards grid */}
          <View className="flex-row flex-wrap justify-between">
            <View className="w-[48%] mb-3">
              <MetricCard
                label="Monthly payment"
                value={euro(selectedScenario.financing_installment_eur)}
                hint="Financing"
              />
            </View>
            <View className="w-[48%] mb-3">
              <MetricCard
                label="Self-consumption"
                value={`${(selectedScenario.self_consumption_ratio * 100).toFixed(0)}%`}
                hint="Solar used directly"
              />
            </View>
            <View className="w-[48%]">
              <MetricCard
                label="Payback"
                value={selectedScenario.payback_month ? `${(selectedScenario.payback_month / 12).toFixed(1)} yrs` : "N/A"}
                hint="Break-even"
              />
            </View>
            <View className="w-[48%]">
              <MetricCard
                label="Monthly saving"
                value={euro(selectedScenario.monthly_saving_eur)}
                accent="primary"
                hint="Savings"
              />
            </View>
          </View>

          {/* Recommended bundle details */}
          <View className="rounded-2xl border border-border bg-card p-4">
            <View className="flex-row items-center space-x-1.5 mb-2">
              <TrendingUp size={15} className="text-muted-foreground" />
              <Text className="text-xs uppercase tracking-wider text-muted-foreground font-semibold ml-1">
                Recommended bundle
              </Text>
            </View>
            <Text className="text-lg font-bold text-foreground">
              {scenarioNames[selectedScenario.id] || selectedScenario.id}
            </Text>
            <View className="mt-3 flex-row flex-wrap gap-1.5">
              {selectedScenario.components.solar_pv && (
                <View className="rounded-full bg-primary/10 px-2.5 py-0.5">
                  <Text className="text-[10px] font-semibold text-primary">
                    Solar PV ({selectedScenario.sizing.solar_pv_kwp} kWp)
                  </Text>
                </View>
              )}
              {selectedScenario.components.battery && (
                <View className="rounded-full bg-primary/10 px-2.5 py-0.5">
                  <Text className="text-[10px] font-semibold text-primary">
                    Battery ({selectedScenario.sizing.battery_kwh} kWh)
                  </Text>
                </View>
              )}
              {selectedScenario.components.heat_pump && (
                <View className="rounded-full bg-primary/10 px-2.5 py-0.5">
                  <Text className="text-[10px] font-semibold text-primary">
                    Heat Pump ({selectedScenario.sizing.heat_pump_kw} kW)
                  </Text>
                </View>
              )}
              {selectedScenario.components.ev_charger && (
                <View className="rounded-full bg-primary/10 px-2.5 py-0.5">
                  <Text className="text-[10px] font-semibold text-primary">
                    EV Charger
                  </Text>
                </View>
              )}
            </View>
            <Text className="mt-3 text-sm text-muted-foreground leading-relaxed">
              {recommendation.reasoning}
            </Text>
          </View>

          {/* Short term forecast chart */}
          <View className="rounded-2xl border border-border bg-card p-4">
            <Text className="text-xs font-semibold uppercase tracking-wider text-muted-foreground mb-3">
              Short-term forecast (12 months)
            </Text>
            <RNLineChart
              data={{
                labels: selectedScenario.short_term_forecast.map((pt) => pt.month.slice(-3)),
                datasets: [
                  {
                    data: selectedScenario.short_term_forecast.map((pt) => pt.total_eur),
                    color: () => '#ffffff',
                    strokeWidth: 2,
                  },
                  {
                    data: forecast.baseline.short_term_forecast.map((pt) => pt.total_eur),
                    color: () => '#94a3b8',
                    strokeWidth: 2,
                  }
                ],
                legend: ['Scenario', 'Baseline']
              }}
              width={Dimensions.get('window').width - 72}
              height={200}
              chartConfig={{
                backgroundColor: '#111827',
                backgroundGradientFrom: '#111827',
                backgroundGradientTo: '#111827',
                decimalPlaces: 0,
                color: (opacity = 1) => `rgba(255, 255, 255, ${opacity})`,
                labelColor: (opacity = 1) => `rgba(148, 163, 184, ${opacity})`,
                style: {
                  borderRadius: 16
                },
                propsForDots: {
                  r: '2',
                  strokeWidth: '1',
                  stroke: '#ffffff'
                }
              }}
              bezier
              style={{
                marginVertical: 8,
                borderRadius: 16
              }}
            />
          </View>

          {/* Long term forecast chart */}
          <View className="rounded-2xl border border-border bg-card p-4">
            <Text className="text-xs font-semibold uppercase tracking-wider text-muted-foreground mb-3">
              Long-term forecast (20 years)
            </Text>
            <RNLineChart
              data={{
                labels: selectedScenario.long_term_forecast.map((pt) => String(pt.year)),
                datasets: [
                  {
                    data: selectedScenario.long_term_forecast.map((pt) => pt.annual_total_eur),
                    color: () => '#ffffff',
                    strokeWidth: 2,
                  },
                  {
                    data: forecast.baseline.long_term_forecast.map((pt) => pt.annual_total_eur),
                    color: () => '#94a3b8',
                    strokeWidth: 2,
                  }
                ],
                legend: ['Scenario', 'Baseline']
              }}
              width={Dimensions.get('window').width - 72}
              height={200}
              chartConfig={{
                backgroundColor: '#111827',
                backgroundGradientFrom: '#111827',
                backgroundGradientTo: '#111827',
                decimalPlaces: 0,
                color: (opacity = 1) => `rgba(255, 255, 255, ${opacity})`,
                labelColor: (opacity = 1) => `rgba(148, 163, 184, ${opacity})`,
                style: {
                  borderRadius: 16
                },
                propsForDots: {
                  r: '2',
                  strokeWidth: '1',
                  stroke: '#ffffff'
                }
              }}
              bezier
              style={{
                marginVertical: 8,
                borderRadius: 16
              }}
            />
          </View>

          {selectedScenario.payback_month && (
            <Text className="text-center text-xs text-muted-foreground mt-1">
              Payoff: Year {Math.ceil(selectedScenario.payback_month / 12)}
            </Text>
          )}

          {selectedScenario.monthly_saving_eur < 0 && (
            <View className="rounded-2xl border border-border bg-card p-4">
              <Text className="text-xs uppercase tracking-wider text-muted-foreground font-semibold">
                Post-payoff savings
              </Text>
              <Text className="mt-2 text-lg font-bold text-primary">
                {euro(selectedScenario.monthly_saving_post_payoff_eur)}/month
              </Text>
              <Text className="mt-1 text-xs text-muted-foreground">
                After loan is paid off
              </Text>
            </View>
          )}

          <View className="flex-row justify-between space-x-1 pt-2">
            <View className="flex-1 mr-1">
              <Detail icon={<LineChartIcon size={14} className="text-muted-foreground" />} label="Modeled" />
            </View>
            <View className="flex-1 mx-1">
              <Detail icon={<Clock size={14} className="text-muted-foreground" />} label="Tariffs" />
            </View>
            <View className="flex-1 ml-1">
              <Detail icon={<Leaf size={14} className="text-muted-foreground" />} label="ROI verified" />
            </View>
          </View>
        </View>

        {/* Navigation CTAs */}
        <View className="mt-8 space-y-3 pb-12">
          <Button
            onPress={() => router.push("/compare")}
            className="h-12 bg-primary text-primary-foreground font-semibold"
          >
            Compare scenarios
          </Button>
          <Button
            onPress={() => router.push("/advisor")}
            variant="outline"
            className="h-12"
          >
            Ask the AI advisor
          </Button>
        </View>
      </ScrollView>
    </View>
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
    <View>
      <View className="flex-row justify-between mb-1">
        <Text className="text-sm text-muted-foreground font-semibold">{label}</Text>
        <Text className="text-sm font-extrabold text-foreground">{euro(amount)}/mo</Text>
      </View>
      <View className="h-2.5 w-full bg-muted rounded-full overflow-hidden">
        <View
          className={
            "h-full rounded-full " +
            (tone === "primary" ? "bg-primary" : "bg-muted-foreground/40")
          }
          style={{ width: `${pct}%` }}
        />
      </View>
    </View>
  );
}

function Detail({ icon, label }: { icon: React.ReactNode; label: string }) {
  return (
    <View className="flex-row items-center justify-center space-x-1.5 rounded-lg border border-border bg-card/50 px-2 py-1.5">
      {icon}
      <Text className="text-[10px] text-muted-foreground ml-1">{label}</Text>
    </View>
  );
}

function CostRow({ icon, label, value, bold = false }: { icon: React.ReactNode; label: string; value: string; bold?: boolean }) {
  return (
    <View className="flex-row items-center justify-between">
      <View className="flex-row items-center space-x-2">
        {icon}
        <Text className={`text-sm ml-2 ${bold ? "text-foreground font-bold" : "text-muted-foreground font-medium"}`}>{label}</Text>
      </View>
      <Text className={`text-sm ${bold ? "text-foreground font-bold" : "text-foreground font-medium"}`}>{value}</Text>
    </View>
  );
}
