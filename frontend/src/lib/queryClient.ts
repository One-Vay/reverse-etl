import { QueryClient } from "@tanstack/react-query";

export const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 30_000,
      retry: 1,
      refetchOnWindowFocus: false,
    },
  },
});

export const queryKeys = {
  sources: ["sources"] as const,
  destinations: ["destinations"] as const,
  mappings: ["mappings"] as const,
  syncs: ["syncs"] as const,
};
