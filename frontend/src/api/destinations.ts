import { api, buildQuery } from "@/api/client";
import type {
  ColumnInfo,
  ConnectionTestResult,
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

  /** Try connecting with a destination's stored credentials. Never rejects
   * on a bad connection — inspect `.success` instead, so the UI can show an
   * inline result rather than treating it as an app error. */
  testConnection: (id: number) =>
    api.post<ConnectionTestResult>(`/destinations/${id}/test-connection`),

  listEntities: (id: number) => api.get<string[]>(`/destinations/${id}/entities`),

  getEntityFields: (id: number, entity: string) =>
    api.get<ColumnInfo[]>(
      `/destinations/${id}/entities/${encodeURIComponent(entity)}/fields`,
    ),
};
