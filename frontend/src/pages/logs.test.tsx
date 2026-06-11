import "@testing-library/jest-dom";
import { render, screen } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { LogsPage } from "./logs";
import { vi, describe, it, expect } from "vitest";

// Mock the hooks
vi.mock("@/hooks/use-activity", () => ({
  useActivity: () => ({
    data: {
      items: [
        {
          id: 1,
          timestamp: "2026-06-11T08:20:00Z",
          level: "INFO",
          category: "check",
          message: "Check succeeded for Device X",
          device_id: 1,
          device_name: "Device X",
          module_name: "test_module",
          traceback: null,
        },
        {
          id: 2,
          timestamp: "2026-06-11T08:25:00Z",
          level: "ERROR",
          category: "notification",
          message: "Email dispatch failed",
          device_id: null,
          device_name: null,
          module_name: null,
          traceback: "Traceback error line",
        },
      ],
      total: 2,
    },
    isLoading: false,
    error: null,
  }),
}));

vi.mock("@/hooks/use-devices", () => ({
  useDevices: () => ({
    data: [
      {
        id: 1,
        name: "Device X",
        model: "Model X",
        module_id: 1,
        module_name: "test_module",
        device_type: "camera",
        current_version: "1.0.0",
        has_update: false,
        latest_detected_version: null,
        last_checked: null,
        last_notified_version: null,
        created_at: "2026-06-11T08:00:00Z",
        updated_at: "2026-06-11T08:00:00Z",
      },
    ],
    isLoading: false,
  }),
}));

describe("LogsPage", () => {
  it("renders logs table and message content successfully", () => {
    const queryClient = new QueryClient();
    render(
      <QueryClientProvider client={queryClient}>
        <LogsPage />
      </QueryClientProvider>
    );

    expect(screen.getByText("Activity Logs")).toBeInTheDocument();
    expect(screen.getByText("Check succeeded for Device X")).toBeInTheDocument();
    expect(screen.getByText("Email dispatch failed")).toBeInTheDocument();
    expect(screen.getByText("INFO")).toBeInTheDocument();
    expect(screen.getByText("ERROR")).toBeInTheDocument();
  });
});
