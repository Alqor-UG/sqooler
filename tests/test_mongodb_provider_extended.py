"""
The tests for the extended mongodb storage provider
"""

import uuid
from typing import Any
from decouple import config

import pytest
from bson.objectid import ObjectId

from sqooler.storage_providers.mongodb import MongodbProviderExtended
from sqooler.schemes import MongodbLoginInformation

from .storage_provider_test_utils import StorageProviderTestUtils

DB_NAME = "mongodbtest"


class TestMongodbProviderExtended(StorageProviderTestUtils):
    """
    The class that contains all the tests for the dropbox provider.
    """

    def get_login_class(self) -> Any:
        """
        Get the storage provider.
        """
        return MongodbLoginInformation

    def get_storage_provider(self) -> Any:
        """
        Get the storage provider.
        """
        return MongodbProviderExtended

    def get_login(self) -> MongodbLoginInformation:
        """
        Get the login information for the mongodb database.
        """
        # put together the login information
        mongodb_username = config("MONGODB_USERNAME")
        mongodb_password = config("MONGODB_PASSWORD")
        mongodb_database_url = config("MONGODB_DATABASE_URL")
        login_dict = {
            "mongodb_username": mongodb_username,
            "mongodb_password": mongodb_password,
            "mongodb_database_url": mongodb_database_url,
        }
        return MongodbLoginInformation(**login_dict)

    @classmethod
    def teardown_class(cls) -> None:
        """
        Remove the `storage` folder.
        """

        # put together the login information
        mongodb_username = config("MONGODB_USERNAME")
        mongodb_password = config("MONGODB_PASSWORD")
        mongodb_database_url = config("MONGODB_DATABASE_URL")

        login_dict = {
            "mongodb_username": mongodb_username,
            "mongodb_password": mongodb_password,
            "mongodb_database_url": mongodb_database_url,
        }
        login_info = MongodbLoginInformation(**login_dict)

        # Remove all the collections that start with queued.
        storage_provider = MongodbProviderExtended(login_info, DB_NAME)
        database = storage_provider.client["jobs"]
        for collection_name in database.list_collection_names():
            if collection_name.startswith("queued.dummy"):
                collection = database[collection_name]
                collection.drop()

        # Remove all the collections from results that start with dummy
        database = storage_provider.client["results"]
        for collection_name in database.list_collection_names():
            if collection_name.startswith("dummy"):
                collection = database[collection_name]
                collection.drop()

        # Remove all the collections from status that start with dummy
        database = storage_provider.client["status"]
        for collection_name in database.list_collection_names():
            if collection_name.startswith("dummy"):
                collection = database[collection_name]
                collection.drop()

        # Remove all the dummy configs
        database = storage_provider.client["backends"]
        collection = database["configs"]

        database = storage_provider.client["status"]
        for config_dict in collection.find():
            if "display_name" in config_dict:
                if "dummy" in config_dict["display_name"]:
                    print("Deleting config: " + config_dict["display_name"])
                    collection.delete_one({"_id": ObjectId(config_dict["_id"])})
            if "payload" in config_dict:
                if "display_name" in config_dict["payload"]:
                    print(config_dict["payload"])
                    if "dummy" in config_dict["payload"]["display_name"]:
                        print(
                            "Deleting config: " + config_dict["payload"]["display_name"]
                        )
                        collection.delete_one({"_id": ObjectId(config_dict["_id"])})
                else:
                    print("Deleting config: " + config_dict["display_name"])
                    collection.delete_one({"_id": ObjectId(config_dict["_id"])})
            else:
                print("Deleting random config")
                collection.delete_one({"_id": ObjectId(config_dict["_id"])})

    def test_mongodb_object(self) -> None:
        """
        Test that we can create a MongoDB object.
        """
        self.storage_object_tests(DB_NAME)

    def test_file_remove(self) -> None:
        """
        Test that it is possible to remove a file and we raise the right errors.
        """
        self.remove_file_not_found_test(DB_NAME)

    def test_not_active(self) -> None:
        """
        Test that we cannot work with the provider if it is not active.
        """
        storage_provider = MongodbProviderExtended(
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
        # create a mongodb object
        storage_provider = MongodbProviderExtended(self.get_login(), DB_NAME)

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

        with pytest.raises(FileNotFoundError):
            storage_provider.get_file_content(storage_path, uuid.uuid4().hex[:24])

        # move it and get it back
        second_path = "test/subcollection_2"
        storage_provider.move_file(storage_path, second_path, job_id)
        test_result = storage_provider.get_file_content(second_path, job_id)

        assert test_content == test_result

        # clean up our mess
        storage_provider.delete_file(second_path, job_id)

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
        # create a mongodb object
        storage_provider = MongodbProviderExtended(self.get_login(), DB_NAME)
        backend_name, backend_config_info = self.get_dummy_config(sign=False)
        config_path = "backends/configs"

        storage_provider.upload_config(backend_config_info, backend_name)

        # can we get the backend in the list ?
        backends = storage_provider.get_backends()
        assert backend_name in backends

        # can we get the config of the backend ?
        backend_info = storage_provider.get_backend_dict(backend_name)
        backend_dict = backend_info.model_dump()
        assert (
            backend_dict["backend_name"]
            == f"mongodbtest_{backend_config_info.display_name}_simulator"
        )
        # make sure that we raise an error if we try to get a backend that does not exist
        with pytest.raises(FileNotFoundError):
            storage_provider.get_backend_dict("dummy_non_existing")

        # test how we can delete a backend. main challenge is to get the id of the config
        document_to_find = {"display_name": backend_name}

        database = storage_provider.client["backends"]
        collection = database["configs"]

        result_found = collection.find_one(document_to_find)
        storage_provider.delete_file(config_path, str(result_found["_id"]))

    def test_update_raise_error(self) -> None:
        """
        Test that it is update a file once it was uploaded.
        """

        # create a dropbox object
        storage_provider = MongodbProviderExtended(self.get_login(), DB_NAME)

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

    @pytest.mark.parametrize("sign_it", [True, False])
    def test_backend_status(self, sign_it: bool) -> None:
        """
        Test that we can get the status of a backend.
        """
        backend_name, storage_provider = self.backend_status_tests(
            DB_NAME, sign=sign_it
        )

        # test how we can delete a backend. main challenge is to get the id of the config
        config_path = "backends/configs"
        database = storage_provider.client["backends"]
        collection = database["configs"]

        if not sign_it:
            document_to_find = {"display_name": backend_name}
        elif sign_it:
            document_to_find = {"payload.display_name": backend_name}

        result_found = collection.find_one(document_to_find)
        storage_provider.delete_file(config_path, str(result_found["_id"]))

    def test_jobs(self) -> None:
        """
        Test that we can handle the necessary functions for the jobs and status.
        """
        backend_name, job_id, username, storage_provider = self.job_tests(DB_NAME)

        # what happens if we try get an unknown job ?
        job_result = storage_provider.get_result(
            display_name=backend_name,
            username=username,
            job_id=uuid.uuid4().hex,
        )
        assert job_result.status == "ERROR"

        # remove the obsolete collection from the storage
        database = storage_provider.client["jobs"]
        collection = database[f"queued.{backend_name}"]
        collection.drop()

        # remove the obsolete status from the storage
        status_dir = "status/" + backend_name
        storage_provider.delete_file(status_dir, job_id)

        # remove the obsolete collection from the storage
        database = storage_provider.client["status"]
        collection = database[backend_name]
        collection.drop()

        # remove the obsolete result from the storage
        result_json_dir = "results/" + backend_name
        storage_provider.delete_file(result_json_dir, job_id)
        # remove the obsolete collection from the storage
        database = storage_provider.client["results"]
        collection = database[backend_name]
        collection.drop()

        # remove the obsolete config from the storage
        config_path = "backends/configs"

        database = storage_provider.client["backends"]
        collection = database["configs"]
        document_to_find = {"payload.display_name": backend_name}
        result_found = collection.find_one(document_to_find)
        storage_provider.delete_file(config_path, str(result_found["_id"]))
