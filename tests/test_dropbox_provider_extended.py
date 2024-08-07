"""
The tests for the storage provider
"""

from typing import Any

import pytest
from decouple import config
from pytest import LogCaptureFixture

from sqooler.schemes import DropboxLoginInformation
from sqooler.storage_providers.dropbox import DropboxCore, DropboxProviderExtended

from .storage_provider_test_utils import StorageCoreTestUtils, StorageProviderTestUtils

DB_NAME = "dropboxtest"


class TestDropboxCore(StorageCoreTestUtils):
    """
    The class that contains all the tests for the dropbox core.
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
        return DropboxCore

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

    def test_file_remove(self) -> None:
        """
        Test that it is possible to remove a file and we raise the right errors.
        """
        self.remove_file_not_found_test(DB_NAME)

    def test_not_active(self) -> None:
        """
        Test that we cannot work with the provider if it is not active.
        """
        self.active_tests(DB_NAME)

    def test_upload_etc(self) -> None:
        """
        Test that it is possible to upload a file.
        """
        self.upload_tests(DB_NAME)

    def test_update_raise_error(self) -> None:
        """
        Test that it is update a file once it was uploaded.
        """

        self.update_raise_error_test(DB_NAME)


class TestDropboxProviderExtended(StorageProviderTestUtils):
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
        return DropboxProviderExtended

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

    def test_dropbox_object(self) -> None:
        """
        Test that we can create a dropbox object.
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

    @pytest.mark.parametrize("sign_it", [True, False])
    def test_status_dict(self, sign_it: bool) -> None:
        """
        Test that we can get the status of a backend.
        """
        self.status_tests(DB_NAME, sign=sign_it)

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

    def test_file_queue(self) -> None:
        """
        Test that we can queue a file.
        """
        self.file_queue_test(DB_NAME)

    def test_sign_and_verify_result(self) -> None:
        """
        Test that it is possible a result a verify it properly.
        """
        self.sign_and_verify_result_test(DB_NAME)

    @pytest.mark.parametrize("sign_it", [True, False])
    def test_jobs(self, sign_it: bool) -> None:
        """
        Test that we can handle the necessary functions for the jobs and status.
        """
        backend_name, _, _, storage_provider = self.job_tests(DB_NAME, sign=sign_it)

        # remove the obsolete stuff in the Queued_Jobs folder
        queued_path = "/Backend_files/Queued_Jobs/" + backend_name
        storage_provider.delete_folder(queued_path)

    def test_upload_public_key(self) -> None:
        """
        Test that it is possible to upload the public key.
        """
        self.signature_tests(DB_NAME)

    def test_user_signature(self) -> None:
        """
        Test that we can create a signature for the user.
        """
        self.user_signature_tests(DB_NAME)
