import { fireEvent, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import type { Device } from "../../src/api/types";
import { DeviceCard } from "../../src/features/dashboard/DeviceCard";
import { renderWithProviders } from "../test-utils";

function makeDevice(overrides: Partial<Device> = {}): Device {
  return {
    id: 1,
    device_type_id: 1,
    device_type_name: "Sony Bodies",
    name: "Sony A7IV",
    current_version: "2.00",
    latest_seen_version: "3.00",
    last_checked_at: new Date().toISOString(),
    notes: null,
    status: "update_available",
    created_at: new Date().toISOString(),
    updated_at: new Date().toISOString(),
    ...overrides,
  };
}

describe("DeviceCard", () => {
  it("renders status and version comparison", () => {
    renderWithProviders(
      <DeviceCard
        device={makeDevice()}
        onConfirm={vi.fn()}
        onEdit={vi.fn()}
        onDelete={vi.fn()}
        isConfirmPending={false}
      />,
    );

    expect(screen.getByText("Update Available")).toBeInTheDocument();
    expect(screen.getByText("Local: v2.00")).toBeInTheDocument();
    expect(screen.getByText("Latest: v3.00")).toBeInTheDocument();
  });

  it("hides confirm action for never_checked and up_to_date", () => {
    const { rerender } = renderWithProviders(
      <DeviceCard
        device={makeDevice({ status: "never_checked", latest_seen_version: null })}
        onConfirm={vi.fn()}
        onEdit={vi.fn()}
        onDelete={vi.fn()}
        isConfirmPending={false}
      />,
    );

    expect(screen.queryByRole("button", { name: /sync local/i })).not.toBeInTheDocument();

    rerender(
      <DeviceCard
        device={makeDevice({
          status: "up_to_date",
          latest_seen_version: "2.00",
          current_version: "2.00",
        })}
        onConfirm={vi.fn()}
        onEdit={vi.fn()}
        onDelete={vi.fn()}
        isConfirmPending={false}
      />,
    );

    expect(screen.queryByRole("button", { name: /sync local/i })).not.toBeInTheDocument();
  });

  it("disables confirm button during pending", () => {
    renderWithProviders(
      <DeviceCard
        device={makeDevice()}
        onConfirm={vi.fn()}
        onEdit={vi.fn()}
        onDelete={vi.fn()}
        isConfirmPending={true}
      />,
    );

    expect(screen.getByRole("button", { name: /syncing/i })).toBeDisabled();
  });

  it("fires confirm with mouse click", async () => {
    const user = userEvent.setup();
    const onConfirm = vi.fn();

    renderWithProviders(
      <DeviceCard
        device={makeDevice()}
        onConfirm={onConfirm}
        onEdit={vi.fn()}
        onDelete={vi.fn()}
        isConfirmPending={false}
      />,
    );

    await user.click(screen.getByRole("button", { name: /sync local/i }));
    expect(onConfirm).toHaveBeenCalledWith(1);
  });

  it("fires confirm on Enter key", () => {
    const onConfirm = vi.fn();

    renderWithProviders(
      <DeviceCard
        device={makeDevice()}
        onConfirm={onConfirm}
        onEdit={vi.fn()}
        onDelete={vi.fn()}
        isConfirmPending={false}
      />,
    );

    const button = screen.getByRole("button", { name: /sync local/i });
    button.focus();
    fireEvent.keyDown(button, { key: "Enter", code: "Enter", charCode: 13 });
    fireEvent.click(button);

    expect(onConfirm).toHaveBeenCalledWith(1);
  });
});
