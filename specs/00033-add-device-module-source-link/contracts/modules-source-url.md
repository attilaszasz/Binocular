# Modules Source URL Contract

## GET /api/v1/modules

| Field | Type | Required | Semantics |
|-------|------|----------|-----------|
| source_url | string | yes | Declared canonical URL, or empty string when absent |

## Compatibility

| Scenario | Response |
|----------|----------|
| Existing module row | `source_url: ""` |
| Module omits constant | `source_url: ""` |
| Module declares constant | Declared string |
