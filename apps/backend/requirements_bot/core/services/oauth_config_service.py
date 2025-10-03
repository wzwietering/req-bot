import os

from pydantic import BaseModel, ValidationError


class OAuthProviderConfig(BaseModel):
    """OAuth provider configuration model."""

    name: str
    client_id: str
    client_secret: str
    server_metadata_url: str | None = None
    authorize_url: str | None = None
    access_token_url: str | None = None
    userinfo_endpoint: str | None = None
    scopes: list[str] = []


class ConfigValidationError(Exception):
    """Raised when OAuth configuration validation fails."""

    pass


class OAuthConfigService:
    """Service for validating and managing OAuth provider configurations."""

    SUPPORTED_PROVIDERS = {
        "google": {
            "required_scopes": ["openid", "email", "profile"],
            "server_metadata_url": "https://accounts.google.com/.well-known/openid-configuration",
        },
        "github": {
            "required_scopes": ["user:email"],
            "authorize_url": "https://github.com/login/oauth/authorize",
            "access_token_url": "https://github.com/login/oauth/access_token",
        },
        "microsoft": {
            "required_scopes": ["openid", "email", "profile", "User.Read"],
            "server_metadata_url": "https://login.microsoftonline.com/common/v2.0/.well-known/openid-configuration",
        },
    }

    def __init__(self):
        self._validated_configs: dict[str, OAuthProviderConfig] = {}

    def validate_provider_config(self, provider_name: str) -> OAuthProviderConfig:
        """Validate and return configuration for a specific provider."""
        if provider_name not in self.SUPPORTED_PROVIDERS:
            raise ConfigValidationError(f"Unsupported OAuth provider: {provider_name}")

        # Check if already validated
        if provider_name in self._validated_configs:
            return self._validated_configs[provider_name]

        try:
            config = self._get_provider_config_from_env(provider_name)
            self._validate_provider_requirements(provider_name, config)
            self._validated_configs[provider_name] = config
            return config
        except ValidationError as e:
            raise ConfigValidationError(f"Invalid configuration for {provider_name}: {e}") from e

    def get_available_providers(self) -> list[str]:
        """Get list of properly configured OAuth providers."""
        available = []
        for provider_name in self.SUPPORTED_PROVIDERS:
            try:
                self.validate_provider_config(provider_name)
                available.append(provider_name)
            except ConfigValidationError:
                continue
        return available

    def validate_all_configurations(self) -> dict[str, str]:
        """Validate all provider configurations and return status report."""
        results = {}
        for provider_name in self.SUPPORTED_PROVIDERS:
            try:
                self.validate_provider_config(provider_name)
                results[provider_name] = "configured"
            except ConfigValidationError as e:
                results[provider_name] = f"error: {str(e)}"
        return results

    def _get_provider_config_from_env(self, provider_name: str) -> OAuthProviderConfig:
        """Get provider configuration from environment variables."""
        prefix = provider_name.upper()
        client_id = os.getenv(f"{prefix}_CLIENT_ID")
        client_secret = os.getenv(f"{prefix}_CLIENT_SECRET")

        if not client_id:
            raise ConfigValidationError(f"Missing {prefix}_CLIENT_ID environment variable")
        if not client_secret:
            raise ConfigValidationError(f"Missing {prefix}_CLIENT_SECRET environment variable")

        provider_spec = self.SUPPORTED_PROVIDERS[provider_name]

        return OAuthProviderConfig(
            name=provider_name,
            client_id=client_id,
            client_secret=client_secret,
            server_metadata_url=provider_spec.get("server_metadata_url"),
            authorize_url=provider_spec.get("authorize_url"),
            access_token_url=provider_spec.get("access_token_url"),
            scopes=provider_spec.get("required_scopes", []),
        )

    def _validate_provider_requirements(self, provider_name: str, config: OAuthProviderConfig):
        """Validate provider-specific requirements."""
        if len(config.client_id) < 10:
            raise ConfigValidationError(f"Client ID for {provider_name} appears too short")

        if len(config.client_secret) < 10:
            raise ConfigValidationError(f"Client secret for {provider_name} appears too short")

        # Additional validation for specific providers
        if provider_name == "google" and not config.server_metadata_url:
            raise ConfigValidationError("Google OAuth requires server_metadata_url")

        if provider_name == "github" and (not config.authorize_url or not config.access_token_url):
            raise ConfigValidationError("GitHub OAuth requires authorize_url and access_token_url")

        if provider_name == "microsoft" and not config.server_metadata_url:
            raise ConfigValidationError("Microsoft OAuth requires server_metadata_url")
