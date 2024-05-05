"""
The tests for the storage provider
"""

import uuid
from typing import Any

import pytest
from decouple import config
from pytest import LogCaptureFixture

from sqooler.schemes import DropboxLoginInformation
from sqooler.storage_providers.dropbox import DropboxProviderExtended

from .storage_provider_test_utils import (
    StorageProviderTestUtils,
    clean_dummies_from_folder,
)

DB_NAME = "dropboxtest"


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

    @classmethod
    def teardown_class(cls) -> None:
        """
        Clean out the old dummy files
        """
        # clean stupid dummy files for the config
        backend_config_path = "/Backend_files/Config/"
        clean_dummies_from_folder(backend_config_path)

    def test_dropbox_object(self) -> None:
        """
        Test that we can create a dropbox object.
        """
        self.storage_object_tests(DB_NAME)

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

    @pytest.mark.parametrize("sign_it", [True, False])
    def test_upload_and_update_config(self, sign_it: bool) -> None:
        """
        Test that we can upload and update a config.
        """
        self.config_tests(DB_NAME, sign=sign_it)

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

        # remove the obsolete status from the storage folder on the dropbox
        status_dir = "/Backend_files/Status/" + backend_name
        storage_provider.delete_folder(status_dir)

        # remove the obsolete config folder
        config_path = "/Backend_files/Config/" + backend_name
        storage_provider.delete_folder(config_path)

        # remove the obsolete stuff in the Queued_Jobs folder
        queued_path = "/Backend_files/Queued_Jobs/" + backend_name
        storage_provider.delete_folder(queued_path)

        # remove the obsolete result from the storage folder on the dropbox
        result_path = "/Backend_files/Result/" + backend_name
        storage_provider.delete_folder(result_path)

    def test_upload_public_key(self) -> None:
        """
        Test that it is possible to upload the public key.
        """
        self.signature_tests(DB_NAME)
