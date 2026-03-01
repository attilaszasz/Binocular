import { screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import { ApiError } from "../../src/api/types";
import { DeviceForm } from "../../src/features/forms/DeviceForm";
import { renderWithProviders } from "../test-utils";

describe("DeviceForm", () => {
  const deviceTypes = [
    {
      id: 1,
      name: "Sony Bodies",
      firmware_source_url: "https://example.com",
      extension_module_id: null,
      check_frequency_minutes: 360,
      device_count: 0,
      created_at: new Date().toISOString(),
      updated_at: new Date().toISOString(),
    },
  ];

  it("validates required fields", async () => {
    const user = userEvent.setup();

    renderWithProviders(
      <DeviceForm
        mode="create"
        deviceTypes={deviceTypes}
        isSubmitting={false}
        onCancel={vi.fn()}
        onSubmit={vi.fn().mockResolvedValue(undefined)}
      />,
    );

    await user.clear(screen.getByLabelText("Name"));
    await user.clear(screen.getByLabelText("Current Version"));
    await user.click(screen.getByRole("button", { name: "Add Device" }));

    expect(screen.getAllByText("This field is required").length).toBeGreaterThan(0);
  });

  it("maps server duplicate error to name field", async () => {
    const user = userEvent.setup();

    renderWithProviders(
      <DeviceForm
        mode="create"
        deviceTypes={deviceTypes}
        isSubmitting={false}
        onCancel={vi.fn()}
        onSubmit={vi.fn().mockRejectedValue(
          new ApiError({
            message: "A device with this name already exists.",
            status: 409,
            field: "name",
          }),
        )}
      />,
    );

    await user.type(screen.getByLabelText("Name"), "Sony A7IV");
    await user.type(screen.getByLabelText("Current Version"), "2.00");
    await user.click(screen.getByRole("button", { name: "Add Device" }));

    expect(screen.getByText("A device with this name already exists.")).toBeInTheDocument();
  });
});
