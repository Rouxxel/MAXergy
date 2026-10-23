import React, { useEffect, useRef, useState } from "react";
import { ScrollView, View, Text, Image, Pressable, Animated, Dimensions } from "react-native";
import { LineChart as RNLineChart } from "react-native-chart-kit";
import { Link, useRouter } from "expo-router";
import { useQuery } from "@tanstack/react-query";
import { ArrowRight } from "lucide-react-native";

import { Header } from "@/components/header";
import { Button } from "@/components/ui/Button";
import { getBenchmark } from "@/services/endpoints";
import { FeatureCard, StepCard, SummaryCard, FAQItem } from "@/components/landing";
import { trackPageView, trackCTAClick, trackBenchmarkLoad } from "@/services/analytics";
import useScrollAnimation from "@/lib/useScrollAnimation";
import benchmarkFallback from "@/services/fixtures/benchmark.json";
import { euro, signedEuro } from "@/services/savings";
import { validateBenchmarkData } from "@/services/validation";

export default function LandingPage() {
  const router = useRouter();
  const scrollViewRef = useRef<ScrollView>(null);
  const [scrollY, setScrollY] = useState(new Animated.Value(0));

  // Track page view on mount
  useEffect(() => {
    trackPageView("/landing");
  }, []);

  // Fetch benchmark data
  const { data: benchmarkData, isLoading: benchmarkLoading, error: benchmarkError } = useQuery({
    queryKey: ["benchmark"],
    queryFn: getBenchmark,
    staleTime: 60 * 60 * 1000, // 1 hour
  });

  // Track benchmark load status
  useEffect(() => {
    if (benchmarkLoading) return;
    if (benchmarkError) {
      trackBenchmarkLoad("error");
    } else if (benchmarkData) {
      trackBenchmarkLoad("success");
    }
  }, [benchmarkLoading, benchmarkError, benchmarkData]);

  // If the API is unavailable, show the last recorded engine run (same shape, with its
  // forecast start month) instead of hand-written numbers.
  const fallbackData = validateBenchmarkData(benchmarkFallback);
  const data = benchmarkData || fallbackData;

  const handleStartAssessment = () => {
    trackCTAClick("primary", "hero");
    router.push("/assessment");
  };

  const heroAnim = useScrollAnimation();
  const whatIsMaxergyAnim = useScrollAnimation();
  const howItWorksAnim = useScrollAnimation();
  const exampleOutputAnim = useScrollAnimation();
  const featuresAnim = useScrollAnimation();
  const faqAnim = useScrollAnimation();

  // Track scroll position and trigger animations when in view
  const onScroll = Animated.event(
    [{ nativeEvent: { contentOffset: { y: scrollY } } }],
    { useNativeDriver: false }
  );

  // For simplicity, we'll trigger animations manually on component mount for each section
  useEffect(() => {
    // Trigger hero animation immediately
    setTimeout(heroAnim.triggerAnimation, 100);
    // Trigger other sections with delay
    setTimeout(whatIsMaxergyAnim.triggerAnimation, 300);
    setTimeout(howItWorksAnim.triggerAnimation, 500);
    setTimeout(exampleOutputAnim.triggerAnimation, 700);
    setTimeout(featuresAnim.triggerAnimation, 900);
    setTimeout(faqAnim.triggerAnimation, 1100);
  }, []);

  return (
    <Animated.ScrollView
      ref={scrollViewRef}
      className="flex-1 bg-background"
      onScroll={onScroll}
      scrollEventThrottle={16}
    >
      <Header />

      <View className="px-5 py-12 space-y-12">
        {/* Hero Section */}
        <Animated.View className="space-y-6" style={heroAnim.animatedStyle}>
          <Text className="text-4xl font-extrabold tracking-tight text-foreground text-center leading-tight">
            Plan your energy upgrade with confidence
          </Text>
          <Text className="text-base text-muted-foreground text-center leading-relaxed">
            AI-powered analysis for German households. See how solar, batteries, heat pumps, and EV charging could save you money over 20 years.
          </Text>
          
          <View className="space-y-3 pt-4">
            <Button
              size="lg"
              className="bg-primary text-primary-foreground flex-row justify-center items-center"
              onPress={handleStartAssessment}
            >
              <Text className="text-primary-foreground font-semibold text-base mr-2">Start Your Assessment</Text>
              <ArrowRight size={18} className="text-primary-foreground" />
            </Button>
            <Button
              size="lg"
              variant="outline"
              onPress={() => trackCTAClick("secondary", "hero")}
            >
              Learn More
            </Button>
          </View>

          <View className="items-center justify-center pt-8">
            <View className="aspect-square w-full max-w-sm rounded-2xl bg-muted/20 flex items-center justify-center p-8 border border-border">
              <View className="text-center items-center space-y-4">
                <View className="h-24 w-24 rounded-full bg-primary/20 items-center justify-center">
                  <ArrowRight size={40} className="text-primary transform -rotate-45" />
                </View>
                <Text className="text-sm text-muted-foreground text-center">
                  Solar, Battery & Heating upgrades calculated instantly.
                </Text>
              </View>
            </View>
          </View>
        </Animated.View>

        {/* What is MAXergy Section */}
        <Animated.View className="border-t border-border pt-12 space-y-6" style={whatIsMaxergyAnim.animatedStyle}>
          <View className="space-y-3">
            <Text className="text-2xl font-bold tracking-tight text-foreground text-center">What is MAXergy?</Text>
            <Text className="text-sm text-muted-foreground text-center leading-relaxed">
              MAXergy is an AI-powered home energy upgrade planner designed specifically for German households. We help you understand the financial impact of energy efficiency upgrades like solar PV, battery storage, heat pumps, and EV charging.
            </Text>
          </View>

          <View className="grid gap-3 flex-row flex-wrap justify-between">
            <View className="w-[48%] rounded-lg border border-border bg-card p-4 items-center space-y-2 mb-3">
              <Text className="text-2xl font-bold text-primary">6</Text>
              <Text className="text-xs text-muted-foreground text-center">Upgrade scenarios analyzed</Text>
            </View>
            <View className="w-[48%] rounded-lg border border-border bg-card p-4 items-center space-y-2 mb-3">
              <Text className="text-2xl font-bold text-primary">20 years</Text>
              <Text className="text-xs text-muted-foreground text-center">Long-term projections</Text>
            </View>
            <View className="w-[48%] rounded-lg border border-border bg-card p-4 items-center space-y-2">
              <Text className="text-2xl font-bold text-primary">✓</Text>
              <Text className="text-xs text-muted-foreground text-center">German market specific</Text>
            </View>
            <View className="w-[48%] rounded-lg border border-border bg-card p-4 items-center space-y-2">
              <Text className="text-2xl font-bold text-primary">AI</Text>
              <Text className="text-xs text-muted-foreground text-center">Personalized recommendations</Text>
            </View>
          </View>

          <View className="rounded-lg border border-border bg-muted/30 p-4">
            <Text className="text-xs text-muted-foreground leading-relaxed">
              <Text className="font-semibold text-foreground">German Market Context: </Text>
              Built for the German energy market with current tariffs (Arbeitspreis, Grundpreis), EEG feed-in tariffs, and subsidy considerations.
            </Text>
          </View>
        </Animated.View>

        {/* How It Works Section */}
        <Animated.View className="border-t border-border pt-12 space-y-6" style={howItWorksAnim.animatedStyle}>
          <Text className="text-2xl font-bold tracking-tight text-foreground text-center">How it works</Text>
          
          <View className="space-y-6">
            <StepCard
              step={1}
              title="Tell us about your home"
              description="Complete a 9-step assessment sharing your energy usage, building characteristics, and upgrade preferences."
            />
            <StepCard
              step={2}
              title="We analyze your energy use"
              description="Baseline forecast calculates your current energy costs using your actual tariffs and consumption patterns."
            />
            <StepCard
              step={3}
              title="See upgrade scenarios"
              description="Compare 6 different upgrade options with costs, savings, and ROI for each scenario."
            />
            <StepCard
              step={4}
              title="Get personalized recommendations"
              description="AI selects the optimal scenario based on your situation with break-even timing and long-term projections."
            />
            <StepCard
              step={5}
              title="Chat with AI advisor"
              description="Ask questions about your results, get explanations of savings calculations, and explore what-if scenarios."
            />
          </View>
        </Animated.View>

        {/* Example Output Section */}
        <Animated.View className="border-t border-border pt-12 space-y-6" style={exampleOutputAnim.animatedStyle}>
          <View className="space-y-3 items-center">
            <View className="bg-primary/10 rounded-full px-3 py-1">
              <Text className="text-xs font-semibold text-primary">Typical German household benchmark</Text>
            </View>
            <Text className="text-2xl font-bold tracking-tight text-foreground text-center leading-tight">
              Save around {euro(data.recommendation.cumulative_savings_eur)} over {data.projection_years} years
            </Text>
            <Text className="text-sm font-semibold text-foreground text-center">
              {data.recommendation.monthly_saving_eur >= 0
                ? `Saves ${euro(data.recommendation.monthly_saving_eur)}/month from the start (loan included)`
                : `During financing: ${signedEuro(data.recommendation.monthly_saving_eur)}/month`}
              {" · "}After payoff: {signedEuro(data.recommendation.monthly_saving_post_payoff_eur)}/month
            </Text>
            <Text className="text-xs text-muted-foreground text-center leading-relaxed">
              This estimate is based on a representative {data.household.occupants}-person household in {data.household.location.split(',')[0]} with {data.household.heating_type} heating, a {data.household.vehicle_type} car, and a {data.household.roof_orientation}-facing roof.
            </Text>
          </View>

          {/* Household Summary Cards */}
          <View className="space-y-2">
            <SummaryCard label="Location" value={data.household.location} />
            <SummaryCard label="Household size" value={`${data.household.occupants} people`} />
            <SummaryCard label="Annual electricity" value={`${data.household.annual_electricity_kwh.toLocaleString('de-DE')} kWh`} />
            <SummaryCard label="Heating type" value={`${data.household.heating_type.charAt(0).toUpperCase() + data.household.heating_type.slice(1)} (${data.household.heating_annual_kwh.toLocaleString('de-DE')} kWh)`} />
            <SummaryCard label="Vehicle type" value={data.household.vehicle_type.charAt(0).toUpperCase() + data.household.vehicle_type.slice(1)} />
            <SummaryCard label="Annual mileage" value={`${data.household.annual_mileage_km.toLocaleString('de-DE')} km`} />
            <SummaryCard label="Roof area" value={`${data.household.roof_area_m2} m²`} />
            <SummaryCard label="Roof orientation" value={`${data.household.roof_orientation.charAt(0).toUpperCase() + data.household.roof_orientation.slice(1)}, ${data.household.roof_tilt_deg}° tilt`} />
          </View>

          {/* Recommended Plan Card */}
          <View className="rounded-lg border border-border bg-card p-5 space-y-4">
            <View className="flex-row items-center justify-between">
              <Text className="text-base font-bold text-foreground">
                Recommended Plan: {data.recommendation.scenario.split('_').map(w => w.charAt(0).toUpperCase() + w.slice(1)).join(' ')}
              </Text>
              <View className="bg-emerald-500/10 rounded-full px-2 py-0.5">
                <Text className="text-[10px] font-semibold text-emerald-500">Best option</Text>
              </View>
            </View>
            <Text className="text-xs text-muted-foreground leading-relaxed">
              {data.recommendation.description}
            </Text>
            <Text className="text-xs text-muted-foreground leading-relaxed">
              {data.recommendation.rationale}
            </Text>
            
            <View className="border-t border-border pt-4 grid gap-2 flex-row flex-wrap justify-between">
              <View className="w-[30%] space-y-1">
                <Text className="text-[10px] text-muted-foreground">Break-even</Text>
                <Text className="text-sm font-extrabold text-foreground">
                  {data.recommendation.break_even_year ? `Year ${data.recommendation.break_even_year}` : "Not reached"}
                </Text>
              </View>
              <View className="w-[30%] space-y-1">
                <Text className="text-[10px] text-muted-foreground">Monthly pay</Text>
                <Text className="text-sm font-extrabold text-foreground">{euro(data.recommendation.monthly_instalment_eur)}</Text>
              </View>
              <View className="w-[30%] space-y-1">
                <Text className="text-[10px] text-muted-foreground">{data.projection_years}-yr net</Text>
                <Text className="text-sm font-extrabold text-primary">{signedEuro(data.recommendation.cumulative_savings_eur)}</Text>
              </View>
            </View>
          </View>

          {/* Cumulative Savings Chart */}
          <View className="rounded-lg border border-border bg-card p-5 space-y-3">
            <Text className="text-sm font-semibold text-foreground">
              Cumulative Net Savings Over {data.projection_years} Years
            </Text>
            <RNLineChart
              data={{
                labels: data.cumulative_series.map((p, i) => (i % 5 === 0 ? String(p.year) : "")),
                datasets: [
                  { data: data.cumulative_series.map((p) => p.central ?? 0), color: () => "#B8FF5A", strokeWidth: 2 },
                  { data: data.cumulative_series.map((p) => p.low ?? 0), color: () => "rgba(148,163,184,0.6)", strokeWidth: 1 },
                  { data: data.cumulative_series.map((p) => p.high ?? 0), color: () => "rgba(148,163,184,0.6)", strokeWidth: 1 },
                ],
                legend: ["Central prices", "Low", "High"],
              }}
              width={Dimensions.get("window").width - 72}
              height={200}
              yLabelsOffset={4}
              formatYLabel={(v) => `€${Math.round(Number(v) / 1000)}k`}
              withDots={false}
              chartConfig={{
                backgroundColor: "#111827",
                backgroundGradientFrom: "#111827",
                backgroundGradientTo: "#111827",
                decimalPlaces: 0,
                color: (opacity = 1) => `rgba(255, 255, 255, ${opacity})`,
                labelColor: (opacity = 1) => `rgba(148, 163, 184, ${opacity})`,
              }}
              style={{ borderRadius: 12 }}
            />
            <Text className="text-[10px] text-muted-foreground">
              Recommended plan vs. today, loan instalments included. MAXergy engine (model v{data.model_version}),
              forecast starting {data.forecast_start ?? "next month"}; low/high = energy-price scenarios.
            </Text>
          </View>

          {/* Household Comparison Charts (reference run of the three documented profiles) */}
          <Text className="text-[10px] text-muted-foreground">
            Reference run of three example households (forecast starting July 2026).
          </Text>
          <View className="space-y-4">
            <View className="rounded-lg border border-border bg-card p-4 space-y-2">
              <Text className="text-xs font-semibold text-center text-foreground">Average German Household</Text>
              <Image
                source={require("../assets/average_german_household_comparison.png")}
                className="w-full h-32 rounded-lg"
                resizeMode="contain"
              />
            </View>
            <View className="rounded-lg border border-border bg-card p-4 space-y-2">
              <Text className="text-xs font-semibold text-center text-foreground">High Benefit Household</Text>
              <Image
                source={require("../assets/high_benefit_household_comparison.png")}
                className="w-full h-32 rounded-lg"
                resizeMode="contain"
              />
            </View>
            <View className="rounded-lg border border-border bg-card p-4 space-y-2">
              <Text className="text-xs font-semibold text-center text-foreground">Low Benefit Household</Text>
              <Image
                source={require("../assets/low_benefit_household_comparison.png")}
                className="w-full h-32 rounded-lg"
                resizeMode="contain"
              />
            </View>
          </View>

          {/* Disclaimer */}
          <View className="rounded-lg border border-border bg-muted/20 p-4">
            <Text className="text-xs text-muted-foreground leading-relaxed">
              <Text className="font-semibold text-foreground">Note: </Text>
              These figures describe a typical German household benchmark. They are not yet personalised for your home. Your actual savings may differ based on your specific situation.
            </Text>
          </View>

          {/* CTA */}
          <View className="items-center space-y-3">
            <Button
              size="lg"
              className="bg-primary text-primary-foreground w-full flex-row justify-center items-center"
              onPress={handleStartAssessment}
            >
              <Text className="text-primary-foreground font-semibold text-base mr-2">Get Your Personal Estimate</Text>
              <ArrowRight size={18} className="text-primary-foreground" />
            </Button>
            <Text className="text-xs text-muted-foreground text-center">
              Personalise the estimate using your roof, heating, driving and energy use.
            </Text>
          </View>
        </Animated.View>

        {/* Features Section */}
        <Animated.View className="border-t border-border pt-12 space-y-6" style={featuresAnim.animatedStyle}>
          <Text className="text-2xl font-bold tracking-tight text-foreground text-center">Why MAXergy?</Text>
          
          <View className="space-y-4">
            <FeatureCard
              icon="Zap"
              title="German Market Specific"
              description="Built for German tariffs, subsidies, and regulations including EEG feed-in tariffs."
            />
            <FeatureCard
              icon="TrendingUp"
              title="Data-Driven"
              description="All calculations based on your actual input, not generic assumptions."
            />
            <FeatureCard
              icon="Shield"
              title="Transparent"
              description="Clear methodology, visible assumptions, no hidden fees."
            />
            <FeatureCard
              icon="LayoutGrid"
              title="Comprehensive"
              description="Analyzes 6 scenarios across electricity, heating, and mobility."
            />
            <FeatureCard
              icon="Brain"
              title="AI-Powered"
              description="Intelligent recommendations and personalized advice."
            />
            <FeatureCard
              icon="Calendar"
              title="Future-Proof"
              description="20-year projections help you make long-term decisions."
            />
          </View>
        </Animated.View>

        {/* FAQ Section */}
        <Animated.View className="border-t border-border pt-12 space-y-6" style={faqAnim.animatedStyle}>
          <Text className="text-2xl font-bold tracking-tight text-foreground text-center">Frequently Asked Questions</Text>
          
          <View className="space-y-3">
            <FAQItem
              question="How accurate are the savings estimates?"
              answer="Our estimates are based on your actual energy consumption, current tariffs, and German market conditions. The 20-year projections use different price scenarios (low, central, high) to show sensitivity to energy price trends. Short-term estimates (12 months) use constant prices validated against historical data."
            />
            <FAQItem
              question="What data do I need to provide?"
              answer="You'll need information about your household (occupants, location), energy usage (electricity bills, heating fuel), building characteristics (roof area, orientation), and mobility (vehicle type, annual mileage). The assessment takes about 5-10 minutes to complete."
            />
            <FAQItem
              question="How long does the assessment take?"
              answer="The 9-step assessment typically takes 5-10 minutes. Once submitted, your personalized results are generated immediately."
            />
            <FAQItem
              question="Is my data secure?"
              answer="Yes. Your data is processed securely and is not shared with third parties. We use industry-standard security practices to protect your information."
            />
            <FAQItem
              question="What if I don't have a roof suitable for solar?"
              answer="MAXergy analyzes all scenarios, including those that don't require solar panels (e.g., heat pump only, EV charging only). The recommendation engine will suggest the best option for your specific situation."
            />
          </View>
        </Animated.View>

        {/* Footer */}
        <View className="border-t border-border pt-12 pb-8 space-y-6">
          <View className="space-y-2">
            <Text className="text-base font-bold text-foreground">MAXergy</Text>
            <Text className="text-xs text-muted-foreground">
              Plan your energy upgrade with confidence
            </Text>
          </View>
          
          <View className="space-y-4">
            <View>
              <Text className="font-semibold text-foreground text-sm mb-1">Product</Text>
              <Link href="/landing" asChild>
                <Pressable><Text className="text-xs text-muted-foreground">Home</Text></Pressable>
              </Link>
              <Link href="/assessment" asChild className="mt-1">
                <Pressable><Text className="text-xs text-muted-foreground">Assessment</Text></Pressable>
              </Link>
            </View>
            <View>
              <Text className="font-semibold text-foreground text-sm mb-1">Legal</Text>
              <Text className="text-xs text-muted-foreground">Privacy Policy</Text>
              <Text className="text-xs text-muted-foreground mt-1">Terms of Service</Text>
              <Text className="text-xs text-muted-foreground mt-1">Impressum</Text>
            </View>
            <View>
              <Text className="font-semibold text-foreground text-sm mb-1">Contact</Text>
              <Text className="text-xs text-muted-foreground">contact@maxergy.de</Text>
            </View>
          </View>
          
          <Text className="text-[10px] text-muted-foreground text-center pt-4 border-t border-border/50">
            © 2026 MAXergy. All rights reserved.
          </Text>
        </View>
      </View>
    </Animated.ScrollView>
  );
}
