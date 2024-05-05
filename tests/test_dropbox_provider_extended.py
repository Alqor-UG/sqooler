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

    def test_upload_etc(self) -> None:
        """
        Test that it is possible to upload a file.
        """

        # create a dropbox object
        storage_provider = DropboxProviderExtended(self.get_login(), DB_NAME)

        # upload a file and get it back
        file_id = uuid.uuid4().hex
        test_content = {"experiment_0": "Nothing happened here."}
        storage_path = "test_folder"
        job_id = f"world-{file_id}"
        storage_provider.upload(test_content, storage_path, job_id)

        # make sure that this did not add the _id field to the dict
        assert "_id" not in test_content

        test_result = storage_provider.get_file_content(storage_path, job_id)

        assert test_content == test_result

        # move it and get it back
        second_path = "test_folder_2"
        storage_provider.move_file(storage_path, second_path, job_id)
        test_result = storage_provider.get_file_content(second_path, job_id)
        assert test_content == test_result

        # make sure that get_file_content raises an error if the file does not exist
        with pytest.raises(FileNotFoundError):
            storage_provider.get_file_content(storage_path, "non_existing")

        # clean up our mess
        storage_provider.delete_file(second_path, job_id)

    def test_update_raise_error(self) -> None:
        """
        Test that it is update a file once it was uploaded.
        """

        # create a dropbox object
        storage_provider = DropboxProviderExtended(self.get_login(), DB_NAME)

        # file properties
        file_id = uuid.uuid4().hex
        test_content = {"experiment_0": "Nothing happened here."}
        storage_path = "test_folder"
        job_id = f"world-{file_id}"

        # make sure that we cannot update a file if it does not exist

        with pytest.raises(FileNotFoundError):
            storage_provider.update_file(test_content, storage_path, job_id)

        # upload a file and get it back
        storage_provider.upload(test_content, storage_path, job_id)
        test_result = storage_provider.get_file_content(storage_path, job_id)

        assert test_content == test_result

        # update it and get it back
        test_content = {"experiment_1": "Nothing happened here."}
        storage_provider.update_file(test_content, storage_path, job_id)
        test_result = storage_provider.get_file_content(storage_path, job_id)
        assert test_content == test_result

        # clean up our mess
        storage_provider.delete_file(storage_path, job_id)

    def test_upload_and_update_config(self) -> None:
        """
        Test that we can upload and update a config.
        """
        self.config_tests(DB_NAME)
        self.config_tests(DB_NAME, sign=False)

    def test_configs(self) -> None:
        """
        Test that we are able to obtain a list of backends.
        """

        # create a dropbox object
        storage_provider = DropboxProviderExtended(self.get_login(), DB_NAME)

        backend_name, config_info = self.get_dummy_config(sign=False)
        storage_provider.upload_config(config_info, backend_name)
        dummy_path = f"Backend_files/Config/{backend_name}"

        # can we get the backend in the list ?
        backends = storage_provider.get_backends()
        assert backend_name in backends

        # can we get the config of the backend ?
        backend_info = storage_provider.get_backend_dict(backend_name)
        backend_dict = backend_info.model_dump()
        assert (
            backend_dict["backend_name"]
            == f"dropboxtest_{config_info.display_name}_simulator"
        )

        # delete the old config file
        storage_provider.delete_file(dummy_path, "config")

        # delete also the old folder
        storage_provider.delete_folder(dummy_path)

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
        backend_name, _, username, storage_provider = self.job_tests(
            DB_NAME, sign=sign_it
        )

        # what happens if we try to get a result that does not exist ?
        result_info = storage_provider.get_result(
            display_name=backend_name,
            username=username,
            job_id="dglfjhous",
        )
        assert result_info.status == "ERROR"

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
