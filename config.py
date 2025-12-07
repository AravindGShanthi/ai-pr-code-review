"""
Configuration management for AI PR Assist application.

Handles environment variables and application settings with type validation.
"""

import os
from functools import lru_cache
from typing import Literal

from pydantic import BaseModel, Field, ValidationError, field_validator


class Settings(BaseModel):
    """Application settings loaded from environment variables."""

    github_token: str = Field(
        default="",
        description="GitHub API token for authentication",
    )

    openai_api_key: str = Field(
        default="",
        description="OpenAI API key for LLM access",
    )

    model_name: str = Field(
        default="gpt-4o-mini",
        description="LLM model to use for code review",
    )

    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = Field(
        default="INFO",
        description="Logging level",
    )

    debug_mode: bool = Field(
        default=False,
        description="Enable debug mode",
    )

    @field_validator("github_token")
    @classmethod
    def validate_github_token(cls, v: str) -> str:
        """Validate GitHub token is provided."""
        v = v.strip() if v else ""
        if not v:
            raise ValueError("GITHUB_TOKEN environment variable is required")
        if not v.startswith("github"):
            raise ValueError("GITHUB_TOKEN should start with 'github'")
        return v

    @field_validator("openai_api_key")
    @classmethod
    def validate_openai_key(cls, v: str) -> str:
        """Validate OpenAI API key is provided."""
        v = v.strip() if v else ""
        if not v:
            raise ValueError("OPENAI_API_KEY environment variable is required")
        if not v.startswith("sk-"):
            raise ValueError("OPENAI_API_KEY should start with 'sk-'")
        return v


def _load_settings() -> Settings:
    """
    Load application settings from environment.

    Returns:
        Settings: Validated application settings.

    Raises:
        ValueError: If required environment variables are missing or invalid.

    """
    try:
        log_level = os.getenv("LOG_LEVEL", "INFO")
        if log_level not in ("DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"):
            log_level = "INFO"
        debug_str = os.getenv("DEBUG", "False").lower()
        debug_mode = debug_str in ("true", "1", "yes")

        settings = Settings(
            github_token=os.getenv("GITHUB_TOKEN", ""),
            openai_api_key=os.getenv("OPENAI_API_KEY", ""),
            model_name=os.getenv("MODEL_NAME", "gpt-4o-mini"),
            log_level=log_level,  # type: ignore[arg-type]
            debug_mode=debug_mode,
        )
    except ValidationError as e:
        error_message = f"Configuration validation error: {e}"
        raise ValueError(error_message) from e
    else:
        return settings


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """
    Get cached application settings.

    Returns:
        Settings: Validated application settings.

    """
    return _load_settings()


def init_settings() -> Settings:
    """
    Initialize settings (ensures caching is set up).

    Returns:
        Settings: Validated application settings.

    """
    return get_settings()


def get_github_token() -> str:
    """
    Get GitHub token from settings.

    Returns:
        str: GitHub API token.

    """
    return get_settings().github_token


def get_openai_key() -> str:
    """
    Get OpenAI API key from settings.

    Returns:
        str: OpenAI API key.

    """
    return get_settings().openai_api_key


def get_model_name() -> str:
    """
    Get model name from settings.

    Returns:
        str: Model name for LLM.

    """
    return get_settings().model_name
