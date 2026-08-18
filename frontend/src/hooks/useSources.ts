import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { sourcesApi } from "@/api/sources";
import type { SourceInput } from "@/api/types";
import { useToast } from "@/context/ToastContext";
import { queryKeys } from "@/lib/queryClient";
import { getErrorMessage } from "@/lib/utils";

export function useSources() {
  return useQuery({
    queryKey: queryKeys.sources,
    queryFn: () => sourcesApi.list({ limit: 200 }),
  });
}

export function useCreateSource() {
  const queryClient = useQueryClient();
  const { showToast } = useToast();

  return useMutation({
    mutationFn: (input: SourceInput) => sourcesApi.create(input),
    onSuccess: (source) => {
      queryClient.invalidateQueries({ queryKey: queryKeys.sources });
      showToast({
        variant: "success",
        title: "Source connected",
        description: `"${source.name}" is ready to use in mappings.`,
      });
    },
    onError: (error) => {
      showToast({
        variant: "error",
        title: "Couldn't create source",
        description: getErrorMessage(error),
      });
    },
  });
}

export function useUpdateSource() {
  const queryClient = useQueryClient();
  const { showToast } = useToast();

  return useMutation({
    mutationFn: ({ id, input }: { id: number; input: Partial<SourceInput> }) =>
      sourcesApi.update(id, input),
    onSuccess: (source) => {
      queryClient.invalidateQueries({ queryKey: queryKeys.sources });
      queryClient.invalidateQueries({ queryKey: queryKeys.syncs });
      showToast({
        variant: "success",
        title: "Source updated",
        description: `"${source.name}" saved.`,
      });
    },
    onError: (error) => {
      showToast({
        variant: "error",
        title: "Couldn't update source",
        description: getErrorMessage(error),
      });
    },
  });
}

export function useDeleteSource() {
  const queryClient = useQueryClient();
  const { showToast } = useToast();

  return useMutation({
    mutationFn: (id: number) => sourcesApi.remove(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: queryKeys.sources });
      showToast({ variant: "success", title: "Source deleted" });
    },
    onError: (error) => {
      showToast({
        variant: "error",
        title: "Couldn't delete source",
        description: getErrorMessage(error),
      });
    },
  });
}
