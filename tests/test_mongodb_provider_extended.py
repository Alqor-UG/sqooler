"""
The tests for the extended mongodb storage provider
"""

from typing import Any

import pytest
from decouple import config
from pytest import LogCaptureFixture

from sqooler.schemes import MongodbLoginInformation
from sqooler.storage_providers.mongodb import MongodbCore, MongodbProviderExtended

from .storage_provider_test_utils import StorageCoreTestUtils, StorageProviderTestUtils

DB_NAME = "mongodbtest"


class TestMongodbCore(StorageCoreTestUtils):
    """
    The class that contains all the tests for the extended local provider.
    """

    def get_login_class(self) -> Any:
        """
        Get the storage provider.
        """
        return MongodbLoginInformation

    def get_storage_provider(self) -> Any:
        """
        Get the storage provider.
        """
        return MongodbCore

    def get_login(self) -> MongodbLoginInformation:
        """
        Pull all the login information from the environment variables.
        """
        # put together the login information
        mongodb_username = config("MONGODB_USERNAME")
        mongodb_password = config("MONGODB_PASSWORD")
        mongodb_database_url = config("MONGODB_DATABASE_URL")
        login_dict = {
            "mongodb_username": mongodb_username,
            "mongodb_password": mongodb_password,
            "mongodb_database_url": mongodb_database_url,
        }
        return MongodbLoginInformation(**login_dict)

    def test_not_active(self) -> None:
        """
        Test that we cannot work with the provider if it is not active.
        """
        print("Testing not active")
        self.active_tests(DB_NAME)

    def test_upload_etc(self) -> None:
        """
        Test that it is possible to upload a file.
        """
        self.upload_tests(DB_NAME)

    def test_file_remove(self) -> None:
        """
        Test that it is possible to remove a file and we raise the right errors.
        """
        self.remove_file_not_found_test(DB_NAME)

    def test_update_raise_error(self) -> None:
        """
        Test that it is update a file once it was uploaded.
        """
        self.update_raise_error_test(DB_NAME)


class TestMongodbProviderExtended(StorageProviderTestUtils):
    """
    The class that contains all the tests for the dropbox provider.
    """

    def get_login_class(self) -> Any:
        """
        Get the storage provider.
        """
        return MongodbLoginInformation

    def get_storage_provider(self) -> Any:
        """
        Get the storage provider.
        """
        return MongodbProviderExtended

    def get_login(self) -> MongodbLoginInformation:
        """
        Get the login information for the mongodb database.
        """
        # put together the login information
        mongodb_username = config("MONGODB_USERNAME")
        mongodb_password = config("MONGODB_PASSWORD")
        mongodb_database_url = config("MONGODB_DATABASE_URL")
        login_dict = {
            "mongodb_username": mongodb_username,
            "mongodb_password": mongodb_password,
            "mongodb_database_url": mongodb_database_url,
        }
        return MongodbLoginInformation(**login_dict)

    def test_mongodb_object(self) -> None:
        """
        Test that we can create a MongoDB object.
        """
        self.storage_object_tests(DB_NAME)

    @pytest.mark.parametrize("sign_it", [True, False])
    def test_upload_and_update_config(self, sign_it: bool) -> None:
        """
        Test that we can upload and update a config.
        """
        self.config_tests(DB_NAME, sign=sign_it)

    @pytest.mark.parametrize("sign_it", [True, False])
    def test_missing_status_in_update(
        self,
        sign_it: bool,
        caplog: LogCaptureFixture,
    ) -> None:
        """
        Test that we can upload and update a config.
        """
        self.missing_status_tests(DB_NAME, sign=sign_it, caplog=caplog)

    def test_upload_public_key(self) -> None:
        """
        Test that it is possible to upload the public key.
        """
        self.signature_tests(DB_NAME)

    @pytest.mark.parametrize("sign_it", [True, False])
    def test_backend_status(
        self,
        sign_it: bool,
        caplog: LogCaptureFixture,
    ) -> None:
        """
        Test that we can get the status of a backend.
        """
        self.backend_status_tests(DB_NAME, sign=sign_it, caplog=caplog)

    def test_sign_and_verify_result(self) -> None:
        """
        Test that it is possible a result a verify it properly.
        """
        self.sign_and_verify_result_test(DB_NAME)

    @pytest.mark.parametrize("sign_it", [True, False])
    def test_status_dict(self, sign_it: bool) -> None:
        """
        Test that we can get the status of a backend.
        """
        self.status_tests(DB_NAME, sign=sign_it)

    @pytest.mark.parametrize("sign_it", [True, False])
    def test_jobs(self, sign_it: bool) -> None:
        """
        Test that we can handle the necessary functions for the jobs and status.
        """
        backend_name, _, _, storage_provider = self.job_tests(DB_NAME, sign=sign_it)

        # remove the obsolete collection from the storage
        database = storage_provider.client["jobs"]
        collection = database[f"queued.{backend_name}"]
        collection.drop()
        collection = database[f"finished.{backend_name}"]
        collection.drop()

        # remove the obsolete collection from the storage
        database = storage_provider.client["status"]
        collection = database[backend_name]
        collection.drop()

        # remove the obsolete collection from the storage
        database = storage_provider.client["results"]
        collection = database[backend_name]
        collection.drop()

    def test_file_queue(self) -> None:
        """
        Test that we can queue a file.
        """
        self.file_queue_test(DB_NAME)
