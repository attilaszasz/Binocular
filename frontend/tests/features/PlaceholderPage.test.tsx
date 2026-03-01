import { screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { PlaceholderPage } from "../../src/features/placeholders/PlaceholderPage";
import { renderWithProviders } from "../test-utils";

describe("PlaceholderPage", () => {
  it("renders title and description", () => {
    renderWithProviders(
      <PlaceholderPage
        title="Activity Logs"
        description="System execution and scraping history will appear here."
      />,
    );

    expect(screen.getByText("Activity Logs")).toBeInTheDocument();
    expect(
      screen.getByText("System execution and scraping history will appear here."),
    ).toBeInTheDocument();
  });
});
