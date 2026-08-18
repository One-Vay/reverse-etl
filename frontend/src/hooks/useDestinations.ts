import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { destinationsApi } from "@/api/destinations";
import type { DestinationInput } from "@/api/types";
import { useToast } from "@/context/ToastContext";
import { queryKeys } from "@/lib/queryClient";
import { getErrorMessage } from "@/lib/utils";

export function useDestinations() {
  return useQuery({
    queryKey: queryKeys.destinations,
    queryFn: () => destinationsApi.list({ limit: 200 }),
  });
}

export function useCreateDestination() {
  const queryClient = useQueryClient();
  const { showToast } = useToast();

  return useMutation({
    mutationFn: (input: DestinationInput) => destinationsApi.create(input),
    onSuccess: (destination) => {
      queryClient.invalidateQueries({ queryKey: queryKeys.destinations });
      showToast({
        variant: "success",
        title: "Destination connected",
        description: `"${destination.name}" is ready to use in syncs.`,
      });
    },
    onError: (error) => {
      showToast({
        variant: "error",
        title: "Couldn't create destination",
        description: getErrorMessage(error),
      });
    },
  });
}

export function useUpdateDestination() {
  const queryClient = useQueryClient();
  const { showToast } = useToast();

  return useMutation({
    mutationFn: ({ id, input }: { id: number; input: Partial<DestinationInput> }) =>
      destinationsApi.update(id, input),
    onSuccess: (destination) => {
      queryClient.invalidateQueries({ queryKey: queryKeys.destinations });
      queryClient.invalidateQueries({ queryKey: queryKeys.syncs });
      showToast({
        variant: "success",
        title: "Destination updated",
        description: `"${destination.name}" saved.`,
      });
    },
    onError: (error) => {
      showToast({
        variant: "error",
        title: "Couldn't update destination",
        description: getErrorMessage(error),
      });
    },
  });
}

export function useDeleteDestination() {
  const queryClient = useQueryClient();
  const { showToast } = useToast();

  return useMutation({
    mutationFn: (id: number) => destinationsApi.remove(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: queryKeys.destinations });
      showToast({ variant: "success", title: "Destination deleted" });
    },
    onError: (error) => {
      showToast({
        variant: "error",
        title: "Couldn't delete destination",
        description: getErrorMessage(error),
      });
    },
  });
}

/** Entity types a destination can receive records as, for the mapping
 * form's entity picker. Disabled until `destinationId` is set. */
export function useDestinationEntities(destinationId: number | undefined) {
  return useQuery({
    queryKey: queryKeys.destinationEntities(destinationId ?? 0),
    queryFn: () => destinationsApi.listEntities(destinationId as number),
    enabled: destinationId != null && destinationId > 0,
    staleTime: 60_000,
  });
}

/** Fields of one destination entity, for the mapping form's field picker.
 * Disabled until both `destinationId` and `entity` are set. */
export function useDestinationEntityFields(
  destinationId: number | undefined,
  entity: string | undefined,
) {
  return useQuery({
    queryKey: queryKeys.destinationEntityFields(destinationId ?? 0, entity ?? ""),
    queryFn: () =>
      destinationsApi.getEntityFields(destinationId as number, entity as string),
    enabled: destinationId != null && destinationId > 0 && !!entity,
    staleTime: 60_000,
  });
}

/** Tests a destination's stored credentials. Resolves with `{success,
 * message}` even on failed connections — only rejects for app-level errors
 * (destination not found, connector not implemented, network failure),
 * which is when the error toast fires. */
export function useTestDestinationConnection() {
  const { showToast } = useToast();

  return useMutation({
    mutationFn: (id: number) => destinationsApi.testConnection(id),
    onError: (error) => {
      showToast({
        variant: "error",
        title: "Couldn't test connection",
        description: getErrorMessage(error),
      });
    },
  });
}
