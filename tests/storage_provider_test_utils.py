"""
This module contains the test utils for the storage providers. So it is called by the ..._provider tests.
"""

import sys
import uuid
from datetime import datetime, timezone
from typing import Any, Tuple, Type

import dropbox
import pytest
from decouple import config
from dropbox.exceptions import ApiError, AuthError
from icecream import ic
from pydantic import ValidationError
from pytest import LogCaptureFixture

from sqooler.schemes import ResultDict, get_init_results, get_init_status
from sqooler.security import create_jwk_pair
from sqooler.storage_providers.base import StorageCore, StorageProvider
from sqooler.utils import get_dummy_config


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


class StorageCoreTestUtils:
    """
    The test utils for the storage cores.
    """

    def get_login_class(self) -> Any:
        """
        Get the login for the provider.
        """
        raise NotImplementedError

    def get_storage_provider(self) -> Type[StorageCore]:
        """
        Get the storage provider.
        """
        raise NotImplementedError

    def get_login(self) -> Any:
        """
        Get the login information for the storage provider.
        """
        raise NotImplementedError

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
        test_result = storage_provider.get(storage_path, job_id)

        assert test_content == test_result

        # make sure that get_file_content raises an error if the file does not exist
        with pytest.raises(FileNotFoundError):
            storage_provider.get(storage_path, "non_existing")

        # make sure that delete_file raises an error if the file does not exist
        with pytest.raises(FileNotFoundError):
            storage_provider.delete(storage_path, "non_existing")

        with pytest.raises(FileNotFoundError):
            job_id_test = uuid.uuid4().hex[:24]
            storage_provider.delete(storage_path, job_id_test)

        # clean up our mess
        storage_provider.delete(storage_path, job_id)

    def active_tests(self, db_name: str) -> None:
        """
        Test that we cannot work with the provider if it is not active.
        """
        # create a storageprovider object
        storage_provider_class = self.get_storage_provider()
        print(f"Testing not active for {db_name}")
        print(self.get_login())
        try:
            storage_provider = storage_provider_class(self.get_login(), db_name)
        except TypeError:
            storage_provider = storage_provider_class(self.get_login())

        # set the storage_provider to inactive
        storage_provider.is_active = False

        # make sure that we cannot upload if it is not active
        test_content = {"experiment_0": "Nothing happened here."}
        storage_path = "test/subcollection"

        job_id = uuid.uuid4().hex[:24]
        second_path = "test/subcollection_2"
        with pytest.raises(ValueError):
            storage_provider.upload(test_content, storage_path, job_id)
        with pytest.raises(ValueError):
            storage_provider.get(storage_path, job_id)
        with pytest.raises(ValueError):
            storage_provider.move(storage_path, second_path, job_id)
        with pytest.raises(ValueError):
            storage_provider.delete(second_path, job_id)

    def upload_tests(self, db_name: str) -> None:
        """
        Test that we can upload a file.
        """

        # create a storageprovider object
        storage_provider_class = self.get_storage_provider()
        try:
            storage_provider = storage_provider_class(self.get_login(), db_name)
        except TypeError:
            storage_provider = storage_provider_class(self.get_login())

        # upload a file and get it back
        test_content = {"experiment_0": "Nothing happened here."}
        storage_path = "test/subcollection"

        job_id = uuid.uuid4().hex[:24]
        storage_provider.upload(test_content, storage_path, job_id)
        test_result = storage_provider.get(storage_path, job_id)

        assert test_content == test_result

        # make sure that get_file_content raises an error if the file does not exist
        with pytest.raises(FileNotFoundError):
            storage_provider.get(storage_path, "non_existing")

        # move it and get it back
        second_path = "test/subcollection_2"
        storage_provider.move(storage_path, second_path, job_id)
        test_result = storage_provider.get(second_path, job_id)

        assert test_content == test_result

        # make sure that we get a warning if we are trying to upload a file that already exists
        with pytest.raises(FileExistsError):
            storage_provider.upload(test_content, second_path, job_id)

        # test that we can update the file properly
        new_content = {"experiment_0": "What happened here."}
        storage_provider.update(new_content, second_path, job_id)
        test_result = storage_provider.get(second_path, job_id)
        assert new_content["experiment_0"] == test_result["experiment_0"]

        # clean up our mess
        storage_provider.delete(second_path, job_id)

    def update_raise_error_test(self, db_name: str) -> None:
        """
        Test that it is update a file once it was uploaded.
        """

        storage_provider_class = self.get_storage_provider()
        try:
            storage_provider = storage_provider_class(self.get_login(), db_name)
        except TypeError:
            storage_provider = storage_provider_class(self.get_login())

        # file properties
        test_content = {"experiment_0": "Nothing happened here."}
        storage_path = "test/test_folder"
        mongo_id = uuid.uuid4().hex[:24]

        # make sure that we cannot update a file if it does not exist

        with pytest.raises(FileNotFoundError):
            storage_provider.update(test_content, storage_path, mongo_id)

        # upload a file and get it back
        storage_provider.upload(test_content, storage_path, mongo_id)
        test_result = storage_provider.get(storage_path, mongo_id)

        assert test_content == test_result

        # update it and get it back
        test_content = {"experiment_1": "Nothing happened here."}
        storage_provider.update(test_content, storage_path, mongo_id)
        test_result = storage_provider.get(storage_path, mongo_id)
        assert test_content == test_result

        # clean up our mess
        storage_provider.delete(storage_path, mongo_id)


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

    def file_queue_test(self, db_name: str) -> None:
        """
        Test the file queue and that it gives back reproducable results.
        """

        # first upload two files to the same folder
        storage_provider_class = self.get_storage_provider()
        try:
            storage_provider = storage_provider_class(self.get_login(), db_name)
        except TypeError:
            storage_provider = storage_provider_class(self.get_login())

        test_content = {"experiment_1": "Nothing happened here."}
        storage_path = "test/subcollection"

        job_id_1 = uuid.uuid4().hex[:24]
        storage_provider.upload(test_content, storage_path, job_id_1)

        test_content = {"experiment_2": "Nothing happened here."}
        storage_path = "test/subcollection"

        job_id_2 = uuid.uuid4().hex[:24]
        storage_provider.upload(test_content, storage_path, job_id_2)

        # now make sure that we can get the files back
        test_result = storage_provider.get_file_queue("test/subcollection")

        ic(test_result)
        assert len(test_result) >= 2
        # make sure that the .json is not in the file names that are returned
        assert all(".json" not in res_string for res_string in test_result)

        # remove the files
        storage_provider.delete("test/subcollection", job_id_1)
        storage_provider.delete("test/subcollection", job_id_2)

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

        backend_name, config_info = get_dummy_config(sign)
        private_jwk, _ = create_jwk_pair(backend_name)

        # does it fail if we try to upload the config without a private key?
        if sign:
            with pytest.raises(ValueError):
                storage_provider.upload_config(config_info, display_name=backend_name)

        # test that we cannot upload the config where the display_name in the config
        # is different from the display_name in the upload_config

        with pytest.warns(UserWarning):
            poor_backend_name, poor_config_info = get_dummy_config(sign)
            ic(poor_config_info.display_name)
            ic(poor_backend_name)
            poor_config_info.display_name = "dummynone"
            storage_provider.upload_config(
                poor_config_info,
                display_name=poor_backend_name,
                private_jwk=private_jwk,
            )

            obtained_config = storage_provider.get_config(poor_backend_name)
            assert obtained_config.display_name == poor_backend_name
            storage_provider._delete_config(poor_backend_name)

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

        # and again also with a poor name in the config_info
        config_info.last_queue_check = datetime.now(timezone.utc).replace(microsecond=0)
        config_info.display_name = "dummy"
        with pytest.warns(UserWarning):
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
        with pytest.raises(FileNotFoundError), pytest.warns(UserWarning):
            storage_provider.update_config(config_info, display_name="randonname")
        ic(backend_name)
        # can we get the backend in the list ?
        backends = storage_provider.get_backends()
        ic(backends)
        assert backend_name in backends

        # can we get the config of the backend ?
        backend_info = storage_provider.get_backend_dict(backend_name)
        backend_dict = backend_info.model_dump()
        assert backend_dict["backend_name"] == f"{db_name}_{backend_name}_simulator"
        # make sure that we raise an error if we try to get a backend that does not exist
        with pytest.raises(FileNotFoundError):
            storage_provider.get_backend_dict("dummy_non_existing")

        # clean up
        storage_provider._delete_config(backend_name)

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

        # create a dummy key
        key_id = "dummy_key"
        private_jwk, public_jwk = create_jwk_pair(key_id)

        # create a dummy config
        backend_name, config_info = get_dummy_config(sign=True)

        storage_provider.upload_config(
            config_info, display_name=backend_name, private_jwk=private_jwk
        )
        storage_provider.upload_public_key(public_jwk, display_name=backend_name)

        with pytest.raises(ValueError):
            storage_provider.upload_public_key(private_jwk, display_name=backend_name)

        # now test that we can also get the public key
        obtained_public_jwk = storage_provider.get_public_key(backend_name)
        assert obtained_public_jwk.x == public_jwk.x

        with pytest.raises(FileNotFoundError):
            obtained_public_jwk = storage_provider.get_public_key("random")

        # now make sure that we can use the same public key for a different backend
        other_backend_name, other_config_info = get_dummy_config(sign=True)
        storage_provider.upload_config(
            other_config_info, display_name=other_backend_name, private_jwk=private_jwk
        )
        obtained_public_jwk = storage_provider.get_public_key(other_backend_name)
        assert obtained_public_jwk.x == public_jwk.x

        # now make sure that we cannot upload a public key with a poor kid
        _, poor_public_jwk = create_jwk_pair("random")
        with pytest.raises(ValueError):
            storage_provider.upload_public_key(
                poor_public_jwk, display_name=backend_name
            )

        # remove old stuff
        storage_provider._delete_config(backend_name)
        storage_provider._delete_config(other_backend_name)
        storage_provider._delete_public_key(key_id)

    def user_signature_tests(self, db_name: str) -> None:
        """
        Test that we can create a signature for the user.
        """
        # create a storageprovider object
        storage_provider_class = self.get_storage_provider()
        try:
            storage_provider = storage_provider_class(self.get_login(), db_name)
        except TypeError:
            storage_provider = storage_provider_class(self.get_login())

        # create a user name
        dummy_user = uuid.uuid4().hex[:24]

        # create a dummy key
        key_id = f"user{dummy_user}"
        private_jwk, public_jwk = create_jwk_pair(key_id)

        # make sure that we cannot upload it as a normal backend
        # this is impossible as the config is not uploaded
        with pytest.raises(FileNotFoundError):
            storage_provider.upload_public_key(
                public_jwk, display_name=dummy_user, type="backend"
            )

        # make sure that we can upload the public key now
        storage_provider.upload_public_key(
            public_jwk, display_name=dummy_user, type="user"
        )

        # make sure that we cannot upload it again
        with pytest.raises(ValueError):
            storage_provider.upload_public_key(private_jwk, display_name=dummy_user)

        # now test that we can also get the public key
        obtained_public_jwk = storage_provider.get_public_key_from_kid(
            kid=f"user{dummy_user}"
        )
        assert obtained_public_jwk.x == public_jwk.x

        # remove old stuff
        storage_provider._delete_public_key(key_id)

    def backend_status_tests(
        self,
        db_name: str,
        sign: bool,
        caplog: LogCaptureFixture,
    ) -> Tuple[str, Any]:
        """
        Test the backend status.
        """
        # create a storageprovider object
        storage_provider_class = self.get_storage_provider()
        try:
            storage_provider = storage_provider_class(self.get_login(), db_name)
        except TypeError:
            storage_provider = storage_provider_class(self.get_login())

        backend_name, config_info = get_dummy_config(sign)
        private_jwk, _ = create_jwk_pair(backend_name)

        # and make sure that we raise an error if the backend is not there
        with pytest.raises(FileNotFoundError):
            status_schema = storage_provider.get_backend_status(backend_name)

        # make sure that we fail safely if the backend config is not there
        with pytest.raises(FileNotFoundError):
            storage_provider.timestamp_queue(backend_name, private_jwk)

        assert (
            f"The configuration for the backend {backend_name} does not exist."
            in caplog.text
        )

        storage_provider.upload_config(
            config_info, display_name=backend_name, private_jwk=private_jwk
        )

        # can we get the backend in the list ?
        backends = storage_provider.get_backends()
        assert backend_name in backends

        # can we get the status of the backend ?
        status_schema = storage_provider.get_backend_status(backend_name)
        status_dict = status_schema.model_dump()
        assert (
            status_dict["backend_name"]
            == f"{storage_provider.name}_{backend_name}_simulator"
        )
        assert status_dict["backend_version"] == config_info.version
        assert not status_dict["pending_jobs"]
        assert not status_dict["status_msg"]

        # given that the time stamp is not set, we should have an unoperational device
        assert status_dict["operational"] is False

        # let us now update the time stamp
        storage_provider.timestamp_queue(backend_name, private_jwk)

        # this should have changed the status
        status_schema = storage_provider.get_backend_status(backend_name)
        assert status_schema.operational is True

        # clean up
        storage_provider._delete_config(backend_name)
        return backend_name, storage_provider

    def sign_and_verify_result_test(self, db_name: str) -> None:
        """
        Test the ability to sign and verify a result with a JWK
        """
        # create a storageprovider object
        storage_provider_class = self.get_storage_provider()
        try:
            storage_provider = storage_provider_class(self.get_login(), db_name)
        except TypeError:
            storage_provider = storage_provider_class(self.get_login())

        backend_name, config_info = get_dummy_config(sign=True)
        private_jwk, public_jwk = create_jwk_pair("test_kid")

        # upload the config
        storage_provider.upload_config(
            config_info, display_name=backend_name, private_jwk=private_jwk
        )

        # upload the public key
        storage_provider.upload_public_key(public_jwk, display_name=backend_name)

        # create dummies
        result_dict = get_init_results()

        # the following is a bit of a dirty hack to get the job_id such
        # that we can test the dropbox provider
        if db_name == "dropboxtest":
            job_id = (
                (datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S"))
                + "-"
                + backend_name
                + "-"
                + config("TEST_USERNAME")
                + "-"
                + (uuid.uuid4().hex)[:5]
            )
        else:
            job_id = uuid.uuid4().hex[:24]

        # upload a signed result
        storage_provider.upload_result(
            result_dict,
            backend_name,
            job_id,
            private_jwk,
        )

        # now test that we can get the result
        obtained_result = storage_provider.get_result(
            backend_name, config("TEST_USERNAME"), job_id
        )
        assert obtained_result.job_id == job_id

        # now test that we can verify the result
        verified_result = storage_provider.verify_result(backend_name, job_id)
        assert verified_result is True

        # now also verify the it fails if we use another private key to sign the result
        wrong_private_jwk, _ = create_jwk_pair("other_kid")

        if db_name == "dropboxtest":
            wrong_job_id = (
                (datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S"))
                + "-"
                + backend_name
                + "-"
                + config("TEST_USERNAME")
                + "-"
                + (uuid.uuid4().hex)[:5]
            )
        else:
            wrong_job_id = uuid.uuid4().hex[:24]

        # upload another signed with another job_id result
        storage_provider.upload_result(
            result_dict,
            backend_name,
            wrong_job_id,
            wrong_private_jwk,
        )
        poor_result = storage_provider.verify_result(backend_name, wrong_job_id)
        assert poor_result is False

        # remove the useless results
        storage_provider._delete_result(backend_name, job_id)

    def status_tests(self, db_name: str, sign: bool = True) -> None:
        """
        Test the status upload and download.
        """
        # create a storageprovider object
        storage_provider_class = self.get_storage_provider()
        try:
            storage_provider = storage_provider_class(self.get_login(), db_name)
        except TypeError:
            storage_provider = storage_provider_class(self.get_login())

        backend_name, config_info = get_dummy_config(sign=sign)
        # create a dummy key
        private_jwk, _ = create_jwk_pair(backend_name)
        storage_provider.upload_config(
            config_info, display_name=backend_name, private_jwk=private_jwk
        )

        username = config("TEST_USERNAME")
        job_id = uuid.uuid4().hex[:24]

        # now also test that we can upload the status
        status_msg_dict = storage_provider.upload_status(
            display_name=backend_name,
            username=username,
            job_id=job_id,
            private_jwk=private_jwk,
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

        # clean up
        storage_provider._delete_status(
            display_name=backend_name,
            username=username,
            job_id=job_id,
        )
        # now test that we can upload the status without the private key if we are not singing
        storage_provider.upload_status(
            display_name=backend_name,
            username=username,
            job_id=job_id,
        )
        storage_provider._delete_status(
            display_name=backend_name,
            username=username,
            job_id=job_id,
        )

        # clean up the config
        storage_provider._delete_config(backend_name)

    def missing_status_tests(
        self,
        db_name: str,
        sign: bool,
        caplog: LogCaptureFixture,
    ) -> None:
        """
        Test that we can handle the missing status for the `update_in_database`.
        This should normally not happen, but should be explained properly.
        """
        # create a storageprovider object
        storage_provider_class = self.get_storage_provider()
        try:
            storage_provider = storage_provider_class(self.get_login(), db_name)
        except TypeError:
            storage_provider = storage_provider_class(self.get_login())

        backend_name, config_info = get_dummy_config(sign=sign)
        key_id = "dummy_key"
        private_jwk, _ = create_jwk_pair(key_id)

        storage_provider.upload_config(
            config_info, display_name=backend_name, private_jwk=private_jwk
        )

        if db_name == "dropboxtest":
            job_id = (
                (datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S"))
                + "-"
                + backend_name
                + "-"
                + config("TEST_USERNAME")
                + "-"
                + (uuid.uuid4().hex)[:5]
            )
        else:
            job_id = uuid.uuid4().hex[:24]

        # we now also need to test the update_in_database part of the storage provider
        result_dict = ResultDict(
            display_name=backend_name,
            backend_version="0.0.1",
            job_id=job_id,
            status="INITIALIZING",
        )

        job_status = get_init_status()

        storage_provider.update_in_database(
            result_dict,
            job_status,
            job_id,
            backend_name,
            private_jwk=private_jwk,
        )

        assert "The status file was missing" in caplog.text

        # clean up
        storage_provider._delete_config(backend_name)

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

        backend_name, config_info = get_dummy_config(sign=sign)

        # create a dummy key
        key_id = "dummy_key"
        private_jwk, public_jwk = create_jwk_pair(key_id)

        storage_provider.upload_config(
            config_info, display_name=backend_name, private_jwk=private_jwk
        )

        if sign:
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

        # now also test that we can upload the status without the private key
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
        if sign:
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

        # clean stuff up
        storage_provider._delete_result(backend_name, job_id)
        storage_provider._delete_status(backend_name, username, job_id)
        storage_provider._delete_config(backend_name)
        if sign:
            storage_provider._delete_public_key(key_id)

        return backend_name, job_id, username, storage_provider
