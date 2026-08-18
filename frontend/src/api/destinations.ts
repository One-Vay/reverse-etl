import { api, buildQuery } from "@/api/client";
import type {
  Destination,
  DestinationInput,
  ListParams,
  ListResponse,
} from "@/api/types";

export const destinationsApi = {
  list: (params: ListParams = {}) =>
    api.get<ListResponse<Destination>>(`/destinations/${buildQuery(params)}`),
  get: (id: number) => api.get<Destination>(`/destinations/${id}`),
  create: (input: DestinationInput) => api.post<Destination>("/destinations/", input),
  update: (id: number, input: Partial<DestinationInput>) =>
    api.put<Destination>(`/destinations/${id}`, input),
  remove: (id: number) => api.delete<void>(`/destinations/${id}`),
};
