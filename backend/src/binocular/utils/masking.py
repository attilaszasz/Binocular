from collections.abc import MutableMapping
from typing import Any

_secrets: list[str] = []


def set_secrets_to_mask(secrets: list[str]) -> None:
    """Set the list of secrets to be masked in structured logs.

    Args:
        secrets: List of secret values to mask.
    """
    global _secrets
    # Filter out empty or extremely short secrets to avoid over-masking
    _secrets = [s for s in secrets if s and len(s) >= 3]


def mask_secrets_processor(
    logger: Any,
    method_name: str,
    event_dict: MutableMapping[str, Any],
) -> MutableMapping[str, Any]:
    """Structlog processor to mask secrets in log messages and dictionary values.

    Args:
        logger: The logger instance.
        method_name: The log method name (e.g. "info").
        event_dict: The event dictionary containing the log fields.

    Returns:
        The event dictionary with secrets masked.
    """
    if not _secrets:
        return event_dict

    def _mask_value(val: Any) -> Any:
        if isinstance(val, str):
            for secret in _secrets:
                if secret in val:
                    val = val.replace(secret, "********")
            return val
        elif isinstance(val, dict):
            return {k: _mask_value(v) for k, v in val.items()}
        elif isinstance(val, list):
            return [_mask_value(v) for v in val]
        return val

    for key, value in list(event_dict.items()):
        event_dict[key] = _mask_value(value)

    return event_dict
