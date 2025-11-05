"""Task commands for Podio CLI."""
import json
import sys
from typing import Optional
from pathlib import Path
import typer

from ..client import get_client
from ..output import print_json, print_error, print_success, handle_api_error, format_response

app = typer.Typer(help="Manage Podio tasks")


@app.command("get")
def get_task(
    task_id: int = typer.Argument(..., help="Task ID to retrieve"),
):
    """
    Get a Podio task by ID.

    Examples:
        podio task get 12345
    """
    try:
        client = get_client()
        result = client.Task.find(task_id=task_id)
        formatted = format_response(result)
        print_json(formatted)
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
        print_json(formatted)
    except Exception as e:
        exit_code = handle_api_error(e)
        raise typer.Exit(exit_code)


@app.command("complete")
def complete_task(
    task_id: int = typer.Argument(..., help="Task ID to complete"),
):
    """
    Mark a Podio task as complete.

    Examples:
        podio task complete 12345
    """
    try:
        client = get_client()
        result = client.Task.complete(task_id=task_id)
        formatted = format_response(result)
        print_success(f"Task {task_id} marked as complete")
        print_json(formatted)
    except Exception as e:
        exit_code = handle_api_error(e)
        raise typer.Exit(exit_code)


@app.command("delete")
def delete_task(
    task_id: int = typer.Argument(..., help="Task ID to delete"),
):
    """
    Delete a Podio task.

    Examples:
        podio task delete 12345
    """
    try:
        client = get_client()
        client.Task.delete(task_id=task_id)
        print_success(f"Task {task_id} deleted successfully")
        print_json({"task_id": task_id, "deleted": True})
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
):
    """
    Update an existing Podio task.

    Examples:
        podio task update 12345 --json-file update.json
        podio task update 12345 --text "Updated description"
        cat update.json | podio task update 12345
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
        print_json(formatted)
    except Exception as e:
        exit_code = handle_api_error(e)
        raise typer.Exit(exit_code)
