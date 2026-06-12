import "@testing-library/jest-dom"
import { render, screen } from "@testing-library/react"
import { describe, it, expect } from "vitest"
import { MemoryRouter } from "react-router-dom"
import { Monitor } from "lucide-react"
import { NavItem } from "./nav-item"
import { TooltipProvider } from "@/components/ui/tooltip"

describe("NavItem", () => {
  it("renders with label when not collapsed", () => {
    render(
      <MemoryRouter>
        <NavItem to="/inventory" label="Inventory" icon={Monitor} collapsed={false} />
      </MemoryRouter>
    )

    expect(screen.getByText("Inventory")).toBeInTheDocument()
    const link = screen.getByRole("link")
    expect(link).toBeInTheDocument()
    
    // Check it has layout classes for expanded state and NO literal function strings
    expect(link.className).not.toContain("({ isActive }) =>")
    expect(link.className).toContain("gap-3")
    expect(link.className).toContain("px-3")
  })

  it("renders without label and with tooltip when collapsed", () => {
    render(
      <MemoryRouter>
        <TooltipProvider>
          <NavItem to="/inventory" label="Inventory" icon={Monitor} collapsed={true} />
        </TooltipProvider>
      </MemoryRouter>
    )

    // The label text shouldn't be rendered directly (it's inside the tooltip content, which isn't open yet)
    expect(screen.queryByText("Inventory")).not.toBeInTheDocument()
    
    const link = screen.getByRole("link")
    expect(link).toBeInTheDocument()
    
    // Check it does not contain the callback function string literal
    expect(link.className).not.toContain("({ isActive }) =>")
    
    // When collapsed, it should have justify-center and px-2 (instead of gap-3/px-3)
    expect(link.className).toContain("justify-center")
    expect(link.className).toContain("px-2")
    expect(link.className).not.toContain("gap-3")
    expect(link.className).not.toContain("px-3")
  })
})
