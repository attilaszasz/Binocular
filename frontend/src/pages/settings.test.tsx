import "@testing-library/jest-dom";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { afterEach, it, expect, vi } from "vitest";
import { SettingsPage } from "./settings";

globalThis.ResizeObserver = class { observe() {} unobserve() {} disconnect() {} };

afterEach(() => vi.restoreAllMocks());
it.each([false, true])("saves and tests both notification configurations with fake requests (%s)", async fail => {
  const channels = [{ type: "email", enabled: false, config: {} }, { type: "gotify", enabled: false, config: {} }];
  vi.spyOn(globalThis, "fetch").mockImplementation(async (_url, init) => new Response(JSON.stringify(init?.method ? (fail ? { detail: "Fake failure" } : { success: true }) : channels), { status: init?.method && fail ? 400 : 200 }));
  const { container } = render(<SettingsPage />);
  await screen.findByText("Notification Settings");
  for (const [label, value] of [["SMTP Host", "offline.test"], ["SMTP Port", "25"], ["SMTP Username", "operator"], ["SMTP Password / App Password", "fake"], ["From Email Address", "from@example.test"], ["Recipient Email Address", "to@example.test"], ["Gotify Server URL", "https://offline.test"], ["Gotify Application Token", "fake"]]) {
    fireEvent.change(screen.getByLabelText(label), { target: { value } });
  }
  fireEvent.click(screen.getByLabelText("Use SSL/TLS or STARTTLS connection"));
  for (const form of container.querySelectorAll("form")) {
    fireEvent.submit(form);
    await waitFor(() => expect(screen.queryByText("Saving...")).not.toBeInTheDocument());
  }
  for (const button of screen.getAllByRole("button", { name: "Test Connection" })) {
    fireEvent.click(button);
    await waitFor(() => expect(screen.queryByText("Testing...")).not.toBeInTheDocument());
  }
  if (fail) expect(screen.getAllByText("Fake failure")).toHaveLength(2);
  else expect(screen.getByText("Test email sent successfully!")).toBeInTheDocument();
});

it("shows a fetch failure", async () => {
  vi.spyOn(globalThis, "fetch").mockRejectedValue(new Error("offline"));
  render(<SettingsPage />);
  expect(await screen.findByText("Failed to load settings configuration.")).toBeInTheDocument();
});
