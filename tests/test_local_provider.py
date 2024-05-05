"""
The tests for the storage provider using mongodb
"""

import shutil
from typing import Any

# get the environment variables
from decouple import config

from sqooler.schemes import LocalLoginInformation
from sqooler.storage_providers.local import LocalProvider

from .storage_provider_test_utils import StorageProviderTestUtils

DB_NAME = "storage"


class TestLocalProvider(StorageProviderTestUtils):
    """
    The class that contains all the tests for the dropbox provider.
    """

    def get_login_class(self) -> Any:
        """
        Get the storage provider.
        """
        return LocalLoginInformation

    def get_storage_provider(self) -> Any:
        """
        Get the storage provider.
        """
        return LocalProvider

    @classmethod
    def teardown_class(cls) -> None:
        """
        Remove the `storage` folder.
        """
        shutil.rmtree(config("BASE_PATH"))

    def get_login(self) -> LocalLoginInformation:
        """
        Pull all the login information from the environment variables.
        """
        return LocalLoginInformation(base_path=config("BASE_PATH"))

    def test_upload_etc(self) -> None:
        """
        Test that it is possible to upload a file.
        """
        self.upload_tests(DB_NAME)
