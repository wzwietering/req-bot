"""Common validation helpers for API schemas."""


def validate_non_empty_text(value: str, field_name: str = "Text", max_length: int | None = None) -> str:
    """Validate that text is not empty or whitespace-only.

    Args:
        value: The text value to validate
        field_name: Name of the field for error messages
        max_length: Optional maximum length to enforce

    Returns:
        Trimmed text value

    Raises:
        ValueError: If text is empty, whitespace-only, or exceeds max length
    """
    trimmed = value.strip()
    if not trimmed:
        raise ValueError(f"{field_name} cannot be empty or only whitespace")
    if max_length and len(trimmed) > max_length:
        raise ValueError(f"{field_name} exceeds maximum length of {max_length} characters")
    return trimmed
