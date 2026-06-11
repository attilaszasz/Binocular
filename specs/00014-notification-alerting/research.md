# Research: Notification & Alerting

## Apprise Integration for Email & Gotify
Apprise is a Python library that provides unified access to multiple notification services. To dispatch notifications, we instantiate `apprise.Apprise()`, add target URLs (e.g., `mailto://user:pass@smtp.server.com` or `gotify://host/token`), and call the async-friendly or synchronous `send()` method. Apprise handles transport, retries, and protocol-specific payload formatting internally, simplifying the dispatch of alerts.
Sources: Apprise GitHub Documentation, Python Apprise API Reference.

## Jinja2 HTML Email Templates
Jinja2 allows dynamic HTML rendering. For light-themed, mobile-friendly emails, we design a clean HTML template using inline CSS since many email clients ignore external or block styles. The layout should include a responsive container, high-contrast text, and simple branding that aligns with Binocular's light theme. The template receives context variables like `device_name`, `module_name`, `old_version`, `new_version`, and `update_url`.
Sources: HTML Email Design Guide, Jinja2 Documentation.

## Notification Deduplication via last_notified_version
To prevent alert fatigue, notifications must only be dispatched when a newly detected firmware version is strictly newer than the device's recorded `last_notified_version`. By tracking this state on the `devices` table, the check runner can inspect the check result, compare versions using semantic versioning rules, and perform the dispatch only if the new version is greater.
Sources: Semantic Versioning Specification, Database State Pattern.

## Notification Channel Configuration & Testing
A flexible notification system requires persistent channel configurations in the database (e.g., `notification_channels` table storing type, config JSON, and enabled status). To help the operator verify settings immediately, a test endpoint `/api/v1/notifications/test` should accept a channel configuration, attempt a test dispatch via Apprise, and return the outcome (success or error detail) dynamically.
Sources: FastAPI Endpoint Design, UX Settings Validation Patterns.
