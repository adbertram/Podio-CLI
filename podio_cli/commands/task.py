"""Task commands for Podio CLI."""
import json
import sys
from typing import Optional, List, Any
from pathlib import Path
import typer

from ..client import get_client
from ..output import print_json, print_output, print_error, print_success, print_warning, handle_api_error, format_response

app = typer.Typer(help="Manage Podio tasks")


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


def _apply_client_filter(data: List[dict], filters: List[str]) -> List[dict]:
    """Apply client-side filtering for cases where API doesn't support filtering."""
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

# Subcommand group for label operations
label_app = typer.Typer(help="Manage task labels")
app.add_typer(label_app, name="label")


@app.command("list")
def list_tasks(
    limit: int = typer.Option(100, "--limit", "-l", help="Maximum tasks to return"),
    filter: Optional[List[str]] = typer.Option(None, "--filter", "-f", help="Filter (field:op:value)"),
    properties: Optional[str] = typer.Option(None, "--properties", "-p", help="Comma-separated fields to include"),
    completed: Optional[bool] = typer.Option(None, "--completed", help="Filter by completion status"),
    grouping: Optional[str] = typer.Option(None, "--grouping", "-g", help="Group by: due_date, created_by, responsible, app, space, org"),
    sort: Optional[str] = typer.Option(None, "--sort", "-s", help="Sort by: created_on, completed_on, rank"),
    responsible: Optional[int] = typer.Option(None, "--responsible", help="Filter by responsible user ID"),
    space: Optional[int] = typer.Option(None, "--space", help="Filter by space ID"),
    table: bool = typer.Option(False, "--table", "-t", help="Output as formatted table"),
):
    """
    List tasks for the authenticated user.

    Supports filtering, grouping, and sorting via API parameters.

    Filter examples:
        --filter "status:active"
        --filter "text:contains:urgent"

    Examples:
        podio task list
        podio task list --limit 50
        podio task list --completed false
        podio task list --grouping due_date
        podio task list --space 12345 --sort created_on
        podio task list --filter "status:active" --properties "task_id,text,due_date"
        podio task list --table
    """
    try:
        client = get_client()

        # Build API parameters
        params = {"limit": limit}
        if completed is not None:
            params["completed"] = completed
        if grouping:
            params["grouping"] = grouping
        if sort:
            params["sort_by"] = sort
        if responsible:
            params["responsible"] = responsible
        if space:
            params["space"] = space

        # Use raw transport for task listing
        result = client.transport.GET(url="/task/", **params)
        formatted = format_response(result)

        # Apply client-side filter if specified
        if filter:
            formatted = _apply_client_filter(formatted, filter)

        # Apply limit (client-side as backup)
        if isinstance(formatted, list) and len(formatted) > limit:
            formatted = formatted[:limit]

        # Apply properties filter
        if properties:
            formatted = _apply_properties_filter(formatted, properties)

        print_output(formatted, table=table)
    except Exception as e:
        exit_code = handle_api_error(e)
        raise typer.Exit(exit_code)


@label_app.command("list")
def label_list(
    table: bool = typer.Option(False, "--table", "-t", help="Output as formatted table"),
):
    """
    List all task labels for the authenticated user.

    Examples:
        podio task label list
        podio task label list --table
    """
    try:
        client = get_client()
        result = client.Task.get_labels()
        formatted = format_response(result)
        print_output(formatted, table=table)
    except Exception as e:
        exit_code = handle_api_error(e)
        raise typer.Exit(exit_code)


@label_app.command("create")
def label_create(
    text: str = typer.Argument(..., help="Label text/name"),
    color: Optional[str] = typer.Option(None, "--color", "-c", help="Label color (hex code or color name)"),
    table: bool = typer.Option(False, "--table", "-t", help="Output as formatted table"),
):
    """
    Create a new task label.

    Examples:
        podio task label create "High Priority"
        podio task label create "Urgent" --color red
        podio task label create "Review" --color "#FF5733"
    """
    try:
        client = get_client()
        result = client.Task.create_label(text=text, color=color)
        formatted = format_response(result)
        print_success(f"Label '{text}' created successfully")
        print_output(formatted, table=table)
    except Exception as e:
        exit_code = handle_api_error(e)
        raise typer.Exit(exit_code)


@label_app.command("update")
def label_update(
    task_id: int = typer.Argument(..., help="Task ID to update labels on"),
    labels: str = typer.Option(..., "--labels", "-l", help="Comma-separated label IDs or names"),
    table: bool = typer.Option(False, "--table", "-t", help="Output as formatted table"),
):
    """
    Update labels on a task. This replaces all existing labels.

    Examples:
        podio task label update 12345 --labels "123,456"
        podio task label update 12345 --labels "High Priority,Urgent"
    """
    try:
        client = get_client()

        # Parse labels - could be IDs or names
        label_list_parsed = [l.strip() for l in labels.split(",")]

        # Try to convert to integers if they look like IDs
        parsed_labels: List = []
        for label in label_list_parsed:
            try:
                parsed_labels.append(int(label))
            except ValueError:
                # It's a label name, keep as string
                parsed_labels.append(label)

        result = client.Task.update_labels(task_id=task_id, labels=parsed_labels)
        formatted = format_response(result)
        print_success(f"Labels updated on task {task_id}")
        print_output(formatted, table=table)
    except Exception as e:
        exit_code = handle_api_error(e)
        raise typer.Exit(exit_code)


@label_app.command("delete")
def label_delete(
    label_id: int = typer.Argument(..., help="Label ID to delete"),
    table: bool = typer.Option(False, "--table", "-t", help="Output as formatted table"),
):
    """
    Delete a task label.

    Examples:
        podio task label delete 12345
    """
    try:
        client = get_client()
        client.Task.delete_label(label_id=label_id)
        print_success(f"Label {label_id} deleted successfully")
        print_output({"label_id": label_id, "deleted": True}, table=table)
    except Exception as e:
        exit_code = handle_api_error(e)
        raise typer.Exit(exit_code)


@app.command("get")
def get_task(
    task_id: int = typer.Argument(..., help="Task ID to retrieve"),
    table: bool = typer.Option(False, "--table", "-t", help="Output as formatted table"),
):
    """
    Get a Podio task by ID.

    Examples:
        podio task get 12345
        podio task get 12345 --table
    """
    try:
        client = get_client()
        result = client.Task.find(task_id=task_id)
        formatted = format_response(result)
        print_output(formatted, table=table)
    except Exception as e:
        exit_code = handle_api_error(e)
        raise typer.Exit(exit_code)


@app.command("create")
def create_task(
    json_file: Optional[Path] = typer.Option(
        None,
        "--json-file",
        help="Path to JSON file with task data",
    ),
    text: Optional[str] = typer.Option(None, "--text", help="Task text/description"),
    ref_type: Optional[str] = typer.Option(
        None,
        "--ref-type",
        help="Reference type (e.g., 'item', 'app')",
    ),
    ref_id: Optional[int] = typer.Option(None, "--ref-id", help="Reference ID"),
    due_date: Optional[str] = typer.Option(
        None,
        "--due-date",
        help="Due date (YYYY-MM-DD format)",
    ),
    private: bool = typer.Option(False, "--private", help="Make task private"),
    table: bool = typer.Option(False, "--table", "-t", help="Output as formatted table"),
):
    """
    Create a new Podio task.

    Task data can be provided via JSON file/stdin or command-line options.

    Task data format:
        {
            "text": "Task description",
            "description": "Detailed description",
            "due_date": "2025-01-15",
            "private": false,
            "ref_type": "item",
            "ref_id": 12345
        }

    Examples:
        podio task create --json-file task.json
        cat task.json | podio task create
        podio task create --text "Follow up" --ref-type item --ref-id 12345
        podio task create --text "Follow up" --table
    """
    try:
        client = get_client()

        # Determine input method
        if json_file or (not sys.stdin.isatty() and not text):
            # Read from file or stdin
            if json_file:
                if not json_file.exists():
                    print_error(f"File not found: {json_file}")
                    raise typer.Exit(1)
                with open(json_file) as f:
                    task_data = json.load(f)
            else:
                try:
                    task_data = json.load(sys.stdin)
                except json.JSONDecodeError as e:
                    print_error(f"Invalid JSON from stdin: {e}")
                    raise typer.Exit(1)
        else:
            # Build from command-line options
            if not text:
                print_error("Either --text or --json-file/stdin is required")
                raise typer.Exit(1)

            task_data = {"text": text, "private": private}
            if ref_type:
                task_data["ref_type"] = ref_type
            if ref_id:
                task_data["ref_id"] = ref_id
            if due_date:
                task_data["due_date"] = due_date

        result = client.Task.create(attributes=task_data)
        formatted = format_response(result)
        print_success("Task created successfully")
        print_output(formatted, table=table)
    except Exception as e:
        exit_code = handle_api_error(e)
        raise typer.Exit(exit_code)


@app.command("complete")
def complete_task(
    task_id: int = typer.Argument(..., help="Task ID to complete"),
    table: bool = typer.Option(False, "--table", "-t", help="Output as formatted table"),
):
    """
    Mark a Podio task as complete.

    Examples:
        podio task complete 12345
        podio task complete 12345 --table
    """
    try:
        client = get_client()
        result = client.Task.complete(task_id=task_id)
        formatted = format_response(result)
        print_success(f"Task {task_id} marked as complete")
        print_output(formatted, table=table)
    except Exception as e:
        exit_code = handle_api_error(e)
        raise typer.Exit(exit_code)


@app.command("delete")
def delete_task(
    task_id: int = typer.Argument(..., help="Task ID to delete"),
    table: bool = typer.Option(False, "--table", "-t", help="Output as formatted table"),
):
    """
    Delete a Podio task.

    Examples:
        podio task delete 12345
        podio task delete 12345 --table
    """
    try:
        client = get_client()
        client.Task.delete(task_id=task_id)
        print_success(f"Task {task_id} deleted successfully")
        print_output({"task_id": task_id, "deleted": True}, table=table)
    except Exception as e:
        exit_code = handle_api_error(e)
        raise typer.Exit(exit_code)


@app.command("update")
def update_task(
    task_id: int = typer.Argument(..., help="Task ID to update"),
    json_file: Optional[Path] = typer.Option(
        None,
        "--json-file",
        help="Path to JSON file with update data",
    ),
    text: Optional[str] = typer.Option(None, "--text", help="Update task text"),
    due_date: Optional[str] = typer.Option(
        None,
        "--due-date",
        help="Update due date (YYYY-MM-DD format)",
    ),
    table: bool = typer.Option(False, "--table", "-t", help="Output as formatted table"),
):
    """
    Update an existing Podio task.

    Examples:
        podio task update 12345 --json-file update.json
        podio task update 12345 --text "Updated description"
        cat update.json | podio task update 12345
        podio task update 12345 --text "Updated" --table
    """
    try:
        client = get_client()

        # Determine input method
        if json_file or (not sys.stdin.isatty() and not text):
            # Read from file or stdin
            if json_file:
                if not json_file.exists():
                    print_error(f"File not found: {json_file}")
                    raise typer.Exit(1)
                with open(json_file) as f:
                    update_data = json.load(f)
            else:
                try:
                    update_data = json.load(sys.stdin)
                except json.JSONDecodeError as e:
                    print_error(f"Invalid JSON from stdin: {e}")
                    raise typer.Exit(1)
        else:
            # Build from command-line options
            if not text and not due_date:
                print_error("Provide --text, --due-date, or --json-file/stdin")
                raise typer.Exit(1)

            update_data = {}
            if text:
                update_data["text"] = text
            if due_date:
                update_data["due_date"] = due_date

        result = client.Task.update(task_id=task_id, attributes=update_data)
        formatted = format_response(result)
        print_success(f"Task {task_id} updated successfully")
        print_output(formatted, table=table)
    except Exception as e:
        exit_code = handle_api_error(e)
        raise typer.Exit(exit_code)


@app.command("list-labels", hidden=True)
def list_labels_deprecated(
    table: bool = typer.Option(False, "--table", "-t", help="Output as formatted table"),
):
    """[DEPRECATED] Use 'podio task label list' instead."""
    print_warning("'podio task list-labels' is deprecated. Use 'podio task label list' instead.")
    return label_list(table=table)


@app.command("create-label", hidden=True)
def create_label_deprecated(
    text: str = typer.Argument(..., help="Label text/name"),
    color: Optional[str] = typer.Option(None, "--color", help="Label color (hex code or color name)"),
    table: bool = typer.Option(False, "--table", "-t", help="Output as formatted table"),
):
    """[DEPRECATED] Use 'podio task label create' instead."""
    print_warning("'podio task create-label' is deprecated. Use 'podio task label create' instead.")
    return label_create(text=text, color=color, table=table)


@app.command("update-labels", hidden=True)
def update_labels_deprecated(
    task_id: int = typer.Argument(..., help="Task ID"),
    labels: str = typer.Option(..., "--labels", help="Comma-separated label IDs or names"),
    table: bool = typer.Option(False, "--table", "-t", help="Output as formatted table"),
):
    """[DEPRECATED] Use 'podio task label update' instead."""
    print_warning("'podio task update-labels' is deprecated. Use 'podio task label update' instead.")
    return label_update(task_id=task_id, labels=labels, table=table)


@app.command("delete-label", hidden=True)
def delete_label_deprecated(
    label_id: int = typer.Argument(..., help="Label ID to delete"),
    table: bool = typer.Option(False, "--table", "-t", help="Output as formatted table"),
):
    """[DEPRECATED] Use 'podio task label delete' instead."""
    print_warning("'podio task delete-label' is deprecated. Use 'podio task label delete' instead.")
    return label_delete(label_id=label_id, table=table)
