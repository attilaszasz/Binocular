import "@testing-library/jest-dom";
import { render, screen } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { ModulesPage } from "./modules";
import { vi, describe, it, expect } from "vitest";

// Mock the hooks
vi.mock("@/hooks/use-modules", () => ({
  useModules: () => ({
    data: [
      {
        id: 1,
        name: "test_module",
        device_type: "camera",
        version: "1.0.0",
        author: "Test Author",
        file_path: "/app/modules/test_module.py",
        is_official: false,
        status: "active",
      },
    ],
    isLoading: false,
    error: null,
  }),
  useUploadModule: () => ({
    mutate: vi.fn(),
    isPending: false,
    isSuccess: false,
  }),
  useUpdateModule: () => ({
    mutate: vi.fn(),
    isPending: false,
  }),
  useDeleteModule: () => ({
    mutate: vi.fn(),
    isPending: false,
  }),
}));

describe("ModulesPage", () => {
  it("renders modules list successfully", () => {
    const queryClient = new QueryClient();
    render(
      <QueryClientProvider client={queryClient}>
        <ModulesPage />
      </QueryClientProvider>
    );

    expect(screen.getByText("test_module")).toBeInTheDocument();
    expect(screen.getByText("Test Author")).toBeInTheDocument();
    expect(screen.getByText("active")).toBeInTheDocument();
  });
});
