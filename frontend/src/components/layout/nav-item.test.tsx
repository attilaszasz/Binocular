import "@testing-library/jest-dom";
import { render, screen } from "@testing-library/react";
import { it, expect } from "vitest";
import { MemoryRouter } from "react-router-dom";
import { Camera } from "lucide-react";
import { TooltipProvider } from "@/components/ui/tooltip";
import { NavItem } from "./nav-item";

it.each([true, false])("preserves all navigation names without opening tooltips (collapsed=%s)", collapsed => {
  render(<MemoryRouter initialEntries={["/modules"]}><TooltipProvider>
    {[["/inventory", "Inventory"], ["/modules", "Modules"], ["/logs", "Logs"], ["/settings", "Settings"]].map(([to, label]) =>
      <NavItem key={to} to={to} label={label} icon={Camera} collapsed={collapsed} />)}
  </TooltipProvider></MemoryRouter>);
  for (const label of ["Inventory", "Modules", "Logs", "Settings"]) {
    const link = screen.getByRole("link", { name: label });
    expect(link).toHaveAttribute("aria-label", label);
    if (label === "Modules") expect(link).toHaveAttribute("aria-current", "page");
    else expect(link).not.toHaveAttribute("aria-current");
  }
  expect(screen.queryByRole("tooltip")).not.toBeInTheDocument();
});

it.each(["/modules/123", "/modules-other"])("marks only the active route or its descendants current (%s)", pathname => {
  render(<MemoryRouter initialEntries={[pathname]}><TooltipProvider>
    <NavItem to="/modules" label="Modules" icon={Camera} collapsed />
  </TooltipProvider></MemoryRouter>);
  const link = screen.getByRole("link", { name: "Modules" });
  if (pathname === "/modules/123") expect(link).toHaveAttribute("aria-current", "page");
  else expect(link).not.toHaveAttribute("aria-current");
});
