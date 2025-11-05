"""Configuration management for Podio CLI."""
import os
from pathlib import Path
from typing import Optional
from dotenv import load_dotenv


class Config:
    """Configuration manager for Podio CLI authentication and settings."""

    def __init__(self):
        """Initialize configuration by loading from .env file."""
        # Look for .env in current directory first, then parent directory
        env_path = Path.cwd() / ".env"
        if not env_path.exists():
            env_path = Path.cwd().parent / ".env"

        if env_path.exists():
            load_dotenv(env_path)
        else:
            # Try loading from default location
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

    def get_missing_credentials(self) -> list[str]:
        """Get list of missing credentials for any authentication method."""
        missing = []

        # Check for client credentials (required for all methods)
        if not self.client_id:
            missing.append("PODIO_CLIENT_ID")
        if not self.client_secret:
            missing.append("PODIO_CLIENT_SECRET")

        # Check if either user or app auth is complete
        has_complete_auth = self.has_user_auth() or self.has_app_auth()

        if not has_complete_auth:
            if not self.username:
                missing.append("PODIO_USERNAME (for user auth)")
            if not self.password:
                missing.append("PODIO_PASSWORD (for user auth)")
            if not self.app_id:
                missing.append("PODIO_APP_ID (for app auth)")
            if not self.app_token:
                missing.append("PODIO_APP_TOKEN (for app auth)")

        return missing


# Global config instance
_config: Optional[Config] = None


def get_config() -> Config:
    """Get or create the global config instance."""
    global _config
    if _config is None:
        _config = Config()
    return _config
