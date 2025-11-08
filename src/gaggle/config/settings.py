"""Application settings and configuration management."""

from pydantic import Field, validator
from pydantic_settings import BaseSettings


class GaggleSettings(BaseSettings):
    """Gaggle application settings."""

    # LLM Configuration
    anthropic_api_key: str | None = Field(None, description="Anthropic API key")
    aws_profile: str | None = Field(None, description="AWS profile for Bedrock")
    aws_region: str = Field("us-east-1", description="AWS region")

    # GitHub Configuration
    github_token: str | None = Field(None, description="GitHub personal access token")
    github_repo: str | None = Field(None, description="GitHub repository name")
    github_org: str | None = Field(None, description="GitHub organization")

    # Sprint Configuration
    default_sprint_duration: int = Field(
        10, description="Default sprint duration in days"
    )
    max_parallel_tasks: int = Field(5, description="Maximum parallel tasks per sprint")
    default_team_size: int = Field(6, description="Default team size")

    # Model Configuration
    haiku_model: str = Field("claude-3-haiku-20240307", description="Haiku model ID")
    sonnet_model: str = Field(
        "claude-3-5-sonnet-20241022", description="Sonnet model ID"
    )
    opus_model: str = Field("claude-3-opus-20240229", description="Opus model ID")

    # Cost Management
    token_budget_per_sprint: int | None = Field(
        None, description="Token budget per sprint"
    )
    cost_tracking_enabled: bool = Field(True, description="Enable cost tracking")
    max_cost_per_sprint: float | None = Field(
        None, description="Maximum cost per sprint in USD"
    )

    # Logging Configuration
    log_level: str = Field("INFO", description="Logging level")
    structured_logging: bool = Field(True, description="Enable structured logging")
    log_file: str | None = Field(None, description="Log file path")

    # Development Configuration
    debug_mode: bool = Field(False, description="Enable debug mode")
    dry_run: bool = Field(False, description="Enable dry run mode (no actual changes)")

    class Config:
        env_file = ".env"
        env_prefix = "GAGGLE_"
        case_sensitive = False

    @validator("github_token")
    @classmethod
    def validate_github_token(cls, v):
        """Validate GitHub token format."""
        if v and not v.startswith(("ghp_", "github_pat_")):
            raise ValueError("GitHub token must start with ghp_ or github_pat_")
        return v

    @validator("log_level")
    @classmethod
    def validate_log_level(cls, v):
        """Validate log level."""
        valid_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        if v.upper() not in valid_levels:
            raise ValueError(f"Log level must be one of: {valid_levels}")
        return v.upper()


# Global settings instance
settings = GaggleSettings()
