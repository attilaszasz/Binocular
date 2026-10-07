ALTER TABLE modules ADD COLUMN display_name TEXT NOT NULL DEFAULT '' CHECK(length(display_name) <= 120);
ALTER TABLE modules ADD COLUMN coverage_notes TEXT NOT NULL DEFAULT '' CHECK(length(coverage_notes) <= 1000);
ALTER TABLE modules ADD COLUMN model_examples TEXT NOT NULL DEFAULT '[]';
ALTER TABLE modules ADD COLUMN help_url TEXT NOT NULL DEFAULT '' CHECK(length(help_url) <= 2048);
ALTER TABLE modules ADD COLUMN registration_origin TEXT NOT NULL DEFAULT 'legacy' CHECK(registration_origin IN ('legacy', 'bundled', 'custom'));
ALTER TABLE modules ADD COLUMN official_content_hash TEXT NOT NULL DEFAULT '' CHECK(official_content_hash = '' OR (length(official_content_hash) = 64 AND official_content_hash NOT GLOB '*[^0-9a-f]*'));
