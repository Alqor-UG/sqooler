"""
The module that contains all the necessary logic for communication with the external
storage for the jobs. It creates an abstract API layer for the storage providers.
"""
import sys
import uuid
from abc import ABC, abstractmethod
import json

from typing import Mapping, Callable, Any
import functools

# necessary for the local provider
import shutil
import os

# necessary for the dropbox provider
import datetime
import dropbox
from dropbox.files import WriteMode
from dropbox.exceptions import ApiError, AuthError

# necessary for the mongodb provider
from pymongo.mongo_client import MongoClient
from bson.objectid import ObjectId

from .schemes import (
    ResultDict,
    MongodbLoginInformation,
    DropboxLoginInformation,
    LocalLoginInformation,
    BackendStatusSchemaOut,
    BackendConfigSchemaIn,
    BackendConfigSchemaOut,
)


def validate_active(func: Callable) -> Callable:
    """
    Decorator to check if the storage provider is active.
    """

    @functools.wraps(func)
    def wrapper(self: Any, *args: Any, **kwargs: Any) -> Callable:
        """
        Wrapper around the function that checks if the storage provider is active."""
        if not self.is_active:
            raise ValueError("The storage provider is not active.")
        return func(self, *args, **kwargs)

    return wrapper


class StorageProvider(ABC):
    """
    The template for accessing any storage providers like dropbox, mongodb, amazon S3 etc.
    """

    def __init__(self, name: str, is_active: bool = True) -> None:
        """
        Any storage provide must have a name that is not empty.

        Args:
            name: The name of the storage provider
            is_active: Is the storage provider active.
        """
        if not name:
            raise ValueError("The name of the storage provider cannot be empty.")
        self.name = name
        self.is_active = is_active

    @abstractmethod
    def upload(self, content_dict: Mapping, storage_path: str, job_id: str) -> None:
        """
        Upload the file to the storage
        """

    @abstractmethod
    def get_file_content(self, storage_path: str, job_id: str) -> dict:
        """
        Get the file content from the storage
        """

    @abstractmethod
    def get_backends(self) -> list[str]:
        """
        Get a list of all the backends that the provider offers.
        """

    @abstractmethod
    def get_backend_dict(self, display_name: str) -> BackendConfigSchemaOut:
        """
        The configuration of the backend.

        Args:
            display_name: The identifier of the backend

        Returns:
            The full schema of the backend.
        """

    @abstractmethod
    def get_backend_status(self, display_name: str) -> BackendStatusSchemaOut:
        """
        Get the status of the backend. This follows the qiskit logic.

        Args:
            display_name: The name of the backend

        Returns:
            The status dict of the backend
        """

    @abstractmethod
    def upload_job(self, job_dict: dict, display_name: str, username: str) -> str:
        """
        Upload the job to the storage provider.

        Args:
            job_dict: the full job dict
            display_name: the name of the backend
            username: the name of the user that submitted the job

        Returns:
            The job id of the uploaded job.
        """

    @abstractmethod
    def get_job_content(self, storage_path: str, job_id: str) -> dict:
        """
        Get the content of the job from the storage. This is a wrapper around get_file_content
        and and handles the different ways of identifiying the job.

        storage_path: the path towards the file, excluding the filename / id
        job_id: the id of the file we are about to look up

        Returns:
            The content of the job
        """

    @abstractmethod
    def upload_status(self, display_name: str, username: str, job_id: str) -> dict:
        """
        This function uploads a status file to the backend and creates the status dict.

        Args:
            display_name: The name of the backend to which we want to upload the job
            username: The username of the user that is uploading the job
            job_id: The job_id of the job that we want to upload the status for

        Returns:
            The status dict of the job
        """

    @abstractmethod
    def get_status(self, display_name: str, username: str, job_id: str) -> dict:
        """
        This function gets the status file from the backend and returns the status dict.

        Args:
            display_name: The name of the backend to which we want to upload the job
            username: The username of the user that is uploading the job
            job_id: The job_id of the job that we want to upload the status for

        Returns:
            The status dict of the job
        """

    @abstractmethod
    def get_result(self, display_name: str, username: str, job_id: str) -> ResultDict:
        """
        This function gets the result file from the backend and returns the result dict.

        Args:
            display_name: The name of the backend to which we want to upload the job
            username: The username of the user that is uploading the job
            job_id: The job_id of the job that we want to upload the status for

        Returns:
            The result dict of the job
        """

    @abstractmethod
    def update_file(self, content_dict: dict, storage_path: str, job_id: str) -> None:
        """
        Update the file content.

        Args:
            content_dict: The dictionary containing the new content of the file
            storage_path: The path to the file
            job_id: The id of the job

        Returns:
            None
        """

    @abstractmethod
    def move_file(self, start_path: str, final_path: str, job_id: str) -> None:
        """
        Move the file from `start_path` to `final_path`
        """

    @abstractmethod
    def delete_file(self, storage_path: str, job_id: str) -> None:
        """
        Delete the file from the storage
        """

    @abstractmethod
    def upload_config(
        self, config_dict: BackendConfigSchemaIn, backend_name: str
    ) -> None:
        """
        The function that uploads the spooler configuration to the storage.

        Args:
            config_dict: The model containing the configuration
            backend_name (str): The name of the backend

        Returns:
            None
        """

    @abstractmethod
    def update_in_database(
        self,
        result_dict: ResultDict,
        status_msg_dict: dict,
        job_id: str,
        backend_name: str,
    ) -> None:
        """
        Upload the status and result to the `StorageProvider`.

        Args:
            result_dict: the dictionary containing the result of the job
            status_msg_dict: the dictionary containing the status message of the job
            job_id: the name of the job
            backend_name: the name of the backend

        Returns:
            None
        """

    @abstractmethod
    def get_file_queue(self, storage_path: str) -> list[str]:
        """
        Get a list of files

        Args:
            storage_path: Where are we looking for the files.

        Returns:
            A list of files that was found.
        """

    @abstractmethod
    def get_next_job_in_queue(self, backend_name: str) -> dict:
        """
        A function that obtains the next job in the queue.

        Args:
            backend_name (str): The name of the backend

        Returns:
            the path towards the job
        """

    def backend_dict_to_qiskit(
        self, backend_config_info: BackendConfigSchemaIn
    ) -> BackendConfigSchemaOut:
        """
        This function transforms the dictionary that is safed in the storage provider
        into a qiskit backend dictionnary.

        Args:
            backend_config_info: The dictionary that contains the configuration of the backend

        Returns:
            The qiskit backend dictionary
        """
        backend_config_dict = backend_config_info.model_dump()
        display_name = backend_config_dict["display_name"]
        # for comaptibility with qiskit
        backend_config_dict["basis_gates"] = []
        for gate in backend_config_dict["gates"]:
            backend_config_dict["basis_gates"].append(gate["name"])

        # if the name is already in the dict, we should set the backend_name to the name
        # otherwise we calculate it.
        if backend_config_dict["simulator"]:
            backend_name = f"{self.name}_{display_name}_simulator"
        else:
            backend_name = f"{self.name}_{display_name}_hardware"

        backend_config_dict["backend_name"] = backend_name
        backend_config_dict["n_qubits"] = backend_config_dict["num_wires"]
        backend_config_dict["backend_version"] = backend_config_dict["version"]

        backend_config_dict["conditional"] = False
        backend_config_dict["local"] = False
        backend_config_dict["open_pulse"] = False
        backend_config_dict["memory"] = True
        backend_config_dict["coupling_map"] = "linear"
        return BackendConfigSchemaOut(**backend_config_dict)

    def backend_dict_to_qiskit_status(
        self, backend_dict: BackendConfigSchemaIn
    ) -> BackendStatusSchemaOut:
        """
        This function transforms the dictionary that is safed in the storage provider
        into a qiskit backend status dictionnary.

        Args:
            backend_dict: The dictionary that contains the configuration of the backend

        Returns:
            The qiskit backend dictionary
        """
        backend_status_dict = {
            "backend_name": "",
            "backend_version": "",
            "operational": True,
            "pending_jobs": 0,
            "status_msg": "",
        }

        display_name = backend_dict.display_name

        # if the name is already in the dict, we should set the backend_name to the name
        # otherwise we calculate it.
        if backend_dict.simulator:
            backend_name = f"{self.name}_{display_name}_simulator"
        else:
            backend_name = f"{self.name}_{display_name}_hardware"

        backend_status_dict["backend_name"] = backend_name
        backend_status_dict["backend_version"] = backend_dict.version

        # now I also need to obtain the operational status from the backend.
        backend_status_dict["operational"] = backend_dict.operational

        # would be nice to attempt to get the pending jobs too, if possible easily.
        if backend_dict.pending_jobs:
            backend_status_dict["pending_jobs"] = backend_dict.pending_jobs
        else:
            backend_status_dict["pending_jobs"] = 0

        # and also handle the status message which is currently optional BackendConfigSchemaIn
        if backend_dict.status_msg:
            backend_status_dict["status_msg"] = backend_dict.status_msg
        else:
            backend_status_dict["status_msg"] = ""
        return BackendStatusSchemaOut(**backend_status_dict)


class DropboxProviderExtended(StorageProvider):
    """
    The class that implements the dropbox storage provider.
    """

    def __init__(
        self, login_dict: DropboxLoginInformation, name: str, is_active: bool = True
    ) -> None:
        """
        Args:
            login_dict: The dictionary that contains the login information
            name: The name of the storage provider
            is_active: Is the storage provider active.
        """

        super().__init__(name, is_active)
        self.app_key = login_dict.app_key
        self.app_secret = login_dict.app_secret
        self.refresh_token = login_dict.refresh_token

    def upload(self, content_dict: Mapping, storage_path: str, job_id: str) -> None:
        """
        Upload the content_dict as a json file to the dropbox

        Args:
            content_dict: the content of the file that should be uploaded
            storage_path: the path where the file should be stored, but excluding the file name
            job_id: the name of the file without the .json extension
        """

        # create the appropriate string for the dropbox API
        dump_str = json.dumps(content_dict)

        # strip trailing and leading slashes from the storage_path
        storage_path = storage_path.strip("/")

        # create the full path
        full_path = "/" + storage_path + "/" + job_id + ".json"

        # Create an instance of a Dropbox class, which can make requests to the API.
        with dropbox.Dropbox(
            app_key=self.app_key,
            app_secret=self.app_secret,
            oauth2_refresh_token=self.refresh_token,
        ) as dbx:
            # Check that the access token is valid
            dbx.users_get_current_account()
            dbx.files_upload(
                dump_str.encode("utf-8"), full_path, mode=WriteMode("overwrite")
            )

    def get_file_content(self, storage_path: str, job_id: str) -> dict:
        """
        Get the file content from the dropbox

        storage_path: the path where the file should be stored, but excluding the file name
        job_id: the name of the file. Is a json file
        """

        # strip trailing and leading slashes from the storage_path
        storage_path = storage_path.strip("/")

        # Create an instance of a Dropbox class, which can make requests to the API.
        with dropbox.Dropbox(
            app_key=self.app_key,
            app_secret=self.app_secret,
            oauth2_refresh_token=self.refresh_token,
        ) as dbx:
            # Check that the access token is valid
            try:
                dbx.users_get_current_account()
            except AuthError:
                sys.exit("ERROR: Invalid access token.")
            full_path = "/" + storage_path + "/" + job_id + ".json"
            _, res = dbx.files_download(path=full_path)
            data = res.content
        return json.loads(data.decode("utf-8"))

    def get_job_content(self, storage_path: str, job_id: str) -> dict:
        """
        Get the content of the job from the storage. This is a wrapper around get_file_content
        and and handles the different ways of identifiying the job.

        storage_path: the path towards the file, excluding the filename / id
        job_id: the id of the file we are about to look up

        Returns:
            The content of the job
        """
        return self.get_file_content(storage_path=storage_path, job_id=f"job-{job_id}")

    def update_file(self, content_dict: dict, storage_path: str, job_id: str) -> None:
        """
        Update the file content.

        Args:
            content_dict: The dictionary containing the new content of the file
            storage_path: The path to the file
            job_id: The id of the job

        Returns:
            None
        """
        # create the appropriate string for the dropbox API
        dump_str = json.dumps(content_dict)

        # strip trailing and leading slashes from the storage_path
        storage_path = storage_path.strip("/")

        # create the full path
        full_path = "/" + storage_path + "/" + job_id + ".json"

        # Create an instance of a Dropbox class, which can make requests to the API.
        with dropbox.Dropbox(
            app_key=self.app_key,
            app_secret=self.app_secret,
            oauth2_refresh_token=self.refresh_token,
        ) as dbx:
            # Check that the access token is valid
            dbx.users_get_current_account()
            dbx.files_upload(
                dump_str.encode("utf-8"), full_path, mode=WriteMode("overwrite")
            )

    @validate_active
    def move_file(self, start_path: str, final_path: str, job_id: str) -> None:
        """
        Move the file from start_path to final_path

        start_path: the path where the file is currently stored, but excluding the file name
        final_path: the path where the file should be stored, but excluding the file name
        job_id: the name of the file. Is a json file

        Returns:
            None
        """
        # strip trailing and leading slashes from the paths
        start_path = start_path.strip("/")
        final_path = final_path.strip("/")

        # Create an instance of a Dropbox class, which can make requests to the API.
        with dropbox.Dropbox(
            app_key=self.app_key,
            app_secret=self.app_secret,
            oauth2_refresh_token=self.refresh_token,
        ) as dbx:
            dbx.users_get_current_account()

            full_start_path = "/" + start_path + "/" + job_id + ".json"
            full_final_path = "/" + final_path + "/" + job_id + ".json"
            dbx.files_move_v2(full_start_path, full_final_path)

    @validate_active
    def delete_file(self, storage_path: str, job_id: str) -> None:
        """
        Remove the file from the dropbox

        Args:
            storage_path: the path where the file should be stored, but excluding the file name
            job_id: the name of the file. Is a json file

        Returns:
            None
        """

        # strip trailing and leading slashes from the storage_path
        storage_path = storage_path.strip("/")

        # Create an instance of a Dropbox class, which can make requests to the API.
        with dropbox.Dropbox(
            app_key=self.app_key,
            app_secret=self.app_secret,
            oauth2_refresh_token=self.refresh_token,
        ) as dbx:
            # Check that the access token is valid
            try:
                dbx.users_get_current_account()
            except AuthError:
                sys.exit("ERROR: Invalid access token.")

            full_path = "/" + storage_path + "/" + job_id + ".json"
            _ = dbx.files_delete(path=full_path)

    def upload_config(
        self, config_dict: BackendConfigSchemaIn, backend_name: str
    ) -> None:
        """
        The function that uploads the spooler configuration to the storage.

        All the configurations are stored in the Backend_files/Config folder.
        For each backend there is a separate folder in which the configuration is stored as a json file.

        Args:
            config_dict: The dictionary containing the configuration
            backend_name (str): The name of the backend

        Returns:
            None
        """

        config_path = "Backend_files/Config/" + backend_name
        self.upload(config_dict.model_dump(), config_path, "config")

    def update_in_database(
        self,
        result_dict: ResultDict,
        status_msg_dict: dict,
        job_id: str,
        backend_name: str,
    ) -> None:
        """
        Upload the status and result to the dropbox.

        Args:
            result_dict: the dictionary containing the result of the job
            status_msg_dict: the dictionary containing the status message of the job
            job_id: the name of the job
            backend_name: the name of the backend

        Returns:
            None
        """
        # this should become part of the json file instead of its name in the future
        extracted_username = job_id.split("-")[2]

        status_json_dir = (
            "/Backend_files/Status/" + backend_name + "/" + extracted_username + "/"
        )
        status_json_name = "status-" + job_id

        job_json_name = "job-" + job_id
        job_json_start_dir = "Backend_files/Running_Jobs"

        if status_msg_dict["status"] == "DONE":
            # let us create the result json file
            result_json_dir = (
                "/Backend_files/Result/" + backend_name + "/" + extracted_username + "/"
            )
            result_json_name = "result-" + job_id
            self.upload(result_dict.model_dump(), result_json_dir, result_json_name)

            # now move the job out of the running jobs into the finished jobs
            job_finished_json_dir = (
                "/Backend_files/Finished_Jobs/"
                + backend_name
                + "/"
                + extracted_username
                + "/"
            )
            self.move_file(job_json_start_dir, job_finished_json_dir, job_json_name)

        elif status_msg_dict["status"] == "ERROR":
            # because there was an error, we move the job to the deleted jobs
            deleted_json_dir = "Backend_files/Deleted_Jobs"
            self.move_file(job_json_start_dir, deleted_json_dir, job_json_name)

        # and create the status json file
        self.upload(status_msg_dict, status_json_dir, status_json_name)

    def get_file_queue(self, storage_path: str) -> list[str]:
        """
        Get a list of files. Typically we are looking for the queued jobs of a backend here.

        Args:
            storage_path: Where are we looking for the files.

        Returns:
            A list of files that was found.
        """

        # strip trailing and leading slashes from the paths
        storage_path = storage_path.strip("/")

        storage_path = "/" + storage_path.strip("/") + "/"

        # Create an instance of a Dropbox class, which can make requests to the API.
        file_list = []
        with dropbox.Dropbox(
            app_key=self.app_key,
            app_secret=self.app_secret,
            oauth2_refresh_token=self.refresh_token,
        ) as dbx:
            # Check that the access token is valid
            try:
                dbx.users_get_current_account()
            except AuthError:
                sys.exit("ERROR: Invalid access token.")
            # We should really handle these exceptions cleaner, but this seems a bit
            # complicated right now
            # pylint: disable=W0703
            try:
                response = dbx.files_list_folder(path=storage_path)
                file_list = response.entries
                file_list = [item.name for item in file_list]
            except ApiError:
                print(f"Could not obtain job queue for {storage_path}")
            except Exception as err:
                print(err)
        return file_list

    @validate_active
    def get_backends(self) -> list[str]:
        """
        Get a list of all the backends that the provider offers.
        """
        backend_config_path = "/Backend_files/Config/"
        with dropbox.Dropbox(
            app_key=self.app_key,
            app_secret=self.app_secret,
            oauth2_refresh_token=self.refresh_token,
        ) as dbx:
            # Check that the access token is valid
            try:
                dbx.users_get_current_account()
            except AuthError:
                sys.exit("ERROR: Invalid access token.")

            folders_results = dbx.files_list_folder(path=backend_config_path)
            entries = folders_results.entries
            backend_names = []
            for entry in entries:
                backend_names.append(entry.name)
        return backend_names

    def get_backend_dict(self, display_name: str) -> BackendConfigSchemaOut:
        """
        The configuration of the backend.

        Args:
            display_name: The identifier of the backend

        Returns:
            The full schema of the backend.
        """
        backend_json_path = f"Backend_files/Config/{display_name}"
        backend_config_dict = self.get_file_content(
            storage_path=backend_json_path, job_id="config"
        )
        backend_config_info = BackendConfigSchemaIn(**backend_config_dict)
        qiskit_backend_dict = self.backend_dict_to_qiskit(backend_config_info)
        return qiskit_backend_dict

    def get_backend_status(self, display_name: str) -> BackendStatusSchemaOut:
        """
        Get the status of the backend. This follows the qiskit logic.

        Args:
            display_name: The name of the backend

        Returns:
            The status dict of the backend
        """
        backend_json_path = f"Backend_files/Config/{display_name}"
        backend_config_dict = self.get_file_content(
            storage_path=backend_json_path, job_id="config"
        )
        backend_config_info = BackendConfigSchemaIn(**backend_config_dict)
        qiskit_backend_dict = self.backend_dict_to_qiskit_status(backend_config_info)
        return qiskit_backend_dict

    def upload_job(self, job_dict: dict, display_name: str, username: str) -> str:
        """
        This function uploads a job to the backend and creates the job_id.

        Args:
            job_dict: The job dictionary that should be uploaded
            display_name: The name of the backend to which we want to upload the job
            username: The username of the user that is uploading the job

        Returns:
            The job_id of the uploaded job
        """
        job_id = (
            (datetime.datetime.utcnow().strftime("%Y%m%d_%H%M%S"))
            + "-"
            + display_name
            + "-"
            + username
            + "-"
            + (uuid.uuid4().hex)[:5]
        )
        # now we upload the job to the backend
        # this is currently very much backend specific
        job_json_dir = "/Backend_files/Queued_Jobs/" + display_name + "/"
        job_json_name = "job-" + job_id

        self.upload(
            content_dict=job_dict, storage_path=job_json_dir, job_id=job_json_name
        )
        return job_id

    def upload_status(self, display_name: str, username: str, job_id: str) -> dict:
        """
        This function uploads a status file to the backend and creates the status dict.

        Args:
            display_name: The name of the backend to which we want to upload the job
            username: The username of the user that is uploading the job
            job_id: The job_id of the job that we want to upload the status for

        Returns:
            The status dict of the job
        """
        status_json_dir = "Backend_files/Status/" + display_name + "/" + username
        status_json_name = "status-" + job_id
        status_dict = {
            "job_id": job_id,
            "status": "INITIALIZING",
            "detail": "Got your json.",
            "error_message": "None",
        }
        self.upload(
            content_dict=status_dict,
            storage_path=status_json_dir,
            job_id=status_json_name,
        )
        return status_dict

    def get_status(self, display_name: str, username: str, job_id: str) -> dict:
        """
        This function gets the status file from the backend and returns the status dict.

        Args:
            display_name: The name of the backend to which we want to upload the job
            username: The username of the user that is uploading the job
            job_id: The job_id of the job that we want to upload the status for

        Returns:
            The status dict of the job
        """
        status_json_dir = "Backend_files/Status/" + display_name + "/" + username
        status_json_name = "status-" + job_id

        status_dict = self.get_file_content(
            storage_path=status_json_dir, job_id=status_json_name
        )
        return status_dict

    def get_result(self, display_name: str, username: str, job_id: str) -> ResultDict:
        """
        This function gets the result file from the backend and returns the result dict.

        Args:
            display_name: The name of the backend to which we want to upload the job
            username: The username of the user that is uploading the job
            job_id: The job_id of the job that we want to upload the status for

        Returns:
            The result dict of the job
        """
        result_json_dir = "Backend_files/Result/" + display_name + "/" + username
        result_json_name = "result-" + job_id
        result_dict = self.get_file_content(
            storage_path=result_json_dir, job_id=result_json_name
        )
        backend_config_info = self.get_backend_dict(display_name)
        result_dict["backend_name"] = backend_config_info.backend_name

        typed_result = ResultDict(**result_dict)
        return typed_result

    def get_next_job_in_queue(self, backend_name: str) -> dict:
        """
        A function that obtains the next job in the queue.

        Args:
            backend_name (str): The name of the backend

        Returns:
            the path towards the job
        """
        job_json_dir = "/Backend_files/Queued_Jobs/" + backend_name + "/"
        job_dict = {"job_id": 0, "job_json_path": "None"}
        job_list = self.get_file_queue(job_json_dir)
        # if there is a job, we should move it
        if job_list:
            job_json_name = job_list[0]
            job_dict["job_id"] = job_json_name[4:-5]

            # split the .json from the job_json_name
            job_json_name = job_json_name.split(".")[0]
            # and move the file into the right directory
            self.move_file(job_json_dir, "Backend_files/Running_Jobs", job_json_name)
            job_dict["job_json_path"] = "Backend_files/Running_Jobs"
        return job_dict


class MongodbProviderExtended(StorageProvider):
    """
    The access to the mongodb
    """

    def __init__(
        self, login_dict: MongodbLoginInformation, name: str, is_active: bool = True
    ) -> None:
        """
        Set up the neccessary keys and create the client through which all the connections will run.

        Args:
            login_dict: The login dict that contains the neccessary
                        information to connect to the mongodb
            name: The name of the storage provider
            is_active: Is the storage provider active.


        Raises:
            ValidationError: If the login_dict is not valid
        """
        super().__init__(name, is_active)
        mongodb_username = login_dict.mongodb_username
        mongodb_password = login_dict.mongodb_password
        mongodb_database_url = login_dict.mongodb_database_url

        uri = f"mongodb+srv://{mongodb_username}:{mongodb_password}@{mongodb_database_url}"
        uri = uri + "/?retryWrites=true&w=majority"
        # Create a new client and connect to the server
        self.client: MongoClient = MongoClient(uri)

        # Send a ping to confirm a successful connection
        self.client.admin.command("ping")

    @validate_active
    def upload(self, content_dict: dict, storage_path: str, job_id: str) -> None:
        """
        Upload the file to the storage

        content_dict: the content that should be uploaded onto the mongodb base
        storage_path: the access path towards the mongodb collection
        job_id: the id of the file we are about to create
        """
        storage_splitted = storage_path.split("/")

        # get the database on which we work
        database = self.client[storage_splitted[0]]

        # get the collection on which we work
        collection_name = ".".join(storage_splitted[1:])
        collection = database[collection_name]

        content_dict["_id"] = ObjectId(job_id)
        collection.insert_one(content_dict)

        # remove the id from the content dict for further use
        content_dict.pop("_id", None)

    @validate_active
    def get_file_content(self, storage_path: str, job_id: str) -> dict:
        """
        Get the file content from the storage

        storage_path: the path towards the file, excluding the filename / id
        job_id: the id of the file we are about to look up
        """
        document_to_find = {"_id": ObjectId(job_id)}

        # get the database on which we work
        database = self.client[storage_path.split("/")[0]]

        # get the collection on which we work
        collection_name = ".".join(storage_path.split("/")[1:])
        collection = database[collection_name]

        result_found = collection.find_one(document_to_find)

        if not result_found:
            return {}

        # remove the id from the result dict for further use
        result_found.pop("_id", None)
        return result_found

    def get_job_content(self, storage_path: str, job_id: str) -> dict:
        """
        Get the content of the job from the storage. This is a wrapper around get_file_content
        and and handles the different ways of identifiying the job.

        storage_path: the path towards the file, excluding the filename / id
        job_id: the id of the file we are about to look up

        Returns:

        """
        job_dict = self.get_file_content(storage_path=storage_path, job_id=job_id)
        job_dict.pop("_id", None)
        return job_dict

    def update_file(self, content_dict: dict, storage_path: str, job_id: str) -> None:
        """
        Update the file content.

        Args:
            content_dict: The dictionary containing the new content of the file
            storage_path: The path to the file
            job_id: The id of the job

        Returns:
            None
        """
        # get the database on which we work
        database = self.client[storage_path.split("/")[0]]

        # get the collection on which we work
        collection_name = ".".join(storage_path.split("/")[1:])
        collection = database[collection_name]

        filter_dict = {"_id": ObjectId(job_id)}

        newvalues = {"$set": content_dict}
        collection.update_one(filter_dict, newvalues)

    @validate_active
    def move_file(self, start_path: str, final_path: str, job_id: str) -> None:
        """
        Move the file from start_path to final_path

        start_path: the path where the file is currently stored, but excluding the file name
        final_path: the path where the file should be stored, but excluding the file name
        job_id: the name of the file. Is a json file

        Returns:
            None
        """
        # get the database on which we work
        database = self.client[start_path.split("/")[0]]

        # get the collection on which we work
        collection_name = ".".join(start_path.split("/")[1:])
        collection = database[collection_name]

        document_to_find = {"_id": ObjectId(job_id)}
        result_found = collection.find_one(document_to_find)

        # delete the old file
        collection.delete_one(document_to_find)

        # add the document to the new collection
        database = self.client[final_path.split("/")[0]]
        collection_name = ".".join(final_path.split("/")[1:])
        collection = database[collection_name]
        collection.insert_one(result_found)

    @validate_active
    def delete_file(self, storage_path: str, job_id: str) -> None:
        """
        Remove the file from the mongodb database

        Args:
            storage_path: the path where the file is currently stored, but excluding the file name
            job_id: the name of the file

        Returns:
            None
        """
        # get the database on which we work
        database = self.client[storage_path.split("/")[0]]

        # get the collection on which we work
        collection_name = ".".join(storage_path.split("/")[1:])
        collection = database[collection_name]

        document_to_find = {"_id": ObjectId(job_id)}
        collection.delete_one(document_to_find)

    @validate_active
    def get_backends(self) -> list[str]:
        """
        Get a list of all the backends that the provider offers.
        """

        # get the database on which we work
        database = self.client["backends"]
        config_collection = database["configs"]
        # get all the documents in the collection configs and save the disply_name in a list
        backend_names: list[str] = []
        for config_dict in config_collection.find():
            backend_names.append(config_dict["display_name"])
        return backend_names

    @validate_active
    def get_backend_dict(self, display_name: str) -> BackendConfigSchemaOut:
        """
        The configuration dictionary of the backend such that it can be sent out to the API to
        the common user. We make sure that it is compatible with QISKIT within this function.

        Args:
            display_name: The identifier of the backend

        Returns:
            The full schema of the backend.
        """
        # get the database on which we work
        database = self.client["backends"]
        config_collection = database["configs"]

        # create the filter for the document with display_name that is equal to display_name
        document_to_find = {"display_name": display_name}
        backend_config_dict = config_collection.find_one(document_to_find)

        if not backend_config_dict:
            raise FileNotFoundError("The backend does not exist for the given storage.")

        backend_config_dict.pop("_id")
        backend_config_info = BackendConfigSchemaIn(**backend_config_dict)
        qiskit_backend_dict = self.backend_dict_to_qiskit(backend_config_info)
        return qiskit_backend_dict

    def get_backend_status(self, display_name: str) -> BackendStatusSchemaOut:
        """
        Get the status of the backend. This follows the qiskit logic.

        Args:
            display_name: The name of the backend

        Returns:
            The status dict of the backend

        Raises:
            FileNotFoundError: If the backend does not exist
        """
        # get the database on which we work
        database = self.client["backends"]
        config_collection = database["configs"]

        # create the filter for the document with display_name that is equal to display_name
        document_to_find = {"display_name": display_name}
        backend_config_dict = config_collection.find_one(document_to_find)

        if not backend_config_dict:
            raise FileNotFoundError(
                f"The backend {display_name} does not exist for the given storageprovider."
            )

        backend_config_dict.pop("_id")
        backend_config_info = BackendConfigSchemaIn(**backend_config_dict)
        qiskit_backend_dict = self.backend_dict_to_qiskit_status(backend_config_info)
        return qiskit_backend_dict

    def upload_config(
        self, config_dict: BackendConfigSchemaIn, backend_name: str
    ) -> None:
        """
        The function that uploads the spooler configuration to the storage.

        Args:
            config_dict: The dictionary containing the configuration
            backend_name (str): The name of the backend

        Returns:
            None
        """
        config_path = "backends/configs"

        # first we have to check if the device already exists in the database

        document_to_find = {"display_name": backend_name}

        # get the database on which we work
        database = self.client["backends"]

        # get the collection on which we work
        collection = database["configs"]

        result_found = collection.find_one(document_to_find)
        config_dict.display_name = backend_name
        if result_found:
            # update the file
            self.update_file(
                content_dict=config_dict.model_dump(),
                storage_path=config_path,
                job_id=result_found["_id"],
            )
            return

        # if the device does not exist, we have to create it

        config_id = uuid.uuid4().hex[:24]
        self.upload(config_dict.model_dump(), config_path, config_id)

    def upload_job(self, job_dict: dict, display_name: str, username: str) -> str:
        """
        Upload the job to the storage provider.

        Args:
            job_dict: the full job dict
            display_name: the name of the backend
            username: the name of the user that submitted the job

        Returns:
            The job id of the uploaded job.
        """

        storage_path = "jobs/queued/" + display_name
        job_id = (uuid.uuid4().hex)[:24]

        self.upload(content_dict=job_dict, storage_path=storage_path, job_id=job_id)
        return job_id

    def upload_status(self, display_name: str, username: str, job_id: str) -> dict:
        """
        This function uploads a status file to the backend and creates the status dict.

        Args:
            display_name: The name of the backend to which we want to upload the job
            username: The username of the user that is uploading the job
            job_id: The job_id of the job that we want to upload the status for

        Returns:
            The status dict of the job
        """
        storage_path = "status/" + display_name
        status_dict = {
            "job_id": job_id,
            "status": "INITIALIZING",
            "detail": "Got your json.",
            "error_message": "None",
        }

        # should we also upload the username into the dict ?

        # now upload the status dict
        self.upload(
            content_dict=status_dict,
            storage_path=storage_path,
            job_id=job_id,
        )
        return status_dict

    def get_status(self, display_name: str, username: str, job_id: str) -> dict:
        """
        This function gets the status file from the backend and returns the status dict.

        Args:
            display_name: The name of the backend to which we want to upload the job
            username: The username of the user that is uploading the job
            job_id: The job_id of the job that we want to upload the status for

        Returns:
            The status dict of the job
        """
        status_json_dir = "status/" + display_name

        status_dict = self.get_file_content(storage_path=status_json_dir, job_id=job_id)
        return status_dict

    def get_result(self, display_name: str, username: str, job_id: str) -> ResultDict:
        """
        This function gets the result file from the backend and returns the result dict.

        Args:
            display_name: The name of the backend to which we want to upload the job
            username: The username of the user that is uploading the job
            job_id: The job_id of the job that we want to upload the status for

        Returns:
            The result dict of the job
        """
        result_json_dir = "results/" + display_name
        result_dict = self.get_file_content(storage_path=result_json_dir, job_id=job_id)
        backend_config_info = self.get_backend_dict(display_name)
        result_dict["backend_name"] = backend_config_info.backend_name

        typed_result = ResultDict(**result_dict)
        return typed_result

    def update_in_database(
        self,
        result_dict: ResultDict | None,
        status_msg_dict: dict,
        job_id: str,
        backend_name: str,
    ) -> None:
        """
        Upload the status and result to the `StorageProvider`.

        The function checks if the reported status of the job has changed to DONE. If so, it will create
        a result json file and move the job json file to the finished folder. It will also update the
        status json file.

        Args:
            result_dict: the dictionary containing the result of the job
            status_msg_dict: the dictionary containing the status message of the job
            job_id: the name of the job
            backend_name: the name of the backend

        Returns:
            None

        Raises:

        """

        job_json_start_dir = "jobs/running"
        # check if the job is done or had an error
        if status_msg_dict["status"] == "DONE":
            # test if the result dict is None
            if result_dict is None:
                raise ValueError(
                    "The 'result_dict' argument cannot be None if the job is done."
                )
            # let us create the result json file
            result_json_dir = "results/" + backend_name
            self.upload(result_dict.model_dump(), result_json_dir, job_id)

            # now move the job out of the running jobs into the finished jobs
            job_finished_json_dir = "jobs/finished/" + backend_name
            self.move_file(job_json_start_dir, job_finished_json_dir, job_id)

        elif status_msg_dict["status"] == "ERROR":
            # because there was an error, we move the job to the deleted jobs
            deleted_json_dir = "jobs/deleted"
            self.move_file(job_json_start_dir, deleted_json_dir, job_id)

        # TODO: most likely we should raise an error if the status of the job is not DONE or ERROR

        # and create the status json file
        status_json_dir = "status/" + backend_name
        self.update_file(status_msg_dict, status_json_dir, job_id)

    def get_file_queue(self, storage_path: str) -> list[str]:
        """
        Get a list of documents in the collection of all the queued jobs.

        Args:
            storage_path: Where are we looking for the files.

        Returns:
            A list of files that was found.
        """
        # strip trailing and leading slashes from the paths
        storage_path = storage_path.strip("/")

        # get the database on which we work
        database = self.client[storage_path.split("/")[0]]

        # get the collection on which we work
        collection_name = ".".join(storage_path.split("/")[1:])
        collection = database[collection_name]

        # now get the id of all the documents in the collection
        results = collection.find({}, {"_id": 1})
        file_list = []
        for result in results:
            file_list.append(str(result["_id"]))
        return file_list

    def get_next_job_in_queue(self, backend_name: str) -> dict:
        """
        A function that obtains the next job in the queue. It looks in the queued folder and moves the
        first job to the running folder.

        Args:
            backend_name (str): The name of the backend

        Returns:
            the path towards the job
        """

        queue_dir = "jobs/queued/" + backend_name
        job_dict = {"job_id": 0, "job_json_path": "None"}
        job_list = self.get_file_queue(queue_dir)
        # if there is a job, we should move it
        if job_list:
            job_id = job_list[0]
            job_dict["job_id"] = job_id

            # and move the file into the right directory
            self.move_file(queue_dir, "jobs/running", job_id)
            job_dict["job_json_path"] = "jobs/running"
        return job_dict


class LocalProviderExtended(StorageProvider):
    """
    Create a file storage that works on the local machine.
    """

    def __init__(
        self, login_dict: LocalLoginInformation, name: str, is_active: bool = True
    ) -> None:
        """
        Set up the neccessary keys and create the client through which all the connections will run.

        Args:
            login_dict: The login dict that contains the neccessary
                        information to connect to the local storage
            name: The name of the storage provider
            is_active: Is the storage provider active.

        Raises:
            ValidationError: If the login_dict is not valid
        """
        super().__init__(name, is_active)
        self.base_path = login_dict.base_path

    @validate_active
    def upload(self, content_dict: Mapping, storage_path: str, job_id: str) -> None:
        """
        Upload the file to the storage
        """
        # strip trailing and leading slashes from the storage_path
        storage_path = storage_path.strip("/")

        # json folder
        folder_path = self.base_path + "/" + storage_path
        if not os.path.exists(folder_path):
            os.makedirs(folder_path)

        # create the full path
        file_name = job_id + ".json"
        full_json_path = os.path.join(folder_path, file_name)
        secure_path = os.path.normpath(full_json_path)

        with open(secure_path, "w", encoding="utf-8") as json_file:
            json.dump(content_dict, json_file)

    @validate_active
    def get_file_content(self, storage_path: str, job_id: str) -> dict:
        """
        Get the file content from the storage
        """
        # strip trailing and leading slashes from the storage_path
        storage_path = storage_path.strip("/")

        # create the full path
        file_name = job_id + ".json"
        full_json_path = os.path.join(self.base_path, storage_path, file_name)
        secure_path = os.path.normpath(full_json_path)

        with open(secure_path, "r", encoding="utf-8") as json_file:
            loaded_data_dict = json.load(json_file)
        return loaded_data_dict

    def get_job_content(self, storage_path: str, job_id: str) -> dict:
        """
        Get the content of the job from the storage. This is a wrapper around get_file_content
        and and handles the different ways of identifiying the job.

        storage_path: the path towards the file, excluding the filename / id
        job_id: the id of the file we are about to look up

        Returns:
            The content of the job
        """
        job_dict = self.get_file_content(storage_path=storage_path, job_id=job_id)
        return job_dict

    def update_file(self, content_dict: dict, storage_path: str, job_id: str) -> None:
        """
        Update the file content.

        Args:
            content_dict: The dictionary containing the new content of the file
            storage_path: The path to the file
            job_id: The id of the job

        Returns:
            None
        """
        # strip trailing and leading slashes from the storage_path
        storage_path = storage_path.strip("/")

        # json folder
        file_name = job_id + ".json"
        full_json_path = os.path.join(self.base_path, storage_path, file_name)
        secure_path = os.path.normpath(full_json_path)

        # does the file already exist ?
        if not os.path.exists(secure_path):
            raise FileNotFoundError(
                f"The file {secure_path} does not exist and cannot be updated."
            )
        with open(secure_path, "w", encoding="utf-8") as json_file:
            json.dump(content_dict, json_file)

    @validate_active
    def move_file(self, start_path: str, final_path: str, job_id: str) -> None:
        """
        Move the file from `start_path` to `final_path`
        """
        start_path = start_path.strip("/")

        source_file = self.base_path + "/" + start_path + "/" + job_id + ".json"

        final_path = self.base_path + "/" + final_path + "/"
        if not os.path.exists(final_path):
            os.makedirs(final_path)

        # Move the file
        shutil.move(source_file, final_path)

    @validate_active
    def delete_file(self, storage_path: str, job_id: str) -> None:
        """
        Delete the file from the storage

        Args:
            storage_path: the path where the file is currently stored, but excluding the file name
            job_id: the name of the file

        Returns:
            None
        """
        storage_path = storage_path.strip("/")
        source_file = self.base_path + "/" + storage_path + "/" + job_id + ".json"
        os.remove(source_file)

    @validate_active
    def get_backends(self) -> list[str]:
        """
        Get a list of all the backends that the provider offers.
        """
        # path of the configs
        config_path = self.base_path + "/backends/configs"
        backend_names: list[str] = []

        # If the folder does not exist, return an empty list
        if not os.path.exists(config_path):
            return backend_names

        # Get a list of all items in the folder
        all_items = os.listdir(config_path)
        # Filter out only the JSON files
        json_files = [item for item in all_items if item.endswith(".json")]

        for file_name in json_files:
            full_json_path = os.path.join(config_path, file_name)
            secure_path = os.path.normpath(full_json_path)

            with open(secure_path, "r", encoding="utf-8") as json_file:
                config_dict = json.load(json_file)
                backend_names.append(config_dict["display_name"])
        return backend_names

    @validate_active
    def get_backend_dict(self, display_name: str) -> BackendConfigSchemaOut:
        """
        The configuration dictionary of the backend such that it can be sent out to the API to
        the common user. We make sure that it is compatible with QISKIT within this function.

        Args:
            display_name: The identifier of the backend

        Returns:
            The full schema of the backend.

        Raises:
            FileNotFoundError: If the backend does not exist
        """
        # path of the configs
        config_path = self.base_path + "/backends/configs"
        file_name = display_name + ".json"
        full_json_path = os.path.join(config_path, file_name)
        secure_path = os.path.normpath(full_json_path)
        with open(secure_path, "r", encoding="utf-8") as json_file:
            backend_config_dict = json.load(json_file)

        if not backend_config_dict:
            raise FileNotFoundError("The backend does not exist for the given storage.")

        backend_config_info = BackendConfigSchemaIn(**backend_config_dict)
        qiskit_backend_dict = self.backend_dict_to_qiskit(backend_config_info)
        return qiskit_backend_dict

    def get_backend_status(self, display_name: str) -> BackendStatusSchemaOut:
        """
        Get the status of the backend. This follows the qiskit logic.

        Args:
            display_name: The name of the backend

        Returns:
            The status dict of the backend

        Raises:
            FileNotFoundError: If the backend does not exist
        """
        # path of the configs
        file_name = display_name + ".json"
        config_path = self.base_path + "/backends/configs"
        full_json_path = os.path.join(config_path, file_name)
        secure_path = os.path.normpath(full_json_path)
        with open(secure_path, "r", encoding="utf-8") as json_file:
            backend_config_dict = json.load(json_file)

        if not backend_config_dict:
            raise FileNotFoundError(
                f"The backend {display_name} does not exist for the given storageprovider."
            )

        backend_config_info = BackendConfigSchemaIn(**backend_config_dict)
        qiskit_backend_dict = self.backend_dict_to_qiskit_status(backend_config_info)
        return qiskit_backend_dict

    def upload_job(self, job_dict: dict, display_name: str, username: str) -> str:
        """
        Upload the job to the storage provider.

        Args:
            job_dict: the full job dict
            display_name: the name of the backend
            username: the name of the user that submitted the job

        Returns:
            The job id of the uploaded job.
        """

        storage_path = "jobs/queued/" + display_name
        job_id = (uuid.uuid4().hex)[:24]

        self.upload(content_dict=job_dict, storage_path=storage_path, job_id=job_id)
        return job_id

    def upload_status(self, display_name: str, username: str, job_id: str) -> dict:
        """
        This function uploads a status file to the backend and creates the status dict.

        Args:
            display_name: The name of the backend to which we want to upload the job
            username: The username of the user that is uploading the job
            job_id: The job_id of the job that we want to upload the status for

        Returns:
            The status dict of the job
        """
        storage_path = "status/" + display_name
        status_dict = {
            "job_id": job_id,
            "status": "INITIALIZING",
            "detail": "Got your json.",
            "error_message": "None",
        }

        # should we also upload the username into the dict ?

        # now upload the status dict
        self.upload(
            content_dict=status_dict,
            storage_path=storage_path,
            job_id=job_id,
        )
        return status_dict

    def get_status(self, display_name: str, username: str, job_id: str) -> dict:
        """
        This function gets the status file from the backend and returns the status dict.

        Args:
            display_name: The name of the backend to which we want to upload the job
            username: The username of the user that is uploading the job
            job_id: The job_id of the job that we want to upload the status for

        Returns:
            The status dict of the job
        """
        status_json_dir = "status/" + display_name

        status_dict = self.get_file_content(storage_path=status_json_dir, job_id=job_id)
        return status_dict

    def get_result(self, display_name: str, username: str, job_id: str) -> ResultDict:
        """
        This function gets the result file from the backend and returns the result dict.

        Args:
            display_name: The name of the backend to which we want to upload the job
            username: The username of the user that is uploading the job
            job_id: The job_id of the job that we want to upload the status for

        Returns:
            The result dict of the job
        """
        result_json_dir = "results/" + display_name
        result_dict = self.get_file_content(storage_path=result_json_dir, job_id=job_id)

        backend_config_info = self.get_backend_dict(display_name)
        result_dict["backend_name"] = backend_config_info.backend_name
        typed_result = ResultDict(**result_dict)
        return typed_result

    def upload_config(
        self, config_dict: BackendConfigSchemaIn, backend_name: str
    ) -> None:
        """
        The function that uploads the spooler configuration to the storage.

        Args:
            config_dict: The dictionary containing the configuration
            backend_name (str): The name of the backend

        Returns:
            None
        """
        # path of the configs
        config_path = os.path.join(self.base_path, "backends/configs")
        config_path = os.path.normpath(os.path.join(self.base_path, "backends/configs"))
        # test if the config path already exists. If it does not, create it
        if not os.path.exists(config_path):
            os.makedirs(config_path)

        file_name = backend_name + ".json"
        full_json_path = os.path.join(config_path, file_name)
        secure_path = os.path.normpath(full_json_path)
        with open(secure_path, "w", encoding="utf-8") as json_file:
            json.dump(config_dict.model_dump(), json_file)

    def update_in_database(
        self,
        result_dict: ResultDict,
        status_msg_dict: dict,
        job_id: str,
        backend_name: str,
    ) -> None:
        """
        Upload the status and result to the `StorageProvider`.

        Args:
            result_dict: the dictionary containing the result of the job
            status_msg_dict: the dictionary containing the status message of the job
            job_id: the name of the job
            backend_name: the name of the backend

        Returns:
            None
        """
        job_json_start_dir = "jobs/running"
        # check if the job is done or had an error
        if status_msg_dict["status"] == "DONE":
            # test if the result dict is None
            if result_dict is None:
                raise ValueError(
                    "The 'result_dict' argument cannot be None if the job is done."
                )
            # let us create the result json file
            result_json_dir = "results/" + backend_name
            self.upload(result_dict.model_dump(), result_json_dir, job_id)

            # now move the job out of the running jobs into the finished jobs
            job_finished_json_dir = "jobs/finished/" + backend_name
            self.move_file(job_json_start_dir, job_finished_json_dir, job_id)

        elif status_msg_dict["status"] == "ERROR":
            # because there was an error, we move the job to the deleted jobs
            deleted_json_dir = "jobs/deleted"
            self.move_file(job_json_start_dir, deleted_json_dir, job_id)

        # and create the status json file
        status_json_dir = "status/" + backend_name
        self.update_file(status_msg_dict, status_json_dir, job_id)

    def get_file_queue(self, storage_path: str) -> list[str]:
        """
        Get a list of files

        Args:
            storage_path: Where are we looking for the files.

        Returns:
            A list of files that was found.
        """
        # get a list of files in the folder
        full_path = self.base_path + "/" + storage_path
        # test if the path exists. Otherwise simply return an empty list
        if not os.path.exists(full_path):
            return []
        return os.listdir(full_path)

    def get_next_job_in_queue(self, backend_name: str) -> dict:
        """
        A function that obtains the next job in the queue.

        Args:
            backend_name: The name of the backend

        Returns:
            the path towards the job
        """
        queue_dir = "jobs/queued/" + backend_name
        job_dict = {"job_id": 0, "job_json_path": "None"}
        job_list = self.get_file_queue(queue_dir)
        # if there is a job, we should move it
        if job_list:
            job_json_name = job_list[0]
            job_id = job_json_name[:-5]
            job_dict["job_id"] = job_id

            # and move the file into the right directory
            self.move_file(queue_dir, "jobs/running", job_id)
            job_dict["job_json_path"] = "jobs/running"
        return job_dict


class LocalProvider(LocalProviderExtended):
    """
    Create a file storage that works on the local machine.
    """

    def __init__(self, login_dict: LocalLoginInformation) -> None:
        """
        Set up the neccessary keys and create the client through which all the connections will run.
        """
        super().__init__(login_dict, name="default", is_active=True)


class MongodbProvider(MongodbProviderExtended):
    """
    The access to the mongodb. This is the simplified version for people that are running devices.
    """

    def __init__(self, login_dict: MongodbLoginInformation) -> None:
        """
        Set up the neccessary keys and create the client through which all the connections will run.
        """
        super().__init__(login_dict, name="default", is_active=True)


class DropboxProvider(DropboxProviderExtended):
    """
    The class that implements the dropbox storage provider.
    """

    def __init__(self, login_dict: DropboxLoginInformation) -> None:
        """
        Args:
            login_dict: The dictionary that contains the login information
            name: The name of the storage provider
            is_active: Is the storage provider active.
        """

        super().__init__(login_dict, name="default", is_active=True)
