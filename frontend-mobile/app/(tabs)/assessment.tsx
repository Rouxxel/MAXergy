import React, { useState } from "react";
import { ScrollView, View, Text, TextInput } from "react-native";
import { useRouter } from "expo-router";
import { useMutation } from "@tanstack/react-query";
import { ArrowLeft, ArrowRight } from "lucide-react-native";
import { z } from "zod";

import { Header } from "@/components/header";
import { ProgressSteps } from "@/components/progress-steps";
import { Button } from "@/components/ui/Button";
import { Input } from "@/components/ui/Input";
import { Label } from "@/components/ui/Label";
import { Switch } from "@/components/ui/Switch";
import { Slider } from "@/components/ui/Slider";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/Select";
import {
  DEFAULT_ELECTRICITY,
  DEFAULT_ROOF,
  ENGINE_DEFAULTS,
  useAssessmentStore,
} from "@/stores/assessmentStore";
import { useUiStore } from "@/stores/uiStore";
import {
  StepCountrySchema,
  StepPostcodeSchema,
  StepOccupantsSchema,
  StepElectricitySchema,
  StepRoofSchema,
  StepHeatingSchema,
  StepMobilitySchema,
  StepUpgradesSchema,
  StepFinancingSchema,
  StepHorizonSchema,
} from "@/services/validation";
import { postAssessment, postLocationEnrich } from "@/services/endpoints";

// The engine models German households only (more countries coming soon).
const COUNTRIES = [{ code: "DE", name: "Germany" }];

// The engine models gas and oil heating (other systems coming soon).
const HEATING_TYPES = [
  { value: "gas", label: "Gas" },
  { value: "oil", label: "Oil" },
];

// Backend vehicle types (energy_model SUPPORTED_VEHICLE_TYPES).
const VEHICLE_TYPES = [
  { value: "petrol", label: "Petrol" },
  { value: "diesel", label: "Diesel" },
  { value: "hybrid", label: "Hybrid" },
  { value: "phev", label: "Plug-in hybrid" },
  { value: "electric", label: "Electric (EV)" },
];

const TARIFF_TYPES = [
  { value: "fixed", label: "Fixed price" },
  { value: "dynamic", label: "Dynamic (hourly)" },
  { value: "ht_nt", label: "Day/night (HT/NT)" },
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

export default function Onboarding() {
  const router = useRouter();
  const { draft, setField, step, setStep, setSubmittedId, applyEnrichment, enrichedPostcode } =
    useAssessmentStore();
  const { setError: setGlobalError } = useUiStore();

  // Roof + site PV yield pre-fill via the MCP (POST /location/enrich). Optional: on 503 or any
  // error the user's own roof inputs are kept and the engine uses its regional yield table.
  const enrichLocation = useMutation({
    mutationFn: (postcode: string) => postLocationEnrich({ postcode, country: "DE" }),
    onSuccess: (result, postcode) => applyEnrichment(postcode, result),
  });

  const submitAssessment = useMutation({
    mutationFn: postAssessment,
    onSuccess: (data) => {
      setSubmittedId(data.assessment_id);
      router.push("/loading");
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
      const stepSchemas: Record<StepId, z.ZodSchema> = {
        country: StepCountrySchema,
        postcode: StepPostcodeSchema,
        occupants: StepOccupantsSchema,
        electricity: StepElectricitySchema,
        roof: StepRoofSchema,
        heating: StepHeatingSchema,
        mobility: StepMobilitySchema,
        upgrades: StepUpgradesSchema,
        financing: StepFinancingSchema,
        horizon: StepHorizonSchema,
      };

      const schema = stepSchemas[current];
      schema.parse(draft);
      return undefined;
    } catch (e) {
      if (e instanceof z.ZodError) {
        const firstError = e.issues[0];
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
    const postcode = draft.location?.postcode?.trim();
    if (current === "postcode" && postcode && postcode !== enrichedPostcode) {
      enrichLocation.mutate(postcode);
    }
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
    <View className="flex-1 bg-background">
      <Header />
      <ScrollView className="flex-1 px-5 pt-6">
        <ProgressSteps current={safeStep} total={steps.length} />

        <View className="mt-8 min-h-[300px]">
          <StepView step={current} />
          {error ? (
            <Text className="mt-3 text-sm text-destructive">{error}</Text>
          ) : null}
        </View>

        <View className="mt-8 flex-row items-center space-x-3 pb-12">
          <Button
            variant="outline"
            onPress={onBack}
            disabled={safeStep === 0}
            className="flex-1 h-12 flex-row justify-center items-center mr-2"
          >
            <ArrowLeft size={16} className="text-muted-foreground mr-1.5" />
            <Text className="text-muted-foreground font-semibold">Back</Text>
          </Button>
          <Button
            onPress={onNext}
            className="flex-[2] h-12 bg-primary flex-row justify-center items-center"
            loading={submitAssessment.isPending}
          >
            <Text className="text-primary-foreground font-semibold">
              {safeStep === steps.length - 1 ? "See my savings" : "Continue"}
            </Text>
            <ArrowRight size={16} className="text-primary-foreground ml-1.5" />
          </Button>
        </View>
      </ScrollView>
    </View>
  );
}

function StepView({ step }: { step: StepId }) {
  const { draft, setField } = useAssessmentStore();

  switch (step) {
    case "country":
      return (
        <Field
          title="Where do you live?"
          subtitle="MAXergy currently models households in Germany; more countries are coming soon."
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
            <SelectContent title="Country">
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
            keyboardType="numeric"
            className="h-12"
            value={draft.location?.postcode ?? ""}
            onChangeText={(text) =>
              setField("location", { country: draft.location?.country ?? "DE", postcode: text.replace(/[^0-9A-Za-z\s-]/g, "") })
            }
            placeholder="e.g. 10115"
          />
        </Field>
      );
    case "occupants":
      return (
        <Field title="How many people live in your home?" subtitle="This helps estimate energy usage patterns.">
          <Input
            keyboardType="numeric"
            className="h-12"
            value={draft.household?.occupants?.toString() ?? ""}
            onChangeText={(text) => {
              const n = parseInt(text, 10);
              setField("household", {
                occupants: Number.isFinite(n) && n > 0 ? n : 1,
                electricity: draft.household?.electricity ?? DEFAULT_ELECTRICITY,
                roof: draft.household?.roof ?? DEFAULT_ROOF,
              });
            }}
            placeholder="2"
          />
        </Field>
      );
    case "electricity":
      return (
        <Field
          title="Annual electricity consumption"
          subtitle="In kWh per year (on your annual bill). Only know your monthly payment? Enter it below."
        >
          <View className="space-y-4">
            <ElectricityBillShortcut />
            <View className="relative">
              <Input
                keyboardType="numeric"
                className="h-12 pr-12"
                value={draft.household?.electricity?.annual_kwh?.toString() ?? ""}
                onChangeText={(text) => {
                  const n = Number(text);
                  setField("household", {
                    occupants: draft.household?.occupants ?? 2,
                    electricity: {
                      annual_kwh: Number.isFinite(n) ? n : 0,
                      current_tariff_type: draft.household?.electricity?.current_tariff_type ?? "fixed",
                      arbeitspreis_eur_per_kwh: draft.household?.electricity?.arbeitspreis_eur_per_kwh ?? ENGINE_DEFAULTS.arbeitspreis_eur_per_kwh,
                      grundpreis_eur_per_month: draft.household?.electricity?.grundpreis_eur_per_month ?? ENGINE_DEFAULTS.grundpreis_eur_per_month,
                      contract_end_date: draft.household?.electricity?.contract_end_date ?? null,
                    },
                    roof: draft.household?.roof ?? DEFAULT_ROOF,
                  });
                }}
                placeholder="3000"
              />
              <Text className="absolute right-4 top-3 text-sm text-muted-foreground">
                kWh
              </Text>
            </View>
            <View className="space-y-2 mt-4">
              <Label className="text-sm text-muted-foreground">Tariff type</Label>
              <Select
                value={draft.household?.electricity?.current_tariff_type ?? "fixed"}
                onValueChange={(v) =>
                  setField("household", {
                    occupants: draft.household?.occupants ?? 2,
                    electricity: {
                      annual_kwh: draft.household?.electricity?.annual_kwh ?? 3000,
                      current_tariff_type: v,
                      arbeitspreis_eur_per_kwh: draft.household?.electricity?.arbeitspreis_eur_per_kwh ?? ENGINE_DEFAULTS.arbeitspreis_eur_per_kwh,
                      grundpreis_eur_per_month: draft.household?.electricity?.grundpreis_eur_per_month ?? ENGINE_DEFAULTS.grundpreis_eur_per_month,
                      contract_end_date: draft.household?.electricity?.contract_end_date ?? null,
                    },
                    roof: draft.household?.roof ?? DEFAULT_ROOF,
                  })
                }
              >
                <SelectTrigger className="h-12">
                  <SelectValue placeholder="Select tariff type" />
                </SelectTrigger>
                <SelectContent title="Tariff type">
                  {TARIFF_TYPES.map((o) => (
                    <SelectItem key={o.value} value={o.value}>
                      {o.label}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </View>
            <View className="flex-row justify-between space-x-3 mt-4">
              <View className="flex-1 mr-2">
                <Label className="text-xs text-muted-foreground">Energy price (€/kWh)</Label>
                <View className="relative mt-1">
                  <Input
                    keyboardType="numeric"
                    className="h-12 pr-8"
                    value={draft.household?.electricity?.arbeitspreis_eur_per_kwh?.toString() ?? ""}
                    onChangeText={(text) => {
                      const n = Number(text);
                      setField("household", {
                        occupants: draft.household?.occupants ?? 2,
                        electricity: {
                          annual_kwh: draft.household?.electricity?.annual_kwh ?? 3000,
                          current_tariff_type: draft.household?.electricity?.current_tariff_type ?? "fixed",
                          arbeitspreis_eur_per_kwh: Number.isFinite(n) ? n : ENGINE_DEFAULTS.arbeitspreis_eur_per_kwh,
                          grundpreis_eur_per_month: draft.household?.electricity?.grundpreis_eur_per_month ?? ENGINE_DEFAULTS.grundpreis_eur_per_month,
                          contract_end_date: draft.household?.electricity?.contract_end_date ?? null,
                        },
                        roof: draft.household?.roof ?? DEFAULT_ROOF,
                      });
                    }}
                    placeholder={String(ENGINE_DEFAULTS.arbeitspreis_eur_per_kwh)}
                  />
                  <Text className="absolute right-3 top-3 text-xs text-muted-foreground">
                    €
                  </Text>
                </View>
              </View>
              <View className="flex-1 ml-2">
                <Label className="text-xs text-muted-foreground">Base fee (€/month)</Label>
                <View className="relative mt-1">
                  <Input
                    keyboardType="numeric"
                    className="h-12 pr-8"
                    value={draft.household?.electricity?.grundpreis_eur_per_month?.toString() ?? ""}
                    onChangeText={(text) => {
                      const n = Number(text);
                      setField("household", {
                        occupants: draft.household?.occupants ?? 2,
                        electricity: {
                          annual_kwh: draft.household?.electricity?.annual_kwh ?? 3000,
                          current_tariff_type: draft.household?.electricity?.current_tariff_type ?? "fixed",
                          arbeitspreis_eur_per_kwh: draft.household?.electricity?.arbeitspreis_eur_per_kwh ?? ENGINE_DEFAULTS.arbeitspreis_eur_per_kwh,
                          grundpreis_eur_per_month: Number.isFinite(n) ? n : ENGINE_DEFAULTS.grundpreis_eur_per_month,
                          contract_end_date: draft.household?.electricity?.contract_end_date ?? null,
                        },
                        roof: draft.household?.roof ?? DEFAULT_ROOF,
                      });
                    }}
                    placeholder="10"
                  />
                  <Text className="absolute right-3 top-3 text-xs text-muted-foreground">
                    €
                  </Text>
                </View>
              </View>
            </View>
          </View>
        </Field>
      );
    case "roof":
      return (
        <Field title="Roughly, how big is your roof?" subtitle="A rough estimate in square meters is fine.">
          <View className="space-y-4">
            <RoofAvailability />
            <RoofSourceBadges />
            <View className="relative">
              <Input
                keyboardType="numeric"
                className="h-12 pr-12"
                value={draft.household?.roof?.usable_area_m2?.toString() ?? ""}
                onChangeText={(text) => {
                  const n = Number(text);
                  setField("household", {
                    occupants: draft.household?.occupants ?? 2,
                    electricity: draft.household?.electricity ?? DEFAULT_ELECTRICITY,
                    roof: {
                      ...DEFAULT_ROOF,
                      ...draft.household?.roof,
                      available: draft.household?.roof?.available ?? true,
                      usable_area_m2: Number.isFinite(n) ? n : 0,
                      orientation: draft.household?.roof?.orientation ?? "south",
                      tilt_deg: draft.household?.roof?.tilt_deg ?? 30,
                      shading_factor: draft.household?.roof?.shading_factor ?? 0.1,
                    },
                  });
                }}
                placeholder="60"
              />
              <Text className="absolute right-4 top-3 text-sm text-muted-foreground">
                m²
              </Text>
            </View>
            <View className="space-y-2 mt-4">
              <Label className="text-sm text-muted-foreground">Roof orientation</Label>
              <Select
                value={draft.household?.roof?.orientation ?? "south"}
                onValueChange={(v) =>
                  setField("household", {
                    occupants: draft.household?.occupants ?? 2,
                    electricity: draft.household?.electricity ?? DEFAULT_ELECTRICITY,
                    roof: {
                      ...DEFAULT_ROOF,
                      ...draft.household?.roof,
                      available: draft.household?.roof?.available ?? true,
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
                <SelectContent title="Orientation">
                  {ROOF_ORIENTATIONS.map((o) => (
                    <SelectItem key={o.value} value={o.value}>
                      {o.label}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </View>
            <View className="flex-row justify-between space-x-3 mt-4">
              <View className="flex-1 mr-2">
                <Label className="text-xs text-muted-foreground">Tilt angle (degrees)</Label>
                <View className="relative mt-1">
                  <Input
                    keyboardType="numeric"
                    className="h-12 pr-8"
                    value={draft.household?.roof?.tilt_deg?.toString() ?? ""}
                    onChangeText={(text) => {
                      const n = Number(text);
                      setField("household", {
                        occupants: draft.household?.occupants ?? 2,
                        electricity: draft.household?.electricity ?? DEFAULT_ELECTRICITY,
                        roof: {
                          ...DEFAULT_ROOF,
                          ...draft.household?.roof,
                          available: draft.household?.roof?.available ?? true,
                          usable_area_m2: draft.household?.roof?.usable_area_m2 ?? 50,
                          orientation: draft.household?.roof?.orientation ?? "south",
                          tilt_deg: Number.isFinite(n) ? n : 30,
                          shading_factor: draft.household?.roof?.shading_factor ?? 0.1,
                        },
                      });
                    }}
                    placeholder="30"
                  />
                  <Text className="absolute right-3 top-3 text-xs text-muted-foreground">
                    °
                  </Text>
                </View>
              </View>
              <View className="flex-1 ml-2">
                <Label className="text-xs text-muted-foreground">Shading factor</Label>
                <View className="relative mt-1">
                  <Input
                    keyboardType="numeric"
                    className="h-12 pr-8"
                    value={draft.household?.roof?.shading_factor?.toString() ?? ""}
                    onChangeText={(text) => {
                      const n = Number(text);
                      const clamped = Math.max(0, Math.min(1, Number.isFinite(n) ? n : 0.1));
                      setField("household", {
                        occupants: draft.household?.occupants ?? 2,
                        electricity: draft.household?.electricity ?? DEFAULT_ELECTRICITY,
                        roof: {
                          ...DEFAULT_ROOF,
                          ...draft.household?.roof,
                          available: draft.household?.roof?.available ?? true,
                          usable_area_m2: draft.household?.roof?.usable_area_m2 ?? 50,
                          orientation: draft.household?.roof?.orientation ?? "south",
                          tilt_deg: draft.household?.roof?.tilt_deg ?? 30,
                          shading_factor: clamped,
                        },
                      });
                    }}
                    placeholder="0.1"
                  />
                  <Text className="absolute right-3 top-3 text-xs text-muted-foreground">
                    0-1
                  </Text>
                </View>
              </View>
            </View>
          </View>
        </Field>
      );
    case "heating":
      return (
        <Field title="How do you heat your home?">
          <View className="space-y-4">
            <View className="space-y-2">
              <Label className="text-sm text-muted-foreground">Heating type</Label>
              <Text className="text-[11px] text-muted-foreground">
                MAXergy can currently model gas and oil heating. Other systems are coming soon.
              </Text>
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
                <SelectContent title="Heating type">
                  {HEATING_TYPES.map((h) => (
                    <SelectItem key={h.value} value={h.value}>
                      {h.label}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </View>
            <View className="space-y-2 mt-4">
              <Label className="text-sm text-muted-foreground">Building floor area</Label>
              <View className="relative">
                <Input
                  keyboardType="numeric"
                  className="h-12 pr-12"
                  value={draft.heating?.building?.floor_area_m2?.toString() ?? ""}
                  onChangeText={(text) => {
                    const n = Number(text);
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
                <Text className="absolute right-4 top-3 text-sm text-muted-foreground">
                  m²
                </Text>
              </View>
            </View>
            <View className="space-y-2 mt-4">
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
                <SelectContent title="Insulation class">
                  {INSULATION_CLASSES.map((i) => (
                    <SelectItem key={i.value} value={i.value}>
                      {i.label}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </View>
            <View className="flex-row justify-between space-x-3 mt-4">
              <View className="flex-1 mr-2">
                <Label className="text-xs text-muted-foreground">Annual consumption</Label>
                <View className="relative mt-1">
                  <Input
                    keyboardType="numeric"
                    className="h-12 pr-12"
                    value={draft.heating?.annual_consumption?.toString() ?? ""}
                    onChangeText={(text) => {
                      const n = Number(text);
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
                  <Text className="absolute right-4 top-3 text-xs text-muted-foreground">
                    kWh
                  </Text>
                </View>
              </View>
              <View className="flex-1 ml-2">
                <Label className="text-xs text-muted-foreground">Annual spend</Label>
                <View className="relative mt-1">
                  <Input
                    keyboardType="numeric"
                    className="h-12 pr-8"
                    value={draft.heating?.annual_spend_eur?.toString() ?? ""}
                    onChangeText={(text) => {
                      const n = Number(text);
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
                  <Text className="absolute right-3 top-3 text-xs text-muted-foreground">
                    €
                  </Text>
                </View>
              </View>
            </View>
          </View>
        </Field>
      );
    case "mobility":
      return (
        <Field title="Do you own a vehicle?" subtitle="We'll factor in fuel savings from charging at home.">
          <View className="space-y-4">
            <View className="space-y-2">
              <Label className="text-sm text-muted-foreground">How many vehicles do you have?</Label>
              <Select
                value={draft.mobility?.vehicle_count?.toString() ?? "0"}
                onValueChange={(v) => {
                  const count = Number(v);
                  const vehicles = Array.from({ length: count }, () => ({
                    vehicle_type: "petrol",
                    annual_mileage_km: null,
                    fuel_consumption_l_per_100km: null,
                    annual_fuel_spend_eur: null,
                  }));
                  setField("mobility", {
                    vehicle_count: count,
                    vehicles,
                  });
                }}
              >
                <SelectTrigger className="h-12">
                  <SelectValue placeholder="Select number of vehicles" />
                </SelectTrigger>
                <SelectContent title="Number of vehicles">
                  <SelectItem value="0">None</SelectItem>
                  <SelectItem value="1">1 vehicle</SelectItem>
                  <SelectItem value="2">2 vehicles</SelectItem>
                  <SelectItem value="3">3 vehicles</SelectItem>
                  <SelectItem value="4">4 vehicles</SelectItem>
                  <SelectItem value="5">5+ vehicles</SelectItem>
                </SelectContent>
              </Select>
            </View>
            {(draft.mobility?.vehicle_count ?? 0) > 0 && (
              <View className="space-y-6 mt-4">
                <Text className="text-[11px] text-muted-foreground">
                  Combustion cars are combined into one mobility profile (total km and fuel spend).
                  Electric cars are already charged from your household electricity, so they are not
                  counted twice.
                </Text>
                {Array.from({ length: draft.mobility?.vehicle_count ?? 0 }).map((_, index) => (
                  <View key={index} className="space-y-4 rounded-lg border border-border p-4 bg-muted/10">
                    <Text className="text-sm font-bold text-foreground">Vehicle {index + 1}</Text>
                    <View className="space-y-2">
                      <Label className="text-sm text-muted-foreground">Vehicle type</Label>
                      <Select
                        value={draft.mobility?.vehicles?.[index]?.vehicle_type ?? "petrol"}
                        onValueChange={(v) => {
                          const newVehicles = [...(draft.mobility?.vehicles ?? [])];
                          newVehicles[index] = {
                            ...newVehicles[index],
                            vehicle_type: v,
                          };
                          setField("mobility", {
                            vehicle_count: draft.mobility?.vehicle_count ?? 0,
                            vehicles: newVehicles,
                          });
                        }}
                      >
                        <SelectTrigger className="h-12">
                          <SelectValue placeholder="Select vehicle type" />
                        </SelectTrigger>
                        <SelectContent title="Vehicle type">
                          {VEHICLE_TYPES.map((t) => (
                            <SelectItem key={t.value} value={t.value}>
                              {t.label}
                            </SelectItem>
                          ))}
                        </SelectContent>
                      </Select>
                    </View>
                    <View className="space-y-2 mt-3">
                      <Label className="text-sm text-muted-foreground">Approximate annual mileage (required)</Label>
                      <View className="relative">
                        <Input
                          keyboardType="numeric"
                          className="h-12 pr-12"
                          value={draft.mobility?.vehicles?.[index]?.annual_mileage_km?.toString() ?? ""}
                          onChangeText={(text) => {
                            const n = Number(text);
                            const newVehicles = [...(draft.mobility?.vehicles ?? [])];
                            newVehicles[index] = {
                              ...newVehicles[index],
                              annual_mileage_km: text === "" || !Number.isFinite(n) ? null : n,
                            };
                            setField("mobility", {
                              vehicle_count: draft.mobility?.vehicle_count ?? 0,
                              vehicles: newVehicles,
                            });
                          }}
                          placeholder="15000"
                        />
                        <Text className="absolute right-4 top-3 text-sm text-muted-foreground">
                          km
                        </Text>
                      </View>
                    </View>
                    <View className="flex-row justify-between space-x-3 mt-3">
                      <View className="flex-1 mr-2">
                        <Label className="text-xs text-muted-foreground">Fuel consumption</Label>
                        <View className="relative mt-1">
                          <Input
                            keyboardType="numeric"
                            className="h-12 pr-12"
                            value={draft.mobility?.vehicles?.[index]?.fuel_consumption_l_per_100km?.toString() ?? ""}
                            onChangeText={(text) => {
                              const n = Number(text);
                              const newVehicles = [...(draft.mobility?.vehicles ?? [])];
                              newVehicles[index] = {
                                ...newVehicles[index],
                                fuel_consumption_l_per_100km: Number.isFinite(n) ? n : null,
                              };
                              setField("mobility", {
                                vehicle_count: draft.mobility?.vehicle_count ?? 0,
                                vehicles: newVehicles,
                              });
                            }}
                            placeholder="7"
                          />
                          <Text className="absolute right-2 top-3 text-[10px] text-muted-foreground">
                            L/100
                          </Text>
                        </View>
                      </View>
                      <View className="flex-1 ml-2">
                        <Label className="text-xs text-muted-foreground">Annual fuel spend</Label>
                        <View className="relative mt-1">
                          <Input
                            keyboardType="numeric"
                            className="h-12 pr-8"
                            value={draft.mobility?.vehicles?.[index]?.annual_fuel_spend_eur?.toString() ?? ""}
                            onChangeText={(text) => {
                              const n = Number(text);
                              const newVehicles = [...(draft.mobility?.vehicles ?? [])];
                              newVehicles[index] = {
                                ...newVehicles[index],
                                annual_fuel_spend_eur: Number.isFinite(n) ? n : null,
                              };
                              setField("mobility", {
                                vehicle_count: draft.mobility?.vehicle_count ?? 0,
                                vehicles: newVehicles,
                              });
                            }}
                            placeholder="1500"
                          />
                          <Text className="absolute right-3 top-3 text-xs text-muted-foreground">
                            €
                          </Text>
                        </View>
                      </View>
                    </View>
                  </View>
                ))}
              </View>
            )}
          </View>
        </Field>
      );
    case "upgrades":
      return (
        <Field title="Which upgrades are you considering?" subtitle="Select all that apply.">
          <View className="space-y-3">
            <View className="flex-row items-center justify-between rounded-2xl border border-border bg-card p-4 mb-2">
              <Text className="text-base font-medium text-foreground">Solar panels (PV)</Text>
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
            </View>
            <View className="flex-row items-center justify-between rounded-2xl border border-border bg-card p-4 mb-2">
              <Text className="text-base font-medium text-foreground">Battery storage</Text>
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
            </View>
            <View className="flex-row items-center justify-between rounded-2xl border border-border bg-card p-4 mb-2">
              <Text className="text-base font-medium text-foreground">Heat pump</Text>
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
            </View>
            <View className="flex-row items-center justify-between rounded-2xl border border-border bg-card p-4 mb-4">
              <Text className="text-base font-medium text-foreground">EV charger</Text>
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
            </View>
            <View className="space-y-3 pt-2">
              <Text className="text-xs text-muted-foreground font-semibold">Optional size overrides (leave blank for auto-sizing)</Text>
              <View className="flex-row justify-between space-x-2 mt-2">
                <View className="flex-1 mr-1">
                  <Label className="text-[10px] text-muted-foreground">Solar (kWp)</Label>
                  <Input
                    keyboardType="numeric"
                    className="h-10 mt-1"
                    value={draft.upgrade_candidates?.solar_pv_kwp?.toString() ?? ""}
                    onChangeText={(text) => {
                      const n = Number(text);
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
                </View>
                <View className="flex-1 mx-1">
                  <Label className="text-[10px] text-muted-foreground">Battery (kWh)</Label>
                  <Input
                    keyboardType="numeric"
                    className="h-10 mt-1"
                    value={draft.upgrade_candidates?.battery_kwh?.toString() ?? ""}
                    onChangeText={(text) => {
                      const n = Number(text);
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
                </View>
                <View className="flex-1 ml-1">
                  <Label className="text-[10px] text-muted-foreground">Heat pump (kW)</Label>
                  <Input
                    keyboardType="numeric"
                    className="h-10 mt-1"
                    value={draft.upgrade_candidates?.heat_pump_kw?.toString() ?? ""}
                    onChangeText={(text) => {
                      const n = Number(text);
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
                </View>
              </View>
            </View>
          </View>
        </Field>
      );
    case "financing":
      return <FinancingTermStep />;
    case "horizon":
      return <ForecastHorizonStep />;
  }
}

function ElectricityBillShortcut() {
  const { draft, setField } = useAssessmentStore();
  const [bill, setBill] = useState("");
  const electricity = draft.household?.electricity ?? DEFAULT_ELECTRICITY;

  // annual kWh = (monthly bill − base fee) × 12 / energy price — the same conversion the
  // MCP onboarding uses (suggest_electricity_price), with the prices entered in this step.
  const onBill = (value: string) => {
    setBill(value);
    const monthly = Number(value);
    if (!value || !Number.isFinite(monthly) || monthly <= 0) return;
    const kwh = Math.round(
      (Math.max(monthly - electricity.grundpreis_eur_per_month, 0) * 12) /
        Math.max(electricity.arbeitspreis_eur_per_kwh, 0.01),
    );
    setField("household", {
      occupants: draft.household?.occupants ?? 2,
      roof: draft.household?.roof ?? DEFAULT_ROOF,
      electricity: { ...electricity, annual_kwh: kwh },
    });
  };

  return (
    <View className="space-y-2 rounded-2xl border border-border bg-card p-3 mb-4">
      <Label className="text-sm text-muted-foreground">Monthly electricity payment (€)</Label>
      <Input keyboardType="numeric" className="h-11" value={bill} onChangeText={onBill} placeholder="e.g. 95" />
      <Text className="text-[10px] text-muted-foreground">
        Optional. Converts to kWh with the prices below: {electricity.annual_kwh.toLocaleString()} kWh/year.
      </Text>
    </View>
  );
}

function RoofAvailability() {
  const { draft, setField } = useAssessmentStore();
  const roof = { ...DEFAULT_ROOF, ...draft.household?.roof };
  return (
    <View className="space-y-2 mb-3">
      <View className="flex-row items-center justify-between rounded-2xl border border-border bg-card p-4">
        <Text className="text-base font-medium text-foreground">My roof can take solar panels</Text>
        <Switch
          checked={roof.available}
          onCheckedChange={(available) =>
            setField("household", {
              occupants: draft.household?.occupants ?? 2,
              electricity: draft.household?.electricity ?? DEFAULT_ELECTRICITY,
              roof: { ...roof, available },
            })
          }
        />
      </View>
      {!roof.available && (
        <Text className="text-[11px] text-muted-foreground">
          Without a usable roof MAXergy can't model solar-based upgrades yet. You'll still see your
          current monthly costs and forecast.
        </Text>
      )}
    </View>
  );
}

function RoofSourceBadges() {
  const enrichment = useAssessmentStore((s) => s.enrichment);
  const postcode = useAssessmentStore((s) => s.draft.location?.postcode);
  const enrichedPostcode = useAssessmentStore((s) => s.enrichedPostcode);
  if (!enrichment || enrichedPostcode !== postcode) {
    return (
      <Text className="text-[11px] text-muted-foreground mb-3">
        Estimated values — adjust them to match your roof. Solar yield uses the regional average.
      </Text>
    );
  }
  const scanned = enrichment.source.roof === "google_solar" && enrichment.roof;
  const siteYield = enrichment.source.pv_yield === "pvgis" && enrichment.specific_yield_kwh_per_kwp;
  return (
    <View className="flex-row flex-wrap gap-2 mb-3">
      <View className="rounded-full bg-primary/10 px-2.5 py-1">
        <Text className="text-[11px] font-medium text-primary">
          {scanned ? "From satellite roof scan" : "Roof estimated — please check"}
        </Text>
      </View>
      <View className="rounded-full bg-primary/10 px-2.5 py-1">
        <Text className="text-[11px] font-medium text-primary">
          {siteYield
            ? `Site solar yield ${Math.round(enrichment.specific_yield_kwh_per_kwp!)} kWh/kWp`
            : "Estimated from region"}
        </Text>
      </View>
      {enrichment.roof?.low_confidence && (
        <Text className="text-[11px] text-muted-foreground">
          The scan may have found a neighbouring building — check the size.
        </Text>
      )}
    </View>
  );
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
    <View className="space-y-4">
      <View>
        <Text className="text-2xl font-bold tracking-tight text-foreground">{title}</Text>
        {subtitle ? (
          <Text className="mt-1 text-sm text-muted-foreground leading-relaxed">{subtitle}</Text>
        ) : null}
      </View>
      <View className="mt-4">{children}</View>
    </View>
  );
}

function FinancingTermStep() {
  const { draft, setField } = useAssessmentStore();
  const years = draft.financing?.loan_term_years ?? ENGINE_DEFAULTS.loan_term_years;

  const setYears = (y: number) =>
    setField("financing", {
      loan_term_years: Math.max(1, Math.min(30, y)),
      loan_rate_pct: draft.financing?.loan_rate_pct ?? ENGINE_DEFAULTS.loan_rate_pct,
      known_subsidy_eur: draft.financing?.known_subsidy_eur ?? 0,
    });

  return (
    <Field
      title="Preferred financing term"
      subtitle="Longer terms mean lower monthly payments. Shorter terms mean less total interest."
    >
      <View className="space-y-6">
        <View className="rounded-2xl border border-border bg-card p-4">
          <View className="flex-row items-baseline justify-between">
            <Text className="text-sm text-muted-foreground">Term</Text>
            <Text className="text-lg font-semibold text-primary">
              {years} year{years === 1 ? "" : "s"}
            </Text>
          </View>
          <View className="mt-4">
            <Slider
              min={1}
              max={30}
              step={1}
              value={[years]}
              onValueChange={(v) => setYears(v[0] ?? 7)}
            />
          </View>
          <View className="mt-2 flex-row justify-between text-xs text-muted-foreground">
            <Text className="text-xs text-muted-foreground">1 year</Text>
            <Text className="text-xs text-muted-foreground">30 years</Text>
          </View>
        </View>
        <View className="flex-row justify-between space-x-3 mt-4">
          <View className="flex-1 mr-2">
            <Label className="text-sm text-muted-foreground">Loan rate (%)</Label>
            <View className="relative mt-1">
              <Input
                keyboardType="numeric"
                className="h-12 pr-8"
                value={draft.financing?.loan_rate_pct?.toString() ?? ""}
                onChangeText={(text) => {
                  const n = Number(text);
                  setField("financing", {
                    loan_term_years: draft.financing?.loan_term_years ?? ENGINE_DEFAULTS.loan_term_years,
                    loan_rate_pct: Number.isFinite(n) ? n : ENGINE_DEFAULTS.loan_rate_pct,
                    known_subsidy_eur: draft.financing?.known_subsidy_eur ?? 0,
                  });
                }}
                placeholder={String(ENGINE_DEFAULTS.loan_rate_pct)}
              />
              <Text className="absolute right-4 top-3 text-sm text-muted-foreground">
                %
              </Text>
            </View>
          </View>
          <View className="flex-1 ml-2">
            <Label className="text-sm text-muted-foreground">Known subsidy (€)</Label>
            <View className="relative mt-1">
              <Input
                keyboardType="numeric"
                className="h-12 pr-8"
                value={draft.financing?.known_subsidy_eur?.toString() ?? ""}
                onChangeText={(text) => {
                  const n = Number(text);
                  setField("financing", {
                    loan_term_years: draft.financing?.loan_term_years ?? ENGINE_DEFAULTS.loan_term_years,
                    loan_rate_pct: draft.financing?.loan_rate_pct ?? ENGINE_DEFAULTS.loan_rate_pct,
                    known_subsidy_eur: Number.isFinite(n) ? n : 0,
                  });
                }}
                placeholder="0"
              />
              <Text className="absolute right-4 top-3 text-sm text-muted-foreground">
                €
              </Text>
            </View>
          </View>
        </View>
      </View>
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
      <View className="space-y-6">
        <View className="rounded-2xl border border-border bg-card p-4 mb-4">
          <View className="flex-row items-baseline justify-between">
            <Text className="text-sm text-muted-foreground">Short-term (months)</Text>
            <Text className="text-lg font-semibold text-primary">
              {shortTerm} mo
            </Text>
          </View>
          <View className="mt-4">
            <Slider
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
          </View>
          <View className="mt-2 flex-row justify-between text-xs text-muted-foreground">
            <Text className="text-xs text-muted-foreground">1 mo</Text>
            <Text className="text-xs text-muted-foreground">60 mo</Text>
          </View>
        </View>
        <View className="rounded-2xl border border-border bg-card p-4">
          <View className="flex-row items-baseline justify-between">
            <Text className="text-sm text-muted-foreground">Long-term (years)</Text>
            <Text className="text-lg font-semibold text-primary">
              {longTerm} yr
            </Text>
          </View>
          <View className="mt-4">
            <Slider
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
          </View>
          <View className="mt-2 flex-row justify-between text-xs text-muted-foreground">
            <Text className="text-xs text-muted-foreground">1 yr</Text>
            <Text className="text-xs text-muted-foreground">30 yr</Text>
          </View>
        </View>
      </View>
    </Field>
  );
}
