"""Webform commands for Podio CLI."""
import json
import re
import sys
from pathlib import Path
from typing import Optional, Any

import requests
import typer

from ..client import get_client
from ..output import print_json, print_output, print_error, print_success, print_info, handle_api_error, format_response

app = typer.Typer(help="Manage Podio webforms")


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


@app.command("list")
def list_webforms(
    app_id: int = typer.Argument(..., help="Application ID to list webforms from"),
    limit: int = typer.Option(100, "--limit", "-l", help="Maximum webforms to return"),
    properties: Optional[str] = typer.Option(None, "--properties", "-p", help="Comma-separated list of fields to include"),
    table: bool = typer.Option(False, "--table", "-t", help="Output as formatted table"),
):
    """
    List all webforms for an application.

    Returns all webforms (active and disabled) configured on the given app.

    Examples:
        podio webform list 12345
        podio webform list 12345 --limit 10
        podio webform list 12345 --properties "form_id,name,status"
        podio webform list 12345 --table
    """
    try:
        client = get_client()
        # Use raw transport since pypodio2 doesn't have Form area
        result = client.transport.GET(url=f"/form/app/{app_id}/")
        formatted = format_response(result)

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


@app.command("get")
def get_webform(
    form_id: int = typer.Argument(..., help="Webform ID to retrieve"),
    table: bool = typer.Option(False, "--table", "-t", help="Output as formatted table"),
):
    """
    Get a specific webform by ID.

    Returns full details including settings, fields, domains, and attachments configuration.

    Examples:
        podio webform get 12345
        podio webform get 12345 --table
    """
    try:
        client = get_client()
        # Use raw transport since pypodio2 doesn't have Form area
        result = client.transport.GET(url=f"/form/{form_id}")
        formatted = format_response(result)
        print_output(formatted, table=table)
    except Exception as e:
        exit_code = handle_api_error(e)
        raise typer.Exit(exit_code)


def _extract_csrf_token(html: str) -> Optional[str]:
    """Extract CSRF token from webform HTML."""
    # Try meta tag first
    meta_match = re.search(r'<meta\s+name="csrf-token"\s+content="([^"]+)"', html)
    if meta_match:
        return meta_match.group(1)

    # Try bootstrap data JSON
    bootstrap_match = re.search(r'"csrfToken"\s*:\s*"([^"]+)"', html)
    if bootstrap_match:
        return bootstrap_match.group(1)

    return None


def _parse_webform_url(url: str) -> tuple[int, int]:
    """Parse webform URL to extract app_id and form_id.

    URL format: https://podio.com/webforms/{app_id}/{form_id}

    Returns:
        Tuple of (app_id, form_id)
    """
    match = re.search(r'/webforms/(\d+)/(\d+)', url)
    if not match:
        raise ValueError(f"Invalid webform URL format: {url}")
    return int(match.group(1)), int(match.group(2))


@app.command("submit")
def submit_webform(
    url: str = typer.Argument(..., help="Webform URL (e.g., https://podio.com/webforms/12345/67890)"),
    json_file: Optional[Path] = typer.Option(
        None,
        "--json-file",
        "-f",
        help="Path to JSON file with field data",
    ),
    table: bool = typer.Option(False, "--table", "-t", help="Output as formatted table"),
):
    """
    Submit data to a Podio webform via HTTP POST.

    This submits directly to the public webform URL, exactly like a browser would.
    No authentication required - uses the public webform endpoint.

    Field data format (using field external_id as keys):
        {
            "title": "My Title",
            "description": "Some text",
            "category": "Option 1"
        }

    Examples:
        podio webform submit https://podio.com/webforms/30560419/2584779 -f data.json
        echo '{"title": "Test", "synopsis": "Description"}' | podio webform submit https://podio.com/webforms/30560419/2584779
    """
    try:
        # Parse the webform URL
        try:
            app_id, form_id = _parse_webform_url(url)
        except ValueError as e:
            print_error(str(e))
            print_error("Expected format: https://podio.com/webforms/{app_id}/{form_id}")
            raise typer.Exit(1)

        print_info(f"Webform URL: {url}")
        print_info(f"App ID: {app_id}, Form ID: {form_id}")

        # Read field data from file or stdin
        if json_file:
            if not json_file.exists():
                print_error(f"File not found: {json_file}")
                raise typer.Exit(1)
            with open(json_file) as f:
                fields_data = json.load(f)
        else:
            # Read from stdin
            if sys.stdin.isatty():
                print_error("No input provided. Use --json-file or pipe JSON to stdin")
                raise typer.Exit(1)
            try:
                fields_data = json.load(sys.stdin)
            except json.JSONDecodeError as e:
                print_error(f"Invalid JSON from stdin: {e}")
                raise typer.Exit(1)

        # Step 1: GET the webform page to extract CSRF token
        print_info("Fetching webform page for CSRF token...")
        session = requests.Session()
        response = session.get(url)

        if response.status_code != 200:
            print_error(f"Failed to fetch webform: HTTP {response.status_code}")
            raise typer.Exit(1)

        csrf_token = _extract_csrf_token(response.text)
        if not csrf_token:
            print_error("Could not extract CSRF token from webform page")
            raise typer.Exit(1)

        print_info("CSRF token obtained")

        # Step 2: Build form data in fields[key] format
        form_data = {}
        for key, value in fields_data.items():
            form_data[f"fields[{key}]"] = value

        # Step 3: POST to the webform
        print_info("Submitting webform...")
        headers = {
            "X-CSRF-Token": csrf_token,
            "Accept": "application/json, text/plain, */*",
            "Origin": "https://podio.com",
            "Referer": url,
        }

        post_response = session.post(
            url,
            data=form_data,
            headers=headers,
        )

        # Check response
        if post_response.status_code == 200:
            # Try to parse JSON response
            try:
                result = post_response.json()
                print_success("Webform submitted successfully!")
                print_output(result, table=table)
            except json.JSONDecodeError:
                # Response might be HTML redirect on success
                if "success" in post_response.text.lower() or "thank you" in post_response.text.lower():
                    print_success("Webform submitted successfully!")
                    print_output({"status": "success", "message": "Form submitted"}, table=table)
                else:
                    print_success("Webform submitted (response was not JSON)")
                    print_info(f"Response: {post_response.text[:500]}")
        elif post_response.status_code == 302:
            # Redirect usually means success
            print_success("Webform submitted successfully! (redirected)")
            location = post_response.headers.get("Location", "")
            print_output({"status": "success", "redirect": location}, table=table)
        elif post_response.status_code == 422:
            # Validation error
            print_error("Validation error from webform")
            try:
                error_data = post_response.json()
                print_error(json.dumps(error_data, indent=2))
            except json.JSONDecodeError:
                print_error(post_response.text[:500])
            raise typer.Exit(1)
        else:
            print_error(f"Webform submission failed: HTTP {post_response.status_code}")
            print_error(post_response.text[:500])
            raise typer.Exit(1)

    except requests.RequestException as e:
        print_error(f"HTTP request failed: {e}")
        raise typer.Exit(1)
    except Exception as e:
        if isinstance(e, SystemExit):
            raise
        print_error(f"Error: {e}")
        raise typer.Exit(1)
