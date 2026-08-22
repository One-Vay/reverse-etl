import { z } from "zod";

// Advanced numeric fields are rendered as text inputs that may be left
// blank (→ "use the connector's default"), so the schema accepts "" and
// coerces it to undefined rather than a coerced NaN/0.
const optionalPositiveNumber = (max: number) =>
  z
    .union([z.literal(""), z.coerce.number().positive().max(max)])
    .optional()
    .transform((v) => (v === "" || v === undefined ? undefined : v));

export const sourceSchema = z.object({
  name: z.string().min(1, "Name is required").max(255),
  type: z.enum(["postgres", "clickhouse"]),
  host: z.string().min(1, "Host is required"),
  port: z.coerce.number().int().min(1).max(65535),
  database: z.string().min(1, "Database name is required"),
  username: z.string().min(1, "Username is required"),
  password: z.string().optional(),
  connect_timeout: optionalPositiveNumber(300),
  command_timeout: optionalPositiveNumber(300),
  min_pool_size: optionalPositiveNumber(100),
  max_pool_size: optionalPositiveNumber(100),
});
export type SourceFormValues = z.infer<typeof sourceSchema>;

export const destinationSchema = z.object({
  name: z.string().min(1, "Name is required").max(255),
  type: z.enum(["bitrix24", "amocrm"]),
  api_url: z.string().min(1, "API URL is required").url("Must be a valid URL"),
  auth_token: z.string().optional(),
  request_timeout: optionalPositiveNumber(300),
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

const TIME_RE = /^([01]\d|2[0-3]):[0-5]\d$/;

export const syncSchema = z
  .object({
    name: z.string().min(1, "Name is required").max(255),
    source_id: z.coerce.number().int().min(1, "Select a source"),
    destination_id: z.coerce.number().int().min(1, "Select a destination"),
    mapping_id: z.coerce.number().int().min(1, "Select a mapping"),
    interval_value: z.coerce.number().int().min(1, "Must be at least 1"),
    interval_unit: z.enum(["hours", "days"]),
    run_at_time: z
      .union([z.literal(""), z.string().regex(TIME_RE, "Use HH:MM (24h)")])
      .optional()
      .transform((v) => (v === "" || v === undefined ? null : v)),
    incremental_field: z.string().optional(),
    status: z.enum(["active", "paused", "inactive"]).default("active"),
  })
  .refine(
    (data) =>
      data.interval_unit === "hours"
        ? data.interval_value <= 168
        : data.interval_value <= 90,
    {
      message: "At most 168 hours or 90 days",
      path: ["interval_value"],
    },
  );
export type SyncFormValues = z.infer<typeof syncSchema>;

export const featureNoteSchema = z.object({
  column: z.string().min(1, "Required"),
  description: z.string().min(1, "Required"),
});

export const agentSchema = z.object({
  name: z.string().min(1, "Name is required").max(255),
  destination_id: z.coerce.number().int().min(1, "Select a destination"),
  mapping_id: z.coerce.number().int().min(1, "Select a mapping"),
  goal: z.string().min(1, "Describe the goal"),
  actions: z.string().min(1, "Describe the planned actions"),
  feature_notes: z.array(featureNoteSchema).default([]),
  llm_model: z.string().min(1, "Choose a model"),
  selection_strategy: z.enum(["scoring", "clustering", "rule_based"]),
  selection_threshold: z.coerce.number().min(0).max(1),
  incremental_field: z.string().optional(),
  annotation_field: z.string().optional(),
});
export type AgentFormValues = z.infer<typeof agentSchema>;

export const settingsSchema = z.object({
  scheduler_enabled: z.boolean(),
  scheduler_poll_interval_seconds: z.coerce.number().int().min(5).max(3600),
  llm_enabled: z.boolean(),
  llm_base_url: z.string().min(1, "Ollama URL is required"),
  llm_model: z.string().min(1, "Model name is required"),
  telegram_enabled: z.boolean(),
  telegram_bot_token: z.string().optional(),
  telegram_chat_id: z.string().optional(),
  default_connect_timeout_seconds: z.coerce.number().positive().max(300),
  default_request_timeout_seconds: z.coerce.number().positive().max(300),
});
export type SettingsFormValues = z.infer<typeof settingsSchema>;
