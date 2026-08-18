import { useMemo } from "react";

import { useTheme } from "@/context/ThemeContext";

/** Reads a `--token` CSS custom property (stored as raw HSL components) as an hsl() string. */
function readCssVar(name: string, fallback: string): string {
  if (typeof window === "undefined") return fallback;
  const value = getComputedStyle(document.documentElement).getPropertyValue(name).trim();
  return value ? `hsl(${value})` : fallback;
}

/** Chart colors derived from the active theme's design tokens, recomputed on toggle. */
export function useChartColors() {
  const { theme } = useTheme();

  return useMemo(
    () => ({
      primary: readCssVar("--primary", "#3a9d71"),
      success: readCssVar("--success", "#3a9d71"),
      destructive: readCssVar("--destructive", "#e5484d"),
      warning: readCssVar("--warning", "#e8a33d"),
      muted: readCssVar("--muted-foreground", "#71717a"),
      border: readCssVar("--border", "#e4e4e7"),
    }),
    // Recompute whenever the theme toggles, even though `theme` isn't read
    // directly — the CSS variables it swaps are read from the DOM instead.
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [theme],
  );
}
