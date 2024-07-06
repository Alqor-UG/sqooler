"""
The tests for the storage provider
"""

from typing import Any

# get the environment variables
from decouple import config

from sqooler.schemes import DropboxLoginInformation
from sqooler.storage_providers.dropbox import DropboxProvider

from .storage_provider_test_utils import (
    StorageProviderTestUtils,
    clean_dummies_from_folder,
)

DB_NAME = "dropboxtest"


class TestDropboxProvider(StorageProviderTestUtils):
    """
    The class that contains all the tests for the dropbox provider.
    """

    def get_login_class(self) -> Any:
        """
        Get the storage provider.
        """
        return DropboxLoginInformation

    def get_storage_provider(self) -> Any:
        """
        Get the storage provider.
        """
        return DropboxProvider

    def get_login(self) -> DropboxLoginInformation:
        """
        Get the login information for the dropbox database.
        """
        # put together the login information

        app_key = config("APP_KEY")
        app_secret = config("APP_SECRET")
        refresh_token = config("REFRESH_TOKEN")

        login_dict = {
            "app_key": app_key,
            "app_secret": app_secret,
            "refresh_token": refresh_token,
        }
        return DropboxLoginInformation(**login_dict)

    @classmethod
    def teardown_class(cls) -> None:
        """
        Clean out the old dummy files
        """
        # clean stupid dummy files for the config
        backend_config_path = "/Backend_files/Config/"
        clean_dummies_from_folder(backend_config_path)
