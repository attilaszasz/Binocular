import { fireEvent, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { ModulesPage } from "../../src/features/modules/ModulesPage";
import { renderWithProviders } from "../test-utils";

const hookMocks = vi.hoisted(() => ({
  useModules: vi.fn(),
  useUploadModule: vi.fn(),
  useDeleteModule: vi.fn(),
  useReloadModules: vi.fn(),
}));

vi.mock("../../src/features/modules/hooks", () => hookMocks);

const MOCK_MODULE = {
  id: 1,
  filename: "sony_alpha.py",
  module_version: "1.0.0",
  supported_device_type: "sony_alpha_cameras",
  is_active: true,
  file_hash: "abc123",
  last_error: null,
  loaded_at: new Date().toISOString(),
  created_at: new Date().toISOString(),
  updated_at: new Date().toISOString(),
};

const MOCK_INACTIVE_MODULE = {
  ...MOCK_MODULE,
  id: 2,
  filename: "broken_module.py",
  is_active: false,
  last_error: "Missing required function: check_firmware",
};

describe("ModulesPage", () => {
  const uploadMutateAsync = vi.fn();
  const deleteMutateAsync = vi.fn();
  const reloadMutateAsync = vi.fn();

  beforeEach(() => {
    vi.clearAllMocks();
    hookMocks.useUploadModule.mockReturnValue({
      mutateAsync: uploadMutateAsync,
      isPending: false,
      error: null,
    });
    hookMocks.useDeleteModule.mockReturnValue({
      mutateAsync: deleteMutateAsync,
      isPending: false,
    });
    hookMocks.useReloadModules.mockReturnValue({
      mutateAsync: reloadMutateAsync,
      isPending: false,
    });
  });

  describe("Module List (US2)", () => {
    it("renders module table with columns", () => {
      hookMocks.useModules.mockReturnValue({
        isLoading: false,
        isError: false,
        data: [MOCK_MODULE],
      });

      renderWithProviders(<ModulesPage />);

      expect(screen.getByText("sony_alpha.py")).toBeInTheDocument();
      expect(screen.getByText("1.0.0")).toBeInTheDocument();
      expect(screen.getByText("sony_alpha_cameras")).toBeInTheDocument();
    });

    it("shows active status badge", () => {
      hookMocks.useModules.mockReturnValue({
        isLoading: false,
        isError: false,
        data: [MOCK_MODULE],
      });

      renderWithProviders(<ModulesPage />);

      expect(screen.getByText("Active")).toBeInTheDocument();
    });

    it("shows inactive module with error display", () => {
      hookMocks.useModules.mockReturnValue({
        isLoading: false,
        isError: false,
        data: [MOCK_INACTIVE_MODULE],
      });

      renderWithProviders(<ModulesPage />);

      expect(screen.getByText("Error")).toBeInTheDocument();
      expect(
        screen.getByText("Missing required function: check_firmware"),
      ).toBeInTheDocument();
    });

    it("shows empty state when no modules", () => {
      hookMocks.useModules.mockReturnValue({
        isLoading: false,
        isError: false,
        data: [],
      });

      renderWithProviders(<ModulesPage />);

      expect(
        screen.getByText(/no extension modules/i),
      ).toBeInTheDocument();
    });

    it("shows reload button", () => {
      hookMocks.useModules.mockReturnValue({
        isLoading: false,
        isError: false,
        data: [MOCK_MODULE],
      });

      renderWithProviders(<ModulesPage />);

      expect(screen.getByRole("button", { name: /reload/i })).toBeInTheDocument();
    });
  });

  describe("Module Upload (US1)", () => {
    it("renders upload dropzone", () => {
      hookMocks.useModules.mockReturnValue({
        isLoading: false,
        isError: false,
        data: [],
      });

      renderWithProviders(<ModulesPage />);

      expect(screen.getByTestId("upload-dropzone")).toBeInTheDocument();
    });

    it("shows uploading state", () => {
      hookMocks.useModules.mockReturnValue({
        isLoading: false,
        isError: false,
        data: [],
      });
      hookMocks.useUploadModule.mockReturnValue({
        mutateAsync: uploadMutateAsync,
        isPending: true,
        error: null,
      });

      renderWithProviders(<ModulesPage />);

      expect(screen.getByText("Uploading…")).toBeInTheDocument();
    });

    it("shows upload error", () => {
      hookMocks.useModules.mockReturnValue({
        isLoading: false,
        isError: false,
        data: [],
      });
      hookMocks.useUploadModule.mockReturnValue({
        mutateAsync: uploadMutateAsync,
        isPending: false,
        error: { message: "Only .py files are accepted." },
      });

      renderWithProviders(<ModulesPage />);

      expect(screen.getByRole("alert")).toBeInTheDocument();
      expect(screen.getByText("Only .py files are accepted.")).toBeInTheDocument();
    });
  });

  describe("Module Delete (US3)", () => {
    it("shows delete button for each module", () => {
      hookMocks.useModules.mockReturnValue({
        isLoading: false,
        isError: false,
        data: [MOCK_MODULE],
      });

      renderWithProviders(<ModulesPage />);

      expect(
        screen.getByRole("button", { name: /delete.*sony_alpha\.py/i }),
      ).toBeInTheDocument();
    });

    it("shows confirmation dialog on delete click", async () => {
      hookMocks.useModules.mockReturnValue({
        isLoading: false,
        isError: false,
        data: [MOCK_MODULE],
      });

      renderWithProviders(<ModulesPage />);

      const deleteButton = screen.getByRole("button", { name: /delete.*sony_alpha\.py/i });
      fireEvent.click(deleteButton);

      await waitFor(() => {
        expect(screen.getByRole("dialog")).toBeInTheDocument();
      });
      expect(screen.getByText(/delete.*sony_alpha\.py/i)).toBeInTheDocument();
    });
  });

  describe("Loading & Error States", () => {
    it("shows loading skeleton", () => {
      hookMocks.useModules.mockReturnValue({
        isLoading: true,
        isError: false,
        data: undefined,
      });

      renderWithProviders(<ModulesPage />);

      expect(screen.getByText("Extension Modules")).toBeInTheDocument();
    });

    it("shows error banner on fetch failure", () => {
      hookMocks.useModules.mockReturnValue({
        isLoading: false,
        isError: true,
        data: undefined,
        refetch: vi.fn(),
      });

      renderWithProviders(<ModulesPage />);

      expect(screen.getByText(/failed to load modules/i)).toBeInTheDocument();
    });
  });
});
