"""
The module that contains all the necessary logic for communication with the external
storage for the jobs. It creates an abstract API layer for the storage providers.
"""

from abc import ABC, abstractmethod
import re

from typing import Mapping, Callable, Any
import functools

from ..schemes import (
    ResultDict,
    StatusMsgDict,
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

        # transform the name to lowercase
        name = name.lower()

        # make sure that the name only contains alphanumeric characters
        if not re.match("^[a-z0-9]+$", name):
            raise ValueError(
                "The name of the storage provider can only contain lowercase alphanumeric characters."
            )
        self.name = name
        self.is_active = is_active

    @abstractmethod
    def upload(self, content_dict: Mapping, storage_path: str, job_id: str) -> None:
        """
        Upload the file to the storage.

        Args:
            content_dict: The dictionary containing the content of the file
            storage_path: The path to the file
            job_id: The id of the job
        """

    @abstractmethod
    def get_file_content(self, storage_path: str, job_id: str) -> dict:
        """
        Get the file content from the storage.

        Args:
            storage_path: The path to the file
            job_id: The id of the job

        Returns:
            The content of the file

        Raises:
            FileNotFoundError: If the file is not found
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
    def upload_status(
        self, display_name: str, username: str, job_id: str
    ) -> StatusMsgDict:
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
    def get_status(
        self, display_name: str, username: str, job_id: str
    ) -> StatusMsgDict:
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
            The result dict of the job. If the information is not available, the result dict
            has a status of "ERROR".
        """

    @abstractmethod
    def update_file(self, content_dict: dict, storage_path: str, job_id: str) -> None:
        """
        Update the file content. It replaces the old content with the new content.

        Args:
            content_dict: The dictionary containing the new content of the file
            storage_path: The path to the file
            job_id: The id of the job

        Returns:
            None

        Raises:
            FileNotFoundError: If the file is not found
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
        status_msg_dict: StatusMsgDict,
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
        backend_name = self.long_backend_name(
            display_name, backend_config_dict["simulator"]
        )

        backend_config_dict["backend_name"] = backend_name
        backend_config_dict["n_qubits"] = backend_config_dict["num_wires"]
        backend_config_dict["backend_version"] = backend_config_dict["version"]

        backend_config_dict["conditional"] = False
        backend_config_dict["local"] = False
        backend_config_dict["open_pulse"] = False
        backend_config_dict["memory"] = True
        backend_config_dict["coupling_map"] = "linear"
        return BackendConfigSchemaOut(**backend_config_dict)

    def long_backend_name(self, display_name: str, simulator: bool) -> str:
        """
        This function returns the long name of the backend.

        Args:
            display_name: The name of the backend
            simulator: True if the backend is a simulator

        Returns:
            The long name of the backend
        """
        if simulator:
            return f"{self.name}_{display_name}_simulator"
        return f"{self.name}_{display_name}_hardware"

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
