from typing import Any


def format_string(value: Any) -> str:
    """Format any value as a string."""
    return str(value).strip()


def calculate_total(numbers: list[float]) -> float:
    """Calculate sum of numbers."""
    return sum(numbers)
