import { describe, expect, it } from "vitest";

import {
  CUSTOM_TRANSFORMATION,
  TRANSFORMATION_PRESETS,
  isPresetTransformation,
} from "./transformations";

describe("isPresetTransformation", () => {
  it("recognizes every declared preset value, including the empty 'None' preset", () => {
    for (const preset of TRANSFORMATION_PRESETS) {
      expect(isPresetTransformation(preset.value)).toBe(true);
    }
  });

  it("recognizes the custom-mode sentinel as a preset value", () => {
    expect(isPresetTransformation(CUSTOM_TRANSFORMATION)).toBe(true);
  });

  it("does not recognize arbitrary user-typed text", () => {
    expect(isPresetTransformation("concat(first, last)")).toBe(false);
  });
});
