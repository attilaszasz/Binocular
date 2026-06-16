## Research Report

**Context**: Exploring best practices for compact UI card designs using Tailwind CSS and shadcn/ui, and managing derived metadata display.

## Compact Card Spacing
- **Key findings**: Reducing padding (from `p-6` to `p-4` or `p-3`) and optimizing font sizing (using `text-xs` for labels and `text-sm` for primary values) dramatically improves information density.
- **Recommended**: Use Tailwind flex-col structure with gap utilities (e.g., `space-y-2` or `gap-1.5`) to keep metadata compact and clean. Use standard shadcn components with custom padding utility overrides.
- **Avoid**: Large default margins or padding around static content.
### Sources
- https://tailwindcss.com/docs/padding — Tailwind padding utilities
- https://ui.shadcn.com/docs/components/card — Shadcn UI card component reference

## Redundant Tag Removal
- **Key findings**: When a database-derived category (like device type) has a one-to-many/many-to-many mismatch or creates visual noise, it is best to remove it and rely on explicit text labels like Model name.
- **Recommended**: Remove the derived `device_type` badge entirely to eliminate misleading categorization.
- **Avoid**: Keeping outdated or incorrect tags in high-visibility UI components.
### Sources
- https://ui.shadcn.com/docs/components/badge — Shadcn UI badge reference

### Summary
Improving layout density with optimized margins and padding values allows more inventory devices to be displayed simultaneously, while removing the badge prevents misleading categorization.

### Sources Index
| URL | Topic | Fetched |
|-----|-------|---------|
| https://tailwindcss.com/docs/padding | Compact Card Spacing | 2026-06-16 |
| https://ui.shadcn.com/docs/components/card | Compact Card Spacing | 2026-06-16 |
| https://ui.shadcn.com/docs/components/badge | Redundant Tag Removal | 2026-06-16 |
