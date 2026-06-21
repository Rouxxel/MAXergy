import { Zap, TrendingUp, Shield, LayoutGrid, Brain, Calendar, LucideIcon } from "lucide-react";

interface FeatureCardProps {
  icon: string;
  title: string;
  description: string;
}

const icons: Record<string, LucideIcon> = {
  Zap,
  TrendingUp,
  Shield,
  LayoutGrid,
  Brain,
  Calendar,
};

export function FeatureCard({ icon, title, description }: FeatureCardProps) {
  const Icon = icons[icon] || Zap;

  return (
    <div className="rounded-lg border border-border bg-card p-6 space-y-3 transition-transform duration-300 hover:scale-105 hover:border-primary/50">
      <Icon className="h-8 w-8 text-primary" />
      <div className="space-y-1">
        <h3 className="font-semibold">{title}</h3>
        <p className="text-sm text-muted-foreground">{description}</p>
      </div>
    </div>
  );
}
