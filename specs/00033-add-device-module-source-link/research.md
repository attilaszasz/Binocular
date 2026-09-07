# Research

## Optional metadata and SQLite migration

SQLite supports `ALTER TABLE ... ADD COLUMN`; a nullable column preserves existing module rows without a data rewrite. Keep source metadata optional end-to-end so existing third-party modules remain valid. Source: [SQLite ALTER TABLE](https://www.sqlite.org/lang_altertable.html).

## External source link

Render a selected module's canonical page only when a non-empty URL exists. A link opened in a new tab should use `rel="noreferrer"`, which also prevents the new page from retaining an opener. Source: [MDN rel attribute](https://developer.mozilla.org/en-US/docs/Web/HTML/Reference/Attributes/rel).
