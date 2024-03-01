"""
The tests for the storage provider using mongodb
"""

import uuid
from typing import Any

# get the environment variables
from decouple import config

from sqooler.storage_providers.mongodb import MongodbProvider
from sqooler.schemes import ResultDict, MongodbLoginInformation

from .storage_provider_test_utils import StorageProviderTestUtils


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

    def test_upload_etc(self) -> None:
        """
        Test that it is possible to upload a file.
        """
        login_dict = self.get_login()
        storage_provider = MongodbProvider(login_dict)
        # upload a file and get it back
        test_content = {"experiment_0": "Nothing happened here."}
        storage_path = "test/subcollection"

        job_id = uuid.uuid4().hex[:24]
        storage_provider.upload(test_content, storage_path, job_id)
        test_result = storage_provider.get_file_content(storage_path, job_id)

        assert test_content["experiment_0"] == test_result["experiment_0"]

        # move it and get it back
        second_path = "test/subcollection_2"
        storage_provider.move_file(storage_path, second_path, job_id)
        test_result = storage_provider.get_file_content(second_path, job_id)
        assert test_content["experiment_0"] == test_result["experiment_0"]

        # test that we can also get the job from the database
        test_result = storage_provider.get_job_content(second_path, job_id)
        assert test_content["experiment_0"] == test_result["experiment_0"]

        # test that we can update the file properly

        new_content = {"experiment_0": "What happened here."}
        storage_provider.update_file(new_content, second_path, job_id)
        test_result = storage_provider.get_job_content(second_path, job_id)
        assert new_content["experiment_0"] == test_result["experiment_0"]

        # clean up our mess
        storage_provider.delete_file(second_path, job_id)

    def test_upload_configs(self) -> None:
        """
        We would like to make sure that we can properly upload the configuration files
        that come from the spoolers.
        """

        storage_provider = MongodbProvider(self.get_login())

        backend_name, backend_config_info = self.get_dummy_config()
        storage_provider.upload_config(backend_config_info, backend_name)

        # can we get the backend in the list ?
        # get the database on which we work
        database = storage_provider.client["backends"]
        configs = database["configs"]
        document_to_find = {"display_name": backend_name}

        result_found = configs.find_one(document_to_find)
        if result_found is None:
            raise ValueError("The backend was not uploaded properly.")
        assert result_found["display_name"] == backend_config_info.display_name

        # make sure that the upload of the same backend does only update it.
        backend_config_info.num_wires = 4
        storage_provider.upload_config(backend_config_info, backend_name)
        results_found = configs.find(document_to_find)
        assert len(list(results_found)) == 1

        # clean up our mess
        configs.delete_one(document_to_find)

    def test_get_next_job_in_queue(self) -> None:
        """
        Is it possible to work through the queue of jobs?
        """
        storage_provider = MongodbProvider(self.get_login())

        # create a dummy backend
        backend_name, backend_info = self.get_dummy_config()
        storage_provider.upload_config(backend_info, backend_name)

        # first we have to upload a dummy job
        job_id = (uuid.uuid4().hex)[:24]
        job_dict = {"job_id": job_id, "job_json_path": "None"}
        queue_path = "jobs/queued/" + backend_name
        job_dict["job_json_path"] = queue_path

        storage_provider.upload(job_dict, queue_path, job_id=job_id)

        # test if the file_queue is working

        job_list = storage_provider.get_file_queue(queue_path)
        assert job_list

        # the last step is to get the next job and see if this nicely worked out
        next_job = storage_provider.get_next_job_in_queue(backend_name)

        assert next_job.job_id == job_id

        # now also get the job content
        job_json_dict = storage_provider.get_job_content(
            storage_path=next_job.job_json_path, job_id=next_job.job_id
        )
        assert "_id" not in job_json_dict.keys()

        # we now also need to test the update_in_database part of the storage provider

        result_dict = ResultDict(
            display_name=backend_name,
            backend_version="0.0.1",
            job_id=next_job.job_id,
            status="INITIALIZING",
        )

        # upload the status dict without other status.
        status_msg_dict = storage_provider.upload_status(
            backend_name, "test_user", next_job.job_id
        )

        status_msg_dict.status = "DONE"
        storage_provider.update_in_database(
            result_dict, status_msg_dict, next_job.job_id, backend_name
        )

        # we now need to check if the job is in the finished jobs folder
        job_finished_json_dir = "jobs/finished/" + backend_name

        finshed_job = storage_provider.get_file_content(job_finished_json_dir, job_id)
        assert finshed_job["job_id"] == job_id

        # we check if the status was updated
        status_json_dir = "status/" + backend_name
        status_dict = storage_provider.get_file_content(status_json_dir, job_id)
        assert status_dict["status"] == "DONE"

        # clean up the mess
        storage_provider.delete_file(job_finished_json_dir, job_id)
        storage_provider.delete_file(status_json_dir, job_id)

        # remove the unused collections in the jobs
        database = storage_provider.client["jobs"]
        collection = database[f"queued.{backend_name}"]
        collection.drop()

        collection = database[f"finished.{backend_name}"]
        collection.drop()

        # remove the unused collections in the status
        database = storage_provider.client["status"]
        collection = database[f"{backend_name}"]
        collection.drop()
