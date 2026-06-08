import React from 'react';
import { Tooltip, TooltipTrigger, TooltipContent } from '@/components/ui/tooltip';

function resolveVersion(): string {
  try {
    const v = import.meta.env.VITE_APP_VERSION;
    if (typeof v === 'string' && v.length > 0) return v;
  } catch {
    // import.meta.env unavailable
  }
  return 'dev';
}

function versionType(v: string): 'semver' | 'sha' | 'dev' {
  if (v === 'dev') return 'dev';
  if (/^v?\d+\.\d+\.\d+/.test(v)) return 'semver';
  return 'sha';
}

type Props = {
  isCollapsed: boolean;
};

export const VersionDisplay = React.memo(function VersionDisplay({
  isCollapsed,
}: Props) {
  const version = resolveVersion();
  const vtype = versionType(version);

  const abbreviated = (() => {
    if (vtype === 'dev') return 'dev';
    if (vtype === 'semver') {
      const parts = version.split('-');
      return parts[0] ?? version;
    }
    return version.length > 7 ? version.slice(0, 7) + '\u2026' : version;
  })();

  if (!isCollapsed) {
    return (
      <div className="px-4">
        <div className="w-full truncate py-3 text-xs text-muted-foreground">
          <span className="block truncate">{version}</span>
        </div>
      </div>
    );
  }

  return (
    <div className="flex justify-center">
      <Tooltip>
        <TooltipTrigger asChild>
          <div
            className="w-full cursor-default py-3 text-xs text-muted-foreground"
            tabIndex={0}
            role="button"
          >
            <span
              className="block truncate text-center text-[10px]"
              title={version}
            >
              {abbreviated}
            </span>
          </div>
        </TooltipTrigger>
        <TooltipContent side="top">{version}</TooltipContent>
      </Tooltip>
    </div>
  );
});
