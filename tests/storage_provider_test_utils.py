"""
This module contains the test utils for the storage providers. So it is called by the ..._provider tests.
"""

from typing import Any, Tuple, Type

import sys
import uuid

from datetime import datetime, timezone


import dropbox
from dropbox.exceptions import AuthError, ApiError

from decouple import config
import pytest
from pydantic import ValidationError
from sqooler.schemes import BackendConfigSchemaIn, ResultDict
from sqooler.storage_providers.base import StorageProvider

from sqooler.security import create_jwk_pair


def clean_dummies_from_folder(folder_path: str) -> None:
    """
    Clean the folder after the tests. Mostly for the dropbox.
    """
    folder_path = folder_path.strip("/")

    app_key = config("APP_KEY")
    app_secret = config("APP_SECRET")
    refresh_token = config("REFRESH_TOKEN")
    folder_path = "/" + folder_path + "/"
    with dropbox.Dropbox(
        app_key=app_key,
        app_secret=app_secret,
        oauth2_refresh_token=refresh_token,
    ) as dbx:
        # Check that the access token is valid
        try:
            dbx.users_get_current_account()
        except AuthError:
            sys.exit("ERROR: Invalid access token.")

        folders_results = dbx.files_list_folder(path=folder_path)
        entries = folders_results.entries
        for entry in entries:
            if "dummy" in entry.name:
                print("Deleting folder: " + entry.name)
                full_path = folder_path + entry.name

                print("Deleting folder: " + full_path)
                try:
                    dbx.files_delete_v2(path=full_path)
                except ApiError:
                    print(f"Failed to delete {full_path}. Most likely already deleted.")


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

    def get_dummy_config(self, sign: bool = True) -> Tuple[str, BackendConfigSchemaIn]:
        """
        Generate the dummy config of the fermion type.

        Args:
            sign: Whether to sign the files.
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
        dummy_dict["sign"] = sign

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

    def config_tests(self, db_name: str, sign: bool = True) -> None:
        """
        Test that we can create a config and update it.

        Args:
            db_name: The name of the database.
            sign: should I run the tests with signing?
        """

        # create a storageprovider object
        storage_provider_class = self.get_storage_provider()
        try:
            storage_provider = storage_provider_class(self.get_login(), db_name)
        except TypeError:
            storage_provider = storage_provider_class(self.get_login())

        backend_name, config_info = self.get_dummy_config(sign)
        private_jwk, _ = create_jwk_pair(backend_name)

        # does it fail if we try to upload the config without a private key?
        if sign:
            with pytest.raises(ValueError):
                storage_provider.upload_config(config_info, display_name=backend_name)

        storage_provider.upload_config(
            config_info, display_name=backend_name, private_jwk=private_jwk
        )

        # now test that we can cannot upload the config again
        with pytest.raises(FileExistsError):
            storage_provider.upload_config(
                config_info, display_name=backend_name, private_jwk=private_jwk
            )

        # now test that we can also get the config
        obtained_config = storage_provider.get_config(backend_name)
        assert obtained_config.display_name == backend_name

        with pytest.raises(FileNotFoundError):
            obtained_config = storage_provider.get_config("random")

        config_info.cold_atom_type = "boson"
        # now also the datetime
        config_info.last_queue_check = datetime.now(timezone.utc).replace(microsecond=0)

        storage_provider.update_config(
            config_info, display_name=backend_name, private_jwk=private_jwk
        )

        # and again
        config_info.last_queue_check = datetime.now(timezone.utc).replace(microsecond=0)

        storage_provider.update_config(
            config_info, display_name=backend_name, private_jwk=private_jwk
        )
        if sign:
            # test that we cannot update the config with a wrong private key
            wrong_private_jwk, _ = create_jwk_pair(backend_name)
            with pytest.raises(ValueError):
                storage_provider.update_config(
                    config_info,
                    display_name=backend_name,
                    private_jwk=wrong_private_jwk,
                )
        with pytest.raises(FileNotFoundError):
            storage_provider.update_config(config_info, display_name="randonname")

    def signature_tests(self, db_name: str) -> None:
        """
        Test that we can create a signature.
        """
        # create a storageprovider object
        storage_provider_class = self.get_storage_provider()
        try:
            storage_provider = storage_provider_class(self.get_login(), db_name)
        except TypeError:
            storage_provider = storage_provider_class(self.get_login())
        dummy_id = uuid.uuid4().hex[:5]
        backend_name = f"dummy{dummy_id}"

        # create a dummy key
        private_jwk, public_jwk = create_jwk_pair(backend_name)
        storage_provider.upload_public_key(public_jwk, display_name=backend_name)

        with pytest.raises(ValueError):
            storage_provider.upload_public_key(private_jwk, display_name=backend_name)

        # now test that we can also get the public key
        obtained_public_jwk = storage_provider.get_public_key(backend_name)
        assert obtained_public_jwk.x == public_jwk.x

        with pytest.raises(FileNotFoundError):
            obtained_public_jwk = storage_provider.get_public_key("random")

    def job_tests(self, db_name: str, sign: bool = True) -> Tuple[str, str, str, Any]:
        """
        Test the job upload and download.

        Args:
            db_name: The name of the database.
            sign: Should I run the tests with signing?

        Returns:
            The backend name, the job id, the username and the storage provider.
        """
        # create a storageprovider object
        storage_provider_class = self.get_storage_provider()
        try:
            storage_provider = storage_provider_class(self.get_login(), db_name)
        except TypeError:
            storage_provider = storage_provider_class(self.get_login())

        backend_name, config_info = self.get_dummy_config(sign=sign)

        # create a dummy key
        private_jwk, public_jwk = create_jwk_pair(backend_name)

        storage_provider.upload_config(
            config_info, display_name=backend_name, private_jwk=private_jwk
        )

        storage_provider.upload_public_key(public_jwk, display_name=backend_name)

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

        # make sure that last checked is not set
        backend_config = storage_provider.get_config(backend_name)
        assert backend_config.last_queue_check is None

        # test that we can also run with an empty job queue
        next_job = storage_provider.get_next_job_in_queue(backend_name, private_jwk)
        assert next_job.job_id == "None"

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

        # now test that we can move through the queue
        next_job = storage_provider.get_next_job_in_queue(backend_name, private_jwk)
        assert next_job.job_id == job_id
        # now also make sure that we updated the time stamp for the queue
        backend_config = storage_provider.get_config(backend_name)
        assert backend_config.last_queue_check

        # we now also need to test the update_in_database part of the storage provider
        result_dict = ResultDict(
            display_name=backend_name,
            backend_version="0.0.1",
            job_id=next_job.job_id,
            status="INITIALIZING",
        )

        job_status.status = "DONE"
        # this should fail as the signing key is missing
        with pytest.raises(ValueError):
            storage_provider.update_in_database(
                result_dict, job_status, next_job.job_id, backend_name
            )

        storage_provider.update_in_database(
            result_dict,
            job_status,
            next_job.job_id,
            backend_name,
            private_jwk=private_jwk,
        )

        # we now need to check if the job is in the finished jobs folder
        obtained_result = storage_provider.get_result(
            display_name=backend_name,
            username=username,
            job_id=next_job.job_id,
        )

        assert obtained_result.backend_version == "0.0.1"
        return backend_name, job_id, username, storage_provider
