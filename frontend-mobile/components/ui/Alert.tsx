import * as React from "react";
import { View, Text } from "react-native";
import { cva, type VariantProps } from "class-variance-authority";
import { cn } from "@/lib/utils";

const alertVariants = cva(
  "relative w-full rounded-lg border p-4 mb-4",
  {
    variants: {
      variant: {
        default: "bg-background text-foreground border-border",
        destructive: "border-destructive/50 bg-destructive/10 border-destructive",
      },
    },
    defaultVariants: {
      variant: "default",
    },
  }
);

const AlertContext = React.createContext<{ variant?: string }>({});

export const Alert = React.forwardRef<
  React.ElementRef<typeof View>,
  React.ComponentPropsWithoutRef<typeof View> & VariantProps<typeof alertVariants>
>(({ className, variant = "default", children, ...props }, ref) => (
  <AlertContext.Provider value={{ variant: variant ?? undefined }}>
    <View
      ref={ref}
      className={cn(alertVariants({ variant }), className)}
      {...props}
    >
      {children}
    </View>
  </AlertContext.Provider>
));
Alert.displayName = "Alert";

export const AlertTitle = React.forwardRef<
  React.ElementRef<typeof Text>,
  React.ComponentPropsWithoutRef<typeof Text>
>(({ className, children, ...props }, ref) => {
  const { variant } = React.useContext(AlertContext);
  return (
    <Text
      ref={ref}
      className={cn(
        "font-bold leading-none tracking-tight mb-1 text-base",
        variant === "destructive" ? "text-destructive" : "text-foreground",
        className
      )}
      {...props}
    >
      {children}
    </Text>
  );
});
AlertTitle.displayName = "AlertTitle";

export const AlertDescription = React.forwardRef<
  React.ElementRef<typeof Text>,
  React.ComponentPropsWithoutRef<typeof Text>
>(({ className, children, ...props }, ref) => {
  const { variant } = React.useContext(AlertContext);
  return (
    <Text
      ref={ref}
      className={cn(
        "text-sm leading-relaxed",
        variant === "destructive" ? "text-destructive/90" : "text-muted-foreground",
        className
      )}
      {...props}
    >
      {children}
    </Text>
  );
});
AlertDescription.displayName = "AlertDescription";
