import { X, WifiOff } from "lucide-react";
import { useUiStore } from "@/stores/uiStore";

export function ErrorBanner() {
  const { globalError, setError } = useUiStore();

  if (!globalError) return null;

  const isOffline = globalError.toLowerCase().includes("network") || 
                    globalError.toLowerCase().includes("offline") ||
                    globalError.toLowerCase().includes("fetch");

  return (
    <div className="fixed top-0 left-0 right-0 z-50 border-b border-destructive bg-destructive/10 px-4 py-3">
      <div className="mx-auto flex max-w-md items-center gap-4">
        {isOffline && <WifiOff className="h-4 w-4 text-destructive" />}
        <p className="flex-1 text-sm text-destructive">{globalError}</p>
        <button
          onClick={() => setError(undefined)}
          className="rounded-full p-1 text-destructive hover:bg-destructive/20"
        >
          <X className="h-4 w-4" />
        </button>
      </div>
    </div>
  );
}
