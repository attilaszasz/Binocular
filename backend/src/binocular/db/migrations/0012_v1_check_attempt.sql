-- V1 attempts are not successful firmware verification timestamps.
ALTER TABLE devices ADD COLUMN last_check_attempt_at TEXT DEFAULT NULL;
