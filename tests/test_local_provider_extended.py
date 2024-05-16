"""
The tests for the local storage provider
"""

import os
import shutil
from typing import Any

import pytest
from decouple import config
from pytest import LogCaptureFixture

from sqooler.schemes import LocalLoginInformation
from sqooler.storage_providers.local import LocalCore, LocalProviderExtended

from .storage_provider_test_utils import StorageCoreTestUtils, StorageProviderTestUtils

DB_NAME = "localtest"


class TestLocalProviderCore(StorageCoreTestUtils):
    """
    The class that contains all the tests for the extended local provider.
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
        return LocalCore

    @classmethod
    def teardown_class(cls) -> None:
        """
        Remove the `storage` folder.
        """
        shutil.rmtree("storage")

    def get_login(self) -> LocalLoginInformation:
        """
        Pull all the login information from the environment variables.
        """
        return LocalLoginInformation(base_path=config("BASE_PATH"))

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


class TestLocalProviderExtended(StorageProviderTestUtils):
    """
    The class that contains all the tests for the extended local provider.
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
        return LocalProviderExtended

    @classmethod
    def teardown_class(cls) -> None:
        """
        Remove the `storage` folder.
        """
        shutil.rmtree("storage")

    def get_login(self) -> LocalLoginInformation:
        """
        Pull all the login information from the environment variables.
        """
        return LocalLoginInformation(base_path=config("BASE_PATH"))

    def test_localdb_object(self) -> None:
        """
        Test that we can create a MongoDB object.
        """

        self.storage_object_tests(DB_NAME)

    def test_sign_and_verify_result(self) -> None:
        """
        Test that it is possible a result a verify it properly.
        """
        self.sign_and_verify_result_test(DB_NAME)

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
        backend_name, job_id, _, storage_provider = self.job_tests(DB_NAME, sign_it)

        # remove the obsolete job from the storage
        job_dir = f"jobs/finished/{backend_name}"
        storage_provider.delete_file(job_dir, job_id)

        # remove the obsolete collection from the storage
        full_path = os.path.join(storage_provider.base_path, job_dir)
        os.rmdir(full_path)

        # remove the obsolete status from the storage
        status_dir = "status/" + backend_name
        full_path = os.path.join(storage_provider.base_path, status_dir)
        os.rmdir(full_path)

        # remove the obsolete collection from the storage
        result_json_dir = "results/" + backend_name
        full_path = os.path.join(storage_provider.base_path, result_json_dir)
        os.rmdir(full_path)
