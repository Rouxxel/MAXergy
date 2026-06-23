import * as React from "react";
import { View, Text, Pressable, Modal, ScrollView, SafeAreaView } from "react-native";
import { ChevronDown, Check, X } from "lucide-react-native";
import { cn } from "@/lib/utils";

interface SelectContextType {
  value?: string;
  onValueChange?: (value: string) => void;
  open: boolean;
  setOpen: (open: boolean) => void;
  registerItem: (value: string, label: string) => void;
  items: Record<string, string>;
}

const SelectContext = React.createContext<SelectContextType | undefined>(undefined);

export function useSelect() {
  const context = React.useContext(SelectContext);
  if (!context) {
    throw new Error("Select components must be wrapped in <Select />");
  }
  return context;
}

export interface SelectProps {
  value?: string;
  onValueChange?: (value: string) => void;
  children?: React.ReactNode;
}

export function Select({ value, onValueChange, children }: SelectProps) {
  const [open, setOpen] = React.useState(false);
  const [items, setItems] = React.useState<Record<string, string>>({});

  const registerItem = React.useCallback((val: string, label: string) => {
    setItems((prev) => {
      if (prev[val] === label) return prev;
      return { ...prev, [val]: label };
    });
  }, []);

  const valueContext = React.useMemo(
    () => ({
      value,
      onValueChange,
      open,
      setOpen,
      registerItem,
      items,
    }),
    [value, onValueChange, open, registerItem, items]
  );

  return (
    <SelectContext.Provider value={valueContext}>
      {children}
    </SelectContext.Provider>
  );
}

export interface SelectTriggerProps {
  className?: string;
  children?: React.ReactNode;
}

export const SelectTrigger = React.forwardRef<
  React.ElementRef<typeof Pressable>,
  SelectTriggerProps
>(({ className, children, ...props }, ref) => {
  const { setOpen } = useSelect();
  return (
    <Pressable
      ref={ref}
      onPress={() => setOpen(true)}
      className={cn(
        "flex h-11 w-full flex-row items-center justify-between rounded-md border border-input bg-transparent px-3 py-2 text-sm shadow-sm",
        className
      )}
      {...props}
    >
      <View className="flex-1 flex-row items-center">{children}</View>
      <ChevronDown className="h-4 w-4 text-muted-foreground opacity-50 ml-2" />
    </Pressable>
  );
});
SelectTrigger.displayName = "SelectTrigger";

export interface SelectValueProps {
  placeholder?: string;
  className?: string;
}

export function SelectValue({ placeholder, className }: SelectValueProps) {
  const { value, items } = useSelect();
  const label = value !== undefined ? items[value] : undefined;

  return (
    <Text className={cn("text-base text-foreground", !label && "text-muted-foreground", className)}>
      {label || placeholder || ""}
    </Text>
  );
}

export interface SelectContentProps {
  children?: React.ReactNode;
  title?: string;
}

export function SelectContent({ children, title = "Select Option" }: SelectContentProps) {
  const { open, setOpen } = useSelect();

  return (
    <Modal
      visible={open}
      transparent
      animationType="fade"
      onRequestClose={() => setOpen(false)}
    >
      <Pressable
        onPress={() => setOpen(false)}
        className="flex-1 bg-black/60 justify-end p-4"
      >
        <Pressable
          onPress={(e) => e.stopPropagation()}
          className="bg-card border border-border rounded-xl w-full max-h-[80%] overflow-hidden shadow-2xl"
        >
          <SafeAreaView>
            <View className="flex-row items-center justify-between border-b border-border p-4">
              <Text className="text-foreground text-lg font-bold">{title}</Text>
              <Pressable onPress={() => setOpen(false)} className="p-1 rounded-full active:bg-muted">
                <X className="h-5 w-5 text-foreground" />
              </Pressable>
            </View>
            <ScrollView className="p-2" contentContainerStyle={{ paddingBottom: 24 }}>
              {children}
            </ScrollView>
          </SafeAreaView>
        </Pressable>
      </Pressable>
    </Modal>
  );
}

export interface SelectItemProps {
  value: string;
  children: string;
  className?: string;
}

export const SelectItem = React.forwardRef<
  React.ElementRef<typeof Pressable>,
  SelectItemProps
>(({ value: itemValue, children, className, ...props }, ref) => {
  const { value: selectedValue, onValueChange, setOpen, registerItem } = useSelect();

  React.useEffect(() => {
    registerItem(itemValue, children);
  }, [itemValue, children, registerItem]);

  const isSelected = selectedValue === itemValue;

  const handlePress = () => {
    if (onValueChange) {
      onValueChange(itemValue);
    }
    setOpen(false);
  };

  return (
    <Pressable
      ref={ref}
      onPress={handlePress}
      className={cn(
        "flex-row items-center justify-between w-full rounded-md p-3 my-0.5 active:bg-muted",
        isSelected && "bg-muted",
        className
      )}
      {...props}
    >
      <Text className={cn("text-base text-foreground font-medium", isSelected && "text-primary")}>
        {children}
      </Text>
      {isSelected && <Check className="h-4 w-4 text-primary" />}
    </Pressable>
  );
});
SelectItem.displayName = "SelectItem";
