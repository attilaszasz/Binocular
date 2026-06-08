import React, { useRef, useState, useCallback } from 'react';

/**
 * Reads VITE_APP_VERSION (build-time constant from Docker ARG/ENV).
 * Falls back to "dev" when undefined.
 */
function resolveVersion(): string {
  try {
    const v = import.meta.env.VITE_APP_VERSION;
    if (typeof v === 'string' && v.length > 0) return v;
  } catch {
    // import.meta.env unavailable
  }
  return 'dev';
}

/**
 * Determines the type of version string for abbreviated rendering.
 */
function versionType(v: string): 'semver' | 'sha' | 'dev' {
  if (v === 'dev') return 'dev';
  if (/^v?\d+\.\d+\.\d+/.test(v)) return 'semver';
  // SHA fallback — 7 hex chars typical
  return 'sha';
}

type Props = {
  isCollapsed: boolean;
};

/**
 * Displays the application version at the bottom of the sidebar.
 *
 * In expanded state shows the full version string.
 * In collapsed state shows an abbreviated form with a tooltip.
 * Uses React.memo to avoid re-rendering when isCollapsed doesn't change
 * the rendered output (version string is a compile-time constant).
 */
export const VersionDisplay = React.memo(function VersionDisplay({ isCollapsed }: Props) {
  const version = resolveVersion();
  const vtype = versionType(version);
  const tooltipRef = useRef<HTMLDivElement>(null);
  const [tooltipVisible, setTooltipVisible] = useState(false);
  const showTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const hideTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  const clearTimers = useCallback(() => {
    if (showTimerRef.current !== null) {
      clearTimeout(showTimerRef.current);
      showTimerRef.current = null;
    }
    if (hideTimerRef.current !== null) {
      clearTimeout(hideTimerRef.current);
      hideTimerRef.current = null;
    }
  }, []);

  const showTooltip = useCallback(() => {
    clearTimers();
    setTooltipVisible(true);
  }, [clearTimers]);

  const showTooltipDelayed = useCallback(() => {
    clearTimers();
    showTimerRef.current = setTimeout(() => {
      setTooltipVisible(true);
    }, 200);
  }, [clearTimers]);

  const hideTooltip = useCallback(() => {
    clearTimers();
    setTooltipVisible(false);
  }, [clearTimers]);

  const handleKeyDown = useCallback(
    (e: React.KeyboardEvent) => {
      if (e.key === 'Escape' && tooltipVisible) {
        setTooltipVisible(false);
        (e.currentTarget as HTMLElement).focus();
      }
    },
    [tooltipVisible],
  );

  // Abbreviated version string for collapsed state
  const abbreviated = (() => {
    if (vtype === 'dev') return 'dev';
    if (vtype === 'semver') {
      // For semver like "v1.2.3-4-gabc1234-dirty", truncate
      const parts = version.split('-');
      return parts[0] ?? version;
    }
    // SHA fallback
    return version.length > 7 ? version.slice(0, 7) + '…' : version;
  })();

  // Unique ID for aria-describedby
  const tooltipId = 'version-tooltip';

  return (
    <div
      className={`relative ${isCollapsed ? 'flex justify-center' : 'px-4'}`}
      onMouseEnter={isCollapsed ? showTooltipDelayed : undefined}
      onMouseLeave={isCollapsed ? hideTooltip : undefined}
      onFocus={isCollapsed ? showTooltip : undefined}
      onBlur={isCollapsed ? hideTooltip : undefined}
    >
      <div
        className="w-full truncate py-3 text-xs text-muted"
        tabIndex={isCollapsed ? 0 : undefined}
        role={isCollapsed ? 'button' : undefined}
        aria-describedby={isCollapsed ? tooltipId : undefined}
        onKeyDown={isCollapsed ? handleKeyDown : undefined}
      >
        {isCollapsed ? (
          <span className="block truncate text-center text-[10px]" title={version}>
            {abbreviated}
          </span>
        ) : (
          <span className="block truncate">{version}</span>
        )}
      </div>

      {/* Tooltip for collapsed state */}
      {isCollapsed && tooltipVisible && (
        <div
          ref={tooltipRef}
          id={tooltipId}
          role="tooltip"
          className="absolute bottom-full left-1/2 z-50 mb-2 -translate-x-1/2 whitespace-nowrap rounded-lg border border-panel bg-panel px-3 py-1.5 text-xs text-ink shadow-lg"
        >
          {version}
        </div>
      )}
    </div>
  );
});
