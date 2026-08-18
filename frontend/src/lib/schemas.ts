import { z } from "zod";

export const sourceSchema = z.object({
  name: z.string().min(1, "Name is required").max(255),
  type: z.enum(["postgres", "clickhouse"]),
  host: z.string().min(1, "Host is required"),
  port: z.coerce.number().int().min(1).max(65535),
  database: z.string().min(1, "Database name is required"),
  username: z.string().min(1, "Username is required"),
  password: z.string().optional(),
});
export type SourceFormValues = z.infer<typeof sourceSchema>;

export const destinationSchema = z.object({
  name: z.string().min(1, "Name is required").max(255),
  type: z.enum(["bitrix24", "amocrm"]),
  api_url: z.string().min(1, "API URL is required").url("Must be a valid URL"),
  auth_token: z.string().optional(),
});
export type DestinationFormValues = z.infer<typeof destinationSchema>;

export const fieldMappingSchema = z.object({
  source_field: z.string().min(1, "Required"),
  destination_field: z.string().min(1, "Required"),
  transformation: z.string().optional(),
});

export const mappingSchema = z.object({
  name: z.string().min(1, "Name is required").max(255),
  source_id: z.coerce.number().int().min(1, "Select a source"),
  source_table: z.string().min(1, "Source table is required"),
  destination_entity: z.string().min(1, "Destination entity is required"),
  field_mappings: z
    .array(fieldMappingSchema)
    .min(1, "Add at least one field mapping")
    .default([]),
});
export type MappingFormValues = z.infer<typeof mappingSchema>;

export const syncSchema = z.object({
  name: z.string().min(1, "Name is required").max(255),
  source_id: z.coerce.number().int().min(1, "Select a source"),
  destination_id: z.coerce.number().int().min(1, "Select a destination"),
  mapping_id: z.coerce.number().int().min(1, "Select a mapping"),
  schedule: z.string().min(1, "Schedule is required"),
  incremental_field: z.string().optional(),
  status: z.enum(["active", "paused", "inactive"]).default("active"),
});
export type SyncFormValues = z.infer<typeof syncSchema>;
