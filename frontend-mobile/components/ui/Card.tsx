import * as React from "react";
import { View, Text } from "react-native";
import { cn } from "@/lib/utils";

export const Card = React.forwardRef<
  React.ElementRef<typeof View>,
  React.ComponentPropsWithoutRef<typeof View>
>(({ className, ...props }, ref) => (
  <View
    ref={ref}
    className={cn(
      "rounded-xl border border-border bg-card shadow-sm p-5 mb-4",
      className
    )}
    {...props}
  />
));
Card.displayName = "Card";

export const CardHeader = React.forwardRef<
  React.ElementRef<typeof View>,
  React.ComponentPropsWithoutRef<typeof View>
>(({ className, ...props }, ref) => (
  <View
    ref={ref}
    className={cn("flex flex-col space-y-1.5 pb-4", className)}
    {...props}
  />
));
CardHeader.displayName = "CardHeader";

export const CardTitle = React.forwardRef<
  React.ElementRef<typeof Text>,
  React.ComponentPropsWithoutRef<typeof Text>
>(({ className, children, ...props }, ref) => (
  <Text
    ref={ref}
    className={cn(
      "text-xl font-bold text-card-foreground leading-none tracking-tight",
      className
    )}
    {...props}
  >
    {children}
  </Text>
));
CardTitle.displayName = "CardTitle";

export const CardDescription = React.forwardRef<
  React.ElementRef<typeof Text>,
  React.ComponentPropsWithoutRef<typeof Text>
>(({ className, children, ...props }, ref) => (
  <Text
    ref={ref}
    className={cn("text-sm text-muted-foreground mt-1", className)}
    {...props}
  >
    {children}
  </Text>
));
CardDescription.displayName = "CardDescription";

export const CardContent = React.forwardRef<
  React.ElementRef<typeof View>,
  React.ComponentPropsWithoutRef<typeof View>
>(({ className, ...props }, ref) => (
  <View ref={ref} className={cn("pt-0", className)} {...props} />
));
CardContent.displayName = "CardContent";

export const CardFooter = React.forwardRef<
  React.ElementRef<typeof View>,
  React.ComponentPropsWithoutRef<typeof View>
>(({ className, ...props }, ref) => (
  <View
    ref={ref}
    className={cn("flex-row items-center pt-4 border-t border-border mt-4", className)}
    {...props}
  />
));
CardFooter.displayName = "CardFooter";
