import { api, buildQuery } from "@/api/client";
import type { ListParams, ListResponse, Mapping, MappingInput } from "@/api/types";

export const mappingsApi = {
  list: (params: ListParams = {}) =>
    api.get<ListResponse<Mapping>>(`/mappings/${buildQuery(params)}`),
  get: (id: number) => api.get<Mapping>(`/mappings/${id}`),
  create: (input: MappingInput) => api.post<Mapping>("/mappings/", input),
  update: (id: number, input: Partial<MappingInput>) =>
    api.put<Mapping>(`/mappings/${id}`, input),
  remove: (id: number) => api.delete<void>(`/mappings/${id}`),
};
