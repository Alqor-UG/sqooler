"""
The module that contains all the necessary logic for communication with the MongoDb storage providers.
"""

import uuid
from typing import Optional

# necessary for the mongodb provider
from pymongo.mongo_client import MongoClient
from bson.objectid import ObjectId
from bson.errors import InvalidId

from ..schemes import (
    ResultDict,
    StatusMsgDict,
    MongodbLoginInformation,
    BackendStatusSchemaOut,
    BackendConfigSchemaIn,
    NextJobSchema,
    DisplayNameStr,
)

from .base import StorageProvider, validate_active
from ..security import JWK, sign_payload


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

        Args:
            storage_path: the path towards the file, excluding the filename / id
            job_id: the id of the file we are about to look up

        Returns:
            The content of the file
        """
        try:
            document_to_find = {"_id": ObjectId(job_id)}
        except InvalidId as err:
            raise FileNotFoundError(
                f"The job_id {job_id} is not valid. Please check the job_id."
            ) from err

        document_to_find = {"_id": ObjectId(job_id)}

        # get the database on which we work
        database = self.client[storage_path.split("/")[0]]

        # get the collection on which we work
        collection_name = ".".join(storage_path.split("/")[1:])
        collection = database[collection_name]

        result_found = collection.find_one(document_to_find)

        if not result_found:
            raise FileNotFoundError(
                f"Could not find a file under {storage_path} with the id {job_id}."
            )

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
        # get the database on which we work
        database = self.client[storage_path.split("/")[0]]

        # get the collection on which we work
        collection_name = ".".join(storage_path.split("/")[1:])
        collection = database[collection_name]

        filter_dict = {"_id": ObjectId(job_id)}
        result = collection.replace_one(filter_dict, content_dict)

        if result.matched_count == 0:
            raise FileNotFoundError(f"Could not update file under {storage_path}")

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
        try:
            document_to_find = {"_id": ObjectId(job_id)}
        except InvalidId as err:
            raise FileNotFoundError(
                f"The job_id {job_id} is not valid. Please check the job_id."
            ) from err
        result = collection.delete_one(document_to_find)
        if result.deleted_count == 0:
            raise FileNotFoundError(
                f"Could not find a file under {storage_path} with the id {job_id}."
            )

    @validate_active
    def get_backends(self) -> list[DisplayNameStr]:
        """
        Get a list of all the backends that the provider offers.
        """

        # get the database on which we work
        database = self.client["backends"]
        config_collection = database["configs"]
        # get all the documents in the collection configs and save the disply_name in a list
        backend_names: list[DisplayNameStr] = []
        for config_dict in config_collection.find():
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
        config_path = "backends/configs"

        # first we have to check if the device already exists in the database

        document_to_find = {"display_name": display_name}

        # get the database on which we work
        database = self.client["backends"]

        # get the collection on which we work
        collection = database["configs"]

        result_found = collection.find_one(document_to_find)
        config_dict.display_name = display_name
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

    @validate_active
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
        # get the database on which we work
        database = self.client["backends"]
        config_collection = database["configs"]

        # create the filter for the document with display_name that is equal to display_name
        document_to_find = {"display_name": display_name}
        backend_config_dict = config_collection.find_one(document_to_find)

        if not backend_config_dict:
            raise FileNotFoundError("The backend does not exist for the given storage.")

        backend_config_dict.pop("_id")
        return BackendConfigSchemaIn(**backend_config_dict)

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
        except FileNotFoundError as err:
            # if the job_id is not valid, we return an error
            return StatusMsgDict(
                job_id=job_id,
                status="ERROR",
                detail="The job_id is not valid.",
                error_message=str(err),
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
        backend_config_info = self.get_backend_dict(display_name)
        return self._adapt_result_dict(result_dict, backend_config_info)

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

        pk_paths = "backends/public_keys"

        # first we have to check if the device already exists in the database

        document_to_find = {"display_name": display_name}

        # get the database on which we work
        database = self.client["backends"]

        # get the collection on which we work
        collection = database["public_keys"]

        result_found = collection.find_one(document_to_find)
        if result_found:
            # update the file
            self.update_file(
                content_dict=public_jwk.model_dump(),
                storage_path=pk_paths,
                job_id=result_found["_id"],
            )
            return

        # if the device does not exist, we have to create it

        config_id = uuid.uuid4().hex[:24]
        self.upload(public_jwk.model_dump(), pk_paths, config_id)

    def get_public_key(self, display_name: DisplayNameStr) -> JWK:
        """
        The function that gets the spooler public JWK for the device.

        Args:
            display_name : The name of the backend

        Returns:
            JWk : The public JWK object
        """
        # get the database on which we work
        database = self.client["backends"]
        collection = database["public_keys"]

        # create the filter for the document with display_name that is equal to display_name
        document_to_find = {"display_name": display_name}
        public_jwk_dict = collection.find_one(document_to_find)

        if not public_jwk_dict:
            raise FileNotFoundError("The backend does not exist for the given storage.")

        public_jwk_dict.pop("_id")
        return JWK(**public_jwk_dict)

    def update_in_database(
        self,
        result_dict: ResultDict | None,
        status_msg_dict: StatusMsgDict,
        job_id: str,
        display_name: DisplayNameStr,
        private_jwk: Optional[JWK] = None,
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
            display_name: the name of the backend
            private_jwk: the private JWK to sign the result with

        Returns:
            None

        Raises:

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

        # TODO: most likely we should raise an error if the status of the job is not DONE or ERROR

        # and create the status json file
        status_json_dir = "status/" + display_name
        self.update_file(status_msg_dict.model_dump(), status_json_dir, job_id)

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

    def get_next_job_in_queue(self, display_name: str) -> NextJobSchema:
        """
        A function that obtains the next job in the queue. If there is no job, it returns an empty
        dict. If there is a job, it moves the job from the queue to the running folder.
        It also update the time stamp for when the system last looked into the file queue.

        Args:
            display_name: The name of the backend

        Returns:
            the job dict
        """

        queue_dir = "jobs/queued/" + display_name
        job_dict = {"job_id": 0, "job_json_path": "None"}
        job_list = self.get_file_queue(queue_dir)

        # update the time stamp of the last job
        self.timestamp_queue(display_name)

        # if there is a job, we should move it
        if job_list:
            job_id = job_list[0]
            job_dict["job_id"] = job_id

            # and move the file into the right directory
            self.move_file(queue_dir, "jobs/running", job_id)
            job_dict["job_json_path"] = "jobs/running"
        return NextJobSchema(**job_dict)


class MongodbProvider(MongodbProviderExtended):
    """
    The access to the mongodb. This is the simplified version for people that are running devices.
    """

    def __init__(self, login_dict: MongodbLoginInformation) -> None:
        """
        Set up the neccessary keys and create the client through which all the connections will run.
        """
        super().__init__(login_dict, name="default", is_active=True)
