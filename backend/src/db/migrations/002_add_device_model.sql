-- Add optional manufacturer model identifier to devices.

ALTER TABLE device
ADD COLUMN model TEXT NULL;
