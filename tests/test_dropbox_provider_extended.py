"""
The tests for the storage provider
"""

import uuid
from pydantic import ValidationError
from decouple import config

import pytest

from sqooler.storage_providers import DropboxProviderExtended
from sqooler.schemes import DropboxLoginInformation, BackendConfigSchemaIn

DB_NAME = "dropboxtest"


class TestDropboxProviderExtended:
    """
    The class that contains all the tests for the dropbox provider.
    """

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
        dropbox_provider = DropboxProviderExtended(self.get_login(), DB_NAME)
        assert not dropbox_provider is None

        # test that we cannot create a dropbox object a poor login dict structure
        poor_login_dict = {
            "app_key_t": "test",
            "app_secret": "test",
            "refresh_token": "test",
        }
        with pytest.raises(ValidationError):
            DropboxProviderExtended(DropboxLoginInformation(**poor_login_dict), DB_NAME)

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

        # clean up our mess
        storage_provider.delete_file(second_path, job_id)

    def test_configs(self) -> None:
        """
        Test that we are able to obtain a list of backends.
        """

        # create a dropbox object
        storage_provider = DropboxProviderExtended(self.get_login(), DB_NAME)

        # create a dummy config
        dummy_id = uuid.uuid4().hex[:5]
        dummy_dict: dict = {}
        dummy_dict["gates"] = []
        dummy_dict["supported_instructions"] = []
        dummy_dict["name"] = "Dummy"
        dummy_dict["num_wires"] = 3
        dummy_dict["version"] = "0.0.1"
        dummy_dict["simulator"] = True
        dummy_dict["cold_atom_type"] = "fermion"
        dummy_dict["num_species"] = 1
        dummy_dict["wire_order"] = "interleaved"
        dummy_dict["max_shots"] = 5
        dummy_dict["max_experiments"] = 5
        dummy_dict["description"] = "Dummy simulator for testing"
        backend_name = f"dummy{dummy_id}"
        dummy_dict["display_name"] = backend_name
        dummy_path = f"Backend_files/Config/{backend_name}"
        dummy_dict["operational"] = True

        config_info = BackendConfigSchemaIn(**dummy_dict)
        storage_provider.upload_config(config_info, backend_name)

        # can we get the backend in the list ?
        backends = storage_provider.get_backends()
        assert f"dummy{dummy_id}" in backends

        # can we get the config of the backend ?
        backend_info = storage_provider.get_backend_dict(backend_name)
        backend_dict = backend_info.model_dump()
        assert (
            backend_dict["backend_name"]
            == f"dropboxtest_{dummy_dict['display_name']}_simulator"
        )

        storage_provider.delete_file(dummy_path, "config")

    def test_jobs(self) -> None:
        """
        Test that we can handle the necessary functions for the jobs and status.
        """
        # pylint: disable=too-many-locals
        # create a dropbox object
        storage_provider = DropboxProviderExtended(self.get_login(), DB_NAME)

        # create a dummy config
        dummy_id = uuid.uuid4().hex[:5]
        dummy_dict: dict = {}
        dummy_dict["gates"] = []
        dummy_dict["supported_instructions"] = []
        dummy_dict["name"] = "Dummy"
        dummy_dict["num_wires"] = 3
        dummy_dict["version"] = "0.0.1"
        dummy_dict["simulator"] = True
        dummy_dict["cold_atom_type"] = "fermion"
        dummy_dict["num_species"] = 1
        dummy_dict["wire_order"] = "interleaved"
        dummy_dict["max_shots"] = 5
        dummy_dict["max_experiments"] = 5
        dummy_dict["description"] = "Dummy simulator for testing"
        backend_name = f"dummy{dummy_id}"
        dummy_dict["display_name"] = backend_name
        dummy_dict["operational"] = True

        config_info = BackendConfigSchemaIn(**dummy_dict)
        storage_provider.upload_config(config_info, backend_name)

        # let us first test the we can upload a dummy job
        job_payload = {
            "experiment_0": {
                "instructions": [
                    ("load", [7], []),
                    ("load", [2], []),
                    ("measure", [2], []),
                    ("measure", [6], []),
                    ("measure", [7], []),
                ],
                "num_wires": 8,
                "shots": 4,
                "wire_order": "sequential",
            },
        }
        username = "dummy_user"

        job_id = storage_provider.upload_job(
            job_dict=job_payload, display_name=backend_name, username=username
        )
        assert len(job_id) > 1

        # now also test that we can upload the status
        job_response_dict = storage_provider.upload_status(
            display_name=backend_name,
            username=username,
            job_id=job_id,
        )
        assert len(job_response_dict["job_id"]) > 1

        # now test that we can get the job status
        job_status = storage_provider.get_status(
            display_name=backend_name,
            username=username,
            job_id=job_id,
        )
        assert job_status["job_id"] == job_id

        # test that we can get a job result
        # first upload a dummy result
        dummy_result = {"results": "dummy"}
        result_json_dir = "Backend_files/Result/" + backend_name + "/" + username
        result_json_name = "result-" + job_id

        storage_provider.upload(dummy_result, result_json_dir, result_json_name)
        # now get the result
        result = storage_provider.get_result(
            display_name=backend_name,
            username=username,
            job_id=job_id,
        )
        assert result["results"] == dummy_result["results"]

        # remove the obsolete job from the storage folder on the dropbox
        job_dir = "/Backend_files/Queued_Jobs/" + backend_name + "/"
        job_name = "job-" + job_id
        storage_provider.delete_file(job_dir, job_name)

        # remove the obsolete status from the storage folder on the dropbox
        status_dir = "/Backend_files/Status/" + backend_name + "/" + username
        status_name = "status-" + job_id
        storage_provider.delete_file(status_dir, status_name)

        # remove the obsolete result from the storage folder on the dropbox
        storage_provider.delete_file(result_json_dir, result_json_name)
