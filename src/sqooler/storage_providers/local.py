"""
The module that contains all the necessary logic for communication with the local storage providers.
"""

import uuid
import json

from typing import Mapping, Optional

# necessary for the local provider
import shutil
import os

from ..schemes import (
    ResultDict,
    StatusMsgDict,
    LocalLoginInformation,
    BackendStatusSchemaOut,
    BackendConfigSchemaIn,
    NextJobSchema,
    DisplayNameStr,
)

from .base import StorageProvider, validate_active
from ..security import JWK, sign_payload


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

        # does the file already exist ?
        if not os.path.exists(secure_path):
            raise FileNotFoundError(
                f"The file {secure_path} does not exist and cannot be loaded."
            )
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

        Raises:
            FileNotFoundError: If the file is not found
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

        Raises:
            FileNotFoundError: If the file is not found

        Returns:
            None
        """
        storage_path = storage_path.strip("/")
        source_file = self.base_path + "/" + storage_path + "/" + job_id + ".json"
        os.remove(source_file)

    @validate_active
    def get_backends(self) -> list[DisplayNameStr]:
        """
        Get a list of all the backends that the provider offers.
        """
        # path of the configs
        config_path = self.base_path + "/backends/configs"
        backend_names: list[DisplayNameStr] = []

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

    def get_backend_status(
        self, display_name: DisplayNameStr
    ) -> BackendStatusSchemaOut:
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

    def upload_job(
        self, job_dict: dict, display_name: DisplayNameStr, username: str
    ) -> str:
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

    def upload_status(
        self, display_name: DisplayNameStr, username: str, job_id: str
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
        storage_path = "status/" + display_name
        status_draft = {
            "job_id": job_id,
            "status": "INITIALIZING",
            "detail": "Got your json.",
            "error_message": "None",
        }

        # should we also upload the username into the dict ?
        status_dict = StatusMsgDict(**status_draft)
        # now upload the status dict
        self.upload(
            content_dict=status_dict.model_dump(),
            storage_path=storage_path,
            job_id=job_id,
        )
        return status_dict

    def get_status(
        self, display_name: DisplayNameStr, username: str, job_id: str
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
        status_json_dir = "status/" + display_name

        try:
            status_dict = self.get_file_content(
                storage_path=status_json_dir, job_id=job_id
            )
            return StatusMsgDict(**status_dict)
        except FileNotFoundError:
            # if the job_id is not valid, we return an error
            return StatusMsgDict(
                job_id=job_id,
                status="ERROR",
                detail="Cannot get status",
                error_message=f"Could not find status for {display_name} with job_id {job_id}.",
            )

    def get_result(
        self, display_name: DisplayNameStr, username: str, job_id: str
    ) -> ResultDict:
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

        try:
            backend_config_info = self.get_backend_dict(display_name)
        except FileNotFoundError:
            # if the backend does not exist, we return an error
            return ResultDict(
                display_name="",
                backend_version="",
                job_id=job_id,
                qobj_id=None,
                success=False,
                status="ERROR",
                header={},
                results=[],
            )

        result_json_dir = "results/" + display_name
        try:
            result_dict = self.get_file_content(
                storage_path=result_json_dir, job_id=job_id
            )
        except FileNotFoundError:
            # if the job_id is not valid, we return an error
            return ResultDict(
                display_name=display_name,
                backend_version="",
                job_id=job_id,
                qobj_id=None,
                success=False,
                status="ERROR",
                header={},
                results=[],
            )
        return self._adapt_result_dict(result_dict, backend_config_info)

    def upload_config(
        self, config_dict: BackendConfigSchemaIn, display_name: DisplayNameStr
    ) -> None:
        """
        The function that uploads the spooler configuration to the storage.

        Args:
            config_dict: The dictionary containing the configuration
            display_name : The name of the backend

        Returns:
            None
        """
        # path of the configs
        config_path = os.path.join(self.base_path, "backends/configs")
        config_path = os.path.normpath(config_path)
        # test if the config path already exists. If it does not, create it
        if not os.path.exists(config_path):
            os.makedirs(config_path)

        file_name = display_name + ".json"
        full_json_path = os.path.join(config_path, file_name)
        secure_path = os.path.normpath(full_json_path)
        with open(secure_path, "w", encoding="utf-8") as json_file:
            json_file.write(config_dict.model_dump_json())

    def get_config(self, display_name: DisplayNameStr) -> BackendConfigSchemaIn:
        """
        The function that downloads the spooler configuration to the storage.

        Args:
            display_name : The name of the backend

        Raises:
            FileNotFoundError: If the backend does not exist

        Returns:
            The configuration of the backend in complete form.
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

        return BackendConfigSchemaIn(**backend_config_dict)

    def upload_public_key(self, public_jwk: JWK, display_name: DisplayNameStr) -> None:
        """
        The function that uploads the spooler public JWK to the storage.

        Args:
            public_jwk: The JWK that contains the public key
            display_name : The name of the backend

        Returns:
            None
        """
        # first make sure that the public key is intended for verification
        if not public_jwk.key_ops == "verify":
            raise ValueError("The key is not intended for verification")

        # make sure that the key does not contain a private key
        if public_jwk.d is not None:
            raise ValueError("The key contains a private key")

        # path of the public keys
        key_path = os.path.join(self.base_path, "backends/public_keys")
        key_path = os.path.normpath(key_path)
        # test if the config path already exists. If it does not, create it
        if not os.path.exists(key_path):
            os.makedirs(key_path)

        # this should most likely depend on the kid at some point
        file_name = display_name + ".json"
        full_json_path = os.path.join(key_path, file_name)
        secure_path = os.path.normpath(full_json_path)
        with open(secure_path, "w", encoding="utf-8") as json_file:
            json_file.write(public_jwk.model_dump_json())

    def get_public_key(self, display_name: DisplayNameStr) -> JWK:
        """
        The function that gets the spooler public JWK for the device.

        Args:
            display_name : The name of the backend

        Returns:
            JWk : The public JWK object
        """

        # path of the configs
        key_path = os.path.join(self.base_path, "backends/public_keys")
        file_name = display_name + ".json"
        full_json_path = os.path.join(key_path, file_name)
        secure_path = os.path.normpath(full_json_path)
        with open(secure_path, "r", encoding="utf-8") as json_file:
            public_key_dict = json.load(json_file)

        if not public_key_dict:
            raise FileNotFoundError("The backend does not exist for the given storage.")

        return JWK(**public_key_dict)

    def update_in_database(
        self,
        result_dict: ResultDict,
        status_msg_dict: StatusMsgDict,
        job_id: str,
        display_name: DisplayNameStr,
        private_jwk: Optional[JWK] = None,
    ) -> None:
        """
        Upload the status and result to the `StorageProvider`.

        Args:
            result_dict: the dictionary containing the result of the job
            status_msg_dict: the dictionary containing the status message of the job
            job_id: the name of the job
            display_name: the name of the backend
            private_jwk: the private key of the backend

        Returns:
            None
        """
        job_json_start_dir = "jobs/running"
        # check if the job is done or had an error
        if status_msg_dict.status == "DONE":
            # test if the result dict is None
            if result_dict is None:
                raise ValueError(
                    "The 'result_dict' argument cannot be None if the job is done."
                )
            # let us create the result json file
            result_json_dir = "results/" + display_name

            # let us see if we should sign the result
            backend_config = self.get_config(display_name)
            if backend_config.sign:
                # get the private key
                if private_jwk is None:
                    raise ValueError(
                        "The private key is not given, but the backend is configured to sign."
                    )
                # we should sign the result
                signed_result = sign_payload(result_dict.model_dump(), private_jwk)
                self.upload(signed_result.model_dump(), result_json_dir, job_id)
            else:
                self.upload(result_dict.model_dump(), result_json_dir, job_id)

            # now move the job out of the running jobs into the finished jobs
            job_finished_json_dir = "jobs/finished/" + display_name

            self.move_file(job_json_start_dir, job_finished_json_dir, job_id)

        elif status_msg_dict.status == "ERROR":
            # because there was an error, we move the job to the deleted jobs
            deleted_json_dir = "jobs/deleted"
            self.move_file(job_json_start_dir, deleted_json_dir, job_id)

        # and create the status json file
        status_json_dir = "status/" + display_name
        self.update_file(status_msg_dict.model_dump(), status_json_dir, job_id)

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

    def get_next_job_in_queue(self, display_name: str) -> NextJobSchema:
        """
        A function that obtains the next job in the queue.

        Args:
            display_name: The name of the backend

        Returns:
            the dict of the next job
        """
        queue_dir = "jobs/queued/" + display_name
        job_dict = {"job_id": 0, "job_json_path": "None"}
        job_list = self.get_file_queue(queue_dir)

        # update the time stamp of the last job
        self.timestamp_queue(display_name)

        # if there is a job, we should move it
        if job_list:
            job_json_name = job_list[0]
            job_id = job_json_name[:-5]
            job_dict["job_id"] = job_id

            # and move the file into the right directory
            self.move_file(queue_dir, "jobs/running", job_id)
            job_dict["job_json_path"] = "jobs/running"
        return NextJobSchema(**job_dict)


class LocalProvider(LocalProviderExtended):
    """
    Create a file storage that works on the local machine.
    """

    def __init__(self, login_dict: LocalLoginInformation) -> None:
        """
        Set up the neccessary keys and create the client through which all the connections will run.
        """
        super().__init__(login_dict, name="default", is_active=True)
