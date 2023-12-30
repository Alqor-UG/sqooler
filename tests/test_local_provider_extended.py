"""
The tests for the local storage provider
"""
import uuid
import os
import shutil

from decouple import config
from pydantic import ValidationError

import pytest

from sqooler.storage_providers import LocalProviderExtended
from sqooler.schemes import ResultDict, LocalLoginInformation

db_name = "test"


class TestLocalProviderExtended:
    """
    The class that contains all the tests for the dropbox provider.
    """

    def setUp(self) -> None:
        """
        set up the test.
        """
        # load the credentials from the environment through decouple

        # put together the login information
        base_path = "storage"

        login_dict = {
            "base_path": base_path,
        }

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
        mongodb_provider = LocalProviderExtended(self.get_login(), db_name)
        assert not mongodb_provider is None

        # test that we cannot create a dropbox object a poor login dict structure
        poor_login_dict = {
            "app_key_t": "test",
            "app_secret": "test",
            "refresh_token": "test",
        }
        with pytest.raises(ValidationError):
            LocalProviderExtended(LocalLoginInformation(**poor_login_dict), db_name)

    def test_not_active(self) -> None:
        """
        Test that we cannot work with the provider if it is not active.
        """
        entry = StorageProviderDb.objects.get(name="localtest")
        entry.is_active = False
        storage_provider = LocalProviderExtended(
            entry.login, entry.name, entry.is_active
        )

        # make sure that we cannot upload if it is not active
        test_content = {"experiment_0": "Nothing happened here."}
        storage_path = "test/subcollection"

        job_id = uuid.uuid4().hex[:24]
        second_path = "test/subcollection_2"
        with self.assertRaises(ValueError):
            storage_provider.upload(test_content, storage_path, job_id)
        with self.assertRaises(ValueError):
            storage_provider.get_file_content(storage_path, job_id)
        with self.assertRaises(ValueError):
            storage_provider.move_file(storage_path, second_path, job_id)
        with self.assertRaises(ValueError):
            storage_provider.delete_file(second_path, job_id)

    def test_upload_etc(self) -> None:
        """
        Test that it is possible to upload a file.
        """

        # create a mongodb object
        mongodb_entry = StorageProviderDb.objects.get(name="localtest")
        storage_provider = LocalProviderExtended(
            mongodb_entry.login, mongodb_entry.name
        )

        # upload a file and get it back
        test_content = {"experiment_0": "Nothing happened here."}
        storage_path = "test/subcollection"

        job_id = uuid.uuid4().hex[:24]
        storage_provider.upload(test_content, storage_path, job_id)
        test_result = storage_provider.get_file_content(storage_path, job_id)

        self.assertDictEqual(test_content, test_result)

        # move it and get it back
        second_path = "test/subcollection_2"
        storage_provider.move_file(storage_path, second_path, job_id)
        test_result = storage_provider.get_file_content(second_path, job_id)
        self.assertDictEqual(test_content, test_result)

        # clean up our mess
        storage_provider.delete_file(second_path, job_id)

    def test_configs(self) -> None:
        """
        Test that we are able to obtain a list of backends.
        """
        # create a mongodb object
        mongodb_entry = StorageProviderDb.objects.get(name="localtest")
        storage_provider = LocalProviderExtended(
            mongodb_entry.login, mongodb_entry.name
        )

        # create a dummy config
        dummy_id = uuid.uuid4().hex[:5]
        dummy_dict: dict = {}
        dummy_dict["gates"] = []
        dummy_dict["name"] = "Dummy"
        dummy_dict["num_wires"] = 3
        dummy_dict["version"] = "0.0.1"

        backend_name = f"dummy{dummy_id}"
        dummy_dict["display_name"] = backend_name
        dummy_dict["simulator"] = True

        config_path = "backends/configs"
        storage_provider.upload(dummy_dict, config_path, job_id=backend_name)

        # can we get the backend in the list ?
        backends = storage_provider.get_backends()
        self.assertTrue(f"dummy{dummy_id}" in backends)

        # can we get the config of the backend ?
        backend_dict = storage_provider.get_backend_dict(backend_name)
        self.assertEqual(
            backend_dict["backend_name"],
            f"localtest_{dummy_dict['display_name']}_simulator",
        )
        storage_provider.delete_file(config_path, backend_name)

    def test_status(self) -> None:
        """
        Test that we are able to obtain the status of the backend.
        """
        # create a mongodb object
        mongodb_entry = StorageProviderDb.objects.get(name="localtest")
        storage_provider = LocalProviderExtended(
            mongodb_entry.login, mongodb_entry.name
        )

        # create a dummy config
        dummy_id = uuid.uuid4().hex[:5]
        dummy_dict: dict = {}
        dummy_dict["gates"] = []
        dummy_dict["name"] = "Dummy"
        dummy_dict["num_wires"] = 3
        dummy_dict["version"] = "0.0.1"

        # create the necessary status entries
        dummy_dict["operational"] = True
        dummy_dict["pending_jobs"] = 7
        dummy_dict["status_msg"] = "All good"

        backend_name = f"dummy{dummy_id}"
        dummy_dict["display_name"] = backend_name
        dummy_dict["simulator"] = True

        config_path = "backends/configs"
        storage_provider.upload(dummy_dict, config_path, job_id=backend_name)

        # can we get the backend in the list ?
        backends = storage_provider.get_backends()
        self.assertTrue(f"dummy{dummy_id}" in backends)

        # can we get the status of the backend ?
        status_schema = storage_provider.get_backend_status(backend_name)
        status_dict = status_schema.dict()
        self.assertEqual(
            status_dict["backend_name"],
            f"localtest_{dummy_dict['display_name']}_simulator",
        )

        self.assertEqual(status_dict["operational"], dummy_dict["operational"])
        self.assertEqual(status_dict["backend_version"], dummy_dict["version"])
        self.assertEqual(status_dict["pending_jobs"], dummy_dict["pending_jobs"])
        self.assertEqual(status_dict["status_msg"], dummy_dict["status_msg"])

        storage_provider.delete_file(config_path, backend_name)

    def test_status_bare(self) -> None:
        """
        Test status if the backend is not well updated yet.
        """
        # create a mongodb object
        mongodb_entry = StorageProviderDb.objects.get(name="localtest")
        storage_provider = LocalProviderExtended(
            mongodb_entry.login, mongodb_entry.name
        )

        # create a dummy config
        dummy_id = uuid.uuid4().hex[:5]
        dummy_dict: dict = {}
        dummy_dict["gates"] = []
        dummy_dict["name"] = "Dummy"
        dummy_dict["num_wires"] = 3
        dummy_dict["version"] = "0.0.1"

        backend_name = f"dummy{dummy_id}"
        dummy_dict["display_name"] = backend_name
        dummy_dict["simulator"] = True

        config_path = "backends/configs"
        storage_provider.upload(dummy_dict, config_path, job_id=backend_name)

        # can we get the backend in the list ?
        backends = storage_provider.get_backends()
        self.assertTrue(f"dummy{dummy_id}" in backends)

        # can we get the status of the backend ?
        status_schema = storage_provider.get_backend_status(backend_name)
        status_dict = status_schema.dict()
        self.assertEqual(
            status_dict["backend_name"],
            f"localtest_{dummy_dict['display_name']}_simulator",
        )
        self.assertEqual(status_dict["operational"], True)
        self.assertEqual(status_dict["backend_version"], dummy_dict["version"])
        self.assertEqual(status_dict["pending_jobs"], 0)
        self.assertEqual(status_dict["status_msg"], "")

        storage_provider.delete_file(config_path, backend_name)

        # and make sure that we raise an error if the backend is not there
        with self.assertRaises(FileNotFoundError):
            status_schema = storage_provider.get_backend_status(backend_name)

    def test_jobs(self) -> None:
        """
        Test that we can handle the necessary functions for the jobs and status.
        """
        # disable too many local variables
        # pylint: disable=R0914

        # create a mongodb object
        mongodb_entry = StorageProviderDb.objects.get(name="localtest")
        storage_provider = LocalProviderExtended(
            mongodb_entry.login, mongodb_entry.name
        )

        # create a dummy config
        dummy_id = uuid.uuid4().hex[:5]
        dummy_dict: dict = {}
        dummy_dict["gates"] = []
        dummy_dict["name"] = "Dummy"
        dummy_dict["num_wires"] = 3
        dummy_dict["version"] = "0.0.1"

        backend_name = f"dummy{dummy_id}"
        dummy_dict["display_name"] = backend_name
        dummy_dict["simulator"] = True

        config_path = "backends/configs"
        storage_provider.upload(dummy_dict, config_path, job_id=backend_name)

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
        self.assertTrue(len(job_id) > 1)

        # now also test that we can upload the status
        job_response_dict = storage_provider.upload_status(
            display_name=backend_name,
            username=username,
            job_id=job_id,
        )
        self.assertTrue(len(job_response_dict["job_id"]) > 1)
        # now test that we can get the job status
        job_status = storage_provider.get_status(
            display_name=backend_name,
            username=username,
            job_id=job_id,
        )
        self.assertFalse("_id" in job_status.keys())
        self.assertEqual(job_status["job_id"], job_id)

        # test that we can get a job result
        # first upload a dummy result
        dummy_result = {"results": "dummy"}
        result_json_dir = "results/" + backend_name
        storage_provider.upload(dummy_result, result_json_dir, job_id)

        # now get the result
        result = storage_provider.get_result(
            display_name=backend_name,
            username=username,
            job_id=job_id,
        )
        self.assertFalse("_id" in result.keys())
        self.assertEqual(dummy_result["results"], result["results"])

        # remove the obsolete job from the storage
        job_dir = "jobs/queued/" + backend_name
        storage_provider.delete_file(job_dir, job_id)

        # remove the obsolete collection from the storage
        full_path = os.path.join(storage_provider.base_path, job_dir)
        os.rmdir(full_path)

        # remove the obsolete status from the storage
        status_dir = "status/" + backend_name
        storage_provider.delete_file(status_dir, job_id)

        # remove the obsolete collection from the storage
        full_path = os.path.join(storage_provider.base_path, status_dir)
        os.rmdir(full_path)

        # remove the obsolete result from the storage
        storage_provider.delete_file(result_json_dir, job_id)
        # remove the obsolete collection from the storage
        full_path = os.path.join(storage_provider.base_path, result_json_dir)
        os.rmdir(full_path)

    def test_backend_name(self) -> None:
        """
        Test that we separate out properly the backend names
        """
        short_test_name = "tests"
        short_name = get_short_backend_name(short_test_name)

        self.assertEqual(short_test_name, short_name)

        test_name = "alqor_tests_simulator"
        short_name = get_short_backend_name(test_name)
        self.assertEqual(short_test_name, short_name)

        test_name = "alqor_tests_simulator_crap"
        short_name = get_short_backend_name(test_name)
        self.assertEqual("", short_name)
