import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import type { ReactNode } from "react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { DestinationEntityPicker } from "@/components/pipelines/DestinationEntityPicker";

vi.mock("@/api/destinations", () => ({
  destinationsApi: {
    listEntities: vi.fn(),
  },
}));

import { destinationsApi } from "@/api/destinations";

const mockedListEntities = vi.mocked(destinationsApi.listEntities);

function renderWithClient(ui: ReactNode) {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  return render(
    <QueryClientProvider client={queryClient}>{ui}</QueryClientProvider>,
  );
}

describe("DestinationEntityPicker", () => {
  beforeEach(() => {
    mockedListEntities.mockReset().mockResolvedValue(["lead", "contact", "deal"]);
  });

  it("renders nothing without a destinationId", () => {
    const { container } = renderWithClient(
      <DestinationEntityPicker destinationId={undefined} onSelect={vi.fn()} />,
    );
    expect(container).toBeEmptyDOMElement();
  });

  it("stays collapsed until clicked, and doesn't fetch entities while collapsed", () => {
    renderWithClient(<DestinationEntityPicker destinationId={1} onSelect={vi.fn()} />);
    expect(mockedListEntities).not.toHaveBeenCalled();
  });

  it("lists entities once expanded", async () => {
    const user = userEvent.setup();
    renderWithClient(<DestinationEntityPicker destinationId={1} onSelect={vi.fn()} />);

    await user.click(screen.getByRole("button", { name: /browse entities/i }));

    expect(await screen.findByText("lead")).toBeInTheDocument();
    expect(screen.getByText("contact")).toBeInTheDocument();
    expect(screen.getByText("deal")).toBeInTheDocument();
  });

  it("filters entities by the search box", async () => {
    const user = userEvent.setup();
    renderWithClient(<DestinationEntityPicker destinationId={1} onSelect={vi.fn()} />);

    await user.click(screen.getByRole("button", { name: /browse entities/i }));
    await screen.findByText("lead");
    await user.type(screen.getByPlaceholderText("Filter entities…"), "dea");

    expect(screen.getByText("deal")).toBeInTheDocument();
    expect(screen.queryByText("lead")).not.toBeInTheDocument();
  });

  it("selects an entity and collapses the list", async () => {
    const user = userEvent.setup();
    const onSelect = vi.fn();
    renderWithClient(
      <DestinationEntityPicker destinationId={1} onSelect={onSelect} />,
    );

    await user.click(screen.getByRole("button", { name: /browse entities/i }));
    await user.click(await screen.findByText("lead"));

    expect(onSelect).toHaveBeenCalledWith("lead");
    expect(screen.queryByPlaceholderText("Filter entities…")).not.toBeInTheDocument();
  });

  it("shows an error message if entities fail to load", async () => {
    mockedListEntities.mockReset().mockRejectedValue(new Error("boom"));
    const user = userEvent.setup();
    renderWithClient(<DestinationEntityPicker destinationId={1} onSelect={vi.fn()} />);

    await user.click(screen.getByRole("button", { name: /browse entities/i }));

    expect(await screen.findByText(/Couldn't load entities/)).toBeInTheDocument();
  });
});
