import { Loader2 } from "lucide-react";

import { cn } from "@/lib/utils";

export function Spinner({ className }: { className?: string }) {
  return (
    <div className="flex w-full items-center justify-center py-10 text-muted-foreground">
      <Loader2 className={cn("h-5 w-5 animate-spin", className)} />
    </div>
  );
}
