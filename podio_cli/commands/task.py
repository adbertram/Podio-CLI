"""Task commands for Podio CLI."""
import json
import sys
from typing import Optional
from pathlib import Path
import typer

from ..client import get_client
from ..output import print_json, print_output, print_error, print_success, handle_api_error, format_response

app = typer.Typer(help="Manage Podio tasks")


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


@app.command("list-labels")
def list_labels(
    table: bool = typer.Option(False, "--table", "-t", help="Output as formatted table"),
):
    """
    List all task labels for the authenticated user.

    Examples:
        podio task list-labels
        podio task list-labels --table
    """
    try:
        client = get_client()
        result = client.Task.get_labels()
        formatted = format_response(result)
        print_output(formatted, table=table)
    except Exception as e:
        exit_code = handle_api_error(e)
        raise typer.Exit(exit_code)


@app.command("create-label")
def create_label(
    text: str = typer.Argument(..., help="Label text/name"),
    color: Optional[str] = typer.Option(None, "--color", help="Label color (hex code or color name)"),
    table: bool = typer.Option(False, "--table", "-t", help="Output as formatted table"),
):
    """
    Create a new task label.

    Examples:
        podio task create-label "High Priority"
        podio task create-label "Urgent" --color "red"
        podio task create-label "Review" --color "#FF5733"
        podio task create-label "Urgent" --table
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


@app.command("update-labels")
def update_task_labels(
    task_id: int = typer.Argument(..., help="Task ID"),
    labels: str = typer.Option(..., "--labels", help="Comma-separated label IDs or names"),
    table: bool = typer.Option(False, "--table", "-t", help="Output as formatted table"),
):
    """
    Update labels on a task. This replaces all existing labels.

    Examples:
        podio task update-labels 12345 --labels "123,456"
        podio task update-labels 12345 --labels "High Priority,Urgent"
        podio task update-labels 12345 --labels "123,456" --table
    """
    try:
        client = get_client()

        # Parse labels - could be IDs or names
        label_list = [l.strip() for l in labels.split(",")]

        # Try to convert to integers if they look like IDs
        parsed_labels = []
        for label in label_list:
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


@app.command("delete-label")
def delete_label(
    label_id: int = typer.Argument(..., help="Label ID to delete"),
    table: bool = typer.Option(False, "--table", "-t", help="Output as formatted table"),
):
    """
    Delete a task label.

    Examples:
        podio task delete-label 12345
        podio task delete-label 12345 --table
    """
    try:
        client = get_client()
        client.Task.delete_label(label_id=label_id)
        print_success(f"Label {label_id} deleted successfully")
        print_output({"label_id": label_id, "deleted": True}, table=table)
    except Exception as e:
        exit_code = handle_api_error(e)
        raise typer.Exit(exit_code)
