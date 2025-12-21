"""OAuth authentication commands for Podio CLI.

Implements the CLI-tools auth standards:
- auth login: Initiate authentication flow
- auth status: Check authentication status (exit 0 if authenticated, 2 if not)
- auth logout: Clear stored credentials/tokens
"""
import typer
from typing import Optional
from pypodio2.transport import OAuthAuthorizationCodeAuthorization, OAuthTokenAuthorization
from ..config import get_config
from ..output import print_json, print_table, print_error, print_success

app = typer.Typer(help="Authentication management")


@app.command("status")
def auth_status(
    table: bool = typer.Option(False, "--table", "-t", help="Display as formatted table"),
):
    """
    Check authentication status and display current credentials info.

    Returns exit code 0 if authenticated, 2 if not authenticated.

    Examples:
        podio auth status
        podio auth status --table
    """
    config = get_config()

    # Determine auth method and status
    auth_method = None
    is_authenticated = False
    details = {}

    if config.has_token_auth():
        auth_method = "token"
        is_authenticated = True
        details = {
            "method": "OAuth Token",
            "access_token": f"{config.access_token[:8]}..." if config.access_token else None,
            "refresh_token": "present" if config.refresh_token else "not set",
            "client_id": config.client_id or "not set",
        }
    elif config.has_authorization_code_auth():
        auth_method = "authorization_code"
        is_authenticated = True
        details = {
            "method": "Authorization Code",
            "client_id": config.client_id,
            "redirect_uri": config.redirect_uri,
            "authorization_code": f"{config.authorization_code[:8]}..." if config.authorization_code else None,
        }
    elif config.has_user_auth():
        auth_method = "user"
        is_authenticated = True
        details = {
            "method": "User Credentials",
            "client_id": config.client_id,
            "username": config.username,
        }
    elif config.has_app_auth():
        auth_method = "app"
        is_authenticated = True
        details = {
            "method": "App Credentials",
            "client_id": config.client_id,
            "app_id": config.app_id,
        }

    # Add common config info
    details["organization_id"] = config.organization_id or "not set"
    details["workspace_id"] = config.workspace_id or "not set"
    details["env_file"] = str(config.env_file_path)

    # Build output
    status_data = {
        "authenticated": is_authenticated,
        "auth_method": auth_method,
        **details,
    }

    if is_authenticated:
        # Try to verify the token by making a simple API call
        try:
            from ..client import get_client
            client = get_client()
            # Try to get current user info to verify token is valid
            user = client.User.current()
            status_data["user_id"] = user.get("user_id")
            status_data["email"] = user.get("mail")
            status_data["verified"] = True
        except Exception as e:
            # Token exists but may be expired or invalid
            status_data["verified"] = False
            status_data["verification_error"] = str(e)
            # Still authenticated (has creds), but token needs refresh
            is_authenticated = True

    if table:
        # Format for table display
        if is_authenticated:
            print_success("Authenticated")
        else:
            print_error("Not authenticated")
        print_table([status_data])
    else:
        print_json(status_data)

    # Exit code per README spec: 0 if authenticated, 2 if not
    raise typer.Exit(0 if is_authenticated else 2)


@app.command("login")
def auth_login(
    flow_type: str = typer.Option(
        "client",
        "--flow",
        "-f",
        help="OAuth flow type: 'client' (token, recommended) or 'server' (authorization code)"
    ),
    redirect_uri: str = typer.Option(
        None,
        "--redirect-uri",
        "-r",
        help="Redirect URI (defaults to PODIO_REDIRECT_URI env var)"
    ),
):
    """
    Initiate OAuth authentication flow.

    Guides you through the Podio OAuth process to obtain access tokens.

    Examples:
        podio auth login
        podio auth login --flow client
        podio auth login --flow server --redirect-uri https://example.com/callback
    """
    config = get_config()

    # Check prerequisites
    if not config.client_id:
        print_error("PODIO_CLIENT_ID is required. Set it in your .env file.")
        typer.echo("\nTo get a Client ID:", err=True)
        typer.echo("  1. Go to https://podio.com/settings/api", err=True)
        typer.echo("  2. Create a new API Key", err=True)
        typer.echo("  3. Add PODIO_CLIENT_ID=<your_client_id> to .env", err=True)
        typer.echo("  4. Add PODIO_CLIENT_SECRET=<your_client_secret> to .env", err=True)
        raise typer.Exit(2)

    # Get redirect URI
    uri = redirect_uri or config.redirect_uri
    if not uri:
        # Use default Podio callback for client-side flow
        uri = "https://podio.com/oauth/callback"
        typer.echo(f"Using default redirect URI: {uri}", err=True)

    # Generate URL based on flow type
    if flow_type == "client":
        url = OAuthTokenAuthorization.get_authorization_url(
            client_id=config.client_id,
            redirect_uri=uri,
        )
        typer.echo("\n🔐 Client-side OAuth Flow (Recommended)", err=True)
        typer.echo("=" * 60, err=True)
        typer.echo("\nStep 1: Open this URL in your browser:\n", err=True)
        typer.echo(f"  {url}\n", err=True)
        typer.echo("Step 2: Authorize the application", err=True)
        typer.echo("\nStep 3: Copy the full redirect URL (includes access_token in fragment)", err=True)
        typer.echo("  Example: https://podio.com/oauth/callback#access_token=TOKEN&refresh_token=REFRESH\n", err=True)
        typer.echo("Step 4: Run:", err=True)
        typer.echo('  podio auth parse-callback "YOUR_CALLBACK_URL"\n', err=True)
        typer.echo("Or manually add to .env:", err=True)
        typer.echo("  PODIO_ACCESS_TOKEN=<token>", err=True)
        typer.echo("  PODIO_REFRESH_TOKEN=<refresh_token>", err=True)

    elif flow_type == "server":
        url = OAuthAuthorizationCodeAuthorization.get_authorization_url(
            client_id=config.client_id,
            redirect_uri=uri,
        )
        typer.echo("\n🔐 Server-side OAuth Flow (Authorization Code)", err=True)
        typer.echo("=" * 60, err=True)
        typer.echo("\nStep 1: Open this URL in your browser:\n", err=True)
        typer.echo(f"  {url}\n", err=True)
        typer.echo("Step 2: Authorize the application", err=True)
        typer.echo("\nStep 3: Copy the 'code' parameter from the callback URL", err=True)
        typer.echo(f"  Example: {uri}?code=AUTHORIZATION_CODE\n", err=True)
        typer.echo("Step 4: Add to .env:", err=True)
        typer.echo("  PODIO_AUTHORIZATION_CODE=<code>", err=True)
        typer.echo(f"  PODIO_REDIRECT_URI={uri}", err=True)

    else:
        print_error(f"Invalid flow type: {flow_type}. Use 'client' or 'server'")
        raise typer.Exit(1)

    # Output the URL as JSON for scripting
    print_json({"authorization_url": url, "flow_type": flow_type, "redirect_uri": uri})


@app.command("logout")
def auth_logout(
    yes: bool = typer.Option(False, "--yes", "-y", help="Skip confirmation prompt"),
):
    """
    Clear stored credentials and tokens.

    Removes access tokens and optionally other credentials from .env file.

    Examples:
        podio auth logout
        podio auth logout --yes
    """
    config = get_config()

    if not yes:
        typer.confirm("This will clear your Podio access tokens. Continue?", abort=True)

    # Clear tokens from .env
    from dotenv import set_key

    tokens_cleared = []

    if config.access_token:
        set_key(str(config.env_file_path), "PODIO_ACCESS_TOKEN", "")
        tokens_cleared.append("PODIO_ACCESS_TOKEN")

    if config.refresh_token:
        set_key(str(config.env_file_path), "PODIO_REFRESH_TOKEN", "")
        tokens_cleared.append("PODIO_REFRESH_TOKEN")

    if config.authorization_code:
        set_key(str(config.env_file_path), "PODIO_AUTHORIZATION_CODE", "")
        tokens_cleared.append("PODIO_AUTHORIZATION_CODE")

    if tokens_cleared:
        print_success(f"Cleared: {', '.join(tokens_cleared)}")
        typer.echo(f"Updated: {config.env_file_path}", err=True)
    else:
        typer.echo("No tokens to clear.", err=True)

    print_json({"cleared": tokens_cleared, "env_file": str(config.env_file_path)})


@app.command("parse-callback")
def parse_callback(
    callback_url: str = typer.Argument(..., help="The full callback URL from Podio"),
    save: bool = typer.Option(True, "--save/--no-save", help="Save tokens to .env file"),
):
    """
    Parse a callback URL to extract OAuth tokens and optionally save them.

    This helper command extracts the access token from the callback URL
    that Podio redirects to after authorization.

    Examples:
        podio auth parse-callback "https://podio.com/oauth/callback#access_token=xyz&refresh_token=abc"
        podio auth parse-callback "https://example.com/callback?code=abc123" --no-save
    """
    config = get_config()

    try:
        # Check if it's a client-side flow (fragment identifier with #)
        if "#" in callback_url:
            # Client-side flow - parse fragment
            fragment = callback_url.split("#")[1]
            params = {}
            for param in fragment.split("&"):
                if "=" in param:
                    key, value = param.split("=", 1)
                    params[key] = value

            if "access_token" not in params:
                print_error("No access_token found in URL fragment")
                raise typer.Exit(1)

            typer.echo("\n✅ Tokens extracted from callback URL", err=True)

            if save:
                from dotenv import set_key
                set_key(str(config.env_file_path), "PODIO_ACCESS_TOKEN", params["access_token"])
                if params.get("refresh_token"):
                    set_key(str(config.env_file_path), "PODIO_REFRESH_TOKEN", params["refresh_token"])
                print_success(f"Tokens saved to {config.env_file_path}")

            print_json({
                "access_token": params.get("access_token"),
                "refresh_token": params.get("refresh_token"),
                "expires_in": params.get("expires_in"),
                "saved": save,
            })

        elif "?" in callback_url:
            # Server-side flow - parse query string (authorization code)
            query = callback_url.split("?")[1]
            params = {}
            for param in query.split("&"):
                if "=" in param:
                    key, value = param.split("=", 1)
                    params[key] = value

            if "code" in params:
                typer.echo("\n✅ Authorization code extracted", err=True)

                if save:
                    from dotenv import set_key
                    set_key(str(config.env_file_path), "PODIO_AUTHORIZATION_CODE", params["code"])
                    print_success(f"Authorization code saved to {config.env_file_path}")

                print_json({
                    "authorization_code": params.get("code"),
                    "saved": save,
                })

            elif "error" in params:
                print_error(f"Authorization error: {params.get('error_description', params.get('error'))}")
                raise typer.Exit(1)
            else:
                print_error("No authorization code found in query string")
                raise typer.Exit(1)
        else:
            print_error("Invalid callback URL format. Expected URL with ? (query) or # (fragment)")
            raise typer.Exit(1)

    except typer.Exit:
        raise
    except Exception as e:
        print_error(f"Failed to parse callback URL: {e}")
        raise typer.Exit(1)


@app.command("refresh")
def auth_refresh():
    """
    Manually refresh the access token using the refresh token.

    This is normally done automatically, but can be triggered manually.

    Examples:
        podio auth refresh
    """
    config = get_config()

    if not config.refresh_token:
        print_error("No refresh token available. Run 'podio auth login' first.")
        raise typer.Exit(2)

    if not config.client_id or not config.client_secret:
        print_error("PODIO_CLIENT_ID and PODIO_CLIENT_SECRET required for token refresh.")
        raise typer.Exit(2)

    try:
        # Use httpx or urllib to refresh the token
        import urllib.request
        import urllib.parse
        import json

        data = urllib.parse.urlencode({
            "grant_type": "refresh_token",
            "client_id": config.client_id,
            "client_secret": config.client_secret,
            "refresh_token": config.refresh_token,
        }).encode()

        req = urllib.request.Request(
            "https://podio.com/oauth/token",
            data=data,
            method="POST",
        )

        with urllib.request.urlopen(req) as response:
            result = json.loads(response.read().decode())

        # Save new tokens
        new_access_token = result.get("access_token")
        new_refresh_token = result.get("refresh_token")

        if new_access_token:
            config.save_tokens(new_access_token, new_refresh_token or config.refresh_token)
            print_success("Token refreshed successfully")
            print_json({
                "access_token": f"{new_access_token[:8]}...",
                "refresh_token": "updated" if new_refresh_token else "unchanged",
                "expires_in": result.get("expires_in"),
            })
        else:
            print_error("No access token in response")
            raise typer.Exit(1)

    except urllib.error.HTTPError as e:
        error_body = e.read().decode() if e.fp else str(e)
        print_error(f"Token refresh failed: {error_body}")
        raise typer.Exit(2)
    except Exception as e:
        print_error(f"Token refresh failed: {e}")
        raise typer.Exit(1)
