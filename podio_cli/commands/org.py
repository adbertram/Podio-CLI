"""Organization commands for Podio CLI."""
import typer

from ..client import get_client
from ..output import print_json, handle_api_error, format_response

app = typer.Typer(help="Manage Podio organizations")


@app.command("list")
def list_orgs():
    """
    List all organizations the user is a member of.

    Returns organizations with their org_id and associated spaces.

    Examples:
        podio org list
    """
    try:
        client = get_client()
        result = client.Org.get_all()
        formatted = format_response(result)
        print_json(formatted)
    except Exception as e:
        exit_code = handle_api_error(e)
        raise typer.Exit(exit_code)
