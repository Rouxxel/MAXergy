import { createFileRoute, useNavigate } from "@tanstack/react-router";
import { useState } from "react";
import { z } from "zod";
import { useMutation } from "@tanstack/react-query";
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
import { useUiStore } from "@/stores/uiStore";
import { HouseholdAssessmentSchema } from "@/services/validation";
import { postAssessment } from "@/services/endpoints";

export const Route = createFileRoute("/")({
  head: () => ({
    meta: [
      { title: "MAXergy" },
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

const HEATING_TYPES = [
  { value: "electric", label: "Electric" },
  { value: "gas", label: "Gas" },
  { value: "oil", label: "Oil" },
  { value: "district", label: "District heating" },
  { value: "coal", label: "Coal" },
  { value: "wood_pellets", label: "Wood pellets" },
  { value: "other", label: "Other" },
];

const VEHICLE_TYPES = [
  { value: "ev", label: "Electric (EV)" },
  { value: "gas", label: "Gas / petrol / diesel" },
  { value: "hydrogen", label: "Hydrogen" },
];

const INSULATION_CLASSES = [
  { value: "poor", label: "Poor" },
  { value: "medium", label: "Medium" },
  { value: "good", label: "Good" },
  { value: "excellent", label: "Excellent" },
];

const ROOF_ORIENTATIONS = [
  { value: "south", label: "South" },
  { value: "south_east", label: "South-East" },
  { value: "south_west", label: "South-West" },
  { value: "east", label: "East" },
  { value: "west", label: "West" },
  { value: "north", label: "North" },
];

type StepId =
  | "country"
  | "postcode"
  | "occupants"
  | "electricity"
  | "roof"
  | "heating"
  | "mobility"
  | "upgrades"
  | "financing"
  | "horizon";

function Onboarding() {
  const navigate = useNavigate();
  const { draft, setField, step, setStep, setSubmittedId } = useAssessmentStore();
  const { setError: setGlobalError } = useUiStore();

  const submitAssessment = useMutation({
    mutationFn: postAssessment,
    onSuccess: (data) => {
      setSubmittedId(data.id);
      navigate({ to: "/loading" });
    },
    onError: (error) => {
      const errorMsg = error instanceof Error ? error.message : "Failed to submit assessment";
      setError(errorMsg);
      setGlobalError(errorMsg);
    },
  });

  const steps: StepId[] = [
    "country",
    "postcode",
    "occupants",
    "electricity",
    "roof",
    "heating",
    "mobility",
    "upgrades",
    "financing",
    "horizon",
  ];

  const safeStep = Math.min(step, steps.length - 1);
  const current = steps[safeStep];
  const [error, setError] = useState<string | undefined>();

  const validate = (): string | undefined => {
    try {
      HouseholdAssessmentSchema.parse(draft);
      return undefined;
    } catch (e) {
      if (e instanceof z.ZodError) {
        const firstError = e.errors[0];
        if (firstError) {
          const path = firstError.path.join(".");
          const message = firstError.message;
          return `${path}: ${message}`;
        }
      }
      return "Please check your inputs";
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
      const completed = useAssessmentStore.getState().getCompleted();
      if (completed) {
        submitAssessment.mutate(completed);
      } else {
        setError("Please complete all required fields");
      }
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
            value={draft.location?.country}
            onValueChange={(v) =>
              setField("location", { postcode: draft.location?.postcode ?? "", country: v })
            }
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
    case "postcode":
      return (
        <Field title="What's your postal code?" subtitle="Used to refine solar yield and tariffs.">
          <Input
            inputMode="numeric"
            className="h-12"
            value={draft.location?.postcode ?? ""}
            onChange={(e) =>
              setField("location", { country: draft.location?.country ?? "DE", postcode: e.target.value.replace(/[^0-9A-Za-z\s-]/g, "") })
            }
            placeholder="e.g. 10115"
          />
        </Field>
      );
    case "occupants":
      return (
        <Field title="How many people live in your home?" subtitle="This helps estimate energy usage patterns.">
          <Input
            inputMode="numeric"
            className="h-12"
            type="number"
            value={draft.household?.occupants?.count ?? ""}
            onChange={(e) => {
              const n = parseInt(e.target.value, 10);
              setField("household", {
                occupants: { count: Number.isFinite(n) && n > 0 ? n : 1 },
                electricity: draft.household?.electricity ?? {
                  annual_kwh: 3000,
                  current_tariff_type: "standard",
                  arbeitspreis_eur_per_kwh: 0.35,
                  grundpreis_eur_per_month: 10,
                  contract_end_date: null,
                },
                roof: draft.household?.roof ?? {
                  available: true,
                  usable_area_m2: 50,
                  orientation: "south",
                  tilt_deg: 30,
                  shading_factor: 0.1,
                },
              });
            }}
            placeholder="2"
          />
        </Field>
      );
    case "electricity":
      return (
        <Field title="Annual electricity consumption" subtitle="In kWh per year. Check your bill.">
          <div className="space-y-4">
            <div className="relative">
              <Input
                inputMode="numeric"
                className="h-12 pr-12"
                type="number"
                value={draft.household?.electricity?.annual_kwh ?? ""}
                onChange={(e) => {
                  const n = Number(e.target.value);
                  setField("household", {
                    occupants: draft.household?.occupants ?? { count: 2 },
                    electricity: {
                      annual_kwh: Number.isFinite(n) ? n : 0,
                      current_tariff_type: draft.household?.electricity?.current_tariff_type ?? "standard",
                      arbeitspreis_eur_per_kwh: draft.household?.electricity?.arbeitspreis_eur_per_kwh ?? 0.35,
                      grundpreis_eur_per_month: draft.household?.electricity?.grundpreis_eur_per_month ?? 10,
                      contract_end_date: draft.household?.electricity?.contract_end_date ?? null,
                    },
                    roof: draft.household?.roof ?? {
                      available: true,
                      usable_area_m2: 50,
                      orientation: "south",
                      tilt_deg: 30,
                      shading_factor: 0.1,
                    },
                  });
                }}
                placeholder="3000"
              />
              <span className="pointer-events-none absolute inset-y-0 right-4 grid place-items-center text-sm text-muted-foreground">
                kWh
              </span>
            </div>
            <div className="space-y-2">
              <Label className="text-sm text-muted-foreground">Tariff type</Label>
              <Select
                value={draft.household?.electricity?.current_tariff_type ?? "standard"}
                onValueChange={(v) =>
                  setField("household", {
                    occupants: draft.household?.occupants ?? { count: 2 },
                    electricity: {
                      annual_kwh: draft.household?.electricity?.annual_kwh ?? 3000,
                      current_tariff_type: v,
                      arbeitspreis_eur_per_kwh: draft.household?.electricity?.arbeitspreis_eur_per_kwh ?? 0.35,
                      grundpreis_eur_per_month: draft.household?.electricity?.grundpreis_eur_per_month ?? 10,
                      contract_end_date: draft.household?.electricity?.contract_end_date ?? null,
                    },
                    roof: draft.household?.roof ?? {
                      available: true,
                      usable_area_m2: 50,
                      orientation: "south",
                      tilt_deg: 30,
                      shading_factor: 0.1,
                    },
                  })
                }
              >
                <SelectTrigger className="h-12">
                  <SelectValue placeholder="Select tariff type" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="standard">Standard</SelectItem>
                  <SelectItem value="ht">HT (High Tariff)</SelectItem>
                  <SelectItem value="nt">NT (Low Tariff)</SelectItem>
                </SelectContent>
              </Select>
            </div>
            <div className="grid grid-cols-2 gap-3">
              <div className="space-y-2">
                <Label className="text-sm text-muted-foreground">Energy price (€/kWh)</Label>
                <div className="relative">
                  <Input
                    inputMode="decimal"
                    className="h-12 pr-8"
                    type="number"
                    step="0.01"
                    value={draft.household?.electricity?.arbeitspreis_eur_per_kwh ?? ""}
                    onChange={(e) => {
                      const n = Number(e.target.value);
                      setField("household", {
                        occupants: draft.household?.occupants ?? { count: 2 },
                        electricity: {
                          annual_kwh: draft.household?.electricity?.annual_kwh ?? 3000,
                          current_tariff_type: draft.household?.electricity?.current_tariff_type ?? "standard",
                          arbeitspreis_eur_per_kwh: Number.isFinite(n) ? n : 0.35,
                          grundpreis_eur_per_month: draft.household?.electricity?.grundpreis_eur_per_month ?? 10,
                          contract_end_date: draft.household?.electricity?.contract_end_date ?? null,
                        },
                        roof: draft.household?.roof ?? {
                          available: true,
                          usable_area_m2: 50,
                          orientation: "south",
                          tilt_deg: 30,
                          shading_factor: 0.1,
                        },
                      });
                    }}
                    placeholder="0.35"
                  />
                  <span className="pointer-events-none absolute inset-y-0 right-3 grid place-items-center text-xs text-muted-foreground">
                    €
                  </span>
                </div>
                <p className="text-[10px] text-muted-foreground">Arbeitspreis - price per kWh consumed</p>
              </div>
              <div className="space-y-2">
                <Label className="text-sm text-muted-foreground">Base fee (€/month)</Label>
                <div className="relative">
                  <Input
                    inputMode="decimal"
                    className="h-12 pr-8"
                    type="number"
                    step="0.01"
                    value={draft.household?.electricity?.grundpreis_eur_per_month ?? ""}
                    onChange={(e) => {
                      const n = Number(e.target.value);
                      setField("household", {
                        occupants: draft.household?.occupants ?? { count: 2 },
                        electricity: {
                          annual_kwh: draft.household?.electricity?.annual_kwh ?? 3000,
                          current_tariff_type: draft.household?.electricity?.current_tariff_type ?? "standard",
                          arbeitspreis_eur_per_kwh: draft.household?.electricity?.arbeitspreis_eur_per_kwh ?? 0.35,
                          grundpreis_eur_per_month: Number.isFinite(n) ? n : 10,
                          contract_end_date: draft.household?.electricity?.contract_end_date ?? null,
                        },
                        roof: draft.household?.roof ?? {
                          available: true,
                          usable_area_m2: 50,
                          orientation: "south",
                          tilt_deg: 30,
                          shading_factor: 0.1,
                        },
                      });
                    }}
                    placeholder="10"
                  />
                  <span className="pointer-events-none absolute inset-y-0 right-3 grid place-items-center text-xs text-muted-foreground">
                    €
                  </span>
                </div>
                <p className="text-[10px] text-muted-foreground">Grundpreis - fixed monthly fee</p>
              </div>
            </div>
          </div>
        </Field>
      );
    case "roof":
      return (
        <Field title="Roughly, how big is your roof?" subtitle="A rough estimate in square meters is fine.">
          <div className="space-y-4">
            <div className="relative">
              <Input
                inputMode="decimal"
                className="h-12 pr-12"
                type="number"
                value={draft.household?.roof?.usable_area_m2 ?? ""}
                onChange={(e) => {
                  const n = Number(e.target.value);
                  setField("household", {
                    occupants: draft.household?.occupants ?? { count: 2 },
                    electricity: draft.household?.electricity ?? {
                      annual_kwh: 3000,
                      current_tariff_type: "standard",
                      arbeitspreis_eur_per_kwh: 0.35,
                      grundpreis_eur_per_month: 10,
                      contract_end_date: null,
                    },
                    roof: {
                      available: true,
                      usable_area_m2: Number.isFinite(n) ? n : 0,
                      orientation: draft.household?.roof?.orientation ?? "south",
                      tilt_deg: draft.household?.roof?.tilt_deg ?? 30,
                      shading_factor: draft.household?.roof?.shading_factor ?? 0.1,
                    },
                  });
                }}
                placeholder="60"
              />
              <span className="pointer-events-none absolute inset-y-0 right-4 grid place-items-center text-sm text-muted-foreground">
                m²
              </span>
            </div>
            <div className="space-y-2">
              <Label className="text-sm text-muted-foreground">Roof orientation</Label>
              <Select
                value={draft.household?.roof?.orientation ?? "south"}
                onValueChange={(v) =>
                  setField("household", {
                    occupants: draft.household?.occupants ?? { count: 2 },
                    electricity: draft.household?.electricity ?? {
                      annual_kwh: 3000,
                      current_tariff_type: "standard",
                      arbeitspreis_eur_per_kwh: 0.35,
                      grundpreis_eur_per_month: 10,
                      contract_end_date: null,
                    },
                    roof: {
                      available: true,
                      usable_area_m2: draft.household?.roof?.usable_area_m2 ?? 50,
                      orientation: v,
                      tilt_deg: draft.household?.roof?.tilt_deg ?? 30,
                      shading_factor: draft.household?.roof?.shading_factor ?? 0.1,
                    },
                  })
                }
              >
                <SelectTrigger className="h-12">
                  <SelectValue placeholder="Select orientation" />
                </SelectTrigger>
                <SelectContent>
                  {ROOF_ORIENTATIONS.map((o) => (
                    <SelectItem key={o.value} value={o.value}>
                      {o.label}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            <div className="grid grid-cols-2 gap-3">
              <div className="space-y-2">
                <Label className="text-sm text-muted-foreground">Tilt angle (degrees)</Label>
                <div className="relative">
                  <Input
                    inputMode="decimal"
                    className="h-12 pr-8"
                    type="number"
                    step="1"
                    value={draft.household?.roof?.tilt_deg ?? ""}
                    onChange={(e) => {
                      const n = Number(e.target.value);
                      setField("household", {
                        occupants: draft.household?.occupants ?? { count: 2 },
                        electricity: draft.household?.electricity ?? {
                          annual_kwh: 3000,
                          current_tariff_type: "standard",
                          arbeitspreis_eur_per_kwh: 0.35,
                          grundpreis_eur_per_month: 10,
                          contract_end_date: null,
                        },
                        roof: {
                          available: true,
                          usable_area_m2: draft.household?.roof?.usable_area_m2 ?? 50,
                          orientation: draft.household?.roof?.orientation ?? "south",
                          tilt_deg: Number.isFinite(n) ? n : 30,
                          shading_factor: draft.household?.roof?.shading_factor ?? 0.1,
                        },
                      });
                    }}
                    placeholder="30"
                  />
                  <span className="pointer-events-none absolute inset-y-0 right-3 grid place-items-center text-xs text-muted-foreground">
                    °
                  </span>
                </div>
              </div>
              <div className="space-y-2">
                <Label className="text-sm text-muted-foreground">Shading factor</Label>
                <div className="relative">
                  <Input
                    inputMode="decimal"
                    className="h-12 pr-8"
                    type="number"
                    step="0.1"
                    value={draft.household?.roof?.shading_factor ?? ""}
                    onChange={(e) => {
                      const n = Number(e.target.value);
                      setField("household", {
                        occupants: draft.household?.occupants ?? { count: 2 },
                        electricity: draft.household?.electricity ?? {
                          annual_kwh: 3000,
                          current_tariff_type: "standard",
                          arbeitspreis_eur_per_kwh: 0.35,
                          grundpreis_eur_per_month: 10,
                          contract_end_date: null,
                        },
                        roof: {
                          available: true,
                          usable_area_m2: draft.household?.roof?.usable_area_m2 ?? 50,
                          orientation: draft.household?.roof?.orientation ?? "south",
                          tilt_deg: draft.household?.roof?.tilt_deg ?? 30,
                          shading_factor: Number.isFinite(n) ? n : 0.1,
                        },
                      });
                    }}
                    placeholder="0.1"
                  />
                  <span className="pointer-events-none absolute inset-y-0 right-3 grid place-items-center text-xs text-muted-foreground">
                    0-1
                  </span>
                </div>
                <p className="text-[10px] text-muted-foreground">0 = no shading, 1 = full shading</p>
              </div>
            </div>
          </div>
        </Field>
      );
    case "heating":
      return (
        <Field title="How do you heat your home?">
          <div className="space-y-4">
            <div className="space-y-2">
              <Label className="text-sm text-muted-foreground">Heating type</Label>
              <Select
                value={draft.heating?.fuel_type}
                onValueChange={(v) =>
                setField("heating", {
                  fuel_type: v,
                  annual_consumption: draft.heating?.annual_consumption ?? null,
                  annual_spend_eur: draft.heating?.annual_spend_eur ?? null,
                  building: draft.heating?.building ?? {
                    floor_area_m2: 120,
                    insulation_class: "medium",
                  },
                })
              }
              >
                <SelectTrigger className="h-12">
                  <SelectValue placeholder="Select heating type" />
                </SelectTrigger>
                <SelectContent>
                  {HEATING_TYPES.map((h) => (
                    <SelectItem key={h.value} value={h.value}>
                      {h.label}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            <div className="space-y-2">
              <Label className="text-sm text-muted-foreground">Building floor area</Label>
              <div className="relative">
                <Input
                  inputMode="numeric"
                  className="h-12 pr-12"
                  type="number"
                  value={draft.heating?.building?.floor_area_m2 ?? ""}
                  onChange={(e) => {
                    const n = Number(e.target.value);
                    setField("heating", {
                      fuel_type: draft.heating?.fuel_type ?? "gas",
                      annual_consumption: draft.heating?.annual_consumption ?? null,
                      annual_spend_eur: draft.heating?.annual_spend_eur ?? null,
                      building: {
                        floor_area_m2: Number.isFinite(n) ? n : 0,
                        insulation_class: draft.heating?.building?.insulation_class ?? "medium",
                      },
                    });
                  }}
                  placeholder="120"
                />
                <span className="pointer-events-none absolute inset-y-0 right-4 grid place-items-center text-sm text-muted-foreground">
                  m²
                </span>
              </div>
            </div>
            <div className="space-y-2">
              <Label className="text-sm text-muted-foreground">Insulation class</Label>
              <Select
                value={draft.heating?.building?.insulation_class ?? "medium"}
                onValueChange={(v) =>
                  setField("heating", {
                    fuel_type: draft.heating?.fuel_type ?? "gas",
                    annual_consumption: draft.heating?.annual_consumption ?? null,
                    annual_spend_eur: draft.heating?.annual_spend_eur ?? null,
                    building: {
                      floor_area_m2: draft.heating?.building?.floor_area_m2 ?? 120,
                      insulation_class: v,
                    },
                  })
                }
              >
                <SelectTrigger className="h-12">
                  <SelectValue placeholder="Select insulation class" />
                </SelectTrigger>
                <SelectContent>
                  {INSULATION_CLASSES.map((i) => (
                    <SelectItem key={i.value} value={i.value}>
                      {i.label}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
              <p className="text-[10px] text-muted-foreground">Affects heating demand calculations</p>
            </div>
            <div className="grid grid-cols-2 gap-3">
              <div className="space-y-2">
                <Label className="text-sm text-muted-foreground">Annual consumption</Label>
                <div className="relative">
                  <Input
                    inputMode="numeric"
                    className="h-12 pr-12"
                    type="number"
                    value={draft.heating?.annual_consumption ?? ""}
                    onChange={(e) => {
                      const n = Number(e.target.value);
                      setField("heating", {
                        fuel_type: draft.heating?.fuel_type ?? "gas",
                        annual_consumption: Number.isFinite(n) ? n : null,
                        annual_spend_eur: draft.heating?.annual_spend_eur ?? null,
                        building: draft.heating?.building ?? {
                          floor_area_m2: 120,
                          insulation_class: "medium",
                        },
                      });
                    }}
                    placeholder="20000"
                  />
                  <span className="pointer-events-none absolute inset-y-0 right-4 grid place-items-center text-xs text-muted-foreground">
                    kWh
                  </span>
                </div>
              </div>
              <div className="space-y-2">
                <Label className="text-sm text-muted-foreground">Annual spend</Label>
                <div className="relative">
                  <Input
                    inputMode="decimal"
                    className="h-12 pr-8"
                    type="number"
                    step="0.01"
                    value={draft.heating?.annual_spend_eur ?? ""}
                    onChange={(e) => {
                      const n = Number(e.target.value);
                      setField("heating", {
                        fuel_type: draft.heating?.fuel_type ?? "gas",
                        annual_consumption: draft.heating?.annual_consumption ?? null,
                        annual_spend_eur: Number.isFinite(n) ? n : null,
                        building: draft.heating?.building ?? {
                          floor_area_m2: 120,
                          insulation_class: "medium",
                        },
                      });
                    }}
                    placeholder="2000"
                  />
                  <span className="pointer-events-none absolute inset-y-0 right-3 grid place-items-center text-xs text-muted-foreground">
                    €
                  </span>
                </div>
              </div>
            </div>
          </div>
        </Field>
      );
    case "mobility":
      return (
        <Field title="Do you own a vehicle?" subtitle="We'll factor in fuel savings from charging at home.">
          <div className="space-y-4">
            <div className="space-y-2">
              <Label className="text-sm text-muted-foreground">Vehicle type</Label>
              <Select
                value={draft.mobility?.vehicle_type}
                onValueChange={(v) =>
              setField("mobility", {
                vehicle_type: v,
                annual_mileage_km: draft.mobility?.annual_mileage_km ?? null,
                fuel_consumption_l_per_100km: draft.mobility?.fuel_consumption_l_per_100km ?? null,
                annual_fuel_spend_eur: draft.mobility?.annual_fuel_spend_eur ?? null,
              })
            }
              >
                <SelectTrigger className="h-12">
                  <SelectValue placeholder="Select vehicle type" />
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
            <div className="space-y-2">
              <Label className="text-sm text-muted-foreground">Annual mileage</Label>
              <div className="relative">
                <Input
                  inputMode="numeric"
                  className="h-12 pr-12"
                  type="number"
                  value={draft.mobility?.annual_mileage_km ?? ""}
                  onChange={(e) => {
                    const n = Number(e.target.value);
                    setField("mobility", {
                      vehicle_type: draft.mobility?.vehicle_type ?? "gas",
                      annual_mileage_km: Number.isFinite(n) ? n : 0,
                      fuel_consumption_l_per_100km: draft.mobility?.fuel_consumption_l_per_100km ?? null,
                      annual_fuel_spend_eur: draft.mobility?.annual_fuel_spend_eur ?? null,
                    });
                  }}
                  placeholder="15000"
                />
                <span className="pointer-events-none absolute inset-y-0 right-4 grid place-items-center text-sm text-muted-foreground">
                  km
                </span>
              </div>
            </div>
            <div className="grid grid-cols-2 gap-3">
              <div className="space-y-2">
                <Label className="text-sm text-muted-foreground">Fuel consumption</Label>
                <div className="relative">
                  <Input
                    inputMode="decimal"
                    className="h-12 pr-12"
                    type="number"
                    step="0.1"
                    value={draft.mobility?.fuel_consumption_l_per_100km ?? ""}
                    onChange={(e) => {
                      const n = Number(e.target.value);
                      setField("mobility", {
                        vehicle_type: draft.mobility?.vehicle_type ?? "gas",
                        annual_mileage_km: draft.mobility?.annual_mileage_km ?? null,
                        fuel_consumption_l_per_100km: Number.isFinite(n) ? n : null,
                        annual_fuel_spend_eur: draft.mobility?.annual_fuel_spend_eur ?? null,
                      });
                    }}
                    placeholder="7"
                  />
                  <span className="pointer-events-none absolute inset-y-0 right-4 grid place-items-center text-xs text-muted-foreground">
                    L/100km
                  </span>
                </div>
              </div>
              <div className="space-y-2">
                <Label className="text-sm text-muted-foreground">Annual fuel spend</Label>
                <div className="relative">
                  <Input
                    inputMode="decimal"
                    className="h-12 pr-8"
                    type="number"
                    step="0.01"
                    value={draft.mobility?.annual_fuel_spend_eur ?? ""}
                    onChange={(e) => {
                      const n = Number(e.target.value);
                      setField("mobility", {
                        vehicle_type: draft.mobility?.vehicle_type ?? "gas",
                        annual_mileage_km: draft.mobility?.annual_mileage_km ?? null,
                        fuel_consumption_l_per_100km: draft.mobility?.fuel_consumption_l_per_100km ?? null,
                        annual_fuel_spend_eur: Number.isFinite(n) ? n : null,
                      });
                    }}
                    placeholder="1500"
                  />
                  <span className="pointer-events-none absolute inset-y-0 right-3 grid place-items-center text-xs text-muted-foreground">
                    €
                  </span>
                </div>
              </div>
            </div>
          </div>
        </Field>
      );
    case "upgrades":
      return (
        <Field title="Which upgrades are you considering?" subtitle="Select all that apply.">
          <div className="space-y-3">
            <div className="flex items-center justify-between rounded-2xl border border-border bg-card p-4">
              <span className="text-base font-medium">Solar panels (PV)</span>
              <Switch
                checked={!!draft.upgrade_candidates?.solar_pv}
                onCheckedChange={(v) =>
                  setField("upgrade_candidates", {
                    solar_pv: v,
                    battery: draft.upgrade_candidates?.battery ?? false,
                    heat_pump: draft.upgrade_candidates?.heat_pump ?? false,
                    ev_charger: draft.upgrade_candidates?.ev_charger ?? false,
                    solar_pv_kwp: draft.upgrade_candidates?.solar_pv_kwp ?? null,
                    battery_kwh: draft.upgrade_candidates?.battery_kwh ?? null,
                    heat_pump_kw: draft.upgrade_candidates?.heat_pump_kw ?? null,
                  })
                }
              />
            </div>
            <div className="flex items-center justify-between rounded-2xl border border-border bg-card p-4">
              <span className="text-base font-medium">Battery storage</span>
              <Switch
                checked={!!draft.upgrade_candidates?.battery}
                onCheckedChange={(v) =>
                  setField("upgrade_candidates", {
                    solar_pv: draft.upgrade_candidates?.solar_pv ?? true,
                    battery: v,
                    heat_pump: draft.upgrade_candidates?.heat_pump ?? false,
                    ev_charger: draft.upgrade_candidates?.ev_charger ?? false,
                    solar_pv_kwp: draft.upgrade_candidates?.solar_pv_kwp ?? null,
                    battery_kwh: draft.upgrade_candidates?.battery_kwh ?? null,
                    heat_pump_kw: draft.upgrade_candidates?.heat_pump_kw ?? null,
                  })
                }
              />
            </div>
            <div className="flex items-center justify-between rounded-2xl border border-border bg-card p-4">
              <span className="text-base font-medium">Heat pump</span>
              <Switch
                checked={!!draft.upgrade_candidates?.heat_pump}
                onCheckedChange={(v) =>
                  setField("upgrade_candidates", {
                    solar_pv: draft.upgrade_candidates?.solar_pv ?? true,
                    battery: draft.upgrade_candidates?.battery ?? false,
                    heat_pump: v,
                    ev_charger: draft.upgrade_candidates?.ev_charger ?? false,
                    solar_pv_kwp: draft.upgrade_candidates?.solar_pv_kwp ?? null,
                    battery_kwh: draft.upgrade_candidates?.battery_kwh ?? null,
                    heat_pump_kw: draft.upgrade_candidates?.heat_pump_kw ?? null,
                  })
                }
              />
            </div>
            <div className="flex items-center justify-between rounded-2xl border border-border bg-card p-4">
              <span className="text-base font-medium">EV charger</span>
              <Switch
                checked={!!draft.upgrade_candidates?.ev_charger}
                onCheckedChange={(v) =>
                  setField("upgrade_candidates", {
                    solar_pv: draft.upgrade_candidates?.solar_pv ?? true,
                    battery: draft.upgrade_candidates?.battery ?? false,
                    heat_pump: draft.upgrade_candidates?.heat_pump ?? false,
                    ev_charger: v,
                    solar_pv_kwp: draft.upgrade_candidates?.solar_pv_kwp ?? null,
                    battery_kwh: draft.upgrade_candidates?.battery_kwh ?? null,
                    heat_pump_kw: draft.upgrade_candidates?.heat_pump_kw ?? null,
                  })
                }
              />
            </div>
            <div className="space-y-3 pt-2">
              <p className="text-xs text-muted-foreground">Optional size overrides (leave blank for auto-sizing)</p>
              <div className="grid grid-cols-3 gap-3">
                <div className="space-y-2">
                  <Label className="text-xs text-muted-foreground">Solar (kWp)</Label>
                  <Input
                    inputMode="decimal"
                    className="h-10"
                    type="number"
                    step="0.1"
                    value={draft.upgrade_candidates?.solar_pv_kwp ?? ""}
                    onChange={(e) => {
                      const n = Number(e.target.value);
                      setField("upgrade_candidates", {
                        solar_pv: draft.upgrade_candidates?.solar_pv ?? true,
                        battery: draft.upgrade_candidates?.battery ?? false,
                        heat_pump: draft.upgrade_candidates?.heat_pump ?? false,
                        ev_charger: draft.upgrade_candidates?.ev_charger ?? false,
                        solar_pv_kwp: Number.isFinite(n) ? n : null,
                        battery_kwh: draft.upgrade_candidates?.battery_kwh ?? null,
                        heat_pump_kw: draft.upgrade_candidates?.heat_pump_kw ?? null,
                      });
                    }}
                    placeholder="Auto"
                  />
                </div>
                <div className="space-y-2">
                  <Label className="text-xs text-muted-foreground">Battery (kWh)</Label>
                  <Input
                    inputMode="decimal"
                    className="h-10"
                    type="number"
                    step="0.1"
                    value={draft.upgrade_candidates?.battery_kwh ?? ""}
                    onChange={(e) => {
                      const n = Number(e.target.value);
                      setField("upgrade_candidates", {
                        solar_pv: draft.upgrade_candidates?.solar_pv ?? true,
                        battery: draft.upgrade_candidates?.battery ?? false,
                        heat_pump: draft.upgrade_candidates?.heat_pump ?? false,
                        ev_charger: draft.upgrade_candidates?.ev_charger ?? false,
                        solar_pv_kwp: draft.upgrade_candidates?.solar_pv_kwp ?? null,
                        battery_kwh: Number.isFinite(n) ? n : null,
                        heat_pump_kw: draft.upgrade_candidates?.heat_pump_kw ?? null,
                      });
                    }}
                    placeholder="Auto"
                  />
                </div>
                <div className="space-y-2">
                  <Label className="text-xs text-muted-foreground">Heat pump (kW)</Label>
                  <Input
                    inputMode="decimal"
                    className="h-10"
                    type="number"
                    step="0.1"
                    value={draft.upgrade_candidates?.heat_pump_kw ?? ""}
                    onChange={(e) => {
                      const n = Number(e.target.value);
                      setField("upgrade_candidates", {
                        solar_pv: draft.upgrade_candidates?.solar_pv ?? true,
                        battery: draft.upgrade_candidates?.battery ?? false,
                        heat_pump: draft.upgrade_candidates?.heat_pump ?? false,
                        ev_charger: draft.upgrade_candidates?.ev_charger ?? false,
                        solar_pv_kwp: draft.upgrade_candidates?.solar_pv_kwp ?? null,
                        battery_kwh: draft.upgrade_candidates?.battery_kwh ?? null,
                        heat_pump_kw: Number.isFinite(n) ? n : null,
                      });
                    }}
                    placeholder="Auto"
                  />
                </div>
              </div>
            </div>
          </div>
        </Field>
      );
    case "financing":
      return <FinancingTermStep />;
    case "horizon":
      return <ForecastHorizonStep />;
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

function FinancingTermStep() {
  const { draft, setField } = useAssessmentStore();
  const years = draft.financing?.loan_term_years ?? 7;

  const setYears = (y: number) =>
    setField("financing", {
      loan_term_years: Math.max(1, Math.min(30, y)),
      loan_rate_pct: draft.financing?.loan_rate_pct ?? 5.5,
      known_subsidy_eur: draft.financing?.known_subsidy_eur ?? 0,
    });

  return (
    <Field
      title="Preferred financing term"
      subtitle="Longer terms mean lower monthly payments. Shorter terms mean less total interest."
    >
      <div className="space-y-6">
        <div className="rounded-2xl border border-border bg-card p-4">
          <div className="flex items-baseline justify-between">
            <span className="text-sm text-muted-foreground">Term</span>
            <span className="text-lg font-semibold text-primary">
              {years} year{years === 1 ? "" : "s"}
            </span>
          </div>
          <Slider
            className="mt-4"
            min={1}
            max={30}
            step={1}
            value={[years]}
            onValueChange={(v) => setYears(v[0] ?? 7)}
          />
          <div className="mt-2 flex justify-between text-xs text-muted-foreground">
            <span>1 year</span>
            <span>30 years</span>
          </div>
        </div>
        <div className="grid grid-cols-2 gap-3">
          <div className="space-y-2">
            <Label className="text-sm text-muted-foreground">Loan rate (%)</Label>
            <div className="relative">
              <Input
                inputMode="decimal"
                className="h-12 pr-8"
                type="number"
                step="0.1"
                value={draft.financing?.loan_rate_pct ?? ""}
                onChange={(e) => {
                  const n = Number(e.target.value);
                  setField("financing", {
                    loan_term_years: draft.financing?.loan_term_years ?? 7,
                    loan_rate_pct: Number.isFinite(n) ? n : 5.5,
                    known_subsidy_eur: draft.financing?.known_subsidy_eur ?? 0,
                  });
                }}
                placeholder="5.5"
              />
              <span className="pointer-events-none absolute inset-y-0 right-4 grid place-items-center text-sm text-muted-foreground">
                %
              </span>
            </div>
            <p className="text-[10px] text-muted-foreground">Annual interest rate for financing</p>
          </div>
          <div className="space-y-2">
            <Label className="text-sm text-muted-foreground">Known subsidy (€)</Label>
            <div className="relative">
              <Input
                inputMode="decimal"
                className="h-12 pr-8"
                type="number"
                step="0.01"
                value={draft.financing?.known_subsidy_eur ?? ""}
                onChange={(e) => {
                  const n = Number(e.target.value);
                  setField("financing", {
                    loan_term_years: draft.financing?.loan_term_years ?? 7,
                    loan_rate_pct: draft.financing?.loan_rate_pct ?? 5.5,
                    known_subsidy_eur: Number.isFinite(n) ? n : 0,
                  });
                }}
                placeholder="0"
              />
              <span className="pointer-events-none absolute inset-y-0 right-4 grid place-items-center text-sm text-muted-foreground">
                €
              </span>
            </div>
          </div>
        </div>
      </div>
    </Field>
  );
}

function ForecastHorizonStep() {
  const { draft, setField } = useAssessmentStore();
  const shortTerm = draft.forecast_horizon?.short_term_months ?? 12;
  const longTerm = draft.forecast_horizon?.long_term_years ?? 20;

  return (
    <Field
      title="Forecast horizon"
      subtitle="Choose the time periods for your savings forecast."
    >
      <div className="space-y-6">
        <div className="rounded-2xl border border-border bg-card p-4">
          <div className="flex items-baseline justify-between">
            <span className="text-sm text-muted-foreground">Short-term (months)</span>
            <span className="text-lg font-semibold text-primary">
              {shortTerm} mo
            </span>
          </div>
          <Slider
            className="mt-4"
            min={1}
            max={60}
            step={1}
            value={[shortTerm]}
            onValueChange={(v) =>
              setField("forecast_horizon", {
                short_term_months: v[0] ?? 12,
                long_term_years: longTerm,
              })
            }
          />
          <div className="mt-2 flex justify-between text-xs text-muted-foreground">
            <span>1 mo</span>
            <span>60 mo</span>
          </div>
        </div>
        <div className="rounded-2xl border border-border bg-card p-4">
          <div className="flex items-baseline justify-between">
            <span className="text-sm text-muted-foreground">Long-term (years)</span>
            <span className="text-lg font-semibold text-primary">
              {longTerm} yr
            </span>
          </div>
          <Slider
            className="mt-4"
            min={1}
            max={30}
            step={1}
            value={[longTerm]}
            onValueChange={(v) =>
              setField("forecast_horizon", {
                short_term_months: shortTerm,
                long_term_years: v[0] ?? 20,
              })
            }
          />
          <div className="mt-2 flex justify-between text-xs text-muted-foreground">
            <span>1 yr</span>
            <span>30 yr</span>
          </div>
        </div>
      </div>
    </Field>
  );
}
