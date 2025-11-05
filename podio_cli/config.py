"""Configuration management for Podio CLI."""
import os
from pathlib import Path
from typing import Optional
from dotenv import load_dotenv


class Config:
    """Configuration manager for Podio CLI authentication and settings."""

    def __init__(self):
        """Initialize configuration by loading from .env file."""
        # Look for .env in these locations (in order of priority):
        # 1. User's home directory: ~/.podio/.env
        # 2. Current directory (for development/testing)
        # 3. Parent directory (for development/testing)

        possible_paths = [
            Path.home() / ".podio" / ".env",  # Global config
            Path.cwd() / ".env",              # Local override
            Path.cwd().parent / ".env",       # Parent directory
        ]

        env_loaded = False
        for env_path in possible_paths:
            if env_path.exists():
                load_dotenv(env_path, override=False)
                env_loaded = True
                break

        if not env_loaded:
            # Try loading from default location (checks environment variables)
            load_dotenv()

    @property
    def client_id(self) -> Optional[str]:
        """Get Podio client ID."""
        return os.getenv("PODIO_CLIENT_ID")

    @property
    def client_secret(self) -> Optional[str]:
        """Get Podio client secret."""
        return os.getenv("PODIO_CLIENT_SECRET")

    @property
    def username(self) -> Optional[str]:
        """Get Podio username (for user authentication)."""
        return os.getenv("PODIO_USERNAME")

    @property
    def password(self) -> Optional[str]:
        """Get Podio password (for user authentication)."""
        return os.getenv("PODIO_PASSWORD")

    @property
    def app_id(self) -> Optional[str]:
        """Get Podio app ID (for app authentication)."""
        return os.getenv("PODIO_APP_ID")

    @property
    def app_token(self) -> Optional[str]:
        """Get Podio app token (for app authentication)."""
        return os.getenv("PODIO_APP_TOKEN")

    @property
    def workspace_id(self) -> Optional[str]:
        """Get default workspace/space ID."""
        return os.getenv("PODIO_WORKSPACE_ID")

    @property
    def organization_id(self) -> Optional[str]:
        """Get default organization ID."""
        return os.getenv("PODIO_ORGANIZATION_ID")

    @property
    def authorization_code(self) -> Optional[str]:
        """Get authorization code (for server-side OAuth flow)."""
        return os.getenv("PODIO_AUTHORIZATION_CODE")

    @property
    def redirect_uri(self) -> Optional[str]:
        """Get redirect URI (for OAuth flows)."""
        return os.getenv("PODIO_REDIRECT_URI")

    @property
    def access_token(self) -> Optional[str]:
        """Get access token (for client-side OAuth flow)."""
        return os.getenv("PODIO_ACCESS_TOKEN")

    @property
    def refresh_token(self) -> Optional[str]:
        """Get refresh token (for token refresh)."""
        return os.getenv("PODIO_REFRESH_TOKEN")

    def has_user_auth(self) -> bool:
        """Check if user authentication credentials are available."""
        return bool(
            self.client_id
            and self.client_secret
            and self.username
            and self.password
        )

    def has_app_auth(self) -> bool:
        """Check if app authentication credentials are available."""
        return bool(
            self.client_id
            and self.client_secret
            and self.app_id
            and self.app_token
        )

    def has_authorization_code_auth(self) -> bool:
        """Check if authorization code credentials are available."""
        return bool(
            self.client_id
            and self.client_secret
            and self.authorization_code
            and self.redirect_uri
        )

    def has_token_auth(self) -> bool:
        """Check if access token authentication is available."""
        return bool(self.access_token)

    def get_missing_credentials(self) -> list[str]:
        """Get list of missing credentials for any authentication method."""
        missing = []

        # Check if any complete auth method is available
        has_complete_auth = (
            self.has_authorization_code_auth() or 
            self.has_user_auth() or 
            self.has_app_auth() or 
            self.has_token_auth()
        )

        if has_complete_auth:
            return missing  # No missing credentials if we have a complete auth method

        # No complete auth found, list what's needed
        if not self.client_id:
            missing.append("PODIO_CLIENT_ID")
        if not self.client_secret:
            missing.append("PODIO_CLIENT_SECRET")

        # Show what's needed for each auth method
        if not self.access_token:
            missing.append("PODIO_ACCESS_TOKEN (for token auth)")
        if not self.authorization_code or not self.redirect_uri:
            missing.append("PODIO_AUTHORIZATION_CODE + PODIO_REDIRECT_URI (for code auth)")
        if not self.username or not self.password:
            missing.append("PODIO_USERNAME + PODIO_PASSWORD (for user auth)")
        if not self.app_id or not self.app_token:
            missing.append("PODIO_APP_ID + PODIO_APP_TOKEN (for app auth)")

        return missing


# Global config instance
_config: Optional[Config] = None


def get_config() -> Config:
    """Get or create the global config instance."""
    global _config
    if _config is None:
        _config = Config()
    return _config
