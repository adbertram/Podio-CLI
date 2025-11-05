"""Item commands for Podio CLI."""
import json
import sys
from typing import Optional
from pathlib import Path
import typer

from ..client import get_client
from ..output import print_json, print_error, print_success, handle_api_error, format_response

app = typer.Typer(help="Manage Podio items")


@app.command("get")
def get_item(
    item_id: int = typer.Argument(..., help="Item ID to retrieve"),
    basic: bool = typer.Option(False, "--basic", help="Get basic item info only"),
):
    """
    Get a Podio item by ID.

    Examples:
        podio item get 12345
        podio item get 12345 --basic
    """
    try:
        client = get_client()
        result = client.Item.find(item_id=item_id, basic=basic)
        formatted = format_response(result)
        print_json(formatted)
    except Exception as e:
        exit_code = handle_api_error(e)
        raise typer.Exit(exit_code)


@app.command("filter")
def filter_items(
    app_id: int = typer.Argument(..., help="Application ID to filter items from"),
    filters: Optional[str] = typer.Option(
        None,
        "--filters",
        help='JSON filter object (e.g., \'{"status": "active"}\')',
    ),
    limit: int = typer.Option(30, "--limit", help="Maximum number of items to return"),
    offset: int = typer.Option(0, "--offset", help="Offset for pagination"),
    sort_by: Optional[str] = typer.Option(
        None,
        "--sort-by",
        help="Field to sort by",
    ),
    sort_desc: bool = typer.Option(False, "--desc", help="Sort in descending order"),
):
    """
    Filter items in a Podio application.

    Examples:
        podio item filter 12345
        podio item filter 12345 --filters '{"status": "active"}'
        podio item filter 12345 --limit 100 --offset 0
        podio item filter 12345 --sort-by "created_on" --desc
    """
    try:
        client = get_client()

        # Build filter attributes
        attributes = {
            "limit": limit,
            "offset": offset,
        }

        # Parse JSON filters if provided
        if filters:
            try:
                filter_dict = json.loads(filters)
                attributes["filters"] = filter_dict
            except json.JSONDecodeError as e:
                print_error(f"Invalid JSON in --filters: {e}")
                raise typer.Exit(1)

        # Add sorting if specified
        if sort_by:
            attributes["sort_by"] = sort_by
            attributes["sort_desc"] = sort_desc

        result = client.Item.filter(app_id=app_id, attributes=attributes)
        formatted = format_response(result)
        print_json(formatted)
    except Exception as e:
        exit_code = handle_api_error(e)
        raise typer.Exit(exit_code)


@app.command("create")
def create_item(
    app_id: int = typer.Argument(..., help="Application ID to create item in"),
    json_file: Optional[Path] = typer.Option(
        None,
        "--json-file",
        help="Path to JSON file with item data",
    ),
    silent: bool = typer.Option(False, "--silent", help="Suppress Podio notifications"),
    no_hook: bool = typer.Option(False, "--no-hook", help="Skip webhook execution"),
):
    """
    Create a new item in a Podio application.

    Reads item data from a JSON file or stdin.

    Item data format:
        {
            "fields": [
                {"external_id": "title", "values": [{"value": "Item Title"}]},
                {"external_id": "status", "values": [{"value": "active"}]}
            ]
        }

    Examples:
        podio item create 12345 --json-file item.json
        cat item.json | podio item create 12345
        podio item create 12345 --json-file item.json --silent
    """
    try:
        client = get_client()

        # Read item data from file or stdin
        if json_file:
            if not json_file.exists():
                print_error(f"File not found: {json_file}")
                raise typer.Exit(1)
            with open(json_file) as f:
                item_data = json.load(f)
        else:
            # Read from stdin
            try:
                item_data = json.load(sys.stdin)
            except json.JSONDecodeError as e:
                print_error(f"Invalid JSON from stdin: {e}")
                raise typer.Exit(1)

        # Validate that we have fields
        if "fields" not in item_data:
            print_error("Item data must contain 'fields' key")
            raise typer.Exit(1)

        result = client.Item.create(
            app_id=app_id,
            attributes=item_data,
            silent=silent,
            hook=not no_hook
        )
        formatted = format_response(result)
        print_success("Item created successfully")
        print_json(formatted)
    except Exception as e:
        exit_code = handle_api_error(e)
        raise typer.Exit(exit_code)


@app.command("update")
def update_item(
    item_id: int = typer.Argument(..., help="Item ID to update"),
    json_file: Optional[Path] = typer.Option(
        None,
        "--json-file",
        help="Path to JSON file with update data",
    ),
    silent: bool = typer.Option(False, "--silent", help="Suppress Podio notifications"),
    no_hook: bool = typer.Option(False, "--no-hook", help="Skip webhook execution"),
):
    """
    Update an existing Podio item.

    Reads update data from a JSON file or stdin.

    Update data format (same as create):
        {
            "fields": [
                {"external_id": "status", "values": [{"value": "completed"}]}
            ]
        }

    Examples:
        podio item update 12345 --json-file update.json
        cat update.json | podio item update 12345
    """
    try:
        client = get_client()

        # Read update data from file or stdin
        if json_file:
            if not json_file.exists():
                print_error(f"File not found: {json_file}")
                raise typer.Exit(1)
            with open(json_file) as f:
                update_data = json.load(f)
        else:
            # Read from stdin
            try:
                update_data = json.load(sys.stdin)
            except json.JSONDecodeError as e:
                print_error(f"Invalid JSON from stdin: {e}")
                raise typer.Exit(1)

        result = client.Item.update(
            item_id=item_id,
            attributes=update_data,
            silent=silent,
            hook=not no_hook
        )
        formatted = format_response(result)
        print_success(f"Item {item_id} updated successfully")
        print_json(formatted)
    except Exception as e:
        exit_code = handle_api_error(e)
        raise typer.Exit(exit_code)


@app.command("delete")
def delete_item(
    item_id: int = typer.Argument(..., help="Item ID to delete"),
    silent: bool = typer.Option(False, "--silent", help="Suppress Podio notifications"),
    no_hook: bool = typer.Option(False, "--no-hook", help="Skip webhook execution"),
):
    """
    Delete a Podio item.

    Examples:
        podio item delete 12345
        podio item delete 12345 --silent
    """
    try:
        client = get_client()
        client.Item.delete(item_id=item_id, silent=silent, hook=not no_hook)
        print_success(f"Item {item_id} deleted successfully")
        print_json({"item_id": item_id, "deleted": True})
    except Exception as e:
        exit_code = handle_api_error(e)
        raise typer.Exit(exit_code)


@app.command("values")
def get_item_values(
    item_id: int = typer.Argument(..., help="Item ID to get values from"),
):
    """
    Get field values for a specific item.

    Examples:
        podio item values 12345
    """
    try:
        client = get_client()
        result = client.Item.values(item_id=item_id)
        formatted = format_response(result)
        print_json(formatted)
    except Exception as e:
        exit_code = handle_api_error(e)
        raise typer.Exit(exit_code)
