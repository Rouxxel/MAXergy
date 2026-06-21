import { createFileRoute, Link } from "@tanstack/react-router";
import { useState, useEffect, useRef } from "react";
import { useQuery } from "@tanstack/react-query";
import { ArrowRight, ChevronDown } from "lucide-react";

import { BrandMark } from "@/components/app-shell";
import { Button } from "@/components/ui/button";
import { getBenchmark } from "@/services/endpoints";
import { FeatureCard, StepCard, SummaryCard, FAQItem } from "@/components/landing";
import cumulativeNetSavings from "@/assets/cumulative_net_savings.png";
import averageGermanHousehold from "@/assets/average_german_household_comparison.png";
import highBenefitHousehold from "@/assets/high_benefit_household_comparison.png";
import lowBenefitHousehold from "@/assets/low_benefit_household_comparison.png";

export const Route = createFileRoute("/landing")({
  head: () => ({
    meta: [
      {
        title: "MAXergy - Plan Your Energy Upgrade with Confidence",
      },
      {
        name: "description",
        content:
          "AI-powered home energy upgrade planner for German households. See how solar, batteries, heat pumps, and EV charging could save you money over 20 years.",
      },
      {
        property: "og:title",
        content: "MAXergy - Plan Your Energy Upgrade with Confidence",
      },
      {
        property: "og:description",
        content:
          "AI-powered home energy upgrade planner for German households. See how solar, batteries, heat pumps, and EV charging could save you money over 20 years.",
      },
      {
        property: "og:type",
        content: "website",
      },
      {
        property: "og:locale",
        content: "de_DE",
      },
      {
        rel: "canonical",
        href: "https://maxergy.de/landing",
      },
    ],
  }),
  component: LandingPage,
});

function LandingPage() {
  const scrollToFeatures = () => {
    const element = document.getElementById("what-is-maxergy");
    if (element) {
      element.scrollIntoView({ behavior: "smooth" });
    }
  };

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

  // Scroll animation hook
  const useScrollAnimation = () => {
    const [isVisible, setIsVisible] = useState(false);
    const ref = useRef<HTMLDivElement>(null);

    useEffect(() => {
      const observer = new IntersectionObserver(
        ([entry]) => {
          if (entry.isIntersecting) {
            setIsVisible(true);
          }
        },
        { threshold: 0.1 }
      );

      if (ref.current) {
        observer.observe(ref.current);
      }

      return () => {
        if (ref.current) {
          observer.unobserve(ref.current);
        }
      };
    }, []);

    return { ref, isVisible };
  };

  const heroAnimation = useScrollAnimation();
  const whatIsMaxergyAnimation = useScrollAnimation();
  const howItWorksAnimation = useScrollAnimation();
  const exampleOutputAnimation = useScrollAnimation();
  const featuresAnimation = useScrollAnimation();
  const faqAnimation = useScrollAnimation();

  // Fallback data if API fails
  const fallbackData = {
    household: {
      location: "Cologne (50667)",
      occupants: 3,
      annual_electricity_kwh: 3500,
      heating_type: "gas",
      heating_annual_kwh: 14000,
      vehicle_type: "petrol",
      annual_mileage_km: 12000,
      roof_area_m2: 35,
      roof_orientation: "south",
      roof_tilt_deg: 32,
    },
    recommendation: {
      scenario: "full_upgrade",
      break_even_year: 8,
      monthly_instalment_eur: 209,
      cumulative_savings_eur: 24828,
      description:
        "Solar panels + battery storage + heat pump + EV charger. Highest projected 20-year cumulative net savings under the central price scenario.",
    },
  };

  const data = benchmarkData || fallbackData;

  return (
    <div className="min-h-screen bg-background">
      {/* Header */}
      <header className="sticky top-0 z-50 border-b border-border bg-background/95 backdrop-blur supports-[backdrop-filter]:bg-background/60">
        <div className="container mx-auto flex h-16 items-center justify-between px-4">
          <Link to="/landing">
            <BrandMark />
          </Link>
          <nav className="hidden md:flex items-center gap-6">
            <Link
              to="/landing"
              className="text-sm font-medium text-muted-foreground hover:text-foreground transition-colors"
            >
              Home
            </Link>
            <Link
              to="/assessment"
              className="text-sm font-medium text-muted-foreground hover:text-foreground transition-colors"
            >
              Assessment
            </Link>
          </nav>
          <Link to="/assessment">
            <Button
              size="sm"
              className="bg-primary text-primary-foreground hover:bg-primary/90"
              onClick={() => trackCTAClick("primary", "header")}
            >
              Start Assessment
            </Button>
          </Link>
        </div>
      </header>

      {/* Hero Section */}
      <section ref={heroAnimation.ref} className="container mx-auto px-4 py-20 md:py-32">
        <div className={`grid gap-12 lg:grid-cols-2 lg:gap-8 items-center transition-opacity duration-700 ${heroAnimation.isVisible ? 'opacity-100' : 'opacity-0'}`}>
          <div className="space-y-8">
            <h1 className="text-4xl font-bold tracking-tight sm:text-5xl md:text-6xl">
              Plan your energy upgrade with confidence
            </h1>
            <p className="text-lg text-muted-foreground md:text-xl">
              AI-powered analysis for German households. See how solar, batteries, heat pumps, and EV charging could
              save you money over 20 years.
            </p>
            <div className="flex flex-col sm:flex-row gap-4">
              <Link to="/assessment">
                <Button
                  size="lg"
                  className="w-full sm:w-auto bg-primary text-primary-foreground hover:bg-primary/90"
                  onClick={() => trackCTAClick("primary", "hero")}
                >
                  Start Your Assessment
                  <ArrowRight className="ml-2 h-4 w-4" />
                </Button>
              </Link>
              <Button
                size="lg"
                variant="outline"
                className="w-full sm:w-auto"
                onClick={() => {
                  trackCTAClick("secondary", "hero");
                  scrollToFeatures();
                }}
              >
                Learn More
              </Button>
            </div>
          </div>
          <div className="relative flex items-center justify-center">
            {/* Hero illustration placeholder - will be replaced with actual graphic */}
            <div className="aspect-square w-full max-w-md rounded-2xl bg-gradient-to-br from-primary/20 to-secondary/20 flex items-center justify-center">
              <div className="text-center space-y-4 p-8">
                <div className="mx-auto h-32 w-32 rounded-full bg-primary/30 flex items-center justify-center">
                  <svg
                    className="h-16 w-16 text-primary"
                    fill="none"
                    stroke="currentColor"
                    viewBox="0 0 24 24"
                  >
                    <path
                      strokeLinecap="round"
                      strokeLinejoin="round"
                      strokeWidth={2}
                      d="M3 12l2-2m0 0l7-7 7 7M5 10v10a1 1 0 001 1h3m10-11l2 2m-2-2v10a1 1 0 01-1 1h-3m-6 0a1 1 0 001-1v-4a1 1 0 011-1h2a1 1 0 011 1v4a1 1 0 001 1m-6 0h6"
                    />
                  </svg>
                </div>
                <p className="text-sm text-muted-foreground">Hero illustration placeholder</p>
              </div>
            </div>
          </div>
        </div>
        <div className="mt-16 flex justify-center">
          <button
            onClick={scrollToFeatures}
            className="animate-bounce text-muted-foreground hover:text-foreground transition-colors"
            aria-label="Scroll to learn more"
          >
            <ChevronDown className="h-8 w-8" />
          </button>
        </div>
      </section>

      {/* What is MAXergy Section */}
      <section id="what-is-maxergy" ref={whatIsMaxergyAnimation.ref} className="container mx-auto px-4 py-20 border-t border-border">
        <div className={`space-y-12 transition-opacity duration-700 ${whatIsMaxergyAnimation.isVisible ? 'opacity-100' : 'opacity-0'}`}>
          <div className="text-center space-y-4">
            <h2 className="text-3xl font-bold tracking-tight sm:text-4xl">What is MAXergy?</h2>
            <p className="text-lg text-muted-foreground max-w-2xl mx-auto">
              MAXergy is an AI-powered home energy upgrade planner designed specifically for German households. We help
              you understand the financial impact of energy efficiency upgrades like solar PV, battery storage, heat
              pumps, and EV charging.
            </p>
          </div>

          <div className="grid gap-6 sm:grid-cols-2 lg:grid-cols-4">
            <div className="rounded-lg border border-border bg-card p-6 text-center space-y-3">
              <div className="text-3xl font-bold text-primary">6</div>
              <div className="text-sm text-muted-foreground">Upgrade scenarios analyzed</div>
            </div>
            <div className="rounded-lg border border-border bg-card p-6 text-center space-y-3">
              <div className="text-3xl font-bold text-primary">20 years</div>
              <div className="text-sm text-muted-foreground">Long-term projections</div>
            </div>
            <div className="rounded-lg border border-border bg-card p-6 text-center space-y-3">
              <div className="text-3xl font-bold text-primary">✓</div>
              <div className="text-sm text-muted-foreground">German market specific</div>
            </div>
            <div className="rounded-lg border border-border bg-card p-6 text-center space-y-3">
              <div className="text-3xl font-bold text-primary">AI</div>
              <div className="text-sm text-muted-foreground">Personalized recommendations</div>
            </div>
          </div>

          <div className="rounded-lg border border-border bg-card p-6">
            <p className="text-sm text-muted-foreground">
              <strong className="text-foreground">German Market Context:</strong> Built for the German energy market
              with current tariffs (Arbeitspreis, Grundpreis), EEG feed-in tariffs, and subsidy considerations.
            </p>
          </div>
        </div>
      </section>

      {/* How It Works Section */}
      <section ref={howItWorksAnimation.ref} className="container mx-auto px-4 py-20 border-t border-border">
        <div className={`space-y-12 transition-opacity duration-700 ${howItWorksAnimation.isVisible ? 'opacity-100' : 'opacity-0'}`}>
          <div className="text-center space-y-4">
            <h2 className="text-3xl font-bold tracking-tight sm:text-4xl">How it works</h2>
          </div>

          <div className="grid gap-8 md:grid-cols-5">
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
          </div>
        </div>
      </section>

      {/* Example Output Section */}
      <section ref={exampleOutputAnimation.ref} className="container mx-auto px-4 py-20 border-t border-border">
        <div className={`space-y-12 transition-opacity duration-700 ${exampleOutputAnimation.isVisible ? 'opacity-100' : 'opacity-0'}`}>
          <div className="text-center space-y-4">
            <div className="inline-flex items-center rounded-full bg-primary/10 px-4 py-1 text-sm font-medium text-primary">
              Typical German household benchmark
            </div>
            <h2 className="text-3xl font-bold tracking-tight sm:text-4xl">
              A typical German household could save around €{data.recommendation.cumulative_savings_eur.toLocaleString('de-DE')} over 20 years
            </h2>
            <p className="text-lg text-muted-foreground max-w-2xl mx-auto">
              This estimate is based on a representative {data.household.occupants}-person household in {data.household.location.split(',')[0]} with {data.household.heating_type} heating, a {data.household.vehicle_type} car,
              and a {data.household.roof_orientation}-facing roof.
            </p>
          </div>

          {/* Household Summary Cards */}
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
            <SummaryCard label="Location" value={data.household.location} />
            <SummaryCard label="Household size" value={`${data.household.occupants} people`} />
            <SummaryCard label="Annual electricity" value={`${data.household.annual_electricity_kwh.toLocaleString('de-DE')} kWh`} />
            <SummaryCard label="Heating type" value={`${data.household.heating_type.charAt(0).toUpperCase() + data.household.heating_type.slice(1)} (${data.household.heating_annual_kwh.toLocaleString('de-DE')} kWh)`} />
            <SummaryCard label="Vehicle type" value={data.household.vehicle_type.charAt(0).toUpperCase() + data.household.vehicle_type.slice(1)} />
            <SummaryCard label="Annual mileage" value={`${data.household.annual_mileage_km.toLocaleString('de-DE')} km`} />
            <SummaryCard label="Roof area" value={`${data.household.roof_area_m2} m²`} />
            <SummaryCard label="Roof orientation" value={`${data.household.roof_orientation.charAt(0).toUpperCase() + data.household.roof_orientation.slice(1)}, ${data.household.roof_tilt_deg}° tilt`} />
          </div>

          {/* Recommended Plan Card */}
          <div className="rounded-lg border border-border bg-card p-6 space-y-6">
            <div className="flex items-center justify-between">
              <h3 className="text-xl font-semibold">Recommended Plan: {data.recommendation.scenario.split('_').map(w => w.charAt(0).toUpperCase() + w.slice(1)).join(' ')}</h3>
              <span className="inline-flex items-center rounded-full bg-green-100 px-3 py-1 text-sm font-medium text-green-800">
                Best option
              </span>
            </div>
            <p className="text-sm text-muted-foreground">
              {data.recommendation.description}
            </p>
            <div className="grid gap-4 sm:grid-cols-3">
              <div className="space-y-1">
                <div className="text-sm text-muted-foreground">Break-even</div>
                <div className="text-2xl font-bold">Year {data.recommendation.break_even_year}</div>
              </div>
              <div className="space-y-1">
                <div className="text-sm text-muted-foreground">Monthly instalment</div>
                <div className="text-2xl font-bold">€{data.recommendation.monthly_instalment_eur}</div>
              </div>
              <div className="space-y-1">
                <div className="text-sm text-muted-foreground">20-year savings</div>
                <div className="text-2xl font-bold text-primary">€{data.recommendation.cumulative_savings_eur.toLocaleString('de-DE')}</div>
              </div>
            </div>
          </div>

          {/* Cumulative Savings Chart */}
          <div className="rounded-lg border border-border bg-card p-6 space-y-4">
            <h3 className="text-lg font-semibold">Cumulative Net Savings Over 20 Years</h3>
            <div className="flex justify-center">
              <img
                src={cumulativeNetSavings}
                alt="Cumulative net savings chart showing baseline vs recommended scenario over 20 years"
                className="max-w-full h-auto rounded-lg"
              />
            </div>
          </div>

          {/* Household Comparison Charts */}
          <div className="grid gap-6 md:grid-cols-3">
            <div className="rounded-lg border border-border bg-card p-4 space-y-3">
              <h4 className="text-sm font-semibold text-center">Average German Household</h4>
              <img
                src={averageGermanHousehold}
                alt="Average German household energy cost comparison"
                className="w-full h-auto rounded-lg"
              />
            </div>
            <div className="rounded-lg border border-border bg-card p-4 space-y-3">
              <h4 className="text-sm font-semibold text-center">High Benefit Household</h4>
              <img
                src={highBenefitHousehold}
                alt="High benefit household energy cost comparison"
                className="w-full h-auto rounded-lg"
              />
            </div>
            <div className="rounded-lg border border-border bg-card p-4 space-y-3">
              <h4 className="text-sm font-semibold text-center">Low Benefit Household</h4>
              <img
                src={lowBenefitHousehold}
                alt="Low benefit household energy cost comparison"
                className="w-full h-auto rounded-lg"
              />
            </div>
          </div>

          {/* Disclaimer */}
          <div className="rounded-lg border border-border bg-muted/50 p-4 text-sm text-muted-foreground">
            <p>
              <strong className="text-foreground">Note:</strong> These figures describe a typical German household
              benchmark. They are not yet personalised for your home. Your actual savings may differ based on your
              specific situation.
            </p>
          </div>

          {/* CTA */}
          <div className="text-center">
            <Link to="/assessment">
              <Button size="lg" className="bg-primary text-primary-foreground hover:bg-primary/90">
                Get Your Personal Estimate
                <ArrowRight className="ml-2 h-4 w-4" />
              </Button>
            </Link>
            <p className="mt-3 text-sm text-muted-foreground">
              Personalise the estimate using your roof, heating, driving and energy use.
            </p>
          </div>
        </div>
      </section>

      {/* Features Section */}
      <section ref={featuresAnimation.ref} className="container mx-auto px-4 py-20 border-t border-border">
        <div className={`space-y-12 transition-opacity duration-700 ${featuresAnimation.isVisible ? 'opacity-100' : 'opacity-0'}`}>
          <div className="text-center space-y-4">
            <h2 className="text-3xl font-bold tracking-tight sm:text-4xl">Why MAXergy?</h2>
          </div>

          <div className="grid gap-6 sm:grid-cols-2 lg:grid-cols-3">
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
          </div>
        </div>
      </section>

      {/* FAQ Section */}
      <section ref={faqAnimation.ref} className="container mx-auto px-4 py-20 border-t border-border">
        <div className={`space-y-12 max-w-3xl mx-auto transition-opacity duration-700 ${faqAnimation.isVisible ? 'opacity-100' : 'opacity-0'}`}>
          <div className="text-center space-y-4">
            <h2 className="text-3xl font-bold tracking-tight sm:text-4xl">Frequently Asked Questions</h2>
          </div>

          <div className="space-y-4">
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
          </div>
        </div>
      </section>

      {/* Footer */}
      <footer className="border-t border-border bg-muted/50">
        <div className="container mx-auto px-4 py-12">
          <div className="grid gap-8 md:grid-cols-4">
            <div className="space-y-4">
              <BrandMark />
              <p className="text-sm text-muted-foreground">
                Plan your energy upgrade with confidence
              </p>
            </div>
            <div>
              <h4 className="font-semibold mb-4">Product</h4>
              <ul className="space-y-2 text-sm text-muted-foreground">
                <li>
                  <Link to="/landing" className="hover:text-foreground">
                    Home
                  </Link>
                </li>
                <li>
                  <Link to="/assessment" className="hover:text-foreground">
                    Assessment
                  </Link>
                </li>
              </ul>
            </div>
            <div>
              <h4 className="font-semibold mb-4">Legal</h4>
              <ul className="space-y-2 text-sm text-muted-foreground">
                <li>
                  <a href="#" className="hover:text-foreground">
                    Privacy Policy
                  </a>
                </li>
                <li>
                  <a href="#" className="hover:text-foreground">
                    Terms of Service
                  </a>
                </li>
                <li>
                  <a href="#" className="hover:text-foreground">
                    Impressum
                  </a>
                </li>
              </ul>
            </div>
            <div>
              <h4 className="font-semibold mb-4">Contact</h4>
              <ul className="space-y-2 text-sm text-muted-foreground">
                <li>
                  <a href="mailto:contact@maxergy.de" className="hover:text-foreground">
                    contact@maxergy.de
                  </a>
                </li>
              </ul>
            </div>
          </div>
          <div className="mt-12 pt-8 border-t border-border text-center text-sm text-muted-foreground">
            © 2026 MAXergy. All rights reserved.
          </div>
        </div>
      </footer>
    </div>
  );
}

