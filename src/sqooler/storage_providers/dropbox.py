"""
The module that contains all the necessary logic for communication with the Dropbox providers.
"""

# necessary for the dropbox provider
import datetime
import json
import logging
import sys
import uuid
from datetime import timezone
from typing import Mapping, Optional

import dropbox
from dropbox.exceptions import ApiError, AuthError
from dropbox.files import WriteMode

from ..schemes import (
    AttributeIdStr,
    AttributePathStr,
    BackendConfigSchemaIn,
    DisplayNameStr,
    DropboxLoginInformation,
    PathStr,
    ResultDict,
    StatusMsgDict,
)
from ..security import JWK
from .base import StorageCore, StorageProvider, datetime_handler, validate_active


class DropboxCore(StorageCore):
    """
    Base class that creates the most important functions for the local storage provider.
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

    def upload_string(
        self, content_string: str, storage_path: str, job_id: str
    ) -> None:
        """
        Upload the content_string as a json file to the dropbox

        Args:
            content_string: the content of the file that should be uploaded
            storage_path: the path where the file should be stored, but excluding the file name
            job_id: the name of the file without the .json extension
        """

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
                content_string.encode("utf-8"), full_path, mode=WriteMode("overwrite")
            )

    @validate_active
    def upload(self, content_dict: Mapping, storage_path: str, job_id: str) -> None:
        """
        Upload the content_dict as a json file to the dropbox

        Args:
            content_dict: the content of the file that should be uploaded
            storage_path: the path where the file should be stored, but excluding the file name
            job_id: the name of the file without the .json extension
        """

        # let us first see if the file already exists by using the get function
        # it would be much nicer to use an exists function, but we do not have that
        try:
            self.get(storage_path, job_id)
            raise FileExistsError(
                f"The file {job_id} in {storage_path} already exists and should not be overwritten."
            )
        except FileNotFoundError:
            # create the appropriate string for the dropbox API
            dump_str = json.dumps(content_dict, default=datetime_handler)
            self.upload_string(dump_str, storage_path, job_id)

    @validate_active
    def get(self, storage_path: str, job_id: str) -> dict:
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
            try:
                _, res = dbx.files_download(path=full_path)
            except ApiError as err:
                raise FileNotFoundError(
                    f"Could not find file under {full_path}"
                ) from err
            data = res.content
        return json.loads(data.decode("utf-8"))

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
        """
        # create the appropriate string for the dropbox API
        dump_str = json.dumps(content_dict, default=datetime_handler)

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

            try:
                dbx.files_get_metadata(full_path)
            except ApiError as err:
                raise FileNotFoundError(
                    f"Could not update file under {full_path}"
                ) from err

            dbx.files_upload(
                dump_str.encode("utf-8"), full_path, mode=WriteMode("overwrite")
            )

    @validate_active
    def move(self, start_path: str, final_path: str, job_id: str) -> None:
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
    def delete(self, storage_path: str, job_id: str) -> None:
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
            try:
                _ = dbx.files_delete_v2(path=full_path)
            except ApiError as err:
                raise FileNotFoundError(
                    f"Could not delete file under {full_path}"
                ) from err

    def delete_folder(self, folder_path: str) -> None:
        """
        Remove the folder from the dropbox. Attention this will remove all the files in the folder.
        It is not a standard function for storage providers, but allows us to better clean up the
        tests.

        Args:
            folder_path: the path where the file should be stored, but excluding the file name

        Returns:
            None
        """

        # strip trailing and leading slashes from the storage_path
        folder_path = folder_path.strip("/")

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

            # to remove a folder there must be no trailing slash
            full_path = "/" + folder_path
            _ = dbx.files_delete_v2(path=full_path)


class DropboxProviderExtended(StorageProvider, DropboxCore):
    """
    The class that implements the dropbox storage provider.

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

    configs_path: PathStr = "Backend_files/Config"
    queue_path: PathStr = "Backend_files/Queued_Jobs"
    running_path: PathStr = "Backend_files/Running_Jobs"
    finished_path: PathStr = "Backend_files/Finished_Jobs"
    deleted_path: PathStr = "Backend_files/Deleted_Jobs"
    status_path: PathStr = "Backend_files/Status"
    results_path: PathStr = "Backend_files/Result"
    pks_path: PathStr = "Backend_files/public_keys"

    def get_attribute_path(
        self,
        attribute_name: AttributePathStr,
        display_name: Optional[DisplayNameStr] = None,
        job_id: Optional[str] = None,
        username: Optional[str] = None,
    ) -> str:
        """
        Get the path to the results of the device.

        Args:
            display_name: The name of the backend
            attribute_name: The name of the attribute
            job_id: The job_id of the job
            username: The username of the user that is uploading the job

        Returns:
            The path to the results of the device.
        """

        match attribute_name:
            case "configs":
                if display_name is None:
                    raise ValueError("The display_name must be set for configs_path.")
                path = f"{self.configs_path}/{display_name}"
            case "results":
                if job_id is None:
                    raise ValueError("The job_id must be set for results path.")
                extracted_username = job_id.split("-")[2]
                path = f"/{self.results_path}/{display_name}/{extracted_username}/"
            case "running":
                path = self.running_path
            case "status":
                path = f"/{self.status_path}/{display_name}/{username}/"
            case "queue":
                path = f"/{self.queue_path}/{display_name}/"
            case "deleted":
                path = self.deleted_path
            case "finished":
                path = f"/{self.finished_path}/{display_name}/{username}/"
            case "pks":
                path = self.pks_path
            case _:
                raise ValueError(f"The attribute name {attribute_name} is not valid.")
        return path

    def get_attribute_id(
        self,
        attribute_name: AttributeIdStr,
        job_id: str,
        display_name: Optional[DisplayNameStr] = None,
    ) -> str:
        """
        Get the path to the id of the device.

        Args:
            attribute_name: The name of the attribute
            job_id: The job_id of the job
            display_name: The name of the backend

        Returns:
            The path to the results of the device.
        """

        match attribute_name:
            case "configs":
                _id = "config"
            case "job":
                _id = f"job-{job_id}"
            case "results":
                _id = "result-" + job_id
            case "status":
                _id = "status-" + job_id
            case _:
                raise ValueError(f"The attribute name {attribute_name} is not valid.")
        return _id

    def update_config(
        self,
        config_dict: BackendConfigSchemaIn,
        display_name: DisplayNameStr,
        private_jwk: Optional[JWK] = None,
    ) -> None:
        """
        The function that updates the spooler configuration to the storage.

        All the configurations are stored in the Backend_files/Config folder.
        For each backend there is a separate folder in which the configuration is stored as a json file.

        Args:
            config_dict: The dictionary containing the configuration
            display_name : The name of the backend
            private_jwk: The private JWK to sign the configuration with

        Returns:
            None
        """

        config_dict = self._verify_config(config_dict, display_name)
        # check that the file exists
        config_path = self.get_attribute_path("configs", display_name=display_name)
        old_config_jws = self.get(config_path, "config")

        upload_dict = self._format_update_config(
            old_config_jws, config_dict, private_jwk
        )

        self.update(upload_dict, config_path, "config")

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
        config_path = f"{self.configs_path}/{display_name}"

        self.delete(storage_path=config_path, job_id="config")
        self.delete_folder(config_path)
        return True

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

        # make sure that the key has the correct kid
        config_dict = self.get_config(display_name)
        if public_jwk.kid != config_dict.kid:
            raise ValueError("The key does not have the correct kid.")
        pks_path = self.get_attribute_path("pks")
        self.upload_string(public_jwk.model_dump_json(), pks_path, config_dict.kid)

    def get_public_key(self, display_name: DisplayNameStr) -> JWK:
        """
        The function that gets the spooler public JWK for the device.

        Args:
            display_name : The name of the backend

        Returns:
            JWk : The public JWK object
        """

        # now get the appropiate kid
        config_dict = self.get_config(display_name)
        if config_dict.kid is None:
            raise ValueError("The kid is not set in the backend configuration.")
        pks_path = self.get_attribute_path("pks")

        public_jwk_dict = self.get(storage_path=pks_path, job_id=config_dict.kid)
        return JWK(**public_jwk_dict)

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
        pks_path = self.get_attribute_path("pks")
        self.delete(storage_path=pks_path, job_id=kid)
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
        Upload the status and result to the dropbox.

        Args:
            result_dict: the dictionary containing the result of the job
            status_msg_dict: the dictionary containing the status message of the job
            job_id: the name of the job
            display_name: the name of the backend
            private_jwk: the private JWK to sign the result with

        Returns:
            None
        """
        # this should become part of the json file instead of its name in the future
        extracted_username = job_id.split("-")[2]

        status_json_dir = self.get_attribute_path(
            "status", display_name, extracted_username
        )

        status_json_name = self.get_attribute_id("status", job_id=job_id)

        job_json_name = self.get_attribute_id("job", job_id)
        job_json_start_dir = self.get_attribute_path("running")

        if status_msg_dict.status == "DONE":
            self.upload_result(
                result_dict,
                display_name,
                job_id,
                private_jwk,
            )
            # now move the job out of the running jobs into the finished jobs
            job_finished_json_dir = self.get_attribute_path(
                "finished", display_name=display_name, username=extracted_username
            )

            self.move(job_json_start_dir, job_finished_json_dir, job_json_name)

        elif status_msg_dict.status == "ERROR":
            # because there was an error, we move the job to the deleted jobs
            deleted_json_dir = self.get_attribute_path("deleted", display_name)
            self.move(job_json_start_dir, deleted_json_dir, job_json_name)

        try:
            self.update(status_msg_dict.model_dump(), status_json_dir, status_json_name)
        except FileNotFoundError:
            logging.warning(
                "The status file was missing for %s with job_id %s was missing.",
                display_name,
                job_id,
            )
            self.upload_status(display_name, username=extracted_username, job_id=job_id)
            self.update(status_msg_dict.model_dump(), status_json_dir, status_json_name)

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
        names: list[str] = []
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
                json_files = [item for item in file_list if item.endswith(".json")]

                # Get the backend names
                names = [file_name.split(".")[0] for file_name in json_files]

            except ApiError:
                print(f"Could not obtain job queue for {storage_path}")
            except Exception as err:
                print(err)
        return names

    @validate_active
    def get_backends(self) -> list[str]:
        """
        Get a list of all the backends that the provider offers.
        """

        # strip possible trailing and leading slashes from the path
        config_path = self.configs_path.strip("/")

        # and now add them nicely
        full_config_path = f"/{config_path}/"
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

            folders_results = dbx.files_list_folder(path=full_config_path)
            entries = folders_results.entries
            backend_names = []
            for entry in entries:
                backend_names.append(entry.name)
        return backend_names

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
        backend_json_path = f"{self.configs_path}/{display_name}"
        backend_config_dict = self.get(storage_path=backend_json_path, job_id="config")
        typed_config = self._adapt_get_config(backend_config_dict)
        return typed_config

    def create_job_id(self, display_name: DisplayNameStr, username: str) -> str:
        """
        Create a job id for the job.

        Args:
            display_name: The name of the backend
            username: The username of the user that is uploading the job

        Returns:
            The job id
        """
        job_id = (
            (datetime.datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S"))
            + "-"
            + display_name
            + "-"
            + username
            + "-"
            + (uuid.uuid4().hex)[:5]
        )
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

        status_json_dir = self.get_attribute_path("status", display_name, username)

        status_json_name = self.get_attribute_id("status", job_id)

        self.delete(storage_path=status_json_dir, job_id=status_json_name)
        self.delete_folder(status_json_dir)
        return True

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
        result_device_dir = self.get_attribute_path("results", display_name, job_id)
        self.delete_folder(result_device_dir)
        return True


class DropboxProvider(DropboxProviderExtended):
    """
    The class that implements the dropbox storage provider.
    """

    def __init__(self, login_dict: DropboxLoginInformation) -> None:
        """
        Args:
            login_dict: The dictionary that contains the login information
        """

        super().__init__(login_dict, name="default", is_active=True)
