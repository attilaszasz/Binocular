import "@testing-library/jest-dom";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { beforeEach, afterEach, it, expect, vi } from "vitest";
import App from "./App";

beforeEach(() => {
  window.history.replaceState({}, "", "/inventory");
  const storage = new Map<string, string>();
  Object.defineProperty(globalThis, "localStorage", { configurable: true, value: { getItem: (key: string) => storage.get(key) ?? null, setItem: (key: string, value: string) => storage.set(key, value), clear: () => storage.clear() } });
  Object.defineProperty(window, "matchMedia", { configurable: true, value: vi.fn(() => ({ matches: false, addEventListener: vi.fn(), removeEventListener: vi.fn() })) });
  globalThis.ResizeObserver = class { observe() {} unobserve() {} disconnect() {} };
  vi.spyOn(globalThis, "fetch").mockImplementation(async url => {
    const path = String(url);
    const data = path.includes("module-kit") ? { files: [] } : path.includes("activity") ? { items: [], total: 0 } : [];
    return new Response(JSON.stringify(data), { status: 200 });
  });
});
afterEach(() => vi.restoreAllMocks());

it("navigates real app, changes theme/sidebar and reaches source/authoring/empty forms", async () => {
  render(<App />);
  await screen.findByText("No devices yet");
  fireEvent.click(screen.getByRole("button", { name: /Add.*Device/i }));
  expect(screen.getByLabelText("Source")).toBeInTheDocument();
  fireEvent.click(screen.getByRole("button", { name: "Cancel" }));
  for (let i = 0; i < 3; i++) fireEvent.click(screen.getByRole("button", { name: /Theme:/ }));
  expect(localStorage.getItem("binocular-theme")).toBe("system");
  fireEvent.click(screen.getByRole("button", { name: "Collapse sidebar" }));
  fireEvent.click(screen.getByRole("button", { name: "Open sidebar" }));
  fireEvent.click(screen.getByRole("link", { name: "Modules" }));
  await screen.findByText("No modules loaded");
  fireEvent.click(screen.getByRole("button", { name: "Create a Module" }));
  expect(screen.getByText("V1 Contract Requirements")).toBeInTheDocument();
  fireEvent.click(screen.getAllByRole("button", { name: "Upload Module" })[0]);
  expect(screen.getByText("Trust Boundary Warning")).toBeInTheDocument();
  fireEvent.click(screen.getByRole("button", { name: "Close" }));
  fireEvent.click(screen.getByRole("button", { name: "Refresh sources" }));
  fireEvent.click(screen.getByRole("link", { name: "Logs" }));
  await screen.findByText("No activity logs found.");
  fireEvent.click(screen.getByRole("link", { name: "Settings" }));
  await screen.findByText("Notification Settings");
  window.history.pushState({}, "", "/unknown");
  fireEvent(window, new PopStateEvent("popstate"));
  await waitFor(() => expect(screen.getByText(/Page not found/i)).toBeInTheDocument());
});
