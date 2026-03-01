import { screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { StatsRow } from "../../src/features/dashboard/StatsRow";
import { renderWithProviders } from "../test-utils";

describe("StatsRow", () => {
  it("renders all three stats", () => {
    renderWithProviders(<StatsRow totalDevices={5} updatesAvailable={2} upToDate={3} />);

    expect(screen.getByText("Total Devices")).toBeInTheDocument();
    expect(screen.getByText("Updates Available")).toBeInTheDocument();
    expect(screen.getByText("Up to Date")).toBeInTheDocument();
    expect(screen.getByText("5")).toBeInTheDocument();
    expect(screen.getByText("2")).toBeInTheDocument();
    expect(screen.getByText("3")).toBeInTheDocument();
  });

  it("exposes polite live region", () => {
    renderWithProviders(<StatsRow totalDevices={1} updatesAvailable={0} upToDate={1} />);

    expect(screen.getByText("Total Devices").closest("div")).toHaveAttribute("aria-live", "polite");
  });
});
