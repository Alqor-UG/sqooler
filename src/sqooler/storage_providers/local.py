"""
The module that contains all the necessary logic for communication with the local storage providers.
"""

import json
import logging
import os

# necessary for the local provider
import shutil
import uuid
from typing import Mapping, Optional

from ..schemes import (
    BackendConfigSchemaIn,
    DisplayNameStr,
    LocalLoginInformation,
    NextJobSchema,
    PathStr,
    ResultDict,
    StatusMsgDict,
)
from ..security import JWK, JWSDict
from .base import StorageCore, StorageProvider, datetime_handler, validate_active


class LocalCore(StorageCore):
    """
    Base class that creates the most important functions for the local storage provider.
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

        Args:
            content_dict: The dictionary containing the content of the file
            storage_path: The path to the file
            job_id: The id of the job
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
            json.dump(content_dict, json_file, default=datetime_handler)

    @validate_active
    def get(self, storage_path: str, job_id: str) -> dict:
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

    @validate_active
    def update(self, content_dict: dict, storage_path: str, job_id: str) -> None:
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
    def move(self, start_path: str, final_path: str, job_id: str) -> None:
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
    def delete(self, storage_path: str, job_id: str) -> None:
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


class LocalProviderExtended(StorageProvider, LocalCore):
    """
    Create a file storage that works on the local machine.

    Attributes:
        configs_path: The path to the folder where the configurations are stored
        queue_path: The path to the folder where the jobs are stored
        running_path: The path to the folder where the running jobs are stored
        finished_path: The path to the folder where the finished jobs are stored
        deleted_path: The path to the folder where the deleted jobs are stored
        status_path: The path to the folder where the status is stored
        results_path: The path to the folder where the results are stored
        pks_path: The path to the folder where the public keys are stored
    """

    configs_path: PathStr = "backends/configs"
    queue_path: PathStr = "jobs/queued"
    running_path: PathStr = "jobs/running"
    finished_path: PathStr = "jobs/finished"
    deleted_path: PathStr = "jobs/deleted"
    status_path: PathStr = "status"
    results_path: PathStr = "results"
    pks_path: PathStr = "backends/public_keys"

    def get_internal_job_id(self, job_id: str) -> str:
        """
        Get the internal job id from the job_id.

        Args:
            job_id: The job_id of the job

        Returns:
            The internal job id
        """
        return job_id

    def get_backends(self) -> list[DisplayNameStr]:
        """
        Get a list of all the backends that the provider offers.
        """
        return self.get_file_queue(self.configs_path)

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

        storage_path = f"{self.queue_path}/{display_name}"
        job_id = (uuid.uuid4().hex)[:24]

        self.upload(content_dict=job_dict, storage_path=storage_path, job_id=job_id)
        return job_id

    def get_device_status_path(
        self, display_name: DisplayNameStr, username: Optional[str] = None
    ) -> str:
        """
        Get the path to the status of the device.

        Args:
            display_name: The name of the backend
            username: The username of the user

        Returns:
            The path to the status of the device.
        """
        return f"{self.status_path}/{display_name}"

    def get_status_id(self, job_id: str) -> str:
        """
        Get the name of the status json file.

        Args:
            job_id: The job_id of the job

        Returns:
            The name of the status json file.
        """
        return job_id

    def _delete_status(
        self, display_name: DisplayNameStr, username: str, job_id: str
    ) -> bool:
        """
        Delete a status from the storage. This is only intended for test purposes.

        Args:
            display_name: The name of the backend to which we want to upload the job
            username: The username of the user that is uploading the job
            job_id: The job_id of the job that we want to upload the status for

        Raises:
            FileNotFoundError: If the status does not exist.

        Returns:
            Success if the file was deleted successfully
        """
        status_json_dir = self.get_device_status_path(display_name)

        self.delete(storage_path=status_json_dir, job_id=job_id)
        return True

    def upload_result(
        self,
        result_dict: ResultDict,
        display_name: DisplayNameStr,
        job_id: str,
        private_jwk: Optional[JWK] = None,
    ) -> bool:
        """
        This function allows us to upload the result file .

        Args:
            result_dict: The result dictionary
            display_name: The name of the backend to which we want to upload the job
            job_id: The job_id of the job that we want to upload the status for
            private_jwk: The private key of the backend

        Returns:
            The success of the upload process
        """
        result_json_dir = f"{self.results_path}/{display_name}"

        return self._common_upload_result(
            result_dict,
            display_name,
            job_id,
            result_json_dir,
            result_json_name=job_id,
            private_jwk=private_jwk,
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

        result_json_dir = f"{self.results_path}/{display_name}"
        try:
            result_dict = self.get(storage_path=result_json_dir, job_id=job_id)
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

    def verify_result(self, display_name: DisplayNameStr, job_id: str) -> bool:
        """
        This function verifies the result and returns the success. If the backend does not sign the
        result, we will reutrn `False` by default, given that we were not able to establish ownership.

        Args:
            display_name: The name of the backend to which we want to upload the job
            job_id: The job_id of the job that we want to upload the status for

        Returns:
            If it was possible to verify the result dict positively.
        """

        result_json_dir = f"{self.results_path}/{display_name}"
        result_dict = self.get(storage_path=result_json_dir, job_id=job_id)
        public_jwk = self.get_public_key(display_name)

        result_jws = JWSDict(**result_dict)
        return result_jws.verify_signature(public_jwk)

    def _delete_result(self, display_name: DisplayNameStr, job_id: str) -> bool:
        """
        Delete a result from the storage. This is only intended for test purposes.

        Args:
            display_name: The name of the backend to which we want to upload the job
            username: The username of the user that is uploading the job
            job_id: The job_id of the job that we want to upload the status for

        Raises:
            FileNotFoundError: If the result does not exist.

        Returns:
            Success if the file was deleted successfully
        """

        result_json_dir = f"{self.results_path}/{display_name}"
        self.delete(storage_path=result_json_dir, job_id=job_id)
        return True

    def update_config(
        self,
        config_dict: BackendConfigSchemaIn,
        display_name: DisplayNameStr,
        private_jwk: Optional[JWK] = None,
    ) -> None:
        """
        The function that updates the spooler configuration on the storage.

        Args:
            config_dict: The dictionary containing the configuration
            display_name : The name of the backend
            private_jwk: The private key of the backend

        Returns:
            None
        """

        config_dict = self._verify_config(config_dict, display_name)
        # path of the configs
        config_path = os.path.join(self.base_path, self.configs_path)
        config_path = os.path.normpath(config_path)

        file_name = display_name + ".json"
        full_json_path = os.path.join(config_path, file_name)
        secure_path = os.path.normpath(full_json_path)

        # check if the file already exists
        if not os.path.exists(secure_path):
            raise FileNotFoundError(
                (
                    f"The file {secure_path} does not exist and should not be updated."
                    "Use the upload_config method instead."
                )
            )

        # now read the old config
        with open(secure_path, "r", encoding="utf-8") as json_file:
            old_config_jws = json.load(json_file)

        upload_dict = self._format_update_config(
            old_config_jws, config_dict, private_jwk
        )
        # maybe this should rather become the update method
        self.upload(
            content_dict=upload_dict,
            storage_path=self.configs_path,
            job_id=display_name,
        )

    def upload_config(
        self,
        config_dict: BackendConfigSchemaIn,
        display_name: DisplayNameStr,
        private_jwk: Optional[JWK] = None,
    ) -> None:
        """
        The function that uploads the spooler configuration to the storage.

        Args:
            config_dict: The dictionary containing the configuration
            display_name : The name of the backend
            private_jwk: The private key of the backend

        Returns:
            None
        """
        config_dict = self._verify_config(config_dict, display_name)

        # path of the configs
        config_path = os.path.join(self.base_path, self.configs_path)
        config_path = os.path.normpath(config_path)
        # test if the config path already exists. If it does not, create it
        if not os.path.exists(config_path):
            os.makedirs(config_path)

        file_name = display_name + ".json"
        full_json_path = os.path.join(config_path, file_name)
        secure_path = os.path.normpath(full_json_path)

        # check if the file already exists
        if os.path.exists(secure_path):
            raise FileExistsError(
                f"The file {secure_path} already exists and should not be overwritten."
            )

        upload_dict = self._format_config_dict(config_dict, private_jwk)
        self.upload(
            content_dict=upload_dict,
            storage_path=self.configs_path,
            job_id=display_name,
        )

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
        backend_config_dict = self.get(self.configs_path, job_id=display_name)
        typed_config = self._adapt_get_config(backend_config_dict)
        return typed_config

    def _delete_config(self, display_name: DisplayNameStr) -> bool:
        """
        Delete a config from the storage. This is only intended for test purposes.

        Args:
            display_name: The name of the backend to which we want to upload the job

        Raises:
            FileNotFoundError: If the status does not exist.

        Returns:
            Success if the file was deleted successfully
        """

        self.delete(storage_path=self.configs_path, job_id=display_name)
        return True

    def upload_public_key(self, public_jwk: JWK, display_name: DisplayNameStr) -> None:
        """
        The function that uploads the spooler public JWK to the storage. It should
        only be used after `upload_config` as the kid is set there.

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

        # make sure that the key has the correct kid
        config_dict = self.get_config(display_name)
        if public_jwk.kid != config_dict.kid:
            raise ValueError("The key does not have the correct kid.")

        # path of the public keys
        key_path = os.path.join(self.base_path, self.pks_path)
        key_path = os.path.normpath(key_path)
        # test if the config path already exists. If it does not, create it
        if not os.path.exists(key_path):
            os.makedirs(key_path)

        # this should most likely depend on the kid at some point
        file_name = f"{public_jwk.kid}.json"
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

        # first we have to get the kid
        config_info = self.get_config(display_name)

        # path of the configs
        key_path = os.path.join(self.base_path, self.pks_path)
        file_name = f"{config_info.kid}.json"
        full_json_path = os.path.join(key_path, file_name)
        secure_path = os.path.normpath(full_json_path)
        with open(secure_path, "r", encoding="utf-8") as json_file:
            public_key_dict = json.load(json_file)

        if not public_key_dict:
            raise FileNotFoundError("The backend does not exist for the given storage.")

        return JWK(**public_key_dict)

    def _delete_public_key(self, kid: str) -> bool:
        """
        Delete a public key from the storage. This is only intended for test purposes.

        Args:
            kid: The key id of the public key

        Raises:
            FileNotFoundError: If the status does not exist.

        Returns:
            Success if the file was deleted successfully
        """
        self.delete(storage_path=self.pks_path, job_id=kid)
        return True

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
        job_json_start_dir = self.running_path
        # check if the job is done or had an error
        if status_msg_dict.status == "DONE":
            # test if the result dict is None
            if result_dict is None:
                raise ValueError(
                    "The 'result_dict' argument cannot be None if the job is done."
                )
            result_uploaded = self.upload_result(
                result_dict, display_name, job_id, private_jwk
            )
            if not result_uploaded:
                raise ValueError("The result was not uploaded successfully.")

            # now move the job out of the running jobs into the finished jobs
            job_finished_json_dir = f"{self.finished_path}/{display_name}"

            self.move(job_json_start_dir, job_finished_json_dir, job_id)

        elif status_msg_dict.status == "ERROR":
            # because there was an error, we move the job to the deleted jobs
            self.move(job_json_start_dir, self.deleted_path, job_id)

        # and create the status json file
        status_json_dir = self.get_device_status_path(display_name)
        try:
            self.update(status_msg_dict.model_dump(), status_json_dir, job_id)
        except FileNotFoundError:
            logging.warning(
                "The status file was missing for %s with job_id %s was missing.",
                display_name,
                job_id,
            )
            self.upload_status(display_name, "", job_id)
            self.update(status_msg_dict.model_dump(), status_json_dir, job_id)

    def get_file_queue(self, storage_path: str) -> list[str]:
        """
        Get a list of files. Only json files are considered. And the ending of
        the file is removed.

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

        all_items = os.listdir(full_path)
        # Filter out only the JSON files
        json_files = [item for item in all_items if item.endswith(".json")]

        # Get the backend names
        names = [os.path.splitext(file_name)[0] for file_name in json_files]

        return names

    def get_next_job_in_queue(
        self, display_name: str, private_jwk: Optional[JWK] = None
    ) -> NextJobSchema:
        """
        A function that obtains the next job in the queue.

        Args:
            display_name: The name of the backend
            private_jwk: The private key of the backend

        Returns:
            the dict of the next job
        """
        queue_dir = f"{self.queue_path}/{display_name}"

        job_dict = self._get_default_next_schema_dict()
        job_list = self.get_file_queue(queue_dir)

        # update the time stamp of the last job
        self.timestamp_queue(display_name, private_jwk)

        # if there is a job, we should move it
        if job_list:
            job_id = job_list[0]
            job_dict["job_id"] = job_id

            # and move the file into the right directory
            self.move(queue_dir, self.running_path, job_id)
            job_dict["job_json_path"] = self.running_path
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
