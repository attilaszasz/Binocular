# Research: Environment-Based Notification Settings

## Topic 1: Pydantic Settings and Multiple Alias Bindings
- **Finding**: In Pydantic v2 Settings, a field can be mapped to multiple environment variables (e.g. prefixed and non-prefixed) using `Field(validation_alias=AliasChoices("prefixed_name", "non_prefixed_name"))`. This allows fields like `smtp_password` to load from `BINOCULAR_SMTP_PASSWORD` or `SMTP_PASSWORD` cleanly.
- **Reference**: Pydantic Settings v2 documentation on AliasChoices.

## Topic 2: Docker/Compose Secrets and File Suffix Resolution
- **Finding**: Standard container secrets are mounted as files under `/run/secrets/`. The custom `load_secret_files` in `config.py` uses `_FILE` suffix mapping (e.g., `BINOCULAR_GOTIFY_TOKEN_FILE` or `GOTIFY_TOKEN_FILE`) to read credentials dynamically from files. We should extend this loader to support non-prefixed environment variables.
- **Reference**: Container secrets design patterns.

## Topic 3: FastAPI Startup Syncing and SQLite Seeding
- **Finding**: To avoid UI mismatch, environment-defined notification settings must be synchronized into the SQLite `notification_channels` table on startup. Running a seeding service during the app lifespan ensures the database remains the single runtime source of truth.
- **Reference**: FastAPI Lifespan startup events.
