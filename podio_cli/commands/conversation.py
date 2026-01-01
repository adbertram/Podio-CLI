"""Conversation (message) commands for Podio CLI."""
import json
import sys
from typing import Optional, List, Any
from pathlib import Path
import typer

from ..client import get_client
from ..output import print_json, print_output, print_error, print_success, print_warning, handle_api_error, format_response

app = typer.Typer(help="Manage Podio conversations (messages)")

# Subcommand group for participant operations
participant_app = typer.Typer(help="Manage conversation participants")
app.add_typer(participant_app, name="participant")


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


def _apply_client_filter(data: Any, filter_str: str) -> Any:
    """Apply client-side filtering based on key:value pairs."""
    if not filter_str or not isinstance(data, list):
        return data

    filters = {}
    for part in filter_str.split(","):
        if ":" in part:
            key, value = part.split(":", 1)
        elif "=" in part:
            key, value = part.split("=", 1)
        else:
            continue
        filters[key.strip()] = value.strip()

    return [
        item for item in data
        if all(str(item.get(k, "")).lower() == v.lower() for k, v in filters.items())
    ]


@participant_app.command("add")
def participant_add(
    conversation_id: int = typer.Argument(..., help="Conversation ID"),
    users: str = typer.Option(..., "--users", "-u", help="Comma-separated list of user IDs to add"),
    table: bool = typer.Option(False, "--table", "-t", help="Output as formatted table"),
):
    """
    Add participants to an existing conversation.

    Examples:
        podio conversation participant add 12345 --users "123456,789012"
        podio conversation participant add 12345 -u "123456"
    """
    try:
        client = get_client()

        # Parse participants
        try:
            participant_ids = [int(p.strip()) for p in users.split(",")]
        except ValueError:
            print_error("Invalid user IDs. Must be comma-separated integers")
            raise typer.Exit(1)

        result = client.Conversation.add_participants(conversation_id, participant_ids)
        formatted = format_response(result)
        print_success(f"Participants added to conversation {conversation_id}")
        print_output(formatted, table=table)
    except Exception as e:
        exit_code = handle_api_error(e)
        raise typer.Exit(exit_code)


@app.command("list")
def list_conversations(
    limit: int = typer.Option(100, "--limit", "-l", help="Maximum conversations to return"),
    offset: int = typer.Option(0, "--offset", help="Offset for pagination"),
    filter: Optional[str] = typer.Option(None, "--filter", "-f", help="Filter by field:value"),
    properties: Optional[str] = typer.Option(None, "--properties", "-p", help="Comma-separated list of fields to include"),
    table: bool = typer.Option(False, "--table", "-t", help="Output as formatted table"),
):
    """
    Get all conversations for the authenticated user.

    Returns conversations ordered by time of the last event.

    Examples:
        podio conversation list
        podio conversation list --limit 20
        podio conversation list --filter "unread:true"
        podio conversation list --properties "conversation_id,subject"
        podio conversation list --table
    """
    try:
        client = get_client()
        result = client.Conversation.find_all(limit=limit, offset=offset)
        formatted = format_response(result)

        # Apply client-side filtering
        if filter and isinstance(formatted, list):
            formatted = _apply_client_filter(formatted, filter)

        # Apply properties filter
        if properties:
            formatted = _apply_properties_filter(formatted, properties)

        print_output(formatted, table=table)
    except Exception as e:
        exit_code = handle_api_error(e)
        raise typer.Exit(exit_code)


@app.command("get")
def get_conversation(
    conversation_id: int = typer.Argument(..., help="Conversation ID to retrieve"),
    table: bool = typer.Option(False, "--table", "-t", help="Output as formatted table"),
):
    """
    Get a specific conversation including participants and messages.

    Only participants in the conversation are allowed to view it.

    Examples:
        podio conversation get 12345
        podio conversation get 12345 --table
    """
    try:
        client = get_client()
        result = client.Conversation.find(conversation_id)
        formatted = format_response(result)
        print_output(formatted, table=table)
    except Exception as e:
        exit_code = handle_api_error(e)
        raise typer.Exit(exit_code)


@app.command("create")
def create_conversation(
    subject: Optional[str] = typer.Option(None, "--subject", help="Conversation subject"),
    text: Optional[str] = typer.Option(None, "--text", help="Message text"),
    participants: Optional[str] = typer.Option(
        None,
        "--participants",
        help="Comma-separated list of user IDs",
    ),
    ref_type: Optional[str] = typer.Option(
        None,
        "--ref-type",
        help="Object type for object-based conversation (e.g., 'item', 'status')",
    ),
    ref_id: Optional[int] = typer.Option(
        None,
        "--ref-id",
        help="Object ID for object-based conversation",
    ),
    json_file: Optional[Path] = typer.Option(
        None,
        "--json-file",
        help="Path to JSON file with conversation data",
    ),
    table: bool = typer.Option(False, "--table", "-t", help="Output as formatted table"),
):
    """
    Create a new conversation with a list of users or on an object.

    Once started, participants cannot be changed (yet).
    Use --ref-type and --ref-id to create a conversation on a specific object.

    Conversation data format:
        {
            "subject": "Conversation subject",
            "text": "Message body",
            "participants": [123456, 789012],
            "file_ids": [111, 222]
        }

    Examples:
        podio conversation create --subject "Hello" --text "Hi there" --participants "123456,789012"
        podio conversation create --ref-type item --ref-id 12345 --subject "Question" --text "Need help"
        podio conversation create --json-file conversation.json
    """
    try:
        client = get_client()

        # Build conversation data
        if json_file:
            if not json_file.exists():
                print_error(f"File not found: {json_file}")
                raise typer.Exit(1)
            with open(json_file) as f:
                conversation_data = json.load(f)
        else:
            if not subject or not text:
                print_error("Missing required arguments. Provide --subject and --text or use --json-file")
                raise typer.Exit(1)

            conversation_data = {
                "subject": subject,
                "text": text,
            }

            # Parse participants if provided
            if participants:
                try:
                    participant_ids = [int(p.strip()) for p in participants.split(",")]
                    conversation_data["participants"] = participant_ids
                except ValueError:
                    print_error("Invalid participant IDs. Must be comma-separated integers")
                    raise typer.Exit(1)

        # Check if creating on object
        if ref_type and ref_id:
            result = client.Conversation.create_for(ref_type=ref_type, ref_id=ref_id, attributes=conversation_data)
        else:
            if not participants and "participants" not in conversation_data:
                print_error("--participants is required for direct conversations (or use --ref-type and --ref-id for object conversations)")
                raise typer.Exit(1)
            result = client.Conversation.create(attributes=conversation_data)

        formatted = format_response(result)
        print_success(f"Conversation created successfully")
        print_output(formatted, table=table)
    except Exception as e:
        exit_code = handle_api_error(e)
        raise typer.Exit(exit_code)


@app.command("reply")
def reply_to_conversation(
    conversation_id: int = typer.Argument(..., help="Conversation ID"),
    text: Optional[str] = typer.Option(None, "--text", help="Reply text"),
    json_file: Optional[Path] = typer.Option(
        None,
        "--json-file",
        help="Path to JSON file with reply data",
    ),
    table: bool = typer.Option(False, "--table", "-t", help="Output as formatted table"),
):
    """
    Reply to an existing conversation.

    Reply data format:
        {
            "text": "Reply message",
            "file_ids": [111, 222],
            "embed_id": 333,
            "embed_url": "https://example.com"
        }

    Examples:
        podio conversation reply 12345 --text "Thanks for the message"
        podio conversation reply 12345 --json-file reply.json
        podio conversation reply 12345 --text "Thanks" --table
    """
    try:
        client = get_client()

        # Build reply data
        if json_file:
            if not json_file.exists():
                print_error(f"File not found: {json_file}")
                raise typer.Exit(1)
            with open(json_file) as f:
                reply_data = json.load(f)
        elif text:
            reply_data = {"text": text}
        else:
            # Try reading from stdin
            if not sys.stdin.isatty():
                try:
                    stdin_data = sys.stdin.read().strip()
                    if stdin_data:
                        reply_data = {"text": stdin_data}
                    else:
                        print_error("No reply text provided. Use --text or --json-file")
                        raise typer.Exit(1)
                except Exception as e:
                    print_error(f"Error reading from stdin: {e}")
                    raise typer.Exit(1)
            else:
                print_error("No reply text provided. Use --text or --json-file")
                raise typer.Exit(1)

        result = client.Conversation.reply(conversation_id, attributes=reply_data)
        formatted = format_response(result)
        print_success(f"Reply sent to conversation {conversation_id}")
        print_output(formatted, table=table)
    except Exception as e:
        exit_code = handle_api_error(e)
        raise typer.Exit(exit_code)


@app.command("add-participants", hidden=True)
def add_participants_deprecated(
    conversation_id: int = typer.Argument(..., help="Conversation ID"),
    participants: str = typer.Option(..., "--participants", help="Comma-separated list of user IDs to add"),
    table: bool = typer.Option(False, "--table", "-t", help="Output as formatted table"),
):
    """[DEPRECATED] Use 'podio conversation participant add' instead."""
    print_warning("'podio conversation add-participants' is deprecated. Use 'podio conversation participant add' instead.")
    return participant_add(conversation_id=conversation_id, users=participants, table=table)


@app.command("mark-read")
def mark_as_read(
    conversation_id: int = typer.Argument(..., help="Conversation ID to mark as read"),
    table: bool = typer.Option(False, "--table", "-t", help="Output as formatted table"),
):
    """
    Mark a conversation as read.

    Examples:
        podio conversation mark-read 12345
        podio conversation mark-read 12345 --table
    """
    try:
        client = get_client()
        client.Conversation.mark_as_read(conversation_id)
        print_success(f"Conversation {conversation_id} marked as read")
        print_output({"conversation_id": conversation_id, "marked_read": True}, table=table)
    except Exception as e:
        exit_code = handle_api_error(e)
        raise typer.Exit(exit_code)


@app.command("mark-unread")
def mark_as_unread(
    conversation_id: int = typer.Argument(..., help="Conversation ID to mark as unread"),
    table: bool = typer.Option(False, "--table", "-t", help="Output as formatted table"),
):
    """
    Mark a conversation as unread.

    Examples:
        podio conversation mark-unread 12345
        podio conversation mark-unread 12345 --table
    """
    try:
        client = get_client()
        client.Conversation.mark_as_unread(conversation_id)
        print_success(f"Conversation {conversation_id} marked as unread")
        print_output({"conversation_id": conversation_id, "marked_unread": True}, table=table)
    except Exception as e:
        exit_code = handle_api_error(e)
        raise typer.Exit(exit_code)


@app.command("star")
def star_conversation(
    conversation_id: int = typer.Argument(..., help="Conversation ID to star"),
    table: bool = typer.Option(False, "--table", "-t", help="Output as formatted table"),
):
    """
    Star a conversation.

    Examples:
        podio conversation star 12345
        podio conversation star 12345 --table
    """
    try:
        client = get_client()
        client.Conversation.star(conversation_id)
        print_success(f"Conversation {conversation_id} starred")
        print_output({"conversation_id": conversation_id, "starred": True}, table=table)
    except Exception as e:
        exit_code = handle_api_error(e)
        raise typer.Exit(exit_code)


@app.command("unstar")
def unstar_conversation(
    conversation_id: int = typer.Argument(..., help="Conversation ID to unstar"),
    table: bool = typer.Option(False, "--table", "-t", help="Output as formatted table"),
):
    """
    Unstar a conversation.

    Examples:
        podio conversation unstar 12345
        podio conversation unstar 12345 --table
    """
    try:
        client = get_client()
        client.Conversation.unstar(conversation_id)
        print_success(f"Conversation {conversation_id} unstarred")
        print_output({"conversation_id": conversation_id, "starred": False}, table=table)
    except Exception as e:
        exit_code = handle_api_error(e)
        raise typer.Exit(exit_code)


@app.command("leave")
def leave_conversation(
    conversation_id: int = typer.Argument(..., help="Conversation ID to leave"),
    table: bool = typer.Option(False, "--table", "-t", help="Output as formatted table"),
):
    """
    Leave a conversation.

    Examples:
        podio conversation leave 12345
        podio conversation leave 12345 --table
    """
    try:
        client = get_client()
        client.Conversation.leave(conversation_id)
        print_success(f"Left conversation {conversation_id}")
        print_output({"conversation_id": conversation_id, "left": True}, table=table)
    except Exception as e:
        exit_code = handle_api_error(e)
        raise typer.Exit(exit_code)


@app.command("search")
def search_conversations(
    query: str = typer.Argument(..., help="Search query"),
    limit: int = typer.Option(10, "--limit", help="Maximum results to return"),
    offset: int = typer.Option(0, "--offset", help="Offset for pagination"),
    table: bool = typer.Option(False, "--table", "-t", help="Output as formatted table"),
):
    """
    Search conversations.

    Examples:
        podio conversation search "project update"
        podio conversation search "budget" --limit 20
        podio conversation search "project" --table
    """
    try:
        client = get_client()
        result = client.Conversation.search(query, limit=limit, offset=offset)
        formatted = format_response(result)
        print_output(formatted, table=table)
    except Exception as e:
        exit_code = handle_api_error(e)
        raise typer.Exit(exit_code)


@app.command("events")
def get_conversation_events(
    conversation_id: int = typer.Argument(..., help="Conversation ID"),
    limit: int = typer.Option(10, "--limit", help="Maximum events to return"),
    offset: int = typer.Option(0, "--offset", help="Offset for pagination"),
    table: bool = typer.Option(False, "--table", "-t", help="Output as formatted table"),
):
    """
    Get events (messages) from a conversation.

    Examples:
        podio conversation events 12345
        podio conversation events 12345 --limit 50
        podio conversation events 12345 --table
    """
    try:
        client = get_client()
        result = client.Conversation.get_events(conversation_id, limit=limit, offset=offset)
        formatted = format_response(result)
        print_output(formatted, table=table)
    except Exception as e:
        exit_code = handle_api_error(e)
        raise typer.Exit(exit_code)


@app.command("on-object")
def get_conversations_on_object(
    ref_type: str = typer.Argument(..., help="Object type (e.g., 'item', 'status')"),
    ref_id: int = typer.Argument(..., help="Object ID"),
    table: bool = typer.Option(False, "--table", "-t", help="Output as formatted table"),
):
    """
    Get all conversations on a specific object.

    Examples:
        podio conversation on-object item 12345
        podio conversation on-object status 67890
        podio conversation on-object item 12345 --table
    """
    try:
        client = get_client()
        result = client.Conversation.get_on_object(ref_type, ref_id)
        formatted = format_response(result)
        print_output(formatted, table=table)
    except Exception as e:
        exit_code = handle_api_error(e)
        raise typer.Exit(exit_code)


@app.command("create-on-object", hidden=True)
def create_conversation_on_object_deprecated(
    ref_type: str = typer.Argument(..., help="Object type (e.g., 'item', 'status')"),
    ref_id: int = typer.Argument(..., help="Object ID"),
    subject: Optional[str] = typer.Option(None, "--subject", help="Conversation subject"),
    text: Optional[str] = typer.Option(None, "--text", help="Message text"),
    participants: Optional[str] = typer.Option(
        None,
        "--participants",
        help="Comma-separated list of user IDs",
    ),
    json_file: Optional[Path] = typer.Option(
        None,
        "--json-file",
        help="Path to JSON file with conversation data",
    ),
    table: bool = typer.Option(False, "--table", "-t", help="Output as formatted table"),
):
    """
    [DEPRECATED] Use 'podio conversation create --ref-type <type> --ref-id <id>' instead.

    Create a new conversation on a specific object.
    """
    print_warning("'podio conversation create-on-object' is deprecated. Use 'podio conversation create --ref-type <type> --ref-id <id>' instead.")
    try:
        client = get_client()

        # Build conversation data
        if json_file:
            if not json_file.exists():
                print_error(f"File not found: {json_file}")
                raise typer.Exit(1)
            with open(json_file) as f:
                conversation_data = json.load(f)
        else:
            if not subject or not text:
                print_error("Missing required arguments. Provide --subject and --text or use --json-file")
                raise typer.Exit(1)

            conversation_data = {
                "subject": subject,
                "text": text,
            }

            # Parse participants if provided
            if participants:
                try:
                    participant_ids = [int(p.strip()) for p in participants.split(",")]
                    conversation_data["participants"] = participant_ids
                except ValueError:
                    print_error("Invalid participant IDs. Must be comma-separated integers")
                    raise typer.Exit(1)

        result = client.Conversation.create_on_object(ref_type, ref_id, attributes=conversation_data)
        formatted = format_response(result)
        print_success(f"Conversation created on {ref_type} {ref_id}")
        print_output(formatted, table=table)
    except Exception as e:
        exit_code = handle_api_error(e)
        raise typer.Exit(exit_code)
