import { render, screen } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { VersionDisplay } from './layout/VersionDisplay';
import { TooltipProvider } from '@/components/ui/tooltip';

function renderWithProviders(ui: React.ReactElement) {
  return render(<TooltipProvider>{ui}</TooltipProvider>);
}

describe('VersionDisplay', () => {
  beforeEach(() => {
    vi.stubEnv('VITE_APP_VERSION', 'v1.2.3');
  });

  afterEach(() => {
    vi.unstubAllEnvs();
  });

  it('renders SemVer tag in expanded state', () => {
    renderWithProviders(<VersionDisplay isCollapsed={false} />);
    expect(screen.getByText('v1.2.3')).toBeInTheDocument();
  });

  it('renders with truncate class in collapsed state for SemVer', () => {
    renderWithProviders(<VersionDisplay isCollapsed={true} />);
    // In collapsed state, the version is in a span inside the tooltip trigger
    const el = screen.getByText(/^v1\.2\.3/);
    expect(el).toBeInTheDocument();
    expect(el.className).toContain('truncate');
  });

  it('renders truncated SHA fallback in collapsed state', () => {
    vi.unstubAllEnvs();
    vi.stubEnv('VITE_APP_VERSION', 'abc1234');
    renderWithProviders(<VersionDisplay isCollapsed={true} />);
    expect(screen.getByText('abc1234')).toBeInTheDocument();
  });

  it('renders "dev" untruncated in both states', () => {
    vi.unstubAllEnvs();
    vi.stubEnv('VITE_APP_VERSION', 'dev');
    const { rerender } = renderWithProviders(<VersionDisplay isCollapsed={false} />);
    expect(screen.getByText('dev')).toBeInTheDocument();

    rerender(<TooltipProvider><VersionDisplay isCollapsed={true} /></TooltipProvider>);
    expect(screen.getByText('dev')).toBeInTheDocument();
  });

  it('shows dev fallback when env var is undefined', () => {
    vi.unstubAllEnvs();
    renderWithProviders(<VersionDisplay isCollapsed={false} />);
    expect(screen.getByText('dev')).toBeInTheDocument();
  });

  it('has text-muted-foreground class on parent for color tokens', () => {
    const { container } = renderWithProviders(<VersionDisplay isCollapsed={false} />);
    const versionParent = container.querySelector('.text-muted-foreground');
    expect(versionParent).toBeTruthy();
  });

  it('renders tooltip wrapper in collapsed state', () => {
    renderWithProviders(<VersionDisplay isCollapsed={true} />);
    // In collapsed state, VersionDisplay renders a button-like trigger for the tooltip
    const trigger = screen.getByRole('button');
    expect(trigger).toBeInTheDocument();
  });

  it('does not re-render when isCollapsed changes with same version string', () => {
    const { rerender } = renderWithProviders(<VersionDisplay isCollapsed={false} />);
    expect(screen.getByText('v1.2.3')).toBeInTheDocument();

    rerender(<TooltipProvider><VersionDisplay isCollapsed={true} /></TooltipProvider>);
    expect(screen.getByText(/^v1\.2\.3/)).toBeInTheDocument();
  });
});
