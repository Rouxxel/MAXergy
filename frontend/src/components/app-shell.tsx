import type { ReactNode } from "react";
import { Link } from "@tanstack/react-router";
import { Home, BarChart3, LayoutGrid, MessageSquare } from "lucide-react";

export function AppShell({
  children,
  hideNav = false,
}: {
  children: ReactNode;
  hideNav?: boolean;
}) {
  return (
    <div className="min-h-screen bg-background font-sans text-foreground">
      <div className="mx-auto w-full max-w-md px-5 pb-28 pt-8">{children}</div>
      {hideNav ? null : <BottomNav />}
    </div>
  );
}

const TABS = [
  { to: "/", label: "Start", icon: Home },
  { to: "/results", label: "Results", icon: BarChart3 },
  { to: "/compare", label: "Compare", icon: LayoutGrid },
  { to: "/advisor", label: "Advisor", icon: MessageSquare },
] as const;

function BottomNav() {
  return (
    <nav className="fixed inset-x-0 bottom-0 z-40 border-t border-border bg-background/95 backdrop-blur">
      <div className="mx-auto flex w-full max-w-md items-stretch justify-between px-2 py-2">
        {TABS.map(({ to, label, icon: Icon }) => (
          <Link
            key={to}
            to={to}
            activeOptions={{ exact: true }}
            className="flex flex-1 flex-col items-center gap-1 rounded-lg px-2 py-1.5 text-[11px] text-muted-foreground transition-colors hover:text-foreground data-[status=active]:text-primary"
          >
            <Icon className="h-5 w-5" />
            {label}
          </Link>
        ))}
      </div>
    </nav>
  );
}

export function BrandMark() {
  return (
    <div className="flex items-center gap-2">
      <div className="grid h-9 w-9 place-items-center rounded-xl bg-primary text-primary-foreground">
        <svg viewBox="0 0 24 24" className="h-5 w-5" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
          <path d="M13 2 4 14h7l-1 8 9-12h-7z" />
        </svg>
      </div>
      <div className="text-lg font-bold tracking-tight">Cloover</div>
    </div>
  );
}