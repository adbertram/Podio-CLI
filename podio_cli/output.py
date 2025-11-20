"""Output formatting and error handling for Podio CLI."""
import json
import sys
from typing import Any


def print_json(data: Any, indent: int = 2):
    """
    Print data as formatted JSON to stdout.

    Args:
        data: Data to output as JSON
        indent: JSON indentation level (default: 2)
    """
    try:
        json_str = json.dumps(data, indent=indent, ensure_ascii=False)
        print(json_str)
    except (TypeError, ValueError) as e:
        print_error(f"Failed to serialize data to JSON: {e}")
        sys.exit(1)


def print_error(message: str):
    """
    Print error message to stderr.

    Args:
        message: Error message to print
    """
    print(f"Error: {message}", file=sys.stderr)


def print_success(message: str):
    """
    Print success message to stderr (keeps stdout clean for JSON).

    Args:
        message: Success message to print
    """
    print(f"✓ {message}", file=sys.stderr)


def handle_api_error(error: Exception) -> int:
    """
    Handle API errors and return appropriate exit code.

    Args:
        error: Exception from API call

    Returns:
        int: Exit code (1 for general errors, 2 for auth errors)
    """
    error_str = str(error)

    # Check for authentication errors
    if "401" in error_str or "unauthorized" in error_str.lower():
        print_error(
            "Authentication failed. Please check your credentials in .env file."
        )
        return 2

    # Check for not found errors
    if "404" in error_str or "not found" in error_str.lower():
        print_error("Resource not found.")
        return 1

    # Check for permission errors
    if "403" in error_str or "forbidden" in error_str.lower():
        print_error("Permission denied or invalid resource ID. Check that the ID is correct and you have access to this resource.")
        return 1

    # Check for rate limiting
    if "420" in error_str or "rate limit" in error_str.lower():
        print_error("Rate limit exceeded. Please try again later.")
        return 1

    # Check for validation errors
    if "400" in error_str or "bad request" in error_str.lower():
        print_error(f"Invalid request: {error_str}")
        return 1

    # Generic error
    print_error(f"API error: {error_str}")
    return 1


def format_response(data: Any) -> Any:
    """
    Format API response data for output.

    Handles common pypodio2 response patterns.

    Args:
        data: Response data from pypodio2

    Returns:
        Formatted data ready for JSON output
    """
    # pypodio2 sometimes returns tuples (response, data)
    if isinstance(data, tuple) and len(data) == 2:
        return data[1]

    return data
