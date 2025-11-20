"""Conversation (message) commands for Podio CLI."""
import json
import sys
from typing import Optional, List
from pathlib import Path
import typer

from ..client import get_client
from ..output import print_json, print_error, print_success, handle_api_error, format_response

app = typer.Typer(help="Manage Podio conversations (messages)")


@app.command("list")
def list_conversations(
    limit: int = typer.Option(10, "--limit", help="Maximum conversations to return"),
    offset: int = typer.Option(0, "--offset", help="Offset for pagination"),
):
    """
    Get all conversations for the authenticated user.

    Returns conversations ordered by time of the last event.

    Examples:
        podio conversation list
        podio conversation list --limit 20
        podio conversation list --offset 10 --limit 20
    """
    try:
        client = get_client()
        result = client.Conversation.find_all(limit=limit, offset=offset)
        formatted = format_response(result)
        print_json(formatted)
    except Exception as e:
        exit_code = handle_api_error(e)
        raise typer.Exit(exit_code)


@app.command("get")
def get_conversation(
    conversation_id: int = typer.Argument(..., help="Conversation ID to retrieve"),
):
    """
    Get a specific conversation including participants and messages.

    Only participants in the conversation are allowed to view it.

    Examples:
        podio conversation get 12345
    """
    try:
        client = get_client()
        result = client.Conversation.find(conversation_id)
        formatted = format_response(result)
        print_json(formatted)
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
    json_file: Optional[Path] = typer.Option(
        None,
        "--json-file",
        help="Path to JSON file with conversation data",
    ),
):
    """
    Create a new conversation with a list of users.

    Once started, participants cannot be changed (yet).

    Conversation data format:
        {
            "subject": "Conversation subject",
            "text": "Message body",
            "participants": [123456, 789012],
            "file_ids": [111, 222],
            "embed_id": 333,
            "embed_url": "https://example.com"
        }

    Examples:
        podio conversation create --subject "Hello" --text "Hi there" --participants "123456,789012"
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
            if not subject or not text or not participants:
                print_error("Missing required arguments. Provide --subject, --text, and --participants or use --json-file")
                raise typer.Exit(1)

            # Parse participants
            try:
                participant_ids = [int(p.strip()) for p in participants.split(",")]
            except ValueError:
                print_error("Invalid participant IDs. Must be comma-separated integers")
                raise typer.Exit(1)

            conversation_data = {
                "subject": subject,
                "text": text,
                "participants": participant_ids,
            }

        result = client.Conversation.create(attributes=conversation_data)
        formatted = format_response(result)
        print_success(f"Conversation created successfully")
        print_json(formatted)
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
        print_json(formatted)
    except Exception as e:
        exit_code = handle_api_error(e)
        raise typer.Exit(exit_code)


@app.command("add-participants")
def add_participants(
    conversation_id: int = typer.Argument(..., help="Conversation ID"),
    participants: str = typer.Option(..., "--participants", help="Comma-separated list of user IDs to add"),
):
    """
    Add participants to an existing conversation.

    Examples:
        podio conversation add-participants 12345 --participants "123456,789012"
    """
    try:
        client = get_client()

        # Parse participants
        try:
            participant_ids = [int(p.strip()) for p in participants.split(",")]
        except ValueError:
            print_error("Invalid participant IDs. Must be comma-separated integers")
            raise typer.Exit(1)

        result = client.Conversation.add_participants(conversation_id, participant_ids)
        formatted = format_response(result)
        print_success(f"Participants added to conversation {conversation_id}")
        print_json(formatted)
    except Exception as e:
        exit_code = handle_api_error(e)
        raise typer.Exit(exit_code)


@app.command("mark-read")
def mark_as_read(
    conversation_id: int = typer.Argument(..., help="Conversation ID to mark as read"),
):
    """
    Mark a conversation as read.

    Examples:
        podio conversation mark-read 12345
    """
    try:
        client = get_client()
        client.Conversation.mark_as_read(conversation_id)
        print_success(f"Conversation {conversation_id} marked as read")
        print_json({"conversation_id": conversation_id, "marked_read": True})
    except Exception as e:
        exit_code = handle_api_error(e)
        raise typer.Exit(exit_code)


@app.command("mark-unread")
def mark_as_unread(
    conversation_id: int = typer.Argument(..., help="Conversation ID to mark as unread"),
):
    """
    Mark a conversation as unread.

    Examples:
        podio conversation mark-unread 12345
    """
    try:
        client = get_client()
        client.Conversation.mark_as_unread(conversation_id)
        print_success(f"Conversation {conversation_id} marked as unread")
        print_json({"conversation_id": conversation_id, "marked_unread": True})
    except Exception as e:
        exit_code = handle_api_error(e)
        raise typer.Exit(exit_code)


@app.command("star")
def star_conversation(
    conversation_id: int = typer.Argument(..., help="Conversation ID to star"),
):
    """
    Star a conversation.

    Examples:
        podio conversation star 12345
    """
    try:
        client = get_client()
        client.Conversation.star(conversation_id)
        print_success(f"Conversation {conversation_id} starred")
        print_json({"conversation_id": conversation_id, "starred": True})
    except Exception as e:
        exit_code = handle_api_error(e)
        raise typer.Exit(exit_code)


@app.command("unstar")
def unstar_conversation(
    conversation_id: int = typer.Argument(..., help="Conversation ID to unstar"),
):
    """
    Unstar a conversation.

    Examples:
        podio conversation unstar 12345
    """
    try:
        client = get_client()
        client.Conversation.unstar(conversation_id)
        print_success(f"Conversation {conversation_id} unstarred")
        print_json({"conversation_id": conversation_id, "starred": False})
    except Exception as e:
        exit_code = handle_api_error(e)
        raise typer.Exit(exit_code)


@app.command("leave")
def leave_conversation(
    conversation_id: int = typer.Argument(..., help="Conversation ID to leave"),
):
    """
    Leave a conversation.

    Examples:
        podio conversation leave 12345
    """
    try:
        client = get_client()
        client.Conversation.leave(conversation_id)
        print_success(f"Left conversation {conversation_id}")
        print_json({"conversation_id": conversation_id, "left": True})
    except Exception as e:
        exit_code = handle_api_error(e)
        raise typer.Exit(exit_code)


@app.command("search")
def search_conversations(
    query: str = typer.Argument(..., help="Search query"),
    limit: int = typer.Option(10, "--limit", help="Maximum results to return"),
    offset: int = typer.Option(0, "--offset", help="Offset for pagination"),
):
    """
    Search conversations.

    Examples:
        podio conversation search "project update"
        podio conversation search "budget" --limit 20
    """
    try:
        client = get_client()
        result = client.Conversation.search(query, limit=limit, offset=offset)
        formatted = format_response(result)
        print_json(formatted)
    except Exception as e:
        exit_code = handle_api_error(e)
        raise typer.Exit(exit_code)


@app.command("events")
def get_conversation_events(
    conversation_id: int = typer.Argument(..., help="Conversation ID"),
    limit: int = typer.Option(10, "--limit", help="Maximum events to return"),
    offset: int = typer.Option(0, "--offset", help="Offset for pagination"),
):
    """
    Get events (messages) from a conversation.

    Examples:
        podio conversation events 12345
        podio conversation events 12345 --limit 50
    """
    try:
        client = get_client()
        result = client.Conversation.get_events(conversation_id, limit=limit, offset=offset)
        formatted = format_response(result)
        print_json(formatted)
    except Exception as e:
        exit_code = handle_api_error(e)
        raise typer.Exit(exit_code)


@app.command("on-object")
def get_conversations_on_object(
    ref_type: str = typer.Argument(..., help="Object type (e.g., 'item', 'status')"),
    ref_id: int = typer.Argument(..., help="Object ID"),
):
    """
    Get all conversations on a specific object.

    Examples:
        podio conversation on-object item 12345
        podio conversation on-object status 67890
    """
    try:
        client = get_client()
        result = client.Conversation.get_on_object(ref_type, ref_id)
        formatted = format_response(result)
        print_json(formatted)
    except Exception as e:
        exit_code = handle_api_error(e)
        raise typer.Exit(exit_code)


@app.command("create-on-object")
def create_conversation_on_object(
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
):
    """
    Create a new conversation on a specific object.

    Examples:
        podio conversation create-on-object item 12345 --subject "Question" --text "Need help" --participants "123456"
        podio conversation create-on-object item 12345 --json-file conversation.json
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

        result = client.Conversation.create_on_object(ref_type, ref_id, attributes=conversation_data)
        formatted = format_response(result)
        print_success(f"Conversation created on {ref_type} {ref_id}")
        print_json(formatted)
    except Exception as e:
        exit_code = handle_api_error(e)
        raise typer.Exit(exit_code)
