"""
The tests for the storage provider
"""

import datetime
import uuid
from datetime import timezone
from typing import Any

# get the environment variables
from decouple import config

from sqooler.schemes import DropboxLoginInformation, ResultDict
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

    def test_upload_etc(self) -> None:
        """
        Test that it is possible to upload a file.
        """
        storage_provider = DropboxProvider(self.get_login())
        # upload a file and get it back
        job_id = uuid.uuid4().hex
        test_content = {"experiment_0": "Nothing happened here."}
        storage_path = "test_folder"
        file_id = f"job-{job_id}"
        storage_provider.upload(test_content, storage_path, file_id)
        test_result = storage_provider.get_file_content(storage_path, file_id)

        assert test_content, test_result

        # move it and get it back
        second_path = "test_folder_2"
        storage_provider.move_file(storage_path, second_path, file_id)
        test_result = storage_provider.get_file_content(second_path, file_id)
        assert test_content == test_result

        # test that we can also get the job from the database
        test_result = storage_provider.get_job_content(second_path, job_id)
        assert test_content["experiment_0"] == test_result["experiment_0"]

        # clean up our mess
        storage_provider.delete_file(second_path, file_id)
