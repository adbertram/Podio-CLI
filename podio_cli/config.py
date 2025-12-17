"""Configuration management for Podio CLI."""
import os
from pathlib import Path
from typing import Optional
from dotenv import load_dotenv
from pypodio2 import RetryConfig


class Config:
    """Configuration manager for Podio CLI authentication and settings."""

    def __init__(self):
        """Initialize configuration by loading from .env file."""
        # Use .env file in the cli-tools/podio installation directory
        # This is the directory containing podio_cli package

        # Get the directory where this config.py file is located
        config_dir = Path(__file__).parent.parent  # Go up from podio_cli/ to cli-tools/podio/
        cli_env_path = config_dir / ".env"

        self.env_file_path = cli_env_path
        self._retry_config: Optional[RetryConfig] = None

        if cli_env_path.exists():
            load_dotenv(cli_env_path, override=True)
        else:
            # Create default .env if it doesn't exist
            cli_env_path.parent.mkdir(parents=True, exist_ok=True)
            cli_env_path.touch()

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

    def save_tokens(self, access_token: str, refresh_token: str):
        """
        Save refreshed tokens to the .env file.

        Args:
            access_token: New access token
            refresh_token: New refresh token
        """
        if not self.env_file_path:
            return

        # Ensure the directory exists
        self.env_file_path.parent.mkdir(parents=True, exist_ok=True)

        # Read existing .env file content
        env_content = {}
        if self.env_file_path.exists():
            with open(self.env_file_path, 'r') as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith('#') and '=' in line:
                        key, value = line.split('=', 1)
                        env_content[key] = value

        # Update tokens
        env_content['PODIO_ACCESS_TOKEN'] = access_token
        env_content['PODIO_REFRESH_TOKEN'] = refresh_token

        # Write back to file
        with open(self.env_file_path, 'w') as f:
            for key, value in env_content.items():
                f.write(f"{key}={value}\n")

    def get_retry_config(self) -> RetryConfig:
        """
        Build (and cache) the retry configuration for outbound Podio requests.

        Environment variables:
            PODIO_RETRY_MAX_ATTEMPTS      (int >= 0, default 5)
            PODIO_RETRY_BASE_DELAY        (float > 0, default 2.0 seconds)
            PODIO_RETRY_MAX_DELAY         (float >= base_delay, default 60.0 seconds)
            PODIO_RETRY_EXPONENTIAL_BASE  (float > 1, default 2.0)
            PODIO_RETRY_JITTER            ("true"/"false", default true)
            PODIO_RETRY_ON_RATE_LIMIT     ("true"/"false", default true)
        """
        if self._retry_config is not None:
            return self._retry_config

        max_retries = self._get_int_env("PODIO_RETRY_MAX_ATTEMPTS", default=5, minimum=0)
        base_delay = self._get_float_env("PODIO_RETRY_BASE_DELAY", default=2.0, minimum=0.001)
        max_delay = self._get_float_env("PODIO_RETRY_MAX_DELAY", default=60.0, minimum=base_delay)
        exponential_base = self._get_float_env(
            "PODIO_RETRY_EXPONENTIAL_BASE",
            default=2.0,
            minimum=1.001
        )
        jitter = self._get_bool_env("PODIO_RETRY_JITTER", default=True)
        retry_on_rate_limit = self._get_bool_env("PODIO_RETRY_ON_RATE_LIMIT", default=True)

        self._retry_config = RetryConfig(
            max_retries=max_retries,
            base_delay=base_delay,
            max_delay=max_delay,
            exponential_base=exponential_base,
            jitter=jitter,
            retry_on_rate_limit=retry_on_rate_limit
        )
        return self._retry_config

    def _get_int_env(self, name: str, default: int, minimum: Optional[int] = None) -> int:
        value = os.getenv(name)
        if value is None:
            return default
        try:
            parsed = int(value)
        except ValueError:
            raise ValueError(f"{name} must be an integer, got {value!r}")
        if minimum is not None and parsed < minimum:
            raise ValueError(f"{name} must be >= {minimum}, got {parsed}")
        return parsed

    def _get_float_env(self, name: str, default: float, minimum: Optional[float] = None) -> float:
        value = os.getenv(name)
        if value is None:
            return default
        try:
            parsed = float(value)
        except ValueError:
            raise ValueError(f"{name} must be a number, got {value!r}")
        if minimum is not None and parsed < minimum:
            raise ValueError(f"{name} must be >= {minimum}, got {parsed}")
        return parsed

    def _get_bool_env(self, name: str, default: bool) -> bool:
        value = os.getenv(name)
        if value is None:
            return default
        normalized = value.strip().lower()
        if normalized not in {"true", "false"}:
            raise ValueError(f"{name} must be either 'true' or 'false', got {value!r}")
        return normalized == "true"


# Global config instance
_config: Optional[Config] = None


def get_config() -> Config:
    """Get or create the global config instance."""
    global _config
    if _config is None:
        _config = Config()
    return _config
