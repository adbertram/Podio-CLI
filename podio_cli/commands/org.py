"""Organization commands for Podio CLI."""
import typer

from ..client import get_client
from ..output import print_json, print_output, handle_api_error, format_response

app = typer.Typer(help="Manage Podio organizations")


@app.command("list")
def list_orgs(
    table: bool = typer.Option(False, "--table", "-t", help="Output as formatted table"),
):
    """
    List all organizations the user is a member of.

    Returns organizations with their org_id and associated spaces.

    Examples:
        podio org list
        podio org list --table
    """
    try:
        client = get_client()
        result = client.Org.get_all()
        formatted = format_response(result)
        print_output(formatted, table=table)
    except Exception as e:
        exit_code = handle_api_error(e)
        raise typer.Exit(exit_code)
