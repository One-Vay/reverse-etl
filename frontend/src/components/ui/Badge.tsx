import type { HTMLAttributes } from "react";

import { cn } from "@/lib/utils";

type Variant = "default" | "success" | "warning" | "destructive" | "muted";

const VARIANT_CLASSES: Record<Variant, string> = {
  default: "bg-primary/10 text-primary-700 dark:text-primary-300",
  success: "bg-success/10 text-success",
  warning: "bg-warning/15 text-warning",
  destructive: "bg-destructive/10 text-destructive",
  muted: "bg-muted text-muted-foreground",
};

interface BadgeProps extends HTMLAttributes<HTMLSpanElement> {
  variant?: Variant;
}

export function Badge({ className, variant = "default", ...props }: BadgeProps) {
  return (
    <span
      className={cn(
        "inline-flex items-center gap-1 rounded-full px-2.5 py-0.5 text-xs font-medium",
        VARIANT_CLASSES[variant],
        className,
      )}
      {...props}
    />
  );
}
