import * as React from "react";
import { Image, type ImageStyle } from "react-native";
import { cn } from "@/lib/utils";

type LogoSize = 64 | 128 | 512;

interface LogoProps {
  size?: LogoSize;
  className?: string;
  style?: ImageStyle;
}

const logoMap = {
  64: require("../assets/logo_64.png"),
  128: require("../assets/logo_128.png"),
  512: require("../assets/logo_512.png"),
};

const sizeMap = {
  64: "w-16 h-16",
  128: "w-32 h-32",
  512: "w-64 h-64",
};

export function Logo({ size = 64, className, style }: LogoProps) {
  const logoSrc = logoMap[size];
  const sizeClass = sizeMap[size];

  return (
    <Image
      source={logoSrc}
      className={cn(sizeClass, className)}
      style={style}
      resizeMode="contain"
    />
  );
}
