"""
The tests for the extended mongodb storage provider
"""

import uuid
from typing import Any

import pytest
from bson.objectid import ObjectId
from decouple import config

from sqooler.schemes import MongodbLoginInformation
from sqooler.storage_providers.mongodb import MongodbProviderExtended

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

    @pytest.mark.parametrize("sign_it", [True, False])
    def test_upload_and_update_config(self, sign_it: bool) -> None:
        """
        Test that we can upload and update a config.
        """
        self.config_tests(DB_NAME, sign=sign_it)

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

    def test_upload_public_key(self) -> None:
        """
        Test that it is possible to upload the public key.
        """
        self.signature_tests(DB_NAME)

    @pytest.mark.parametrize("sign_it", [True, False])
    def test_backend_status(self, sign_it: bool) -> None:
        """
        Test that we can get the status of a backend.
        """
        self.backend_status_tests(DB_NAME, sign=sign_it)

    def test_sign_and_verify_result(self) -> None:
        """
        Test that it is possible a result a verify it properly.
        """
        self.sign_and_verify_result_test(DB_NAME)

    @pytest.mark.parametrize("sign_it", [True, False])
    def test_status_dict(self, sign_it: bool) -> None:
        """
        Test that we can get the status of a backend.
        """
        self.status_tests(DB_NAME, sign=sign_it)

    def test_jobs(self) -> None:
        """
        Test that we can handle the necessary functions for the jobs and status.
        """
        backend_name, _, _, storage_provider = self.job_tests(DB_NAME)

        # remove the obsolete collection from the storage
        database = storage_provider.client["jobs"]
        collection = database[f"queued.{backend_name}"]
        collection.drop()
        collection = database[f"finished.{backend_name}"]
        collection.drop()

        # remove the obsolete collection from the storage
        database = storage_provider.client["status"]
        collection = database[backend_name]
        collection.drop()

        # remove the obsolete collection from the storage
        database = storage_provider.client["results"]
        collection = database[backend_name]
        collection.drop()
