"""
The tests for the storage provider using mongodb
"""

from typing import Any

from bson.objectid import ObjectId

# get the environment variables
from decouple import config

from sqooler.schemes import MongodbLoginInformation
from sqooler.storage_providers.mongodb import MongodbProvider

from .storage_provider_test_utils import StorageProviderTestUtils

DB_NAME = "mongodbtest"


class TestMongodbProvider(StorageProviderTestUtils):
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
        return MongodbProvider

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
        storage_provider = MongodbProvider(login_info)
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
