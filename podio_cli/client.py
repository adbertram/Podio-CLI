"""Podio client factory and wrapper."""
import sys
from typing import Optional
from pypodio2 import api
from .config import get_config


# Global client instance
_client: Optional[api.OAuthClient] = None


class ClientError(Exception):
    """Exception raised for client initialization errors."""
    pass


def get_client() -> api.OAuthClient:
    """
    Get or create the global Podio API client.

    Returns:
        OAuthClient: Authenticated Podio API client

    Raises:
        ClientError: If credentials are missing or authentication fails
    """
    global _client

    if _client is not None:
        return _client

    config = get_config()

    # Check for missing credentials
    missing = config.get_missing_credentials()
    if missing:
        error_msg = (
            "Missing required Podio credentials. Please set the following "
            "environment variables in your .env file:\n\n"
        )
        for cred in missing:
            error_msg += f"  - {cred}\n"

        error_msg += "\nFor client-side token authentication (use existing token):\n"
        error_msg += "  PODIO_ACCESS_TOKEN (optional: PODIO_REFRESH_TOKEN)\n"
        error_msg += "\nFor server-side authorization code flow (most secure):\n"
        error_msg += "  PODIO_CLIENT_ID, PODIO_CLIENT_SECRET, PODIO_AUTHORIZATION_CODE, PODIO_REDIRECT_URI\n"
        error_msg += "\nFor user authentication (recommended for multiple apps):\n"
        error_msg += "  PODIO_CLIENT_ID, PODIO_CLIENT_SECRET, PODIO_USERNAME, PODIO_PASSWORD\n"
        error_msg += "\nFor app authentication (single app only):\n"
        error_msg += "  PODIO_CLIENT_ID, PODIO_CLIENT_SECRET, PODIO_APP_ID, PODIO_APP_TOKEN\n"

        raise ClientError(error_msg)

    # Try token authentication first (simplest, no extra round trip)
    if config.has_token_auth():
        try:
            _client = api.OAuthTokenClient(
                access_token=config.access_token,
                refresh_token=config.refresh_token,
                client_id=config.client_id,  # Pass for token refresh capability
                client_secret=config.client_secret  # Pass for token refresh capability
            )
            return _client
        except Exception as e:
            raise ClientError(f"Failed to authenticate with access token: {e}")

    # Try authorization code flow (most secure for web apps)
    if config.has_authorization_code_auth():
        try:
            _client = api.OAuthAuthorizationCodeClient(
                client_id=config.client_id,
                client_secret=config.client_secret,
                authorization_code=config.authorization_code,
                redirect_uri=config.redirect_uri
            )
            return _client
        except Exception as e:
            raise ClientError(f"Failed to authenticate with authorization code: {e}")
    
    # Try user authentication (preferred for multi-app access)
    if config.has_user_auth():
        try:
            _client = api.OAuthClient(
                api_key=config.client_id,
                api_secret=config.client_secret,
                login=config.username,
                password=config.password
            )
            return _client
        except Exception as e:
            raise ClientError(f"Failed to authenticate with user credentials: {e}")

    # Fall back to app authentication
    if config.has_app_auth():
        try:
            _client = api.OAuthAppClient(
                client_id=config.client_id,
                client_secret=config.client_secret,
                app_id=int(config.app_id),
                app_token=config.app_token
            )
            return _client
        except Exception as e:
            raise ClientError(f"Failed to authenticate with app credentials: {e}")

    # This shouldn't happen if get_missing_credentials() works correctly
    raise ClientError("No valid authentication method available")


def reset_client():
    """Reset the global client instance (useful for testing)."""
    global _client
    _client = None
