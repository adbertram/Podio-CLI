"""Main entry point for Podio CLI."""
import sys
import typer
from typing import Optional

from .client import ClientError

# Create main Typer app
app = typer.Typer(
    name="podio",
    help="CLI interface for Podio API - Manage apps, items, tasks, and more",
    no_args_is_help=True,
    add_completion=True,
)


# Import and register command modules
# These will be imported as they're created
try:
    from .commands import item, app as app_cmd, task, space, org, auth, comment, webhook, conversation, file
    app.add_typer(item.app, name="item", help="Manage Podio items")
    app.add_typer(app_cmd.app, name="app", help="Manage Podio applications")
    app.add_typer(task.app, name="task", help="Manage Podio tasks")
    app.add_typer(space.app, name="space", help="Manage Podio spaces")
    app.add_typer(org.app, name="org", help="Manage Podio organizations")
    app.add_typer(auth.app, name="auth", help="OAuth authentication utilities")
    app.add_typer(comment.app, name="comment", help="Manage Podio comments")
    app.add_typer(webhook.app, name="webhook", help="Manage Podio webhooks")
    app.add_typer(conversation.app, name="conversation", help="Manage Podio conversations")
    app.add_typer(file.app, name="file", help="Manage Podio files")
except ImportError:
    # Commands not yet implemented - will add as we build them
    pass


@app.callback()
def callback(
    ctx: typer.Context,
    version: Optional[bool] = typer.Option(
        None,
        "--version",
        "-v",
        help="Show version and exit",
        is_eager=True,
    ),
):
    """
    Podio CLI - Automate and manage your Podio workspace from the command line.

    Authentication is handled via environment variables in your .env file:
    - PODIO_CLIENT_ID
    - PODIO_CLIENT_SECRET
    - PODIO_USERNAME
    - PODIO_PASSWORD

    Examples:
        podio item get 12345
        podio app list
        podio task create --json-file task.json
    """
    if version:
        typer.echo("podio-cli version 0.1.0")
        raise typer.Exit()


def main():
    """Main entry point for the CLI application."""
    try:
        app()
    except ClientError as e:
        typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(2)
    except KeyboardInterrupt:
        typer.echo("\nAborted!", err=True)
        raise typer.Exit(130)
    except Exception as e:
        typer.echo(f"Unexpected error: {e}", err=True)
        raise typer.Exit(1)


if __name__ == "__main__":
    main()
