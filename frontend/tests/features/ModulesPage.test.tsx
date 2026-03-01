import { screen } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { ModulesPage } from "../../src/features/modules/ModulesPage";
import { renderWithProviders } from "../test-utils";

const hookMocks = vi.hoisted(() => ({
  useModuleDeviceTypes: vi.fn(),
  useCreateDeviceType: vi.fn(),
  useUpdateDeviceType: vi.fn(),
  useDeleteDeviceType: vi.fn(),
}));

vi.mock("../../src/features/modules/hooks", () => hookMocks);

describe("ModulesPage", () => {
  beforeEach(() => {
    hookMocks.useCreateDeviceType.mockReturnValue({ mutateAsync: vi.fn(), isPending: false });
    hookMocks.useUpdateDeviceType.mockReturnValue({ mutateAsync: vi.fn(), isPending: false });
    hookMocks.useDeleteDeviceType.mockReturnValue({ mutateAsync: vi.fn(), isPending: false });
  });

  it("renders module list", () => {
    hookMocks.useModuleDeviceTypes.mockReturnValue({
      isLoading: false,
      isError: false,
      data: [
        {
          id: 1,
          name: "Sony Bodies",
          firmware_source_url: "https://example.com/sony",
          extension_module_id: null,
          check_frequency_minutes: 360,
          device_count: 2,
          created_at: new Date().toISOString(),
          updated_at: new Date().toISOString(),
        },
      ],
    });

    renderWithProviders(<ModulesPage />);

    expect(screen.getByText("Sony Bodies")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Add Module" })).toBeInTheDocument();
  });

  it("shows empty state", () => {
    hookMocks.useModuleDeviceTypes.mockReturnValue({ isLoading: false, isError: false, data: [] });

    renderWithProviders(<ModulesPage />);

    expect(
      screen.getByText("No modules yet. Create one to organize your devices."),
    ).toBeInTheDocument();
  });
});
