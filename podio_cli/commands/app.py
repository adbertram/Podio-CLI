"""Application commands for Podio CLI."""
import typer
from typing import Optional

from ..client import get_client
from ..config import get_config
from ..output import print_json, handle_api_error, format_response

app = typer.Typer(help="Manage Podio applications")


@app.command("get")
def get_app(
    app_id: int = typer.Argument(..., help="Application ID to retrieve"),
):
    """
    Get a Podio application by ID.

    Examples:
        podio app get 12345
    """
    try:
        client = get_client()
        result = client.Application.find(app_id=app_id)
        formatted = format_response(result)
        print_json(formatted)
    except Exception as e:
        exit_code = handle_api_error(e)
        raise typer.Exit(exit_code)


@app.command("list")
def list_apps(
    space_id: Optional[int] = typer.Option(None, "--space-id", "-s", help="Space ID to list apps from (defaults to PODIO_WORKSPACE_ID)"),
):
    """
    List all applications in a space.

    If space_id is not provided, uses PODIO_WORKSPACE_ID from environment.

    Examples:
        podio app list --space-id 87654321
        podio app list  # Uses PODIO_WORKSPACE_ID
    """
    try:
        # Use workspace_id from config if space_id not provided
        if space_id is None:
            config = get_config()
            if config.workspace_id:
                space_id = int(config.workspace_id)
            else:
                raise ValueError(
                    "No space_id provided and PODIO_WORKSPACE_ID not set in environment"
                )

        client = get_client()
        result = client.Application.list_in_space(space_id=space_id)
        formatted = format_response(result)
        print_json(formatted)
    except Exception as e:
        exit_code = handle_api_error(e)
        raise typer.Exit(exit_code)


@app.command("items")
def get_app_items(
    app_id: int = typer.Argument(..., help="Application ID to get items from"),
    limit: int = typer.Option(30, "--limit", help="Maximum number of items to return"),
    offset: int = typer.Option(0, "--offset", help="Offset for pagination"),
):
    """
    Get all items from an application.

    Examples:
        podio app items 12345
        podio app items 12345 --limit 100
    """
    try:
        client = get_client()
        result = client.Application.get_items(app_id=app_id, limit=limit, offset=offset)
        formatted = format_response(result)
        print_json(formatted)
    except Exception as e:
        exit_code = handle_api_error(e)
        raise typer.Exit(exit_code)


@app.command("activate")
def activate_app(
    app_id: int = typer.Argument(..., help="Application ID to activate"),
):
    """
    Activate a Podio application.

    Examples:
        podio app activate 12345
    """
    try:
        client = get_client()
        result = client.Application.activate(app_id=app_id)
        formatted = format_response(result)
        print_json(formatted)
    except Exception as e:
        exit_code = handle_api_error(e)
        raise typer.Exit(exit_code)


@app.command("deactivate")
def deactivate_app(
    app_id: int = typer.Argument(..., help="Application ID to deactivate"),
):
    """
    Deactivate a Podio application.

    Examples:
        podio app deactivate 12345
    """
    try:
        client = get_client()
        result = client.Application.deactivate(app_id=app_id)
        formatted = format_response(result)
        print_json(formatted)
    except Exception as e:
        exit_code = handle_api_error(e)
        raise typer.Exit(exit_code)
