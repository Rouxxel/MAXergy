import { createFileRoute, useNavigate } from "@tanstack/react-router";
import { useState } from "react";
import { z } from "zod";
import { ArrowLeft, ArrowRight } from "lucide-react";

import { AppShell, BrandMark } from "@/components/app-shell";
import { ProgressSteps } from "@/components/progress-steps";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Switch } from "@/components/ui/switch";
import { Slider } from "@/components/ui/slider";
import { useAssessmentStore } from "@/stores/assessmentStore";
import type { HeatingType, SpendSeason, VehicleType } from "@/types";

export const Route = createFileRoute("/")({
  head: () => ({
    meta: [
      { title: "Get started — Cloover" },
      { name: "description", content: "Tell us about your home in a minute and see your potential monthly savings." },
    ],
  }),
  component: Onboarding,
});

const COUNTRIES = [
  { code: "DE", name: "Germany" },
  { code: "FR", name: "France" },
  { code: "NL", name: "Netherlands" },
  { code: "BE", name: "Belgium" },
  { code: "ES", name: "Spain" },
  { code: "IT", name: "Italy" },
];

const HEATING: { value: HeatingType; label: string }[] = [
  { value: "electric", label: "Electric" },
  { value: "gas", label: "Gas" },
  { value: "oil", label: "Oil" },
  { value: "district", label: "District heating" },
  { value: "coal", label: "Coal" },
  { value: "wood_pellets", label: "Wood pellets" },
  { value: "other", label: "Other" },
];

const SEASONS: { value: SpendSeason; label: string }[] = [
  { value: "annual", label: "Annual average" },
  { value: "spring", label: "Spring" },
  { value: "summer", label: "Summer" },
  { value: "autumn", label: "Autumn" },
  { value: "winter", label: "Winter" },
];

const VEHICLE_TYPES: { value: VehicleType; label: string }[] = [
  { value: "ev", label: "Electric (EV)" },
  { value: "gas", label: "Gas / petrol / diesel" },
  { value: "hydrogen", label: "Hydrogen" },
];

const MAX_TERM_MONTHS = 360; // 30 years
const MIN_TERM_MONTHS = 1;

type StepId =
  | "country"
  | "postal"
  | "electricity"
  | "heatingType"
  | "heatingSpend"
  | "vehicle"
  | "fuel"
  | "roof"
  | "term";

function Onboarding() {
  const navigate = useNavigate();
  const { draft, setField, step, setStep } = useAssessmentStore();

  const steps: StepId[] = [
    "country",
    "postal",
    "electricity",
    "heatingType",
    ...(draft.heatingType && draft.heatingType !== "other"
      ? (["heatingSpend"] as StepId[])
      : []),
    "vehicle",
    ...(draft.vehicleOwnership ? (["fuel"] as StepId[]) : []),
    "roof",
    "term",
  ];

  const safeStep = Math.min(step, steps.length - 1);
  const current = steps[safeStep];
  const [error, setError] = useState<string | undefined>();

  const validate = (): string | undefined => {
    switch (current) {
      case "country":
        return draft.country ? undefined : "Pick a country";
      case "postal":
        return z
          .string()
          .min(3, "Postal code looks too short")
          .max(10)
          .safeParse(draft.postalCode ?? "").success
          ? undefined
          : "Enter a valid postal code";
      case "electricity":
        return typeof draft.monthlyElectricitySpend === "number" &&
          draft.monthlyElectricitySpend > 0
          ? undefined
          : "Enter your monthly electricity spend";
      case "heatingType":
        return draft.heatingType ? undefined : "Pick a heating type";
      case "heatingSpend":
        return typeof draft.heatingSpend === "number" && draft.heatingSpend >= 0
          ? undefined
          : "Enter your monthly heating spend";
      case "vehicle":
        if (!draft.vehicleOwnership) return undefined;
        if (!draft.vehicleType) return "Pick the vehicle type";
        if (!draft.vehicleCount || draft.vehicleCount < 1)
          return "How many vehicles do you own?";
        if (
          typeof draft.vehicleMonthlyKm !== "number" ||
          draft.vehicleMonthlyKm < 0
        )
          return "Enter your average monthly distance in km";
        return undefined;
      case "fuel":
        return typeof draft.fuelSpend === "number" && draft.fuelSpend >= 0
          ? undefined
          : "Enter your monthly fuel spend";
      case "roof":
        return typeof draft.roofSize === "number" && draft.roofSize > 0
          ? undefined
          : "Enter your roof size in m²";
      case "term":
        return draft.financingTermMonths && draft.financingTermMonths >= MIN_TERM_MONTHS
          ? undefined
          : "Pick a financing term";
    }
  };

  const onNext = () => {
    const err = validate();
    if (err) {
      setError(err);
      return;
    }
    setError(undefined);
    if (safeStep === steps.length - 1) {
      // Default heatingSpend to 0 when skipped
      if (draft.heatingSpend === undefined) setField("heatingSpend", 0);
      if (!draft.vehicleOwnership && draft.fuelSpend === undefined)
        setField("fuelSpend", 0);
      navigate({ to: "/loading" });
      return;
    }
    setStep(safeStep + 1);
  };

  const onBack = () => {
    setError(undefined);
    if (safeStep > 0) setStep(safeStep - 1);
  };

  return (
    <AppShell>
      <header className="mb-6 flex items-center justify-between">
        <BrandMark />
      </header>
      <ProgressSteps current={safeStep} total={steps.length} />

      <div className="mt-8 min-h-[260px]">
        <StepView step={current} />
        {error ? (
          <p className="mt-3 text-sm text-destructive">{error}</p>
        ) : null}
      </div>

      <div className="mt-8 flex items-center gap-3">
        <Button
          type="button"
          variant="outline"
          onClick={onBack}
          disabled={safeStep === 0}
          className="h-12 flex-1"
        >
          <ArrowLeft className="mr-2 h-4 w-4" /> Back
        </Button>
        <Button
          type="button"
          onClick={onNext}
          className="h-12 flex-[2] bg-primary text-primary-foreground hover:bg-primary/90"
        >
          {safeStep === steps.length - 1 ? "See my savings" : "Continue"}
          <ArrowRight className="ml-2 h-4 w-4" />
        </Button>
      </div>
    </AppShell>
  );
}

function StepView({ step }: { step: StepId }) {
  const { draft, setField } = useAssessmentStore();

  switch (step) {
    case "country":
      return (
        <Field
          title="Where do you live?"
          subtitle="We use this to estimate local energy prices and incentives."
        >
          <Select
            value={draft.country}
            onValueChange={(v) => setField("country", v)}
          >
            <SelectTrigger className="h-12">
              <SelectValue placeholder="Select country" />
            </SelectTrigger>
            <SelectContent>
              {COUNTRIES.map((c) => (
                <SelectItem key={c.code} value={c.code}>
                  {c.name}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </Field>
      );
    case "postal":
      return (
        <Field title="What's your postal code?" subtitle="Used to refine solar yield and tariffs.">
          <Input
            inputMode="numeric"
            className="h-12"
            value={draft.postalCode ?? ""}
            onChange={(e) =>
              setField("postalCode", e.target.value.replace(/[^0-9A-Za-z\s-]/g, ""))
            }
            placeholder="e.g. 10115"
          />
        </Field>
      );
    case "electricity":
      return (
        <Field title="Monthly electricity spend" subtitle="Roughly, in euros per month.">
          <div className="space-y-4">
            <CurrencyInput
              value={draft.monthlyElectricitySpend}
              onChange={(v) => setField("monthlyElectricitySpend", v)}
            />
            <div className="flex items-center justify-between rounded-2xl border border-border bg-card p-4">
              <div className="pr-3">
                <p className="text-base font-medium">Feed-in tariff</p>
                <p className="text-xs text-muted-foreground">
                  Einspeisevergütung — you get paid for solar you export.
                </p>
              </div>
              <Switch
                checked={!!draft.hasFeedInTariff}
                onCheckedChange={(v) => setField("hasFeedInTariff", v)}
              />
            </div>
          </div>
        </Field>
      );
    case "heatingType":
      return (
        <Field title="How do you heat your home?">
          <Select
            value={draft.heatingType}
            onValueChange={(v) => setField("heatingType", v as HeatingType)}
          >
            <SelectTrigger className="h-12">
              <SelectValue placeholder="Select heating type" />
            </SelectTrigger>
            <SelectContent>
              {HEATING.map((h) => (
                <SelectItem key={h.value} value={h.value}>
                  {h.label}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </Field>
      );
    case "heatingSpend":
      return (
        <Field
          title="Monthly heating spend"
          subtitle="Pick a season or stick with the annual average."
        >
          <div className="space-y-4">
            <CurrencyInput
              value={draft.heatingSpend}
              onChange={(v) => setField("heatingSpend", v)}
            />
            <div className="space-y-2">
              <Label className="text-sm text-muted-foreground">
                Heating type this spend covers
              </Label>
              <Select
                value={draft.heatingSpendType ?? draft.heatingType}
                onValueChange={(v) =>
                  setField("heatingSpendType", v as HeatingType)
                }
              >
                <SelectTrigger className="h-12">
                  <SelectValue placeholder="Select heating type" />
                </SelectTrigger>
                <SelectContent>
                  {HEATING.map((h) => (
                    <SelectItem key={h.value} value={h.value}>
                      {h.label}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            <div className="space-y-2">
              <Label className="text-sm text-muted-foreground">Time of year</Label>
              <Select
                value={draft.heatingSpendSeason ?? "annual"}
                onValueChange={(v) =>
                  setField("heatingSpendSeason", v as SpendSeason)
                }
              >
                <SelectTrigger className="h-12">
                  <SelectValue placeholder="Select season" />
                </SelectTrigger>
                <SelectContent>
                  {SEASONS.map((s) => (
                    <SelectItem key={s.value} value={s.value}>
                      {s.label}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
          </div>
        </Field>
      );
    case "vehicle":
      return (
        <Field
          title="Do you own a vehicle?"
          subtitle="We'll factor in fuel savings from charging at home."
        >
          <div className="space-y-4">
            <div className="flex items-center justify-between rounded-2xl border border-border bg-card p-4">
              <span className="text-base font-medium">I own a vehicle</span>
              <Switch
                checked={!!draft.vehicleOwnership}
                onCheckedChange={(v) => setField("vehicleOwnership", v)}
              />
            </div>
            {draft.vehicleOwnership ? (
              <div className="space-y-4 rounded-2xl border border-border bg-card p-4">
                <div className="space-y-2">
                  <Label className="text-sm text-muted-foreground">
                    Vehicle type
                  </Label>
                  <Select
                    value={draft.vehicleType}
                    onValueChange={(v) =>
                      setField("vehicleType", v as VehicleType)
                    }
                  >
                    <SelectTrigger className="h-12">
                      <SelectValue placeholder="EV, gas or hydrogen" />
                    </SelectTrigger>
                    <SelectContent>
                      {VEHICLE_TYPES.map((t) => (
                        <SelectItem key={t.value} value={t.value}>
                          {t.label}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>
                <div className="grid grid-cols-2 gap-3">
                  <div className="space-y-2">
                    <Label className="text-sm text-muted-foreground">
                      How many?
                    </Label>
                    <Input
                      inputMode="numeric"
                      className="h-12"
                      value={draft.vehicleCount ?? ""}
                      onChange={(e) => {
                        const n = parseInt(e.target.value, 10);
                        setField(
                          "vehicleCount",
                          Number.isFinite(n) && n > 0 ? n : 0,
                        );
                      }}
                      placeholder="1"
                    />
                  </div>
                  <div className="space-y-2">
                    <Label className="text-sm text-muted-foreground">
                      Avg km / month
                    </Label>
                    <div className="relative">
                      <Input
                        inputMode="numeric"
                        className="h-12 pr-12"
                        value={draft.vehicleMonthlyKm ?? ""}
                        onChange={(e) => {
                          const n = Number(e.target.value);
                          setField(
                            "vehicleMonthlyKm",
                            Number.isFinite(n) ? n : 0,
                          );
                        }}
                        placeholder="1000"
                      />
                      <span className="pointer-events-none absolute inset-y-0 right-4 grid place-items-center text-sm text-muted-foreground">
                        km
                      </span>
                    </div>
                  </div>
                </div>
              </div>
            ) : null}
          </div>
        </Field>
      );
    case "fuel":
      return (
        <Field
          title="Monthly fuel or charging spend"
          subtitle="For your current vehicle(s)."
        >
          <CurrencyInput
            value={draft.fuelSpend}
            onChange={(v) => setField("fuelSpend", v)}
          />
        </Field>
      );
    case "roof":
      return (
        <Field title="Roughly, how big is your roof?" subtitle="A rough estimate in square meters is fine.">
          <div className="relative">
            <Input
              inputMode="decimal"
              className="h-12 pr-12"
              value={draft.roofSize ?? ""}
              onChange={(e) => {
                const n = Number(e.target.value);
                setField("roofSize", Number.isFinite(n) ? n : 0);
              }}
              placeholder="60"
            />
            <span className="pointer-events-none absolute inset-y-0 right-4 grid place-items-center text-sm text-muted-foreground">
              m²
            </span>
          </div>
        </Field>
      );
    case "term":
      return <FinancingTermStep />;
  }
}

function Field({
  title,
  subtitle,
  children,
}: {
  title: string;
  subtitle?: string;
  children: React.ReactNode;
}) {
  return (
    <div className="space-y-4">
      <div>
        <h1 className="text-2xl font-bold tracking-tight">{title}</h1>
        {subtitle ? (
          <p className="mt-1 text-sm text-muted-foreground">{subtitle}</p>
        ) : null}
      </div>
      <Label className="sr-only">{title}</Label>
      {children}
    </div>
  );
}

function CurrencyInput({
  value,
  onChange,
}: {
  value: number | undefined;
  onChange: (v: number) => void;
}) {
  return (
    <div className="relative">
      <span className="pointer-events-none absolute inset-y-0 left-4 grid place-items-center text-sm text-muted-foreground">
        €
      </span>
      <Input
        inputMode="decimal"
        className="h-12 pl-9"
        value={value ?? ""}
        onChange={(e) => {
          const n = Number(e.target.value);
          onChange(Number.isFinite(n) ? n : 0);
        }}
        placeholder="0"
      />
    </div>
  );
}

function FinancingTermStep() {
  const { draft, setField } = useAssessmentStore();
  const months = draft.financingTermMonths ?? MIN_TERM_MONTHS;
  const years = Math.floor(months / 12);
  const remMonths = months % 12;

  const clamp = (n: number) =>
    Math.min(MAX_TERM_MONTHS, Math.max(MIN_TERM_MONTHS, Math.round(n)));

  const setMonths = (m: number) => setField("financingTermMonths", clamp(m));

  return (
    <Field
      title="Preferred financing term"
      subtitle="Drag the slider, or type an exact duration. Longer terms mean lower monthly payments."
    >
      <div className="space-y-6">
        <div className="rounded-2xl border border-border bg-card p-4">
          <div className="flex items-baseline justify-between">
            <span className="text-sm text-muted-foreground">Term</span>
            <span className="text-lg font-semibold text-primary">
              {years > 0 ? `${years} yr${years === 1 ? "" : "s"}` : ""}
              {years > 0 && remMonths > 0 ? " " : ""}
              {remMonths > 0 || years === 0
                ? `${remMonths || months} mo${(remMonths || months) === 1 ? "" : "s"}`
                : ""}
            </span>
          </div>
          <Slider
            className="mt-4"
            min={MIN_TERM_MONTHS}
            max={MAX_TERM_MONTHS}
            step={1}
            value={[months]}
            onValueChange={(v) => setMonths(v[0] ?? MIN_TERM_MONTHS)}
          />
          <div className="mt-2 flex justify-between text-xs text-muted-foreground">
            <span>1 mo</span>
            <span>30 yrs</span>
          </div>
        </div>
        <div className="grid grid-cols-2 gap-3">
          <div className="space-y-2">
            <Label className="text-sm text-muted-foreground">Years</Label>
            <Input
              inputMode="numeric"
              className="h-12"
              value={years}
              onChange={(e) => {
                const y = Math.max(0, parseInt(e.target.value, 10) || 0);
                setMonths(y * 12 + remMonths);
              }}
            />
          </div>
          <div className="space-y-2">
            <Label className="text-sm text-muted-foreground">Months</Label>
            <Input
              inputMode="numeric"
              className="h-12"
              value={remMonths}
              onChange={(e) => {
                const m = Math.max(0, parseInt(e.target.value, 10) || 0);
                setMonths(years * 12 + m);
              }}
            />
          </div>
        </div>
      </div>
    </Field>
  );
}
