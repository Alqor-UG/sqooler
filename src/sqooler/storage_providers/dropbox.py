"""
The module that contains all the necessary logic for communication with the Dropbox providers.
"""

import sys
import uuid
import json

from typing import Mapping, Optional

# necessary for the dropbox provider
import datetime
from datetime import timezone
import dropbox
from dropbox.files import WriteMode
from dropbox.exceptions import ApiError, AuthError

from ..schemes import (
    ResultDict,
    StatusMsgDict,
    DropboxLoginInformation,
    BackendStatusSchemaOut,
    BackendConfigSchemaIn,
    NextJobSchema,
    DisplayNameStr,
)
from ..security import JWK, sign_payload
from .base import StorageProvider, validate_active, datetime_handler


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

    def upload(self, content_dict: Mapping, storage_path: str, job_id: str) -> None:
        """
        Upload the content_dict as a json file to the dropbox

        Args:
            content_dict: the content of the file that should be uploaded
            storage_path: the path where the file should be stored, but excluding the file name
            job_id: the name of the file without the .json extension
        """

        # create the appropriate string for the dropbox API
        dump_str = json.dumps(content_dict, default=datetime_handler)

        self.upload_string(dump_str, storage_path, job_id)

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
            try:
                _, res = dbx.files_download(path=full_path)
            except ApiError as err:
                raise FileNotFoundError(
                    f"Could not find file under {full_path}"
                ) from err
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
            try:
                _ = dbx.files_delete_v2(path=full_path)
            except ApiError as err:
                raise FileNotFoundError(
                    f"Could not delete file under {full_path}"
                ) from err

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

        # check that the file exists
        config_path = "Backend_files/Config/" + display_name
        old_config_jws = self.get_file_content(config_path, "config")

        upload_dict = self._format_update_config(
            old_config_jws, config_dict, private_jwk
        )
        # maybe this should rather become the update_file function
        self.upload(upload_dict, config_path, "config")

    def upload_config(
        self,
        config_dict: BackendConfigSchemaIn,
        display_name: DisplayNameStr,
        private_jwk: Optional[JWK] = None,
    ) -> None:
        """
        The function that uploads the spooler configuration to the storage.

        All the configurations are stored in the Backend_files/Config folder.
        For each backend there is a separate folder in which the configuration is stored as a json file.

        Args:
            config_dict: The dictionary containing the configuration
            display_name : The name of the backend
            private_jwk: The private JWK to sign the configuration with

        Returns:
            None
        """

        config_path = "Backend_files/Config/" + display_name
        # check if the file already exists
        try:
            self.get_file_content(storage_path=config_path, job_id="config")
            raise FileExistsError(
                f"The configuration for {display_name} already exists and should not be overwritten."
            )
        except FileNotFoundError:
            pass

        upload_dict = self._format_config_dict(config_dict, private_jwk)
        self.upload(upload_dict, config_path, "config")

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

        pk_paths = "Backend_files/public_keys"

        self.upload_string(public_jwk.model_dump_json(), pk_paths, display_name)

    def get_public_key(self, display_name: DisplayNameStr) -> JWK:
        """
        The function that gets the spooler public JWK for the device.

        Args:
            display_name : The name of the backend

        Returns:
            JWk : The public JWK object
        """
        pk_paths = "Backend_files/public_keys"
        public_jwk_dict = self.get_file_content(
            storage_path=pk_paths, job_id=display_name
        )
        return JWK(**public_jwk_dict)

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

        status_json_dir = (
            "/Backend_files/Status/" + display_name + "/" + extracted_username + "/"
        )
        status_json_name = "status-" + job_id

        job_json_name = "job-" + job_id
        job_json_start_dir = "Backend_files/Running_Jobs"

        if status_msg_dict.status == "DONE":
            # let us create the result json file
            result_json_dir = (
                "/Backend_files/Result/" + display_name + "/" + extracted_username + "/"
            )
            result_json_name = "result-" + job_id

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
                self.upload(
                    signed_result.model_dump(), result_json_dir, result_json_name
                )
            else:
                self.upload(result_dict.model_dump(), result_json_dir, result_json_name)

            # now move the job out of the running jobs into the finished jobs
            job_finished_json_dir = (
                "/Backend_files/Finished_Jobs/"
                + display_name
                + "/"
                + extracted_username
                + "/"
            )
            self.move_file(job_json_start_dir, job_finished_json_dir, job_json_name)

        elif status_msg_dict.status == "ERROR":
            # because there was an error, we move the job to the deleted jobs
            deleted_json_dir = "Backend_files/Deleted_Jobs"
            self.move_file(job_json_start_dir, deleted_json_dir, job_json_name)

        # and create the status json file
        self.upload(status_msg_dict.model_dump(), status_json_dir, status_json_name)

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
        backend_json_path = f"Backend_files/Config/{display_name}"
        backend_config_dict = self.get_file_content(
            storage_path=backend_json_path, job_id="config"
        )
        typed_config = self._adapt_get_config(backend_config_dict)
        return typed_config

    def get_backend_status(
        self, display_name: DisplayNameStr
    ) -> BackendStatusSchemaOut:
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

    def upload_job(
        self, job_dict: dict, display_name: DisplayNameStr, username: str
    ) -> str:
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
            (datetime.datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S"))
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
        status_json_dir = "Backend_files/Status/" + display_name + "/" + username
        status_json_name = "status-" + job_id
        status_draft = {
            "job_id": job_id,
            "status": "INITIALIZING",
            "detail": "Got your json.",
            "error_message": "None",
        }
        status_dict = StatusMsgDict(**status_draft)
        self.upload(
            content_dict=status_dict.model_dump(),
            storage_path=status_json_dir,
            job_id=status_json_name,
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
        status_json_dir = "Backend_files/Status/" + display_name + "/" + username
        status_json_name = "status-" + job_id

        try:
            status_dict = self.get_file_content(
                storage_path=status_json_dir, job_id=status_json_name
            )
            return StatusMsgDict(**status_dict)
        except FileNotFoundError:
            status_draft = {
                "job_id": job_id,
                "status": "ERROR",
                "detail": "Could not find the status file.",
                "error_message": f"Missing status file for {job_id}.",
            }
            return StatusMsgDict(**status_draft)

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
        result_json_dir = "Backend_files/Result/" + display_name + "/" + username
        result_json_name = "result-" + job_id
        try:
            result_dict = self.get_file_content(
                storage_path=result_json_dir, job_id=result_json_name
            )
        except FileNotFoundError:
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
        backend_config_info = self.get_backend_dict(display_name)
        return self._adapt_result_dict(result_dict, backend_config_info)

    def get_next_job_in_queue(
        self, display_name: DisplayNameStr, private_jwk: Optional[JWK] = None
    ) -> NextJobSchema:
        """
        A function that obtains the next job in the queue.

        Args:
            display_name: The name of the backend
            private_jwk: The private JWK to sign the job with


        Returns:
            the path towards the job
        """
        job_json_dir = "/Backend_files/Queued_Jobs/" + display_name + "/"
        job_dict = self._get_default_next_schema_dict()
        job_list = self.get_file_queue(job_json_dir)

        # time stamp when we last looked for a job
        self.timestamp_queue(display_name, private_jwk)

        # if there is a job, we should move it
        if job_list:
            job_json_name = job_list[0]
            job_dict["job_id"] = job_json_name[4:-5]

            # split the .json from the job_json_name
            job_json_name = job_json_name.split(".")[0]
            # and move the file into the right directory
            self.move_file(job_json_dir, "Backend_files/Running_Jobs", job_json_name)
            job_dict["job_json_path"] = "Backend_files/Running_Jobs"
        return NextJobSchema(**job_dict)

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
