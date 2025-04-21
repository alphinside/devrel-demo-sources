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
        GCLOUD_LOCATION: Google Cloud location for API services.
        GCLOUD_PROJECT_ID: Google Cloud project identifier.
        BACKEND_URL: URL for the backend service API endpoint.
        STORAGE_BUCKET_NAME: Name of the Google Cloud Storage bucket for storing receipts.
        DB_COLLECTION_NAME: Name of the Firestore collection for storing receipts.
    """

    GCLOUD_LOCATION: str
    GCLOUD_PROJECT_ID: str
    BACKEND_URL: str = "http://localhost:8081/chat"
    STORAGE_BUCKET_NAME: str = "personal-expense-assistant-receipts"
    DB_COLLECTION_NAME: str = "personal-expense-assistant-receipts"

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
        1. Environment variables
        2. YAML configuration file
        3. Constructor-provided values

        Args:
            settings_cls: The Settings class type.
            init_settings: Settings from class initialization.
            env_settings: Settings from environment variables.
            dotenv_settings: Settings from .env file (not used).
            file_secret_settings: Settings from secrets file (not used).

        Returns:
            A tuple of configuration sources in priority order.
        """
        return (
            env_settings,  # Environment variables as first priority
            YamlConfigSettingsSource(
                settings_cls
            ),  # YAML configuration file as second priority
            init_settings,  # Constructor-provided values as last priority
        )


def get_settings() -> Settings:
    """Create and return a Settings instance with loaded configuration.

    Initializes a Settings object that loads configuration values from
    environment variables and the YAML configuration file, with environment
    variables taking precedence.

    Returns:
        A fully configured Settings instance containing all application configuration.
    """
    return Settings()
