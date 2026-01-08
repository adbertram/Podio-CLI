"""Application commands for Podio CLI."""
import typer
import time
import sys
from pathlib import Path
from typing import Optional, Any, List

from ..client import get_client
from ..config import get_config
from ..output import print_json, print_output, print_error, handle_api_error, format_response

app = typer.Typer(help="Manage Podio applications")

# Subcommand group for field operations
field_app = typer.Typer(help="Manage application fields")
app.add_typer(field_app, name="field")


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


def _apply_client_filter(data: list, filters: list) -> list:
    """Apply client-side filtering using field:op:value syntax."""
    if not filters or not isinstance(data, list):
        return data

    result = data
    for f in filters:
        parts = f.split(":", 2)
        if len(parts) < 2:
            continue

        field = parts[0]
        if len(parts) == 2:
            # field:value format (exact match)
            op, value = "eq", parts[1]
        else:
            # field:op:value format
            op, value = parts[1], parts[2]

        filtered = []
        for item in result:
            item_value = item.get(field)
            if item_value is None:
                continue

            # Convert to string for comparison
            item_str = str(item_value).lower()
            value_str = value.lower()

            if op == "eq" and item_str == value_str:
                filtered.append(item)
            elif op == "ne" and item_str != value_str:
                filtered.append(item)
            elif op == "contains" and value_str in item_str:
                filtered.append(item)
            elif op == "gt" and item_str > value_str:
                filtered.append(item)
            elif op == "lt" and item_str < value_str:
                filtered.append(item)

        result = filtered

    return result


@app.command("get")
def get_app(
    app_id: int = typer.Argument(..., help="Application ID to retrieve"),
    fields: bool = typer.Option(False, "--fields", "-f", help="Return only the field schema"),
    include_deleted: bool = typer.Option(False, "--include-deleted", help="Include deleted fields in the response"),
    table: bool = typer.Option(False, "--table", "-t", help="Output as formatted table"),
):
    """
    Get a Podio application by ID.

    By default, deleted fields are excluded from the response.
    Use --include-deleted to show all fields including deleted ones.
    Use --fields to return only the field schema.

    Examples:
        podio app get 12345
        podio app get 12345 --fields
        podio app get 12345 --fields --table
        podio app get 12345 --include-deleted
        podio app get 12345 --table
    """
    try:
        client = get_client()
        result = client.Application.find(app_id=app_id)

        # Filter out deleted fields by default
        if not include_deleted and 'fields' in result:
            result['fields'] = [f for f in result['fields'] if f.get('status') != 'deleted']

        # Return only fields if requested
        if fields:
            result = result.get('fields', [])

        formatted = format_response(result)
        print_output(formatted, table=table)
    except Exception as e:
        exit_code = handle_api_error(e)
        raise typer.Exit(exit_code)


@app.command("list")
def list_apps(
    space_id: Optional[int] = typer.Option(None, "--space-id", "-s", help="Space ID to list apps from (defaults to PODIO_WORKSPACE_ID)"),
    limit: int = typer.Option(100, "--limit", "-l", help="Maximum apps to return"),
    filter: Optional[List[str]] = typer.Option(None, "--filter", "-f", help="Filter (field:op:value)"),
    properties: Optional[str] = typer.Option(None, "--properties", "-p", help="Comma-separated list of fields to include"),
    table: bool = typer.Option(False, "--table", "-t", help="Output as formatted table"),
):
    """
    List all applications in a space.

    If space_id is not provided, uses PODIO_WORKSPACE_ID from environment.

    Filter examples:
        --filter "status:active"
        --filter "name:contains:Sales"

    Examples:
        podio app list --space-id 87654321
        podio app list  # Uses PODIO_WORKSPACE_ID
        podio app list --limit 10
        podio app list --filter "status:active"
        podio app list --properties "app_id,name,link"
        podio app list --table
    """
    try:
        # Use workspace_id from config if space_id not provided
        if space_id is None:
            config = get_config()
            if config.workspace_id:
                space_id = int(config.workspace_id)
            else:
                print_error("No space_id provided and PODIO_WORKSPACE_ID not set in environment")
                raise typer.Exit(1)

        client = get_client()
        result = client.Application.list_in_space(space_id=space_id)
        formatted = format_response(result)

        # Apply client-side filter if specified
        if filter:
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


@app.command("items")
def get_app_items(
    app_id: int = typer.Argument(..., help="Application ID to get items from"),
    limit: int = typer.Option(30, "--limit", help="Maximum number of items to return"),
    offset: int = typer.Option(0, "--offset", help="Offset for pagination"),
    table: bool = typer.Option(False, "--table", "-t", help="Output as formatted table"),
):
    """
    Get all items from an application.

    Examples:
        podio app items 12345
        podio app items 12345 --limit 100
        podio app items 12345 --table
    """
    try:
        client = get_client()
        result = client.Application.get_items(app_id=app_id, limit=limit, offset=offset)
        formatted = format_response(result)
        print_output(formatted, table=table)
    except Exception as e:
        exit_code = handle_api_error(e)
        raise typer.Exit(exit_code)


@app.command("activate")
def activate_app(
    app_id: int = typer.Argument(..., help="Application ID to activate"),
    table: bool = typer.Option(False, "--table", "-t", help="Output as formatted table"),
):
    """
    Activate a Podio application.

    Examples:
        podio app activate 12345
        podio app activate 12345 --table
    """
    try:
        client = get_client()
        result = client.Application.activate(app_id=app_id)
        formatted = format_response(result)
        print_output(formatted, table=table)
    except Exception as e:
        exit_code = handle_api_error(e)
        raise typer.Exit(exit_code)


@app.command("deactivate")
def deactivate_app(
    app_id: int = typer.Argument(..., help="Application ID to deactivate"),
    table: bool = typer.Option(False, "--table", "-t", help="Output as formatted table"),
):
    """
    Deactivate a Podio application.

    Examples:
        podio app deactivate 12345
        podio app deactivate 12345 --table
    """
    try:
        client = get_client()
        result = client.Application.deactivate(app_id=app_id)
        formatted = format_response(result)
        print_output(formatted, table=table)
    except Exception as e:
        exit_code = handle_api_error(e)
        raise typer.Exit(exit_code)


@app.command("create")
def create_app(
    json_file: Optional[Path] = typer.Option(None, "--json-file", "-f", help="JSON file with app configuration"),
    space_id: Optional[int] = typer.Option(None, "--space-id", "-s", help="Space ID to create app in (defaults to PODIO_WORKSPACE_ID)"),
    table: bool = typer.Option(False, "--table", "-t", help="Output as formatted table"),
):
    """
    Create a new Podio application.

    The app configuration must include space_id, config, and fields.
    You can either provide a JSON file with --json-file or pipe JSON via stdin.

    Examples:
        podio app create --json-file app.json
        podio app create --space-id 10479826 --json-file app.json
        cat app.json | podio app create
        podio app create --json-file app.json --table
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
        print_output(formatted, table=table)

    except Exception as e:
        exit_code = handle_api_error(e)
        raise typer.Exit(exit_code)


@app.command("export")
def export_app(
    app_id: int = typer.Argument(..., help="Application ID to export"),
    output: Optional[str] = typer.Option(None, "--output", "-o", help="Output file path (defaults to app_name.xlsx)"),
    format: str = typer.Option("xlsx", "--format", "-f", help="Export format (xlsx or xls)"),
    limit: Optional[int] = typer.Option(None, "--limit", help="Maximum number of items to export"),
    table: bool = typer.Option(False, "--table", "-t", help="Output as formatted table"),
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
        podio app export 12345 --table
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
                print_output(result, table=table)
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


# Field subcommands
@field_app.command("add")
def add_field(
    app_id: int = typer.Argument(..., help="Application ID to add field to"),
    field_type: Optional[str] = typer.Option(None, "--type", help="Field type (text, number, image, date, app, money, progress, location, duration, contact, calculation, embed, question, file, tel)"),
    label: Optional[str] = typer.Option(None, "--label", "-l", help="Field label"),
    required: bool = typer.Option(False, "--required", "-r", help="Whether field is required"),
    json_file: Optional[Path] = typer.Option(None, "--json-file", "-f", help="JSON file with full field configuration (overrides other options)"),
    mimetypes: Optional[str] = typer.Option(None, "--mimetypes", "-m", help="Allowed mimetypes for file fields (comma-separated, e.g., 'application/*,image/*')"),
    table: bool = typer.Option(False, "--table", "-t", help="Output as formatted table"),
):
    """
    Add a new field to an application.

    Supported field types: text, number, image, date, app, money, progress,
    location, duration, contact, calculation, embed, question, file, tel

    You can either provide --type and --label options, or use --json-file for
    full field configuration. When using --json-file, --type and --label are
    not required.

    Examples:
        podio app field add 12345 --type text --label "Title"
        podio app field add 12345 --type file --label "Attachments" --mimetypes "application/*,image/*"
        podio app field add 12345 --json-file field.json
        podio app field add 12345 --type text --label "Title" --table
    """
    try:
        import json as json_module

        if json_file:
            with open(json_file, 'r') as f:
                field_data = json_module.load(f)
            # Extract label from JSON for success message
            field_label = field_data.get('config', {}).get('label', 'field')
        else:
            # Validate that --type and --label are provided when not using --json-file
            if not field_type:
                print_error("--type is required when not using --json-file")
                raise typer.Exit(2)
            if not label:
                print_error("--label is required when not using --json-file")
                raise typer.Exit(2)

            field_label = label
            field_data = {
                'type': field_type,
                'config': {
                    'label': label,
                    'required': required,
                }
            }

            # Add type-specific settings
            if field_type == 'file' and mimetypes:
                field_data['config']['settings'] = {
                    'allowed_mimetypes': [m.strip() for m in mimetypes.split(',')]
                }
            elif field_type == 'text':
                field_data['config']['settings'] = {
                    'size': 'small',
                    'format': 'plain'
                }

        client = get_client()
        result = client.Application.add_field(app_id=app_id, attributes=field_data)
        formatted = format_response(result)

        print(f"✓ Field '{field_label}' added successfully", file=sys.stderr)
        print_output(formatted, table=table)

    except Exception as e:
        exit_code = handle_api_error(e)
        raise typer.Exit(exit_code)


@field_app.command("get")
def get_field(
    app_id: int = typer.Argument(..., help="Application ID"),
    field_id: int = typer.Argument(..., help="Field ID to retrieve"),
    table: bool = typer.Option(False, "--table", "-t", help="Output as formatted table"),
):
    """
    Get a field from an application.

    Examples:
        podio app field get 12345 67890
        podio app field get 12345 67890 --table
    """
    try:
        client = get_client()
        result = client.Application.get_field(app_id=app_id, field_id=field_id)
        formatted = format_response(result)
        print_output(formatted, table=table)
    except Exception as e:
        exit_code = handle_api_error(e)
        raise typer.Exit(exit_code)


@field_app.command("update")
def update_field(
    app_id: int = typer.Argument(..., help="Application ID"),
    field_id: int = typer.Argument(..., help="Field ID to update"),
    json_file: Path = typer.Option(..., "--json-file", "-f", help="JSON file with field configuration"),
    table: bool = typer.Option(False, "--table", "-t", help="Output as formatted table"),
):
    """
    Update a field in an application.

    Examples:
        podio app field update 12345 67890 --json-file field.json
        podio app field update 12345 67890 --json-file field.json --table
    """
    try:
        import json as json_module

        with open(json_file, 'r') as f:
            field_data = json_module.load(f)

        client = get_client()
        result = client.Application.update_field(app_id=app_id, field_id=field_id, attributes=field_data)
        formatted = format_response(result)

        print(f"✓ Field updated successfully", file=sys.stderr)
        print_output(formatted, table=table)

    except Exception as e:
        exit_code = handle_api_error(e)
        raise typer.Exit(exit_code)


@field_app.command("delete")
def delete_field(
    app_id: int = typer.Argument(..., help="Application ID"),
    field_id: int = typer.Argument(..., help="Field ID to delete"),
    force: bool = typer.Option(False, "--force", "-f", help="Skip confirmation prompt"),
    delete_values: bool = typer.Option(False, "--delete-values", "-d", help="Also delete field values from existing items"),
    table: bool = typer.Option(False, "--table", "-t", help="Output as formatted table"),
):
    """
    Delete a field from an application.

    WARNING: This will delete all data stored in this field for all items.

    Examples:
        podio app field delete 12345 67890
        podio app field delete 12345 67890 --force
        podio app field delete 12345 67890 --delete-values
        podio app field delete 12345 67890 --table
    """
    try:
        if not force:
            confirm = typer.confirm(
                "WARNING: Deleting a field will remove all data stored in it. Use --force to skip this prompt. Continue?"
            )
            if not confirm:
                print("Aborted.", file=sys.stderr)
                raise typer.Exit(0)

        client = get_client()
        result = client.Application.delete_field(app_id=app_id, field_id=field_id, delete_values=delete_values)
        formatted = format_response(result)

        print(f"✓ Field deleted successfully", file=sys.stderr)
        print_output(formatted, table=table)

    except Exception as e:
        exit_code = handle_api_error(e)
        raise typer.Exit(exit_code)


@field_app.command("list")
def list_fields(
    app_id: int = typer.Argument(..., help="Application ID"),
    active_only: bool = typer.Option(True, "--active-only/--all", help="Show only active fields"),
    table: bool = typer.Option(False, "--table", "-t", help="Output as formatted table"),
):
    """
    List all fields in an application.

    Examples:
        podio app field list 12345
        podio app field list 12345 --all
        podio app field list 12345 --table
    """
    try:
        client = get_client()
        result = client.Application.find(app_id=app_id)

        fields = result.get('fields', [])
        if active_only:
            fields = [f for f in fields if f.get('status') == 'active']

        # Format output
        output = []
        for field in fields:
            output.append({
                'field_id': field.get('field_id'),
                'label': field.get('label'),
                'type': field.get('type'),
                'external_id': field.get('external_id'),
                'status': field.get('status'),
                'required': field.get('config', {}).get('required', False),
            })

        print_output(output, table=table)

    except Exception as e:
        exit_code = handle_api_error(e)
        raise typer.Exit(exit_code)
