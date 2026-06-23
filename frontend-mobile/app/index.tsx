import React, { useState } from "react";
import { ScrollView, View, Text } from "react-native";
import { StatusBar } from "expo-status-bar";
import { Button } from "@/components/ui/Button";
import { Input } from "@/components/ui/Input";
import { Label } from "@/components/ui/Label";
import { Switch } from "@/components/ui/Switch";
import { Slider } from "@/components/ui/Slider";
import { Alert, AlertTitle, AlertDescription } from "@/components/ui/Alert";
import {
  Card,
  CardHeader,
  CardTitle,
  CardDescription,
  CardContent,
  CardFooter,
} from "@/components/ui/Card";
import {
  Select,
  SelectTrigger,
  SelectValue,
  SelectContent,
  SelectItem,
} from "@/components/ui/Select";

export default function Index() {
  const [inputText, setInputText] = useState("");
  const [selectValue, setSelectValue] = useState("gas");
  const [switchValue, setSwitchValue] = useState(true);
  const [sliderValue, setSliderValue] = useState([30]);

  return (
    <ScrollView className="flex-1 bg-background p-4 pt-12">
      <View className="pb-16">
        <Text className="text-primary text-3xl font-extrabold text-center mb-6">
          MAXergy Showcase
        </Text>

        <Alert variant="default" className="mb-6">
          <AlertTitle>Welcome to React Native Setup</AlertTitle>
          <AlertDescription>
            All custom primitive UI components are rendered below and styled with
            NativeWind.
          </AlertDescription>
        </Alert>

        <Card>
          <CardHeader>
            <CardTitle>Button Showcase</CardTitle>
            <CardDescription>Different shapes, sizes, and states</CardDescription>
          </CardHeader>
          <CardContent className="flex-col gap-3">
            <Button variant="default">Default Button</Button>
            <Button variant="secondary">Secondary Button</Button>
            <Button variant="outline">Outline Button</Button>
            <Button variant="ghost">Ghost Button</Button>
            <Button variant="destructive">Destructive Button</Button>
            <Button variant="default" loading>
              Loading State
            </Button>
            <Button variant="default" disabled>
              Disabled State
            </Button>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Form Elements</CardTitle>
            <CardDescription>Inputs, selects, switches, and sliders</CardDescription>
          </CardHeader>
          <CardContent className="flex-col gap-4">
            <View>
              <Label>Text Input</Label>
              <Input
                placeholder="Enter some text..."
                value={inputText}
                onChangeText={setInputText}
              />
              {inputText ? (
                <Text className="text-foreground text-xs mt-1">
                  You typed: {inputText}
                </Text>
              ) : null}
            </View>

            <View>
              <Label>Select Component</Label>
              <Select value={selectValue} onValueChange={setSelectValue}>
                <SelectTrigger>
                  <SelectValue placeholder="Choose heating type" />
                </SelectTrigger>
                <SelectContent title="Heating Type">
                  <SelectItem value="gas">Gas Heating</SelectItem>
                  <SelectItem value="oil">Oil Heating</SelectItem>
                  <SelectItem value="electricity">Electric Heating</SelectItem>
                  <SelectItem value="heat_pump">Heat Pump</SelectItem>
                </SelectContent>
              </Select>
            </View>

            <View className="flex-row items-center justify-between py-2">
              <Label className="mb-0">Switch Toggle</Label>
              <Switch checked={switchValue} onCheckedChange={setSwitchValue} />
            </View>

            <View>
              <Label>Slider Value: {sliderValue[0]}</Label>
              <Slider
                value={sliderValue}
                onValueChange={setSliderValue}
                min={0}
                max={100}
                step={5}
              />
            </View>
          </CardContent>
        </Card>

        <Alert variant="destructive" className="mt-4">
          <AlertTitle>System Alert</AlertTitle>
          <AlertDescription>
            This is a destructive alert example to verify variant styling works.
          </AlertDescription>
        </Alert>
      </View>
      <StatusBar style="light" />
    </ScrollView>
  );
}
