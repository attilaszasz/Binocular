# Data Model

## Module

| Field | Type | Null | Rule | Purpose |
|-------|------|------|------|---------|
| source_url | TEXT | yes | Empty/NULL means no declared source | Canonical source page for model lookup |

| Migration | Change | Compatibility |
|-----------|--------|---------------|
| 0008 | Add nullable `modules.source_url` | Existing rows remain valid with NULL |

## Data Flow

| Producer | Persistence path | Consumer |
|----------|------------------|----------|
| Module loader | upload and official seeder create/update | modules API, Add Device form |
