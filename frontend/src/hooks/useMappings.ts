import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { mappingsApi } from "@/api/mappings";
import type { MappingInput, SuggestFieldInfo } from "@/api/types";
import { useToast } from "@/context/ToastContext";
import { queryKeys } from "@/lib/queryClient";
import { getErrorMessage } from "@/lib/utils";

export function useMappings() {
  return useQuery({
    queryKey: queryKeys.mappings,
    queryFn: () => mappingsApi.list({ limit: 200 }),
  });
}

export function useCreateMapping() {
  const queryClient = useQueryClient();
  const { showToast } = useToast();

  return useMutation({
    mutationFn: (input: MappingInput) => mappingsApi.create(input),
    onSuccess: (mapping) => {
      queryClient.invalidateQueries({ queryKey: queryKeys.mappings });
      showToast({
        variant: "success",
        title: "Mapping created",
        description: `"${mapping.name}" is ready to use in a sync.`,
      });
    },
    onError: (error) => {
      showToast({
        variant: "error",
        title: "Couldn't create mapping",
        description: getErrorMessage(error),
      });
    },
  });
}

export function useUpdateMapping() {
  const queryClient = useQueryClient();
  const { showToast } = useToast();

  return useMutation({
    mutationFn: ({ id, input }: { id: number; input: Partial<MappingInput> }) =>
      mappingsApi.update(id, input),
    onSuccess: (mapping) => {
      queryClient.invalidateQueries({ queryKey: queryKeys.mappings });
      queryClient.invalidateQueries({ queryKey: queryKeys.syncs });
      showToast({
        variant: "success",
        title: "Mapping updated",
        description: `"${mapping.name}" saved.`,
      });
    },
    onError: (error) => {
      showToast({
        variant: "error",
        title: "Couldn't update mapping",
        description: getErrorMessage(error),
      });
    },
  });
}

/** AI-suggested field pairings. Never rejects for "AI is disabled or
 * unreachable" — the caller should check the resolved `.message`. */
export function useSuggestMappings() {
  const { showToast } = useToast();

  return useMutation({
    mutationFn: ({
      sourceColumns,
      destinationFields,
    }: {
      sourceColumns: SuggestFieldInfo[];
      destinationFields: SuggestFieldInfo[];
    }) => mappingsApi.suggest(sourceColumns, destinationFields),
    onError: (error) => {
      showToast({
        variant: "error",
        title: "Couldn't get AI suggestions",
        description: getErrorMessage(error),
      });
    },
  });
}

export function useDeleteMapping() {
  const queryClient = useQueryClient();
  const { showToast } = useToast();

  return useMutation({
    mutationFn: (id: number) => mappingsApi.remove(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: queryKeys.mappings });
      showToast({ variant: "success", title: "Mapping deleted" });
    },
    onError: (error) => {
      showToast({
        variant: "error",
        title: "Couldn't delete mapping",
        description: getErrorMessage(error),
      });
    },
  });
}
