"""
This module contains the test utils for the storage providers. So it is called by the ..._provider tests.
"""

from typing import Any, Tuple, Type

import uuid
from decouple import config
import pytest
from pydantic import ValidationError
from sqooler.schemes import BackendConfigSchemaIn
from sqooler.storage_providers.base import StorageProvider


class StorageProviderTestUtils:
    """
    The test utils for the storage providers.
    """

    def get_login_class(self) -> Any:
        """
        Get the login for the provider.
        """
        raise NotImplementedError

    def get_storage_provider(self) -> Type[StorageProvider]:
        """
        Get the storage provider.
        """
        raise NotImplementedError

    def get_login(self) -> Any:
        """
        Get the login information for the storage provider.
        """
        raise NotImplementedError

    def get_dummy_config(self) -> Tuple[str, BackendConfigSchemaIn]:
        """
        Generate the dummy config of the fermion type.

        Returns:
            The backend name and the backend config input.
        """

        dummy_id = uuid.uuid4().hex[:5]
        backend_name = f"dummy{dummy_id}"

        dummy_dict: dict = {}
        dummy_dict["gates"] = []
        dummy_dict["display_name"] = backend_name
        dummy_dict["num_wires"] = 3
        dummy_dict["version"] = "0.0.1"
        dummy_dict["description"] = "This is a dummy backend."
        dummy_dict["cold_atom_type"] = "fermion"
        dummy_dict["max_experiments"] = 1
        dummy_dict["max_shots"] = 1
        dummy_dict["simulator"] = True
        dummy_dict["supported_instructions"] = []
        dummy_dict["wire_order"] = "interleaved"
        dummy_dict["num_species"] = 1
        dummy_dict["operational"] = True

        backend_info = BackendConfigSchemaIn(**dummy_dict)
        return backend_name, backend_info

    def remove_file_not_found_test(self, db_name: str) -> None:
        """
        Test if the remove file not found error is raised.

        Args:
            db_name: The name of the database.
        """

        # create a storageprovider object
        storage_provider_class = self.get_storage_provider()
        storage_provider = storage_provider_class(self.get_login(), db_name)

        # upload a file and get it back
        test_content = {"experiment_0": "Nothing happened here."}
        storage_path = "test/subcollection"

        job_id = uuid.uuid4().hex[:24]
        storage_provider.upload(test_content, storage_path, job_id)
        test_result = storage_provider.get_file_content(storage_path, job_id)

        assert test_content == test_result

        # make sure that get_file_content raises an error if the file does not exist
        with pytest.raises(FileNotFoundError):
            storage_provider.get_file_content(storage_path, "non_existing")

        # make sure that delete_file raises an error if the file does not exist
        with pytest.raises(FileNotFoundError):
            storage_provider.delete_file(storage_path, "non_existing")

        with pytest.raises(FileNotFoundError):
            job_id_test = uuid.uuid4().hex[:24]
            storage_provider.delete_file(storage_path, job_id_test)

        # clean up our mess
        storage_provider.delete_file(storage_path, job_id)

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

    def job_tests(self, db_name: str) -> Tuple[str, str, str, Any]:
        """
        Test the job upload and download.

        Args:
            db_name: The name of the database.
        """
        # create a storageprovider object
        storage_provider_class = self.get_storage_provider()
        storage_provider = storage_provider_class(self.get_login(), db_name)

        # create a dummy config
        dummy_id = uuid.uuid4().hex[:5]
        dummy_dict: dict = {}
        dummy_dict["gates"] = []
        dummy_dict["supported_instructions"] = []
        dummy_dict["name"] = "Dummy"
        dummy_dict["num_wires"] = 3
        dummy_dict["version"] = "0.0.1"
        dummy_dict["cold_atom_type"] = "fermion"
        dummy_dict["num_species"] = 1
        dummy_dict["wire_order"] = "interleaved"
        dummy_dict["max_shots"] = 5
        dummy_dict["max_experiments"] = 5
        dummy_dict["description"] = "Dummy simulator for testing"
        dummy_dict["operational"] = True
        backend_name = f"dummy{dummy_id}"
        dummy_dict["display_name"] = backend_name
        dummy_dict["simulator"] = True

        config_info = BackendConfigSchemaIn(**dummy_dict)
        storage_provider.upload_config(config_info, display_name=backend_name)

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
        username = config("TEST_USERNAME")

        job_id = storage_provider.upload_job(
            job_dict=job_payload, display_name=backend_name, username=username
        )
        assert len(job_id) > 1

        # now also test that we can upload the status
        status_msg_dict = storage_provider.upload_status(
            display_name=backend_name,
            username=username,
            job_id=job_id,
        )
        assert len(status_msg_dict.job_id) > 1
        # now test what happens with a poor job id
        job_status = storage_provider.get_status(
            display_name=backend_name,
            username=username,
            job_id="jdsfssdfs",
        )
        assert job_status.status == "ERROR"

        # now test that we can get the job status
        job_status = storage_provider.get_status(
            display_name=backend_name,
            username=username,
            job_id=job_id,
        )
        assert job_status.job_id == job_id

        # make sure that last checked is not set
        backend_config = storage_provider.get_config(backend_name)
        assert backend_config.last_queue_check is None

        # now test that we can move through the queue
        next_job = storage_provider.get_next_job_in_queue(backend_name)
        assert next_job.job_id == job_id
        # now also make sure that we updated the time stamp for the queue
        backend_config = storage_provider.get_config(backend_name)
        assert backend_config.last_queue_check

        return backend_name, job_id, username, storage_provider
