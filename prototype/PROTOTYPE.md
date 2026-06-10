# Prototype Archive

> This directory contains the first-pass implementation archived by `/sddp-regen`.
> All contents are read-only reference material for the V2 regeneration.

- **Archived**: 2026-06-10
- **Git SHA**: 4f3851a3f234fceccbe0b282ae19e1da097d8556
- **Completed Epics**: 31/31
- **Feature Workspaces**: 32 (00001 through 00032)
- **Source Root**: `backend/src/`, `frontend/src/`

## Epic Summary

| Epic | Status | Feature Workspace |
|------|--------|-------------------|
| E001 Application Skeleton & Container | ✓ | 00001-application-skeleton-container |
| E002 Continuous Integration Pipeline | ✓ | 00002-continuous-integration-pipeline |
| E003 Frontend SPA Shell | ✓ | 00003-frontend-spa-shell |
| E004 Data Layer & Migrations | ✓ | 00004-data-layer-migrations |
| E005 Device Inventory Management | ✓ | 00006-device-inventory-management |
| E006 Module Engine & Contract | ✓ | 00007-module-engine-contract |
| E007 Responsible Scraping Client | ✓ | 00005-responsible-scraping-client |
| E008 Module Lifecycle Management | ✓ | 00010-module-lifecycle-management |
| E009 Update Detection & Comparison | ✓ | 00011-update-detection-comparison |
| E010 Manual On-Demand Checks | ✓ | 00014-manual-on-demand-checks |
| E011 Automated Scheduled Checking | ✓ | 00015-automated-scheduled-checking |
| E012 Notification & Alerting | ✓ | 00017-notification-alerting-apprise |
| E013 Self-Hosted Operability | ✓ | 00008-self-hosted-operability |
| E014 Activity Logging & Visibility | ✓ | 00018-activity-logging-visibility |
| E015 Official Sony Alpha Module | ✓ | 00012-official-sony-alpha-module |
| E016 Responsive UI & Dark Mode | ✓ | 00023-responsive-ui-dark-mode |
| E017 Module Dev Kit & Docs | ✓ | 00016-module-dev-kit-docs-authoring |
| E018 Release & Publish Pipeline | ✓ | 00009-release-publish-pipeline |
| E019 Backup & Restore Operations | ✓ | 00019-backup-restore-operations |
| E020 Official Panasonic Lumix Module | ✓ | 00013-now-implement-in-the-same-way |
| E021 Automatic Module Seeding | ✓ | 00021-automatic-module-seeding |
| E022 Device-Module Linking & Refactor | ✓ | 00022-device-module-linking-refactor |
| E023 Official Panasonic Lumix Lenses Module | ✓ | 00024-official-panasonic-lumix-lenses-module |
| E024 Official Godox Flashes Module | ✓ | 00025-official-godox-flashes-module-godox |
| E025 PUID/PGID Entrypoint | ✓ | 00026-puid-pgid-entrypoint |
| E026 Per-Module Frequency on Modules Page | ✓ | 00027-per-module-frequency-on-modules |
| E027 HTML Email Notification Design | ✓ | 00028-html-email-notification-design |
| E028 Notification Deduplication | ✓ | 00029-notification-deduplication |
| E029 Collapsible Menu & Version Display | ✓ | 00030-collapsible-menu-version-display |
| E030 Shadcn UI Component Library Migration | ✓ | 00031-shadcn-ui-component-library-migration |
| E031 AI-Assisted Module Authoring UX | ✓ | 00032-ai-assisted-module-authoring-ux |

## Archive Contents

```
prototype/
├── backend/
│   ├── src/binocular/       # Python backend source
│   ├── tests/               # Backend tests + fixtures
│   ├── modules/             # Backend bundled modules
│   ├── pyproject.toml
│   └── uv.lock
├── frontend/
│   ├── src/                 # React/TypeScript frontend source
│   ├── e2e/                 # Playwright E2E tests
│   ├── public/              # Static assets
│   ├── package.json
│   └── vite.config.ts
├── docker/
│   ├── entrypoint.sh        # PUID/PGID entrypoint
│   └── test-entrypoint.sh
├── docs/                    # User-facing documentation
├── modules/                 # Root-level official modules
├── scripts/                 # Dev scripts
├── specs/
│   ├── prd.md               # Product Requirements Document
│   ├── sad.md               # System Architecture Document
│   ├── dod.md               # Deployment & Operations Document
│   ├── project-plan.md      # Project Implementation Plan
│   ├── adrs/                # Architecture Decision Records (ADR-0001 through ADR-0009)
│   └── 00001-* through 00032-*/  # Feature workspaces
├── Dockerfile
├── compose.yaml
├── .env.example
├── .dockerignore
├── README.md
├── LICENSE
├── package.json
└── PROTOTYPE.md             # This manifest
```
