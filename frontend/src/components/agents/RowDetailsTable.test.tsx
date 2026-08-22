import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { RowDetailsTable } from "@/components/agents/RowDetailsTable";

describe("RowDetailsTable", () => {
  it("shows an empty message when there are no rows", () => {
    render(<RowDetailsTable rows={[]} />);
    expect(screen.getByText(/no rows to show yet/i)).toBeInTheDocument();
  });

  it("renders a row's score, reason, and selected state", () => {
    render(
      <RowDetailsTable
        rows={[
          { index: 0, score: 0.92, reason: "recent buyer", selected: true, record: { EMAIL: "a@x.com" } },
          { index: 1, score: 0.1, reason: "no activity", selected: false, record: null },
        ]}
      />,
    );

    expect(screen.getByText("0.92")).toBeInTheDocument();
    expect(screen.getByText("recent buyer")).toBeInTheDocument();
    expect(screen.getByText("a@x.com")).toBeInTheDocument();
    expect(screen.getByText("no activity")).toBeInTheDocument();
  });

  it("renders the optional caption", () => {
    render(
      <RowDetailsTable
        rows={[{ index: 0, score: 0.5, reason: "x", selected: true, record: {} }]}
        caption="1 of 1 rows selected"
      />,
    );
    expect(screen.getByText("1 of 1 rows selected")).toBeInTheDocument();
  });
});
