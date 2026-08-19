import { api, buildQuery } from "@/api/client";
import type {
  ListParams,
  ListResponse,
  Mapping,
  MappingInput,
  SuggestFieldInfo,
  SuggestMappingsResponse,
} from "@/api/types";

export const mappingsApi = {
  list: (params: ListParams = {}) =>
    api.get<ListResponse<Mapping>>(`/mappings/${buildQuery(params)}`),
  get: (id: number) => api.get<Mapping>(`/mappings/${id}`),
  create: (input: MappingInput) => api.post<Mapping>("/mappings/", input),
  update: (id: number, input: Partial<MappingInput>) =>
    api.put<Mapping>(`/mappings/${id}`, input),
  remove: (id: number) => api.delete<void>(`/mappings/${id}`),

  /** AI-suggested source→destination field pairings. Always resolves
   * (never rejects for "AI is disabled/unreachable") — check `.message`
   * for why `.pairs` might be empty. */
  suggest: (sourceColumns: SuggestFieldInfo[], destinationFields: SuggestFieldInfo[]) =>
    api.post<SuggestMappingsResponse>("/mappings/suggest", {
      source_columns: sourceColumns,
      destination_fields: destinationFields,
    }),
};
