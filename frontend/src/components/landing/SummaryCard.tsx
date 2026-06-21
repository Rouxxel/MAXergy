interface SummaryCardProps {
  label: string;
  value: string;
}

export function SummaryCard({ label, value }: SummaryCardProps) {
  return (
    <div className="rounded-lg border border-border bg-card p-4 space-y-1 transition-transform duration-300 hover:scale-105 hover:border-primary/50">
      <div className="text-sm text-muted-foreground">{label}</div>
      <div className="font-semibold">{value}</div>
    </div>
  );
}
