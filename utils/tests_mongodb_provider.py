"""
The tests for the storage provider
"""
import datetime
import uuid
from .storage_providers import MongodbProvider


class TestMongodbProvider:
    """
    The class that contains all the tests for the dropbox provider.
    """

    def test_upload_etc(self):
        """
        Test that it is possible to upload a file.
        """
        storage_provider = MongodbProvider()
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

        # clean up our mess
        storage_provider.delete_file(second_path, job_id)

    def test_upload_configs(self):
        """
        We would like to make sure that we can properly upload the configuration files
        that come from the spoolers.
        """
        storage_provider = MongodbProvider()
        dummy_id = uuid.uuid4().hex[:5]
        dummy_dict: dict = {}
        dummy_dict["gates"] = []
        dummy_dict["name"] = "Dummy"
        dummy_dict["num_wires"] = 3
        dummy_dict["version"] = "0.0.1"

        backend_name = f"dummy_{dummy_id}"
        storage_provider.upload_config(dummy_dict, backend_name)

        # can we get the backend in the list ?

        # get the database on which we work
        database = storage_provider.client["backends"]
        configs = database["configs"]
        document_to_find = {"display_name": backend_name}

        result_found = configs.find_one(document_to_find)
        assert result_found["name"] == dummy_dict["name"]

    def test_get_next_job_in_queue(self):
        """
        Is it possible to work through the queue of jobs?
        """
        storage_provider = MongodbProvider()

        # create a dummy backend
        dummy_id = uuid.uuid4().hex[:5]
        backend_name = f"dummy_{dummy_id}"

        username = "test_user"
        job_id = (
            (datetime.datetime.utcnow().strftime("%Y%m%d_%H%M%S"))
            + "-"
            + backend_name
            + "-"
            + username
            + "-"
            + (uuid.uuid4().hex)[:5]
        )

        # first we have to upload a dummy job
        job_dict = {"job_id": job_id, "job_json_path": "None"}
        job_name = "job-" + job_id
        queue_path = f"Backend_files/Queued_Jobs/{backend_name}"
        job_dict["job_json_path"] = queue_path

        storage_provider.upload(job_dict, queue_path, job_id=job_name)

        # test if the file_queue is working

        job_list = storage_provider.get_file_queue(queue_path)
        print(job_list)

        # the last step is to get the next job and see if this nicely worked out
        next_job = storage_provider.get_next_job_in_queue(backend_name)

        assert next_job["job_id"] == job_id

        # we now also need to test the update_in_database part of the storage provider
        result_dict = {
            "backend_name": backend_name,
            "backend_version": "0.0.1",
            "job_id": next_job["job_id"],
            "qobj_id": None,
            "success": True,
            "status": "finished",
            "header": {},
            "results": [],
        }
        status_msg_dict = {"status": "DONE"}
        storage_provider.update_in_database(
            result_dict, status_msg_dict, next_job["job_id"]
        )
