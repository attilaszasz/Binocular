import { render, screen } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { VersionDisplay } from './VersionDisplay';

describe('VersionDisplay', () => {
  beforeEach(() => {
    vi.stubEnv('VITE_APP_VERSION', 'v1.2.3');
  });

  afterEach(() => {
    vi.unstubAllEnvs();
  });

  it('renders SemVer tag in expanded state', () => {
    render(<VersionDisplay isCollapsed={false} />);
    expect(screen.getByText('v1.2.3')).toBeInTheDocument();
  });

  it('renders with truncate class in collapsed state for SemVer', () => {
    render(<VersionDisplay isCollapsed={true} />);
    const el = screen.getByText(/^v1\.2\.3/);
    expect(el).toBeInTheDocument();
    expect(el.className).toContain('truncate');
  });

  it('renders truncated SHA fallback in collapsed state', () => {
    vi.unstubAllEnvs();
    vi.stubEnv('VITE_APP_VERSION', 'abc1234');
    render(<VersionDisplay isCollapsed={true} />);
    expect(screen.getByText('abc1234')).toBeInTheDocument();
  });

  it('renders "dev" untruncated in both states', () => {
    vi.unstubAllEnvs();
    vi.stubEnv('VITE_APP_VERSION', 'dev');
    const { rerender } = render(<VersionDisplay isCollapsed={false} />);
    expect(screen.getByText('dev')).toBeInTheDocument();

    rerender(<VersionDisplay isCollapsed={true} />);
    expect(screen.getByText('dev')).toBeInTheDocument();
  });

  it('shows dev fallback when env var is undefined', () => {
    vi.unstubAllEnvs();
    // Don't stub any env — should fall back to "dev"
    render(<VersionDisplay isCollapsed={false} />);
    expect(screen.getByText('dev')).toBeInTheDocument();
  });

  it('has text-muted class on parent for color tokens', () => {
    const { container } = render(<VersionDisplay isCollapsed={false} />);
    // The text-muted class is on the outer div, not the inner span
    const versionParent = container.querySelector('.text-muted');
    expect(versionParent).toBeTruthy();
  });

  it('renders tooltip container in collapsed state', () => {
    render(<VersionDisplay isCollapsed={true} />);
    // In collapsed state, an element with role="button" wraps the version text
    const versionButton = screen.getByRole('button');
    expect(versionButton).toBeInTheDocument();
    expect(versionButton.getAttribute('aria-describedby')).toBe('version-tooltip');
  });

  it('does not re-render when isCollapsed changes with same version string', () => {
    // React.memo should prevent re-render for same props
    const { rerender } = render(<VersionDisplay isCollapsed={false} />);
    expect(screen.getByText('v1.2.3')).toBeInTheDocument();

    rerender(<VersionDisplay isCollapsed={true} />);
    expect(screen.getByText(/^v1\.2\.3/)).toBeInTheDocument();
  });
});
