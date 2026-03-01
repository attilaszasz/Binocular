"""Domain exception hierarchy for API error translation."""

from __future__ import annotations


class BinocularError(Exception):
    """Base class for domain errors that map to API error envelopes."""

    error_code = "INTERNAL_ERROR"
    status_code = 500

    def __init__(self, detail: str, field: str | None = None) -> None:
        super().__init__(detail)
        self.detail = detail
        self.field = field


class NotFoundError(BinocularError):
    """Raised when a requested resource does not exist."""

    error_code = "NOT_FOUND"
    status_code = 404

    def __init__(self, resource_type: str, resource_id: int) -> None:
        super().__init__(f"{resource_type} with id {resource_id} was not found.")


class DuplicateNameError(BinocularError):
    """Raised when a uniqueness constraint is violated for a name field."""

    error_code = "DUPLICATE_NAME"
    status_code = 409

    def __init__(self, resource_type: str, name: str, field: str = "name") -> None:
        super().__init__(f"A {resource_type} named '{name}' already exists.", field=field)


class ValidationError(BinocularError):
    """Raised when a request fails domain-level validation."""

    error_code = "VALIDATION_ERROR"
    status_code = 422


class CascadeBlockedError(BinocularError):
    """Raised when deletion is blocked due to child resources."""

    error_code = "CASCADE_BLOCKED"
    status_code = 409

    def __init__(self, device_type_name: str, device_count: int) -> None:
        super().__init__(
            f"Cannot delete '{device_type_name}': {device_count} devices would also be deleted. "
            "Set confirm_cascade=true to proceed."
        )


class NoLatestVersionError(BinocularError):
    """Raised when confirm update is requested for a never-checked device."""

    error_code = "NO_LATEST_VERSION"
    status_code = 409

    def __init__(self, device_id: int) -> None:
        super().__init__(
            f"Cannot confirm update for device {device_id}: no latest seen version exists."
        )
