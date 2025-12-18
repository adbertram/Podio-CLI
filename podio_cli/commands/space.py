"""Space commands for Podio CLI."""
import typer
from typing import Optional

from ..client import get_client
from ..config import get_config
from ..output import print_json, print_output, handle_api_error, format_response

app = typer.Typer(help="Manage Podio spaces")


@app.command("get")
def get_space(
    space_id: Optional[int] = typer.Option(None, "--space-id", "-s", help="Space ID to retrieve (defaults to PODIO_WORKSPACE_ID)"),
    table: bool = typer.Option(False, "--table", "-t", help="Output as formatted table"),
):
    """
    Get a Podio space by ID.

    If space_id is not provided, uses PODIO_WORKSPACE_ID from environment.

    Examples:
        podio space get --space-id 12345
        podio space get  # Uses PODIO_WORKSPACE_ID
        podio space get --table
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
        result = client.Space.find(space_id=space_id)
        formatted = format_response(result)
        print_output(formatted, table=table)
    except Exception as e:
        exit_code = handle_api_error(e)
        raise typer.Exit(exit_code)


@app.command("list")
def list_spaces(
    org_id: Optional[int] = typer.Option(None, "--org-id", "-o", help="Organization ID to list spaces from (defaults to PODIO_ORGANIZATION_ID)"),
    table: bool = typer.Option(False, "--table", "-t", help="Output as formatted table"),
):
    """
    List all spaces in an organization.

    If org_id is not provided, uses PODIO_ORGANIZATION_ID from environment.

    Examples:
        podio space list --org-id 3747840
        podio space list  # Uses PODIO_ORGANIZATION_ID
        podio space list --table
    """
    try:
        # Use organization_id from config if org_id not provided
        if org_id is None:
            config = get_config()
            if config.organization_id:
                org_id = int(config.organization_id)
            else:
                raise ValueError(
                    "No org_id provided and PODIO_ORGANIZATION_ID not set in environment"
                )

        client = get_client()
        result = client.Space.find_all_for_org(org_id=org_id)
        formatted = format_response(result)
        print_output(formatted, table=table)
    except Exception as e:
        exit_code = handle_api_error(e)
        raise typer.Exit(exit_code)


@app.command("find-by-url")
def find_space_by_url(
    url: str = typer.Argument(..., help="Podio space URL"),
    table: bool = typer.Option(False, "--table", "-t", help="Output as formatted table"),
):
    """
    Find a space by its URL.

    Examples:
        podio space find-by-url https://podio.com/ata-learning-llc/progress-content-management
        podio space find-by-url https://podio.com/org/workspace --table
    """
    try:
        client = get_client()
        result = client.Space.find_by_url(url=url)
        formatted = format_response(result)
        print_output(formatted, table=table)
    except Exception as e:
        exit_code = handle_api_error(e)
        raise typer.Exit(exit_code)
