"""
The tests for the storage provider
"""
import datetime
import uuid
from .storage_providers import DropboxProvider
from .schemes import ResultDict


class TestDropboxProvider:
    """
    The class that contains all the tests for the dropbox provider.
    """

    def test_upload_etc(self) -> None:
        """
        Test that it is possible to upload a file.
        """
        storage_provider = DropboxProvider()
        # upload a file and get it back
        job_id = uuid.uuid4().hex
        test_content = {"experiment_0": "Nothing happened here."}
        storage_path = "test_folder"
        file_id = f"job-{job_id}"
        storage_provider.upload(test_content, storage_path, file_id)
        test_result = storage_provider.get_file_content(storage_path, file_id)

        assert test_content, test_result

        # move it and get it back
        second_path = "test_folder_2"
        storage_provider.move_file(storage_path, second_path, file_id)
        test_result = storage_provider.get_file_content(second_path, file_id)
        assert test_content == test_result

        # test that we can also get the job from the database
        test_result = storage_provider.get_job_content(second_path, job_id)
        assert test_content["experiment_0"] == test_result["experiment_0"]

        # clean up our mess
        storage_provider.delete_file(second_path, file_id)

    def test_upload_configs(self) -> None:
        """
        We would like to make sure that we can properly upload the configuration files
        that come from the spoolers.
        """
        storage_provider = DropboxProvider()
        dummy_id = uuid.uuid4().hex[:5]
        backend_name = f"dummy_{dummy_id}"
        dummy_dict: dict = {}
        dummy_dict["display_name"] = backend_name
        dummy_dict["gates"] = []
        dummy_dict["num_wires"] = 3
        dummy_dict["version"] = "0.0.1"

        storage_provider.upload_config(dummy_dict, backend_name)

        # can we get the backend in the list ?
        dummy_path = f"Backend_files/Config/{backend_name}"
        backend_dict = storage_provider.get_file_content(dummy_path, "config")
        assert backend_dict["display_name"] == dummy_dict["display_name"]

    def test_get_next_job_in_queue(self) -> None:
        """
        Is it possible to work through the queue of jobs?
        """
        storage_provider = DropboxProvider()

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
        result_dict: ResultDict = {
            "display_name": backend_name,
            "backend_version": "0.0.1",
            "job_id": next_job["job_id"],
            "qobj_id": None,
            "success": True,
            "status": "finished",
            "header": {},
            "results": [],
        }
        status_msg_dict = {"status": "INITIALIZING"}
        # upload the status dict without other status.

        # time to update everything
        status_msg_dict = {"status": "DONE"}
        storage_provider.update_in_database(
            result_dict, status_msg_dict, next_job["job_id"], backend_name
        )

        # we now need to check if the job is in the finished jobs folder
        job_finished_json_dir = (
            "/Backend_files/Finished_Jobs/" + backend_name + "/" + username + "/"
        )

        finshed_job = storage_provider.get_file_content(job_finished_json_dir, job_name)
        assert finshed_job["job_id"] == job_id

        # we check if the status was updated
        status_json_dir = "/Backend_files/Status/" + backend_name + "/" + username + "/"
        status_json_name = "status-" + job_id
        status_dict = storage_provider.get_file_content(
            status_json_dir, status_json_name
        )
        assert status_dict["status"] == "DONE"

        # clean up the mess
        storage_provider.delete_file(job_finished_json_dir, job_name)
        storage_provider.delete_file(status_json_dir, status_json_name)
