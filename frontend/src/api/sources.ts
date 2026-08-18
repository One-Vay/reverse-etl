import { api, buildQuery } from "@/api/client";
import type { ListParams, ListResponse, Source, SourceInput } from "@/api/types";

export const sourcesApi = {
  list: (params: ListParams = {}) =>
    api.get<ListResponse<Source>>(`/sources/${buildQuery(params)}`),
  get: (id: number) => api.get<Source>(`/sources/${id}`),
  create: (input: SourceInput) => api.post<Source>("/sources/", input),
  update: (id: number, input: Partial<SourceInput>) =>
    api.put<Source>(`/sources/${id}`, input),
  remove: (id: number) => api.delete<void>(`/sources/${id}`),
};
