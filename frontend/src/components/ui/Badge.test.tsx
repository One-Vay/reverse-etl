import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { Badge } from "./Badge";

describe("Badge", () => {
  it("renders its children", () => {
    render(<Badge>Active</Badge>);
    expect(screen.getByText("Active")).toBeInTheDocument();
  });

  it("applies the destructive variant's classes", () => {
    render(<Badge variant="destructive">Failed</Badge>);
    expect(screen.getByText("Failed")).toHaveClass("text-destructive");
  });

  it("merges a caller-provided className instead of dropping it", () => {
    render(<Badge className="extra-class">Paused</Badge>);
    expect(screen.getByText("Paused")).toHaveClass("extra-class");
  });
});
