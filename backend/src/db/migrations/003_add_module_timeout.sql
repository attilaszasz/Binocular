-- Add configurable module execution timeout to application configuration.

ALTER TABLE app_config
ADD COLUMN module_execution_timeout_seconds INTEGER NOT NULL DEFAULT 30;
