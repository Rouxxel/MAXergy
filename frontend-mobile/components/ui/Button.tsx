import * as React from "react";
import { Pressable, Text, ActivityIndicator } from "react-native";
import { cva, type VariantProps } from "class-variance-authority";
import { cn } from "@/lib/utils";

const buttonVariants = cva(
  "flex-row items-center justify-center gap-2 rounded-md font-medium transition-colors active:opacity-90 disabled:opacity-50",
  {
    variants: {
      variant: {
        default: "bg-primary text-primary-foreground shadow-sm",
        destructive: "bg-destructive text-destructive-foreground shadow-sm",
        outline: "border border-input bg-background shadow-sm text-foreground",
        secondary: "bg-secondary text-secondary-foreground shadow-sm",
        ghost: "bg-transparent text-foreground",
        link: "bg-transparent text-primary underline",
      },
      size: {
        default: "h-11 px-4 py-2.5",
        sm: "h-9 rounded-md px-3 py-1.5 text-xs",
        lg: "h-13 rounded-md px-8 py-3.5",
        icon: "h-11 w-11",
      },
    },
    defaultVariants: {
      variant: "default",
      size: "default",
    },
  }
);

// In React Native, text colors and font sizes need to be explicitly set on Text components
const textVariants = cva("text-sm font-semibold text-center", {
  variants: {
    variant: {
      default: "text-primary-foreground",
      destructive: "text-destructive-foreground",
      outline: "text-foreground",
      secondary: "text-secondary-foreground",
      ghost: "text-foreground",
      link: "text-primary underline",
    },
    size: {
      default: "text-sm",
      sm: "text-xs",
      lg: "text-base",
      icon: "text-sm",
    },
  },
  defaultVariants: {
    variant: "default",
    size: "default",
  },
});

export interface ButtonProps
  extends Omit<React.ComponentPropsWithoutRef<typeof Pressable>, "children">,
    VariantProps<typeof buttonVariants> {
  children?: React.ReactNode;
  textClassName?: string;
  loading?: boolean;
}

const Button = React.forwardRef<React.ElementRef<typeof Pressable>, ButtonProps>(
  (
    {
      className,
      textClassName,
      variant,
      size,
      loading = false,
      disabled = false,
      children,
      ...props
    },
    ref
  ) => {
    return (
      <Pressable
        ref={ref}
        disabled={disabled || loading}
        className={cn(
          buttonVariants({ variant, size }),
          (disabled || loading) && "opacity-50",
          className
        )}
        {...props}
      >
        {loading ? (
          <ActivityIndicator
            size="small"
            color={
              variant === "default"
                ? "#111827"
                : variant === "outline" || variant === "ghost"
                ? "#B8FF5A"
                : "#ffffff"
            }
          />
        ) : typeof children === "string" ? (
          <Text
            className={cn(
              textVariants({ variant, size }),
              textClassName
            )}
          >
            {children}
          </Text>
        ) : (
          children
        )}
      </Pressable>
    );
  }
);

Button.displayName = "Button";

export { Button, buttonVariants };
