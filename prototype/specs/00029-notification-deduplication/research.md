# Research: Notification Deduplication

**Date**: 2026-06-07

## Deduplication Strategy

State-change deduplication is the right fit for firmware versions (discrete values, not continuous metrics). Track `last_notified_version` per device. Dispatch only when `latest_version` is strictly newer than both `current_version` AND `last_notified_version` (or `last_notified_version is NULL`).

Avoid time-window suppression — would block genuine new-version detections that happen within the window. Avoid per-channel dedup state — track once per device, keep model simple.

Alert fingerprinting (Prometheus Alertmanager) and hysteresis (Grafana) are built for continuous metric streams — inappropriate here. ChangeDetection.io's state-diff model is the closest analog.

Sources: prometheus.io/docs/alerting/latest/alertmanager/ (Alertmanager dedup model), grafana.com/docs/grafana/latest/alerting/alerting-rules/ (pending/recovery periods), github.com/dgtlmoon/changedetection.io (state-diff, Apprise-using self-hosted tool)

## Edge Cases

- **User downgrades firmware**: If current_version drops below last_notified_version, dedup gate naturally prevents re-notification for the already-seen highest version — correct.
- **Manual vs scheduled checks**: Both paths funnel through `run_device_check`; shared `last_notified_version` on devices table — no special handling.
- **Dispatch failure**: Update `last_notified_version` only after at least one channel confirms success. If all channels fail, leave unchanged so next check retries. Avoid optimistic update before dispatch.
- **First detection after deployment**: NULL last_notified_version → pass-through, notify on first newer-than-current detection.

## Version Comparison

Use the existing `compare_versions()` from `version_compare.py` for the dedup check — ensures consistency with the initial update-available check. The function handles dotted-numeric, date-based, and calendar-versioning schemes; pre-release suffixes are stripped.

Do not introduce a separate comparison implementation — even minor regex differences could cause silent suppression or false re-notification.

Source: semver.org (SemVer 2.0.0 specification)
