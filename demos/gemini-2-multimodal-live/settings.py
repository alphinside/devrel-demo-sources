"""
Copyright 2025 Google LLC

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

    https://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.
"""

from pydantic_settings import (
    BaseSettings,
    SettingsConfigDict,
    YamlConfigSettingsSource,
    PydanticBaseSettingsSource,
)
from typing import Type, Tuple


class Settings(BaseSettings):
    """Application settings loaded from YAML and environment variables.

    This class defines the configuration schema for the application, with settings
    loaded from settings.yaml file and overridable via environment variables.

    Attributes:
        OLLAMA_SERVICE_URL: Base URL for the Ollama service endpoint
        CLOUDRUN_SERVICE_ACCOUNT_KEY: Path to the service account key file for Cloud Run authentication
        CHAT_HISTORY_DB_URI: Database connection URI for storing chat history
    """

    GEMINI_API_KEY: str

    model_config = SettingsConfigDict(
        yaml_file="settings.yaml", yaml_file_encoding="utf-8"
    )

    @classmethod
    def settings_customise_sources(
        cls,
        settings_cls: Type[BaseSettings],
        init_settings: PydanticBaseSettingsSource,
        env_settings: PydanticBaseSettingsSource,
        dotenv_settings: PydanticBaseSettingsSource,
        file_secret_settings: PydanticBaseSettingsSource,
    ) -> Tuple[PydanticBaseSettingsSource, ...]:
        """Customize the settings sources and their priority order.

        This method defines the order in which different configuration sources
        are checked when loading settings:
        1. Constructor-provided values
        2. YAML configuration file
        3. Environment variables

        Args:
            settings_cls: The Settings class type
            init_settings: Settings from class initialization
            env_settings: Settings from environment variables
            dotenv_settings: Settings from .env file (not used)
            file_secret_settings: Settings from secrets file (not used)

        Returns:
            A tuple of configuration sources in priority order
        """
        return (
            init_settings,  # First, try init_settings (from constructor)
            YamlConfigSettingsSource(settings_cls),  # Then, try YAML
            env_settings,  # Finally, try environment variables
        )


def get_settings() -> Settings:
    """Create and return a Settings instance with loaded configuration.

    Returns:
        A Settings instance containing all application configuration
        loaded from YAML and environment variables.
    """
    return Settings()
