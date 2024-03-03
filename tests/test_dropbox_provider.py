"""
The tests for the storage provider
"""

import datetime
import uuid
from typing import Any
from datetime import timezone


# get the environment variables
from decouple import config
from sqooler.storage_providers.dropbox import DropboxProvider
from sqooler.schemes import ResultDict, DropboxLoginInformation

from .storage_provider_test_utils import StorageProviderTestUtils


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

    def test_upload_configs(self) -> None:
        """
        We would like to make sure that we can properly upload the configuration files
        that come from the spoolers.
        """
        storage_provider = DropboxProvider(self.get_login())

        backend_name, config_info = self.get_dummy_config()
        storage_provider.upload_config(config_info, backend_name)

        # can we get the backend in the list ?
        dummy_path = f"Backend_files/Config/{backend_name}"
        backend_dict = storage_provider.get_file_content(dummy_path, "config")
        assert backend_dict["display_name"] == config_info.display_name

        storage_provider.delete_file(dummy_path, "config")
        # delete also the old folder
        storage_provider.delete_folder(dummy_path)

    def test_get_next_job_in_queue(self) -> None:
        """
        Is it possible to work through the queue of jobs?
        """
        storage_provider = DropboxProvider(self.get_login())

        # create a dummy backend
        backend_name, backend_info = self.get_dummy_config()
        storage_provider.upload_config(backend_info, backend_name)

        username = "test_user"
        job_id = (
            (datetime.datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S"))
            + "-"
            + backend_name
            + "-"
            + username
            + "-"
            + (uuid.uuid4().hex)[:5]
        )

        # first we have to upload a dummy job
        job_dict = {"job_id": job_id, "job_json_path": "None"}
        job_name = "job-" + job_id
        queue_path = f"Backend_files/Queued_Jobs/{backend_name}"
        job_dict["job_json_path"] = queue_path

        storage_provider.upload(job_dict, queue_path, job_id=job_name)

        # test if the file_queue is working

        _ = storage_provider.get_file_queue(queue_path)

        # the last step is to get the next job and see if this nicely worked out
        next_job = storage_provider.get_next_job_in_queue(backend_name)

        assert next_job.job_id == job_id

        # we now also need to test the update_in_database part of the storage provider
        result_dict = ResultDict(
            display_name=backend_name,
            backend_version="0.0.1",
            job_id=next_job.job_id,
            status="INITIALIZING",
        )

        # upload the status dict without other status.
        status_msg_dict = storage_provider.upload_status(
            backend_name,
            "test_user",
            job_id,
        )
        # time to update everything
        status_msg_dict.status = "DONE"
        storage_provider.update_in_database(
            result_dict, status_msg_dict, next_job.job_id, backend_name
        )

        # we now need to check if the job is in the finished jobs folder
        job_finished_json_dir = (
            "/Backend_files/Finished_Jobs/" + backend_name + "/" + username + "/"
        )

        finshed_job = storage_provider.get_file_content(job_finished_json_dir, job_name)
        assert finshed_job["job_id"] == job_id

        # we check if the status was updated
        status_json_dir = "/Backend_files/Status/" + backend_name + "/" + username + "/"
        status_json_name = "status-" + job_id
        status_dict = storage_provider.get_file_content(
            status_json_dir, status_json_name
        )
        assert status_dict["status"] == "DONE"

        # clean up the mess
        storage_provider.delete_file(job_finished_json_dir, job_name)
        storage_provider.delete_file(status_json_dir, status_json_name)

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

        # remove the obsolete job from the storage folder on the dropbox
        finished_dir = "/Backend_files/Finished_Jobs/" + backend_name
        storage_provider.delete_folder(finished_dir)
