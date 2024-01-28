"""
This module contains the test utils for the storage providers. So it is called by the ..._provider tests.
"""

from typing import Any

import pytest
from pydantic import ValidationError


class StorageProviderTestUtils:
    """
    The test utils for the storage providers.
    """

    def get_login_class(self) -> Any:
        """
        Get the login for the provider.
        """
        raise NotImplementedError

    def get_storage_provider(self) -> Any:
        """
        Get the storage provider.
        """
        raise NotImplementedError

    def get_login(self) -> Any:
        """
        Get the login information for the storage provider.
        """
        raise NotImplementedError

    def storage_object_tests(self, db_name: str) -> None:
        """
        Test that we can create a MongoDB object.

        Args:
            db_name: The name of the database.
        """
        storage_provider_class = self.get_storage_provider()
        login_info_class = self.get_login_class()
        mongodb_provider = storage_provider_class(self.get_login(), db_name)
        assert not mongodb_provider is None
        # test that we cannot create a dropbox object a poor login dict structure
        poor_login_dict = {
            "app_key_t": "test",
            "app_secret": "test",
            "refresh_token": "test",
        }
        with pytest.raises(ValidationError):
            storage_provider_class(login_info_class(**poor_login_dict), db_name)

        # test that the db name is all lowercase
        storage_provider = storage_provider_class(self.get_login(), "Whatever")
        assert storage_provider.name == "whatever"

        # test what happens if the name contains contains underscores
        with pytest.raises(ValueError):
            storage_provider = storage_provider_class(
                self.get_login(), "Whatever_is_wrong"
            )

        # test what happens if the name contains contains underscores
        with pytest.raises(ValueError):
            storage_provider = storage_provider_class(
                self.get_login(), "Whatever%/iswrong"
            )
