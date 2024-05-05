"""
The tests for the local storage provider
"""

import os
import shutil
import uuid
from typing import Any

import pytest
from decouple import config
from pytest import LogCaptureFixture

from sqooler.schemes import BackendConfigSchemaIn, LocalLoginInformation
from sqooler.storage_providers.local import LocalProviderExtended

from .storage_provider_test_utils import StorageProviderTestUtils

DB_NAME = "localtest"


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

    def test_not_active(self) -> None:
        """
        Test that we cannot work with the provider if it is not active.
        """
        # create a storageprovider object
        storage_provider = LocalProviderExtended(
            self.get_login(), DB_NAME, is_active=False
        )

        # make sure that we cannot upload if it is not active
        test_content = {"experiment_0": "Nothing happened here."}
        storage_path = "test/subcollection"

        job_id = uuid.uuid4().hex[:24]
        second_path = "test/subcollection_2"
        with pytest.raises(ValueError):
            storage_provider.upload(test_content, storage_path, job_id)
        with pytest.raises(ValueError):
            storage_provider.get_file_content(storage_path, job_id)
        with pytest.raises(ValueError):
            storage_provider.move_file(storage_path, second_path, job_id)
        with pytest.raises(ValueError):
            storage_provider.delete_file(second_path, job_id)

    def test_upload_etc(self) -> None:
        """
        Test that it is possible to upload a file.
        """
        # create a storageprovider object
        storage_provider = LocalProviderExtended(self.get_login(), DB_NAME)

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

        # move it and get it back
        second_path = "test/subcollection_2"
        storage_provider.move_file(storage_path, second_path, job_id)
        test_result = storage_provider.get_file_content(second_path, job_id)

        assert test_content == test_result

        # clean up our mess
        storage_provider.delete_file(second_path, job_id)

    def test_file_remove(self) -> None:
        """
        Test that it is possible to remove a file and we raise the right errors.
        """
        self.remove_file_not_found_test(DB_NAME)

    def test_sign_and_verify_result(self) -> None:
        """
        Test that it is possible a result a verify it properly.
        """
        self.sign_and_verify_result_test(DB_NAME)

    def test_configs(self) -> None:
        """
        Test that we are able to obtain a list of backends.
        """
        # create a storageprovider object
        storage_provider = LocalProviderExtended(self.get_login(), DB_NAME)

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
        dummy_dict["operational"] = True
        backend_name = f"dummy{dummy_id}"
        dummy_dict["display_name"] = backend_name

        config_path = "backends/configs"

        backend_info = BackendConfigSchemaIn(**dummy_dict)
        storage_provider.upload_config(backend_info, backend_name)

        # can we get the backend in the list ?
        backends = storage_provider.get_backends()
        assert f"dummy{dummy_id}" in backends

        # can we get the config of the backend ?
        backend_info = storage_provider.get_backend_dict(backend_name)
        backend_dict = backend_info.model_dump()
        assert (
            backend_dict["backend_name"]
            == f"localtest_{dummy_dict['display_name']}_simulator"
        )
        # make sure that we raise an error if we try to get a backend that does not exist
        with pytest.raises(FileNotFoundError):
            storage_provider.get_backend_dict("dummy_non_existing")
        storage_provider.delete_file(config_path, backend_name)

    @pytest.mark.parametrize("sign_it", [True, False])
    def test_upload_and_update_config(self, sign_it: bool) -> None:
        """
        Test that we can upload and update a config.
        """
        self.config_tests(DB_NAME, sign=sign_it)

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

    def test_update_raise_error(self) -> None:
        """
        Test that it is update a file once it was uploaded.
        """

        # create a dropbox object
        storage_provider = LocalProviderExtended(self.get_login(), DB_NAME)

        # file properties
        test_content = {"experiment_0": "Nothing happened here."}
        storage_path = "test/test_folder"
        mongo_id = uuid.uuid4().hex[:24]

        # make sure that we cannot update a file if it does not exist

        with pytest.raises(FileNotFoundError):
            storage_provider.update_file(test_content, storage_path, mongo_id)

        # upload a file and get it back
        storage_provider.upload(test_content, storage_path, mongo_id)
        test_result = storage_provider.get_file_content(storage_path, mongo_id)

        assert test_content == test_result

        # update it and get it back
        test_content = {"experiment_1": "Nothing happened here."}
        storage_provider.update_file(test_content, storage_path, mongo_id)
        test_result = storage_provider.get_file_content(storage_path, mongo_id)
        assert test_content == test_result

        # clean up our mess
        storage_provider.delete_file(storage_path, mongo_id)

    def test_jobs(self) -> None:
        """
        Test that we can handle the necessary functions for the jobs and status.
        """
        backend_name, job_id, username, storage_provider = self.job_tests(DB_NAME)
        # test that we can get a job result
        # first upload a dummy result
        dummy_result: dict = {
            "backend_name": backend_name,
            "display_name": backend_name,
            "backend_version": "0.0.1",
            "job_id": job_id,
            "qobj_id": None,
            "success": True,
            "status": "INITIALIZING",
            "header": {},
            "results": [],
        }

        result_json_dir = "results/" + backend_name
        storage_provider.upload(dummy_result, result_json_dir, job_id)
        # what happens if we try to get a result that does not exist ?
        result_info = storage_provider.get_result(
            display_name=backend_name,
            username=username,
            job_id="dglfjhous",
        )
        assert result_info.status == "ERROR"

        # now get the result
        result_info = storage_provider.get_result(
            display_name=backend_name,
            username=username,
            job_id=job_id,
        )
        result = result_info.model_dump()
        assert not "_id" in result.keys()
        assert dummy_result["results"] == result["results"]

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

        # remove the obsolete result from the storage
        storage_provider.delete_file(result_json_dir, job_id)
        # remove the obsolete collection from the storage
        full_path = os.path.join(storage_provider.base_path, result_json_dir)
        os.rmdir(full_path)

    def test_get_unsigned_results(self) -> None:
        """
        Test that we can get the results of a job.
        """
        backend_name, job_id, username, storage_provider = self.job_tests(DB_NAME)

        # test that we can get a job result
        # first upload a dummy result
        dummy_result: dict = {
            "backend_name": backend_name,
            "display_name": backend_name,
            "backend_version": "0.0.1",
            "job_id": job_id,
            "qobj_id": None,
            "success": True,
            "status": "INITIALIZING",
            "header": {},
            "results": [],
        }

        result_json_dir = "results/" + backend_name
        storage_provider.upload(dummy_result, result_json_dir, job_id)

        # now get the result
        result_info = storage_provider.get_result(
            display_name=backend_name,
            username=username,
            job_id=job_id,
        )
        result = result_info.model_dump()
        assert not "_id" in result.keys()
        assert dummy_result["results"] == result["results"]

        # remove the obsolete result from the storage
        storage_provider.delete_file(result_json_dir, job_id)
        # remove the obsolete collection from the storage
        full_path = os.path.join(storage_provider.base_path, result_json_dir)
        os.rmdir(full_path)
