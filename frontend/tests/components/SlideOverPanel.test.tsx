import { screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import { SlideOverPanel } from "../../src/components/SlideOverPanel";
import { renderWithProviders } from "../test-utils";

describe("SlideOverPanel", () => {
  it("renders when open", () => {
    renderWithProviders(
      <SlideOverPanel title="Panel" isOpen={true} onClose={vi.fn()}>
        <div>Panel content</div>
      </SlideOverPanel>,
    );

    expect(screen.getByText("Panel content")).toBeInTheDocument();
  });

  it("does not render when closed", () => {
    renderWithProviders(
      <SlideOverPanel title="Panel" isOpen={false} onClose={vi.fn()}>
        <div>Panel content</div>
      </SlideOverPanel>,
    );

    expect(screen.queryByText("Panel content")).not.toBeInTheDocument();
  });

  it("calls onClose when pressing Escape", async () => {
    const user = userEvent.setup();
    const onClose = vi.fn();

    renderWithProviders(
      <SlideOverPanel title="Panel" isOpen={true} onClose={onClose}>
        <div>Panel content</div>
      </SlideOverPanel>,
    );

    await user.keyboard("{Escape}");

    expect(onClose).toHaveBeenCalled();
  });
});
