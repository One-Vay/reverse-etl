/** Common field transformations offered as one-click presets in the mapping
 * editor. `value` is stored verbatim in `field_mappings[].transformation`;
 * the sync engine (not built yet) interprets these names when it applies a
 * mapping. `CUSTOM_TRANSFORMATION` is a sentinel for "type your own",
 * never itself a value that gets saved. */
export const CUSTOM_TRANSFORMATION = "__custom__";

export interface TransformationPreset {
  label: string;
  value: string;
}

export const TRANSFORMATION_PRESETS: TransformationPreset[] = [
  { label: "None", value: "" },
  { label: "Lowercase", value: "lowercase" },
  { label: "Uppercase", value: "uppercase" },
  { label: "Trim whitespace", value: "trim" },
  { label: "To string", value: "to_string" },
  { label: "To number", value: "to_number" },
  { label: "Parse date", value: "parse_date" },
  { label: "Custom…", value: CUSTOM_TRANSFORMATION },
];

const PRESET_VALUES = new Set(TRANSFORMATION_PRESETS.map((preset) => preset.value));

/** Whether a stored transformation value matches one of the built-in
 * presets, vs. being free-form text a user typed in "Custom" mode. */
export function isPresetTransformation(value: string): boolean {
  return PRESET_VALUES.has(value);
}
