"""OAuth authentication commands."""
import typer
from pypodio2.transport import OAuthAuthorizationCodeAuthorization, OAuthTokenAuthorization
from ..config import get_config
from ..output import print_json, print_error

app = typer.Typer(help="OAuth authentication utilities")


@app.command("url")
def get_auth_url(
    flow_type: str = typer.Option(
        "server",
        "--flow",
        "-f",
        help="OAuth flow type: 'server' (authorization code) or 'client' (token)"
    ),
    redirect_uri: str = typer.Option(
        None,
        "--redirect-uri",
        "-r",
        help="Redirect URI (defaults to PODIO_REDIRECT_URI env var)"
    ),
    scope: str = typer.Option(
        None,
        "--scope",
        "-s",
        help="OAuth scope (e.g., 'global:all')"
    ),
):
    """
    Generate an OAuth authorization URL for user authentication.
    
    This command helps you generate the URL to send users to Podio for authorization.
    After the user authorizes, they will be redirected to your redirect_uri with
    either an authorization code (server-side) or access token (client-side).
    """
    try:
        config = get_config()
        
        if not config.client_id:
            print_error("PODIO_CLIENT_ID is required. Set it in your .env file.")
            raise typer.Exit(2)
        
        # Get redirect_uri from parameter or config
        uri = redirect_uri or config.redirect_uri
        if not uri:
            print_error("Redirect URI is required. Provide --redirect-uri or set PODIO_REDIRECT_URI in .env")
            raise typer.Exit(2)
        
        # Generate URL based on flow type
        if flow_type == "server":
            url = OAuthAuthorizationCodeAuthorization.get_authorization_url(
                client_id=config.client_id,
                redirect_uri=uri,
                scope=scope
            )
            typer.echo("\n🔐 Server-side OAuth Flow (Authorization Code)", err=True)
            typer.echo("=" * 60, err=True)
        elif flow_type == "client":
            url = OAuthTokenAuthorization.get_authorization_url(
                client_id=config.client_id,
                redirect_uri=uri,
                scope=scope
            )
            typer.echo("\n🔐 Client-side OAuth Flow (Token)", err=True)
            typer.echo("=" * 60, err=True)
        else:
            print_error(f"Invalid flow type: {flow_type}. Use 'server' or 'client'")
            raise typer.Exit(1)
        
        typer.echo(f"\nDirect users to this URL:\n{url}\n", err=True)
        
        if flow_type == "server":
            typer.echo("After authorization, extract the 'code' parameter from the callback URL:", err=True)
            typer.echo(f"  Example: {uri}?code=AUTHORIZATION_CODE\n", err=True)
            typer.echo("Then set in your .env file:", err=True)
            typer.echo("  PODIO_AUTHORIZATION_CODE=AUTHORIZATION_CODE", err=True)
            typer.echo(f"  PODIO_REDIRECT_URI={uri}\n", err=True)
        else:
            typer.echo("After authorization, extract token from URL fragment:", err=True)
            typer.echo(f"  Example: {uri}#access_token=TOKEN&refresh_token=REFRESH\n", err=True)
            typer.echo("Then set in your .env file:", err=True)
            typer.echo("  PODIO_ACCESS_TOKEN=TOKEN", err=True)
            typer.echo("  PODIO_REFRESH_TOKEN=REFRESH (optional)\n", err=True)
        
        # Output JSON with URL for scripting
        print_json({
            "authorization_url": url,
            "flow_type": flow_type,
            "redirect_uri": uri,
            "scope": scope
        })
        
    except typer.Exit:
        raise
    except Exception as e:
        print_error(f"Failed to generate authorization URL: {e}")
        raise typer.Exit(1)


@app.command("parse-callback")
def parse_callback(
    callback_url: str = typer.Argument(..., help="The full callback URL from Podio"),
):
    """
    Parse a callback URL to extract OAuth tokens or codes.
    
    This helper command extracts the authorization code (server-side) or
    access token (client-side) from the callback URL that Podio redirects to.
    """
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
            
            if "access_token" in params:
                typer.echo("\n✅ Client-side OAuth Flow Detected", err=True)
                typer.echo("=" * 60, err=True)
                typer.echo("\nExtracted tokens:", err=True)
                typer.echo(f"  Access Token: {params.get('access_token')}", err=True)
                typer.echo(f"  Refresh Token: {params.get('refresh_token', 'N/A')}", err=True)
                typer.echo(f"  Expires In: {params.get('expires_in', 'N/A')} seconds", err=True)
                typer.echo(f"  Token Type: {params.get('token_type', 'N/A')}", err=True)
                typer.echo(f"  Scope: {params.get('scope', 'N/A')}\n", err=True)
                
                typer.echo("Add to your .env file:", err=True)
                typer.echo(f"  PODIO_ACCESS_TOKEN={params.get('access_token')}", err=True)
                if params.get('refresh_token'):
                    typer.echo(f"  PODIO_REFRESH_TOKEN={params.get('refresh_token')}", err=True)
                
                print_json(params)
            else:
                print_error("No access token found in URL fragment")
                raise typer.Exit(1)
                
        elif "?" in callback_url:
            # Server-side flow - parse query string
            query = callback_url.split("?")[1]
            params = {}
            for param in query.split("&"):
                if "=" in param:
                    key, value = param.split("=", 1)
                    params[key] = value
            
            if "code" in params:
                typer.echo("\n✅ Server-side OAuth Flow Detected", err=True)
                typer.echo("=" * 60, err=True)
                typer.echo("\nExtracted authorization code:", err=True)
                typer.echo(f"  Code: {params.get('code')}\n", err=True)
                
                typer.echo("Add to your .env file:", err=True)
                typer.echo(f"  PODIO_AUTHORIZATION_CODE={params.get('code')}", err=True)
                typer.echo("  PODIO_REDIRECT_URI=<your_redirect_uri>", err=True)
                
                print_json(params)
            elif "error" in params:
                typer.echo("\n❌ Authorization Error", err=True)
                typer.echo("=" * 60, err=True)
                typer.echo(f"  Error: {params.get('error')}", err=True)
                typer.echo(f"  Reason: {params.get('error_reason')}", err=True)
                typer.echo(f"  Description: {params.get('error_description')}", err=True)
                print_json(params)
                raise typer.Exit(1)
            else:
                print_error("No authorization code found in query string")
                raise typer.Exit(1)
        else:
            print_error("Invalid callback URL format. Expected query string (?) or fragment (#)")
            raise typer.Exit(1)
            
    except typer.Exit:
        raise
    except Exception as e:
        print_error(f"Failed to parse callback URL: {e}")
        raise typer.Exit(1)

