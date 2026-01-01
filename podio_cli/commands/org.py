"""Organization commands for Podio CLI."""
import typer
from typing import Optional, Any

from ..client import get_client
from ..output import print_json, print_output, handle_api_error, format_response

app = typer.Typer(help="Manage Podio organizations")


def _apply_properties_filter(data: Any, properties: str) -> Any:
    """Filter response data to include only specified properties."""
    if not properties:
        return data

    prop_list = [p.strip() for p in properties.split(",")]

    if isinstance(data, dict):
        return {k: v for k, v in data.items() if k in prop_list}
    elif isinstance(data, list):
        return [{k: v for k, v in item.items() if k in prop_list} for item in data]

    return data


def _apply_client_filter(data: Any, filter_str: str) -> Any:
    """Apply client-side filtering based on key:value pairs."""
    if not filter_str or not isinstance(data, list):
        return data

    # Parse filter string (format: key:value or key=value)
    filters = {}
    for part in filter_str.split(","):
        if ":" in part:
            key, value = part.split(":", 1)
        elif "=" in part:
            key, value = part.split("=", 1)
        else:
            continue
        filters[key.strip()] = value.strip()

    # Apply filters
    return [
        item for item in data
        if all(str(item.get(k, "")).lower() == v.lower() for k, v in filters.items())
    ]


@app.command("list")
def list_orgs(
    limit: int = typer.Option(100, "--limit", "-l", help="Maximum organizations to return"),
    filter: Optional[str] = typer.Option(None, "--filter", "-f", help="Filter by field:value (e.g., 'name:ATA')"),
    properties: Optional[str] = typer.Option(None, "--properties", "-p", help="Comma-separated list of fields to include"),
    table: bool = typer.Option(False, "--table", "-t", help="Output as formatted table"),
):
    """
    List all organizations the user is a member of.

    Returns organizations with their org_id and associated spaces.

    Examples:
        podio org list
        podio org list --limit 10
        podio org list --filter "name:ATA"
        podio org list --properties "org_id,name"
        podio org list --table
    """
    try:
        client = get_client()
        result = client.Org.get_all()
        formatted = format_response(result)

        # Apply client-side filtering
        if filter and isinstance(formatted, list):
            formatted = _apply_client_filter(formatted, filter)

        # Apply limit (client-side)
        if isinstance(formatted, list) and len(formatted) > limit:
            formatted = formatted[:limit]

        # Apply properties filter
        if properties:
            formatted = _apply_properties_filter(formatted, properties)

        print_output(formatted, table=table)
    except Exception as e:
        exit_code = handle_api_error(e)
        raise typer.Exit(exit_code)
