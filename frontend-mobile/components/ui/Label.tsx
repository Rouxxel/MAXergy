import * as React from "react";
import { Text } from "react-native";
import { cn } from "@/lib/utils";

export interface LabelProps extends React.ComponentPropsWithoutRef<typeof Text> {
  children?: React.ReactNode;
}

const Label = React.forwardRef<React.ElementRef<typeof Text>, LabelProps>(
  ({ className, children, ...props }, ref) => {
    return (
      <Text
        ref={ref}
        className={cn(
          "text-sm font-semibold text-foreground mb-1.5",
          className
        )}
        {...props}
      >
        {children}
      </Text>
    );
  }
);

Label.displayName = "Label";

export { Label };
