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
  sourceTables: (sourceId: number) => ["sources", sourceId, "tables"] as const,
  sourceTableSchema: (sourceId: number, table: string, schema: string) =>
    ["sources", sourceId, "tables", table, "schema", schema] as const,
  destinations: ["destinations"] as const,
  mappings: ["mappings"] as const,
  syncs: ["syncs"] as const,
};
