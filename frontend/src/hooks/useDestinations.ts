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
