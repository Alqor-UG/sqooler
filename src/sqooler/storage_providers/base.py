"""
The module that contains all the necessary logic for communication with the external
storage for the jobs. It creates an abstract API layer for the storage providers.
"""

import functools
import logging
import re
import warnings
from abc import ABC, abstractmethod
from datetime import datetime, timezone
from typing import Any, Callable, Mapping, Optional

from decouple import config

from ..schemes import (
    BackendConfigSchemaIn,
    BackendConfigSchemaOut,
    BackendNameStr,
    BackendStatusSchemaOut,
    DisplayNameStr,
    NextJobSchema,
    ResultDict,
    StatusMsgDict,
)
from ..security import JWK, sign_payload


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


class StorageCore(ABC):
    """
    A base class that is necessary to manipulate files in a consistent way."""

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

    def upload_file(
        self, content_dict: Mapping, storage_path: str, job_id: str
    ) -> None:
        """
        Depreceated function. Use `upload` instead.
        """
        warnings.warn(
            "`upload_file` is depreceated. Use `upload` instead.", DeprecationWarning
        )
        self.upload(content_dict, storage_path, job_id)

    @abstractmethod
    def get(self, storage_path: str, job_id: str) -> dict:
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

    def get_file_content(self, storage_path: str, job_id: str) -> dict:
        """
        Depreceated function. Use `get` instead.
        """
        warnings.warn(
            "`get_file_content` is depreceated. Use `get` instead.", DeprecationWarning
        )
        return self.get(storage_path, job_id)

    @abstractmethod
    def update(self, content_dict: dict, storage_path: str, job_id: str) -> None:
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

    def update_file(self, content_dict: dict, storage_path: str, job_id: str) -> None:
        """
        Depreceated function. Use `update` instead.
        """
        warnings.warn(
            "`update_file` is depreceated. Use `update` instead.", DeprecationWarning
        )
        self.update(content_dict, storage_path, job_id)

    @abstractmethod
    def move(self, start_path: str, final_path: str, job_id: str) -> None:
        """
        Move the file from `start_path` to `final_path`

        Args:
            start_path: The orginal path to the file
            final_path: The targe path for the file
            job_id: The id of the job
        """

    def move_file(self, start_path: str, final_path: str, job_id: str) -> None:
        """
        Depreceated function. Use `move` instead.
        """
        warnings.warn(
            "`move_file` is depreceated. Use `move` instead.", DeprecationWarning
        )
        self.move(start_path, final_path, job_id)

    @abstractmethod
    def delete(self, storage_path: str, job_id: str) -> None:
        """
        Delete the file from the storage

        Args:
            storage_path: The path to the file
            job_id: The id of the job

        Raises:
            FileNotFoundError: If the file is not found

        Returns:
            None
        """

    def delete_file(self, storage_path: str, job_id: str) -> None:
        """
        Depreceated function. Use `delete` instead.
        """
        warnings.warn(
            "`delete_file` is depreceated. Use `delete` instead.", DeprecationWarning
        )
        self.delete(storage_path, job_id)


class StorageProvider(StorageCore):
    """
    The template for accessing any storage providers like dropbox, mongodb, amazon S3 etc.
    """

    @abstractmethod
    def get_backends(self) -> list[str]:
        """
        Get a list of all the backends that the provider offers.
        """

    @validate_active
    def get_backend_dict(self, display_name: DisplayNameStr) -> BackendConfigSchemaOut:
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
        backend_config_info = self.get_config(display_name)
        qiskit_backend_dict = self.backend_dict_to_qiskit(backend_config_info)
        return qiskit_backend_dict

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
        backend_config_info = self.get_config(display_name)

        # now see how long it has been since the last queue check in minutes
        # if it is more than 5 minutes, we should set the backend to not operational

        qiskit_backend_dict = self.backend_dict_to_qiskit_status(backend_config_info)
        return qiskit_backend_dict

    @abstractmethod
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

    @abstractmethod
    def get_job(self, storage_path: str, job_id: str) -> dict:
        """
        Get the content of the job from the storage. This is a wrapper around get
        and and handles the different ways of identifiying the job.

        storage_path: the path towards the file, excluding the filename / id
        job_id: the id of the file we are about to look up

        Returns:
            The content of the job
        """

    def get_job_content(self, storage_path: str, job_id: str) -> dict:
        """
        Depreceated function. Use `get_job` instead.
        """
        warnings.warn(
            "`get_job_content` is depreceated. Use `get_job` instead.",
            DeprecationWarning,
        )
        return self.get_job(storage_path, job_id)

    @abstractmethod
    def upload_status(
        self,
        display_name: DisplayNameStr,
        username: str,
        job_id: str,
        private_jwk: Optional[JWK] = None,
    ) -> StatusMsgDict:
        """
        This function uploads a status file to the backend and creates the status dict.

        Args:
            display_name: The name of the backend to which we want to upload the job
            username: The username of the user that is uploading the job
            job_id: The job_id of the job that we want to upload the status for
            private_jwk: The private key of the backend

        Returns:
            The status dict of the job
        """

    @abstractmethod
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

    @abstractmethod
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

    @abstractmethod
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

    @abstractmethod
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

    @abstractmethod
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

    @abstractmethod
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

    @abstractmethod
    def upload_config(
        self,
        config_dict: BackendConfigSchemaIn,
        display_name: DisplayNameStr,
        private_jwk: Optional[JWK],
    ) -> None:
        """
        The function that uploads the spooler configuration to the storage.

        Args:
            config_dict: The model containing the configuration
            display_name : The name of the backend
            private_jwk: The private JWK to sign the result with

        Raises:
            ValueError: If the configuration already exists

        Returns:
            None
        """

    @abstractmethod
    def update_config(
        self,
        config_dict: BackendConfigSchemaIn,
        display_name: DisplayNameStr,
        private_jwk: Optional[JWK] = None,
    ) -> None:
        """
        The function that updates an existing spooler configuration for the storage.

        Args:
            config_dict: The model containing the configuration
            display_name : The name of the backend
            private_jwk: The private JWK to sign the result with

        Raises:
            FileNotFoundError: If the configuration does not exist

        Returns:
            None
        """

    @abstractmethod
    def get_config(self, display_name: DisplayNameStr) -> BackendConfigSchemaIn:
        """
        The function that downloads the spooler configuration to the storage.

        Args:
            display_name : The name of the backend

        Returns:
            The configuration of the backend in complete form.
        """

    @abstractmethod
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

    @abstractmethod
    def upload_public_key(self, public_jwk: JWK, display_name: DisplayNameStr) -> None:
        """
        The function that uploads the spooler public JWK to the storage.

        Args:
            public_jwk: The JWK that contains the public key
            display_name : The name of the backend

        Returns:
            None
        """

    @abstractmethod
    def get_public_key(self, display_name: DisplayNameStr) -> JWK:
        """
        The function that gets the spooler public JWK for the device.

        Args:
            display_name : The name of the backend

        Returns:
            JWk : The public JWK object
        """

    @abstractmethod
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

    @abstractmethod
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
            private_jwk: the private JWK to sign the result with

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
    def get_next_job_in_queue(
        self, display_name: DisplayNameStr, private_jwk: Optional[JWK] = None
    ) -> NextJobSchema:
        """
        A function that obtains the next job in the queue. If there is no job, it returns an empty
        dict. If there is a job, it moves the job from the queue to the running folder.
        It also update the time stamp for when the system last looked into the file queue.

        Args:
            display_name: The name of the backend
            private_jwk: The private JWK to sign the result with

        Returns:
            the job dict
        """

    def _common_upload_result(
        self,
        result_dict: ResultDict,
        display_name: DisplayNameStr,
        job_id: str,
        result_json_dir: str,
        result_json_name: str,
        private_jwk: Optional[JWK] = None,
    ) -> bool:
        """
        Common code for the upload of the results.

        Args:
            result_dict: The dictionary containing the result of the job
            display_name: The name of the backend
            job_id: The name of the job
            result_json_dir: The directory where the result should be stored
            result_json_name: The name of the result file
            private_jwk: The private JWK to sign the result with

        Returns:
            The success of the upload process
        """
        # make sure that the job_id is in the result_dict
        if not result_dict.job_id == job_id:
            logging.warning(
                "Tried to upload an inconsistent result for job_id %s.", job_id
            )
            result_dict.job_id = job_id
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
            self.upload(signed_result.model_dump(), result_json_dir, result_json_name)
        else:
            self.upload(result_dict.model_dump(), result_json_dir, result_json_name)
        return True

    def _verify_config(
        self, config_dict: BackendConfigSchemaIn, display_name: DisplayNameStr
    ) -> BackendConfigSchemaIn:
        """
        make sure that members of the config_dict are correct

        Args:
            config_dict: The dictionary containing the configuration
            display_name: The name of the backend

        Raises:
            A warning if the display_name does not match the display_name of the config_dict

        """
        if not config_dict.display_name == display_name:
            config_dict.display_name = display_name
            warnings.warn(
                f"The display_name of the config_dict had to be matched to {display_name}."
            )

        return config_dict

    def _format_config_dict(
        self, config_dict: BackendConfigSchemaIn, private_jwk: Optional[JWK] = None
    ) -> dict:
        """
        Format the config dict to a string that can be written to a file.

        Args:
            config_dict: The dictionary containing the configuration
            private_jwk: The private key of the backend

        Returns:
            The dict representation of the config dict

        Raises:
            ValueError: If the backend is configured to be signed, but no private key is given
        """
        if config_dict.sign:
            # get the private key
            if private_jwk is None:
                raise ValueError(
                    "The private key is not given, but the backend needs to be signed."
                )
            # we sign the result now
            config_dict.kid = private_jwk.kid
            signed_config = sign_payload(config_dict.model_dump(), private_jwk)
            upload_dict = signed_config.model_dump()
        else:
            upload_dict = config_dict.model_dump()
        return upload_dict

    def _format_status_dict(
        self,
        status_dict: StatusMsgDict,
        storage_path: str,
        display_name: DisplayNameStr,
        job_id: str,
        private_jwk: Optional[JWK] = None,
        status_json_name: Optional[str] = None,
    ) -> None:
        """
        Allows us to upload the appropiate status dict to the storage provider.
        """
        # get the backend config
        config_dict = self.get_config(display_name)
        if config_dict.sign and private_jwk:
            # we sign the result now
            signed_status = sign_payload(status_dict.model_dump(), private_jwk)
            upload_dict = signed_status.model_dump()
        else:
            upload_dict = status_dict.model_dump()

        # now upload the status dict
        if status_json_name is None:
            self.upload(
                content_dict=upload_dict,
                storage_path=storage_path,
                job_id=job_id,
            )
        else:
            self.upload(
                content_dict=upload_dict,
                storage_path=storage_path,
                job_id=status_json_name,
            )

    def _format_update_config(
        self,
        old_config_jws: dict,
        config_dict: BackendConfigSchemaIn,
        private_jwk: Optional[JWK] = None,
    ) -> dict:
        """
        The function that formats the config_dict for the update.

        Args:
            old_config_jws: The old configuration in JWS format
            config_dict: The dictionary containing the configuration
            private_jwk: The private JWK to sign the configuration with

        Returns:
            dict: The formatted dictionary
        """
        # now we should check if the old config is signed
        expected_keys_for_jws = {"header", "payload", "signature"}

        # now check if we need a private key
        # this is the case if the old config is signed or the new one should be signed
        if set(old_config_jws.keys()) == expected_keys_for_jws or config_dict.sign:
            if private_jwk is None:
                raise ValueError(
                    "The private key is not given, but the backend is configured to sign."
                )
            if set(old_config_jws.keys()) == expected_keys_for_jws:
                # the old config is signed and we need to check if the private key is the same
                payload = old_config_jws["payload"]

                # now proof that the new private key would create the same signature for the old
                # config to validate that we still have the same private key
                test_signature = sign_payload(payload, private_jwk)
                if not test_signature.signature == old_config_jws["signature"]:
                    raise ValueError(
                        "The new private key does not create the same signature as the old one."
                    )

            # now that we know that the private key is the same, we can sign the new config
            config_dict.kid = private_jwk.kid
            signed_config = sign_payload(config_dict.model_dump(), private_jwk)
            upload_dict = signed_config.model_dump()
        else:
            # the old and the new are not signed
            upload_dict = config_dict.model_dump()
        return upload_dict

    def _get_default_next_schema_dict(self) -> dict:
        return {"job_id": "None", "job_json_path": "None"}

    def _adapt_get_config(self, config_dict: dict) -> BackendConfigSchemaIn:
        """
        Adapt the config dict to the BackendConfigSchemaIn.

        Args:
            config_dict: The dictionary containing the configuration

        Returns:
            The adapted config dict
        """
        # we should verify the result before we send it out
        expected_keys_for_jws = {"header", "payload", "signature"}
        if set(config_dict.keys()) == expected_keys_for_jws:
            payload = config_dict["payload"]
            typed_config = BackendConfigSchemaIn(**payload)
        else:
            typed_config = BackendConfigSchemaIn(**config_dict)
        return typed_config

    def _adapt_result_dict(
        self, result_dict: dict, backend_config_info: BackendConfigSchemaOut
    ) -> ResultDict:
        """
        This function adapts the result dict to the standard format that we use in the system.

        Args:
            result_dict: The result dictionary
            backend_config_info: The configuration of the backend

        Returns:
            The result dict in the standard format
        """
        # done day we should verify the result before we send it out
        expected_keys_for_jws = {"header", "payload", "signature"}
        if set(result_dict.keys()) == expected_keys_for_jws:
            result_payload = result_dict["payload"]
            result_payload["backend_name"] = backend_config_info.backend_name
            typed_result = ResultDict(**result_payload)
        else:
            result_dict["backend_name"] = backend_config_info.backend_name
            typed_result = ResultDict(**result_dict)
        return typed_result

    def _adapt_status_dict(self, status_dict: dict) -> StatusMsgDict:
        """
        This function adapts the status dict to the standard format that we use in the system.

        Args:
            status_dict: The status dictionary
            backend_config_info: The configuration of the backend

        Returns:
            The status dict in the standard format
        """
        # done day we should verify the result before we send it out
        expected_keys_for_jws = {"header", "payload", "signature"}
        if set(status_dict.keys()) == expected_keys_for_jws:
            typed_result = StatusMsgDict(**status_dict["payload"])
        else:
            typed_result = StatusMsgDict(**status_dict)
        return typed_result

    def timestamp_queue(
        self, display_name: DisplayNameStr, private_jwk: Optional[JWK] = None
    ) -> None:
        """
        Updates the time stamp for when the system last looked into the file queue.
        This allows us to track if the system is actually online or not.

        Args:
            display_name : The name of the backend
            private_jwk: The private JWK to sign the result with

        Returns:
            None
        """
        # first let us get the current configuration
        try:
            config_dict = self.get_config(display_name)
        except FileNotFoundError as exc:
            # if the config does not exist, we raise the informed error
            logging.error(
                "The configuration for the backend %s does not exist.", display_name
            )
            raise FileNotFoundError(
                f"The configuration for the backend {display_name} does not exist."
            ) from exc
        # get the current time
        current_time = datetime.now(timezone.utc).replace(microsecond=0)

        # update the time stamp
        config_dict.last_queue_check = current_time

        # upload the new configuration
        self.update_config(config_dict, display_name, private_jwk)

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

    def long_backend_name(
        self, display_name: DisplayNameStr, simulator: bool
    ) -> BackendNameStr:
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

    def _last_queued_to_operational(self, last_queue_check: datetime | None) -> bool:
        """
        Calculate the operational status based on the last time the queue
        was checked.
        """
        # get the timeout from the configuration
        t_timeout = config("T_TIMEOUT", cast=int, default=300)
        if not last_queue_check:
            return False

        last_queue_check = last_queue_check.replace(tzinfo=timezone.utc)
        current_time = datetime.now(timezone.utc).replace(microsecond=0)

        if (current_time - last_queue_check).total_seconds() > t_timeout:
            return False
        return True

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
        last_queue_check = backend_dict.last_queue_check

        # if the name is already in the dict, we should set the backend_name to the name
        # otherwise we calculate it.
        if backend_dict.simulator:
            backend_name = f"{self.name}_{display_name}_simulator"
        else:
            backend_name = f"{self.name}_{display_name}_hardware"

        backend_status_dict["backend_name"] = backend_name
        backend_status_dict["backend_version"] = backend_dict.version

        # now I also need to obtain the operational status from the backend.
        backend_status_dict["operational"] = self._last_queued_to_operational(
            last_queue_check
        )
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


def datetime_handler(in_var: Any) -> str:
    """
    Convert a datetime object to a string.

    Args:
        in_var : The object to convert

    Returns:
        str : The string representation of the object
    """
    if isinstance(in_var, datetime):
        return in_var.isoformat()
    raise TypeError("Unknown type")
