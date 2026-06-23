import React, { useMemo, useState } from "react";
import { ScrollView, View, Text, Pressable } from "react-native";
import { useRouter } from "expo-router";
import { ArrowLeft, Check, ArrowDownUp } from "lucide-react-native";

import { Header } from "@/components/header";
import { BackButton } from "@/components/back-button";
import { Button } from "@/components/ui/Button";
import { useResultsStore } from "@/stores/resultsStore";
import type { Scenario } from "@/types";

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

export default function Compare() {
  const router = useRouter();
  const { forecast, selectedScenarioId, selectScenario } = useResultsStore();
  const [sortDesc, setSortDesc] = useState(true);
  const [openId, setOpenId] = useState<string | undefined>(selectedScenarioId);

  const sorted = useMemo(() => {
    if (!forecast) return [] as Scenario[];
    return [...forecast.scenarios].sort((a, b) =>
      sortDesc
        ? b.monthly_saving_eur - a.monthly_saving_eur
        : a.monthly_saving_eur - b.monthly_saving_eur
    );
  }, [forecast, sortDesc]);

  const recommendedId = useMemo(() => {
    if (!forecast) return undefined;
    const top = [...forecast.scenarios].sort((a, b) => b.monthly_saving_eur - a.monthly_saving_eur)[0];
    return top?.id;
  }, [forecast]);

  if (!forecast) {
    return (
      <View className="flex-1 bg-background">
        <Header />
        <View className="flex-1 items-center justify-center p-6 text-center space-y-4">
          <Text className="text-lg font-semibold text-foreground">Nothing to compare yet</Text>
          <Text className="text-sm text-muted-foreground text-center">
            Finish the onboarding to generate scenarios you can compare.
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

  return (
    <View className="flex-1 bg-background">
      <Header />
      <ScrollView className="flex-1 px-5 pt-4">
        {/* Navigation / Control Row */}
        <View className="flex-row items-center justify-between pb-4 border-b border-border mb-4">
          <BackButton label="Results" />
          
          <Pressable
            onPress={() => setSortDesc((v) => !v)}
            className="flex-row items-center space-x-1.5 rounded-full border border-border bg-card px-3 py-1.5 active:opacity-75"
          >
            <ArrowDownUp size={12} className="text-muted-foreground" />
            <Text className="text-xs text-muted-foreground ml-1">
              {sortDesc ? "Highest savings" : "Lowest savings"}
            </Text>
          </Pressable>
        </View>

        <Text className="text-2xl font-bold tracking-tight text-foreground">Compare scenarios</Text>
        <Text className="mt-1 text-sm text-muted-foreground leading-relaxed">
          Tap any bundle to see details and select it.
        </Text>

        <View className="mt-5 space-y-3 pb-12">
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
              <View
                key={s.id}
                className={
                  "overflow-hidden rounded-2xl border bg-card mb-3 " +
                  (selected ? "border-primary" : isNegativeSavings ? "border-orange-500/30" : "border-border")
                }
              >
                <Pressable
                  onPress={() => setOpenId(open ? undefined : s.id)}
                  className="flex-row items-center justify-between p-4"
                >
                  <View className="flex-1 pr-4">
                    <View className="flex-row items-center flex-wrap gap-1.5">
                      <Text className="font-semibold text-foreground text-sm">
                        {scenarioNames[s.id] || s.id}
                      </Text>
                      {recommended && (
                        <View className="rounded-full bg-primary/20 px-2 py-0.5">
                          <Text className="text-[8px] font-bold uppercase tracking-wider text-primary">
                            Recommended
                          </Text>
                        </View>
                      )}
                      {selected && (
                        <View className="rounded-full bg-secondary/20 px-2 py-0.5">
                          <Text className="text-[8px] font-bold uppercase tracking-wider text-secondary">
                            Selected
                          </Text>
                        </View>
                      )}
                    </View>
                    <Text className="mt-1 text-xs text-muted-foreground leading-relaxed">
                      {components.join(" · ")}
                    </Text>
                  </View>
                  <View className="items-end shrink-0">
                    <Text className={`text-lg font-bold ${isNegativeSavings ? "text-orange-500" : "text-primary"}`}>
                      {euro(s.monthly_saving_eur)}
                    </Text>
                    <Text className="text-[9px] uppercase tracking-wider text-muted-foreground">
                      /month
                    </Text>
                  </View>
                </Pressable>

                {open && (
                  <View className="border-t border-border p-4 bg-muted/5 space-y-4">
                    <View className="space-y-2">
                      <Text className="text-xs uppercase tracking-wider text-muted-foreground font-semibold">
                        Component sizing
                      </Text>
                      <View className="flex-row flex-wrap gap-2">
                        {s.sizing.solar_pv_kwp && (
                          <View className="rounded-lg bg-background/50 border border-border/50 px-3 py-1.5 justify-center">
                            <Text className="text-[10px] text-muted-foreground">Solar: {s.sizing.solar_pv_kwp} kWp</Text>
                          </View>
                        )}
                        {s.sizing.battery_kwh && (
                          <View className="rounded-lg bg-background/50 border border-border/50 px-3 py-1.5 justify-center">
                            <Text className="text-[10px] text-muted-foreground">Battery: {s.sizing.battery_kwh} kWh</Text>
                          </View>
                        )}
                        {s.sizing.heat_pump_kw && (
                          <View className="rounded-lg bg-background/50 border border-border/50 px-3 py-1.5 justify-center">
                            <Text className="text-[10px] text-muted-foreground">Heat Pump: {s.sizing.heat_pump_kw} kW</Text>
                          </View>
                        )}
                      </View>
                    </View>
                    
                    <View className="flex-row justify-between space-x-2">
                      <View className="flex-1">
                        <Stat label="Monthly pay" value={euro(s.financing_installment_eur)} />
                      </View>
                      <View className="flex-1 mx-1">
                        <Stat label="Self-use" value={`${(s.self_consumption_ratio * 100).toFixed(0)}%`} />
                      </View>
                      <View className="flex-1">
                        <Stat label="Payback" value={s.payback_month ? `${(s.payback_month / 12).toFixed(1)} yr` : "N/A"} />
                      </View>
                    </View>

                    <Button
                      onPress={() => selectScenario(s.id)}
                      className="h-11 w-full bg-primary flex-row justify-center items-center"
                    >
                      {selected ? (
                        <>
                          <Check size={16} className="text-primary-foreground mr-1.5" />
                          <Text className="text-primary-foreground font-semibold ml-1">Selected</Text>
                        </>
                      ) : (
                        <Text className="text-primary-foreground font-semibold">Select this bundle</Text>
                      )}
                    </Button>
                  </View>
                )}
              </View>
            );
          })}
        </View>
      </ScrollView>
    </View>
  );
}

function Stat({ label, value }: { label: string; value: string }) {
  return (
    <View className="rounded-xl border border-border bg-background/40 p-2 items-center">
      <Text className="text-[9px] uppercase tracking-wider text-muted-foreground text-center">
        {label}
      </Text>
      <Text className="mt-0.5 text-xs font-bold text-foreground text-center">{value}</Text>
    </View>
  );
}
