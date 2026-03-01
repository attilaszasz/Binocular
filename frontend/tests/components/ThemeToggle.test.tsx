import { screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { ThemeToggle } from "../../src/components/ThemeToggle";
import { renderWithProviders } from "../test-utils";

function mockMatchMedia(matches: boolean) {
  Object.defineProperty(window, "matchMedia", {
    writable: true,
    value: vi.fn().mockImplementation(() => ({
      matches,
      addEventListener: vi.fn(),
      removeEventListener: vi.fn(),
    })),
  });
}

describe("ThemeToggle", () => {
  beforeEach(() => {
    window.localStorage.clear();
    document.documentElement.classList.remove("dark");
    mockMatchMedia(false);
  });

  it("toggles theme and persists preference", async () => {
    const user = userEvent.setup();
    renderWithProviders(<ThemeToggle />);

    await user.click(screen.getByRole("button", { name: /switch to dark mode/i }));

    expect(document.documentElement.classList.contains("dark")).toBe(true);
    expect(window.localStorage.getItem("binocular-theme")).toBe("dark");
  });

  it("uses system preference when no saved value", () => {
    mockMatchMedia(true);

    renderWithProviders(<ThemeToggle />);

    expect(document.documentElement.classList.contains("dark")).toBe(true);
  });
});
