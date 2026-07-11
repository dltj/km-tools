# kmtools/config.py

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

from pydantic import BaseModel, PrivateAttr, SecretStr
from pydantic_settings import (
    BaseSettings,
    PydanticBaseSettingsSource,
    SettingsConfigDict,
    YamlConfigSettingsSource,
)

DEFAULT_CONFIG_DIR = (
    Path.home() / "Library" / "Application Support" / "org.dltj.kmtools"
)

DEFAULT_CONFIG_FILE = DEFAULT_CONFIG_DIR / "config.yml"

logger = logging.getLogger(__name__)


class KMToolsSettings(BaseModel):
    logfile: Path
    dbfile: Path = Path("kmtools.sqlite3")


class TwitterSettings(BaseModel):
    consumer_key: str
    consumer_secret: SecretStr
    access_token_key: SecretStr
    access_token_secret: SecretStr


class MastodonSettings(BaseModel):
    client_id: str
    client_secret: SecretStr
    access_token: SecretStr
    api_base_url: str


class PinboardSettings(BaseModel):
    auth_token: SecretStr


class HypothesisSettings(BaseModel):
    user: str
    api_token: SecretStr


class WaybackSettings(BaseModel):
    access_key: str
    secret_key: SecretStr


class ObsidianSettings(BaseModel):
    db_directory: Path
    daily_directory: Path
    source_directory: Path
    template_directory: Path


class KagiSettings(BaseModel):
    api_token: SecretStr


class Config(BaseSettings):
    """
    Application configuration.

    Values are loaded, in order of priority, from:

    1. explicit keyword arguments passed to Config(...)
    2. environment variables
    3. YAML config file
    4. dotenv file, if configured
    5. file secrets, if configured
    """

    dry_run: bool = False

    kmtools: KMToolsSettings
    twitter: TwitterSettings
    mastodon: MastodonSettings
    pinboard: PinboardSettings
    hypothesis: HypothesisSettings
    wayback: WaybackSettings
    obsidian: ObsidianSettings
    kagi: KagiSettings

    _config_file: Path = PrivateAttr(default=DEFAULT_CONFIG_FILE)

    model_config = SettingsConfigDict(
        yaml_file=DEFAULT_CONFIG_FILE,
        env_prefix="KMTOOLS_",
        env_nested_delimiter="__",
        extra="forbid",
    )

    @classmethod
    def settings_customise_sources(
        cls,
        settings_cls: type[BaseSettings],
        init_settings: PydanticBaseSettingsSource,
        env_settings: PydanticBaseSettingsSource,
        dotenv_settings: PydanticBaseSettingsSource,
        file_secret_settings: PydanticBaseSettingsSource,
    ) -> tuple[PydanticBaseSettingsSource, ...]:
        return (
            init_settings,
            env_settings,
            YamlConfigSettingsSource(settings_cls),
            dotenv_settings,
            file_secret_settings,
        )

    @property
    def config_file(self) -> Path:
        return self._config_file

    @property
    def config_dir(self) -> Path:
        return self._config_file.parent


def build_config(
    **overrides: Any,
) -> Config:
    """
    Create a Config instance.

    Args:
        **overrides:
            Explicit setting overrides. These have highest priority.

    Returns:
        Validated Config instance.

    Examples:
        Load from default config.yaml:

            config = get_config()

        Override nested settings:

            config = get_config(
                kmtools={"dbfile": "test.sqlite3"},
                kagi={"api_token": "fake-token"},
            )

        Override with environment variable:

            KMTOOLS_KAGI__API_TOKEN=abc123 kmtools ...

    """

    logger.debug(
        "config.get_config.creating",
        extra={
            "has_overrides": bool(overrides),
            "override_keys": list(overrides.keys()) if overrides else [],
        },
    )

    return Config(**overrides)


_config: Config | None = None


def init_config(
    **overrides: Any,
) -> Config:
    """
    Initialize the process-wide Config.

    Call this once from the CLI entry point.
    """
    global _config

    _config = build_config(**overrides)
    return _config


def get_config() -> Config:
    """
    Return the process-wide Config.

    If it has not been initialized explicitly, load the default config.
    """
    global _config

    if _config is None:
        _config = build_config()

    return _config


def reset_config() -> None:
    """
    Mostly useful for tests.
    """
    global _config
    _config = None
