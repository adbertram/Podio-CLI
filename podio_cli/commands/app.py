"""Application commands for Podio CLI."""
import typer
import time
import sys
from pathlib import Path
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


@app.command("create")
def create_app(
    json_file: Optional[Path] = typer.Option(None, "--json-file", "-f", help="JSON file with app configuration"),
    space_id: Optional[int] = typer.Option(None, "--space-id", "-s", help="Space ID to create app in (defaults to PODIO_WORKSPACE_ID)"),
):
    """
    Create a new Podio application.

    The app configuration must include space_id, config, and fields.
    You can either provide a JSON file with --json-file or pipe JSON via stdin.

    Examples:
        podio app create --json-file app.json
        podio app create --space-id 10479826 --json-file app.json
        cat app.json | podio app create
    """
    try:
        import json

        # Read JSON from file or stdin
        if json_file:
            with open(json_file, 'r') as f:
                app_data = json.load(f)
        else:
            # Read from stdin
            app_data = json.load(sys.stdin)

        # Override space_id if provided as option
        if space_id is not None:
            app_data['space_id'] = space_id
        elif 'space_id' not in app_data:
            # Try to use workspace_id from config
            config = get_config()
            if config.workspace_id:
                app_data['space_id'] = int(config.workspace_id)
            else:
                raise ValueError(
                    "No space_id provided in JSON and PODIO_WORKSPACE_ID not set in environment"
                )

        client = get_client()
        result = client.Application.create(attributes=app_data)
        formatted = format_response(result)

        print(f"✓ App created successfully", file=sys.stderr)
        print_json(formatted)

    except Exception as e:
        exit_code = handle_api_error(e)
        raise typer.Exit(exit_code)


@app.command("export")
def export_app(
    app_id: int = typer.Argument(..., help="Application ID to export"),
    output: Optional[str] = typer.Option(None, "--output", "-o", help="Output file path (defaults to app_name.xlsx)"),
    format: str = typer.Option("xlsx", "--format", "-f", help="Export format (xlsx or xls)"),
    limit: Optional[int] = typer.Option(None, "--limit", help="Maximum number of items to export"),
):
    """
    Export a Podio application to Excel.

    This command exports all items from an app to an Excel file.
    The export is processed asynchronously by Podio, so this command
    will poll for completion and download the file when ready.

    Examples:
        podio app export 12345
        podio app export 12345 --output my_export.xlsx
        podio app export 12345 --format xls --limit 1000
    """
    try:
        client = get_client()

        # Get app info for default filename
        if output is None:
            app_info = client.Application.find(app_id=app_id)
            app_name = app_info.get('config', {}).get('name', f'app_{app_id}')
            # Sanitize filename
            app_name = "".join(c for c in app_name if c.isalnum() or c in (' ', '-', '_')).strip()
            app_name = app_name.replace(' ', '_')
            output = f"{app_name}.{format}"

        # Prepare export attributes
        export_attrs = {}
        if limit:
            export_attrs['limit'] = limit

        # Print status to stderr so stdout can be used for JSON output
        print(f"Starting export for app {app_id}...", file=sys.stderr)

        # Start the export
        export_result = client.Item.export(app_id=app_id, exporter=format, attributes=export_attrs)
        batch_id = export_result.get('batch_id')

        if not batch_id:
            print("Error: No batch_id returned from export", file=sys.stderr)
            raise typer.Exit(1)

        print(f"Export batch created: {batch_id}", file=sys.stderr)
        print("Waiting for export to complete...", file=sys.stderr)

        # Poll for batch completion
        max_attempts = 60  # 5 minutes max (60 * 5 seconds)
        attempt = 0

        while attempt < max_attempts:
            batch_status = client.Batch.get(batch_id=batch_id)
            status = batch_status.get('status')

            if status == 'completed':
                file_id = batch_status.get('file_id')
                if not file_id:
                    print("Error: Export completed but no file_id returned", file=sys.stderr)
                    raise typer.Exit(1)

                print(f"Export completed. Downloading file {file_id}...", file=sys.stderr)

                # Download the file
                file_data = client.Files.find_raw(file_id=file_id)

                # Write to file
                output_path = Path(output)
                with open(output_path, 'wb') as f:
                    f.write(file_data)

                print(f"Export saved to: {output_path.absolute()}", file=sys.stderr)

                # Output JSON result to stdout
                result = {
                    'app_id': app_id,
                    'batch_id': batch_id,
                    'file_id': file_id,
                    'output_file': str(output_path.absolute()),
                    'format': format
                }
                print_json(result)
                return

            elif status == 'failed':
                print(f"Export failed: {batch_status}", file=sys.stderr)
                raise typer.Exit(1)

            # Still processing
            attempt += 1
            time.sleep(5)

        # Timeout
        print(f"Export timed out after {max_attempts * 5} seconds", file=sys.stderr)
        raise typer.Exit(1)

    except Exception as e:
        exit_code = handle_api_error(e)
        raise typer.Exit(exit_code)
