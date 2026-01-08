"""Output formatting and error handling for Podio CLI."""
import json
import sys
from typing import Any, List, Dict, Optional

from rich.console import Console
from rich.table import Table
from rich import box


# Rich console for table output - use wide width to prevent truncation
console = Console(width=200)


def _flatten_item(item: Dict) -> Dict:
    """
    Flatten a data item by extracting useful nested values.

    Specifically handles Podio API patterns like config.name.

    Args:
        item: Dictionary to flatten

    Returns:
        Flattened dictionary with nested values promoted
    """
    flat = dict(item)

    # Extract common nested config values
    if 'config' in flat and isinstance(flat['config'], dict):
        config = flat['config']
        # Promote name to top level if not already present
        if 'name' not in flat and 'name' in config:
            flat['name'] = config['name']
        if 'item_name' not in flat and 'item_name' in config:
            flat['item_name'] = config['item_name']
        if 'description' not in flat and 'description' in config:
            flat['description'] = config['description']
        if 'type' not in flat and 'type' in config:
            flat['type'] = config['type']
        # Remove config from output since we extracted what we need
        del flat['config']

    # Extract space_id from push channel (for space objects)
    if 'space_id' not in flat and 'push' in flat and isinstance(flat['push'], dict):
        channel = flat['push'].get('channel', '')
        if channel.startswith('/space/'):
            try:
                flat['space_id'] = int(channel.split('/')[2])
            except (IndexError, ValueError):
                pass

    return flat


def print_table(data: Any, title: Optional[str] = None):
    """
    Print data as a formatted table to stdout.

    Handles both lists of dicts and single dicts.
    For nested objects, values are JSON-serialized.

    Args:
        data: Data to output as table (list of dicts or single dict)
        title: Optional table title
    """
    if data is None:
        console.print("[dim]No data[/dim]")
        return

    # Handle wrapped responses (e.g., {items: [...], total: N, filtered: N})
    if isinstance(data, dict) and 'items' in data and isinstance(data['items'], list):
        data = data['items']

    # Convert single dict to list for consistent handling
    if isinstance(data, dict):
        data = [data]

    if not isinstance(data, list) or len(data) == 0:
        console.print("[dim]No data[/dim]")
        return

    # Flatten items to extract nested values
    data = [_flatten_item(item) if isinstance(item, dict) else item for item in data]

    # Get all unique keys from all items for columns
    all_keys: List[str] = []
    for item in data:
        if isinstance(item, dict):
            for key in item.keys():
                if key not in all_keys:
                    all_keys.append(key)

    if not all_keys:
        console.print("[dim]No data[/dim]")
        return

    # Define priority columns that should be shown first (most important)
    priority_columns = [
        'item_id', 'app_id', 'task_id', 'file_id', 'space_id', 'org_id', 'form_id',  # Primary IDs
        'app_item_id',  # Item sequence number
        'name', 'title', 'text',  # Names/content
        'status',  # Status
        'url_label',  # Short identifier
        'type',  # Type info
    ]
    # Columns to hide by default (verbose data, use JSON for full output)
    hidden_columns = [
        'link', 'link_add', 'url', 'url_add',  # URL variations
        'icon', 'icon_id',  # Icons
        'sharefile_vault_url', 'item_accounting_info',  # Rarely needed
        'original', 'default_view_id',  # Internal fields
        'current_revision', 'revision', 'revisions',  # Version info
        'is_default',  # Rarely useful
        'item_name',  # Redundant with name
        'description',  # Often null or long
        'created_by', 'owner', 'push',  # Complex nested objects
        'created_on', 'last_event_on',  # Timestamps
        'post_on_new_app', 'post_on_new_member',  # Boolean flags
        'privacy', 'premium', 'is_overdue',  # Secondary info
        'created_via', 'last_activity',  # Item metadata
        'app_item_id_formatted', 'comment_count',  # Redundant/secondary
        'fields', 'rights', 'ratings', 'comments', 'tags', 'subscribed',  # Complex data
        'pinned', 'liked', 'like_count', 'grant_count',  # Social features
        'external_id', 'presence', 'subscribers',  # Advanced fields
        'initial_revision', 'priority', 'file_count',  # Item internals
        'app', 'ref', 'ref_type',  # Reference objects
        'sharefile_vault_folder_id',  # ShareFile integration
    ]

    # Reorder columns: priority first, then others (excluding hidden)
    ordered_keys = []
    for key in priority_columns:
        if key in all_keys and key not in hidden_columns:
            ordered_keys.append(key)
    for key in all_keys:
        if key not in ordered_keys and key not in hidden_columns:
            ordered_keys.append(key)

    # Limit columns for readability - fewer is better
    max_columns = 6
    if len(ordered_keys) > max_columns:
        ordered_keys = ordered_keys[:max_columns]

    if not ordered_keys:
        console.print("[dim]No data[/dim]")
        return

    # Create table with better settings for wide content
    table = Table(
        title=title,
        show_header=True,
        header_style="bold cyan",
        box=box.HEAVY_HEAD,
    )

    # Add columns - allow wrapping for long values
    for key in ordered_keys:
        table.add_column(key, no_wrap=False)

    # Add rows
    for item in data:
        if isinstance(item, dict):
            row_values = []
            for key in ordered_keys:
                value = item.get(key, "")
                # Format the value
                row_values.append(_format_cell_value(value))
            table.add_row(*row_values)

    console.print(table)


def _format_cell_value(value: Any) -> str:
    """
    Format a cell value for table display.

    Args:
        value: The value to format

    Returns:
        String representation suitable for table display
    """
    if value is None:
        return ""
    if isinstance(value, bool):
        return "✓" if value else "✗"
    if isinstance(value, (dict, list)):
        return json.dumps(value, ensure_ascii=False)
    return str(value)


def print_output(data: Any, table: bool = False, indent: int = 2):
    """
    Print data in the specified format (JSON or table).

    Args:
        data: Data to output
        table: If True, output as table; otherwise as JSON
        indent: JSON indentation level (only used for JSON output)
    """
    if table:
        print_table(data)
    else:
        print_json(data, indent)


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


def print_warning(message: str):
    """
    Print warning message to stderr (yellow).

    Args:
        message: Warning message to print
    """
    yellow = "\033[93m"
    reset = "\033[0m"
    print(f"{yellow}Warning: {message}{reset}", file=sys.stderr)


def print_info(message: str):
    """
    Print informational message to stderr.

    Args:
        message: Info message to print
    """
    print(message, file=sys.stderr)


def handle_api_error(error: Exception) -> int:
    """
    Handle API errors and return appropriate exit code.

    Args:
        error: Exception from API call

    Returns:
        int: Exit code (1 for general errors, 2 for auth errors)
    """
    error_str = str(error)

    # Try to extract friendly error message from TransportException
    friendly_message = None
    status_code = None

    # Check if this is a TransportException with JSON error data
    if "TransportException" in error_str:
        # Extract the JSON portion after the colon
        try:
            # Split on "): " to separate headers from JSON body
            parts = error_str.split("): ", 1)
            if len(parts) == 2:
                json_str = parts[1]
                error_data = json.loads(json_str)

                # Extract the friendly error description
                if "error_description" in error_data:
                    friendly_message = error_data["error_description"]
                elif "error" in error_data:
                    friendly_message = error_data["error"]

                # Try to extract status code from headers dict
                if "status" in parts[0]:
                    import re
                    match = re.search(r"'status':\s*'(\d+)'", parts[0])
                    if match:
                        status_code = match.group(1)
        except (json.JSONDecodeError, ValueError, IndexError):
            # If parsing fails, fall back to original error string
            pass

    # Use friendly message if available, otherwise use original error string
    display_error = friendly_message if friendly_message else error_str

    # Determine status code for error categorization
    if not status_code:
        # Fall back to searching in error string
        if "401" in error_str or "unauthorized" in error_str.lower():
            status_code = "401"
        elif "404" in error_str or "not found" in error_str.lower():
            status_code = "404"
        elif "403" in error_str or "forbidden" in error_str.lower():
            status_code = "403"
        elif "420" in error_str or "429" in error_str or "rate limit" in error_str.lower():
            status_code = "429"
        elif "400" in error_str or "bad request" in error_str.lower():
            status_code = "400"

    # Check for authentication errors
    if status_code == "401":
        print_error(
            "Authentication failed. Please check your credentials in .env file."
        )
        return 2

    # Check for not found errors
    if status_code == "404":
        print_error("Resource not found.")
        return 1

    # Check for permission errors
    if status_code == "403":
        print_error("Permission denied or invalid resource ID. Check that the ID is correct and you have access to this resource.")
        return 1

    # Check for rate limiting
    if status_code in ("420", "429"):
        print_error("Rate limit exceeded. Please try again later.")
        return 1

    # Check for validation errors
    if status_code == "400":
        print_error(f"Invalid request: {display_error}")
        return 1

    # Generic error
    print_error(f"API error: {display_error}")
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


def handle_error(error: Exception) -> int:
    """
    Handle errors and return appropriate exit code.

    Wrapper for handle_api_error for CLI standards compliance.

    Args:
        error: Exception from API call

    Returns:
        int: Exit code (1 for general errors, 2 for auth errors)
    """
    return handle_api_error(error)
