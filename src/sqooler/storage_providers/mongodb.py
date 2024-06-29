"""
The module that contains all the necessary logic for communication with the MongoDb storage providers.
"""

import logging
import uuid
from datetime import timezone
from typing import Optional

from bson.codec_options import CodecOptions
from bson.errors import InvalidId
from bson.objectid import ObjectId
from pymongo.collection import Collection
from pymongo.database import Database
from pymongo.errors import DuplicateKeyError

# necessary for the mongodb provider
from pymongo.mongo_client import MongoClient

from ..schemes import (
    AttributeIdStr,
    AttributePathStr,
    BackendConfigSchemaIn,
    DisplayNameStr,
    MongodbLoginInformation,
    PathStr,
    ResultDict,
    StatusMsgDict,
)
from ..security import JWK
from .base import StorageCore, StorageProvider, validate_active


class MongodbCore(StorageCore):
    """
    Base class that creates the most important functions for the mongodb storage provider.
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

        _, collection = self._get_database_and_collection(storage_path)

        content_dict["_id"] = ObjectId(job_id)

        try:
            collection.insert_one(content_dict)
        except DuplicateKeyError as err:
            raise FileExistsError(
                f"The file with the id {job_id} already exists in the collection {storage_path}."
            ) from err
        # remove the id from the content dict for further use
        content_dict.pop("_id", None)

    @validate_active
    def get(self, storage_path: str, job_id: str) -> dict:
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

        _, collection = self._get_database_and_collection(storage_path)

        result_found = collection.find_one(document_to_find)

        if not result_found:
            raise FileNotFoundError(
                f"Could not find a file under {storage_path} with the id {job_id}."
            )

        # remove the id from the result dict for further use
        result_found.pop("_id", None)
        return result_found

    @validate_active
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

        _, collection = self._get_database_and_collection(storage_path)

        filter_dict = {"_id": ObjectId(job_id)}
        result = collection.replace_one(filter_dict, content_dict)

        if result.matched_count == 0:
            raise FileNotFoundError(f"Could not update file under {storage_path}")

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

        # delete the old file
        _, collection = self._get_database_and_collection(start_path)

        document_to_find = {"_id": ObjectId(job_id)}
        result_found = collection.find_one(document_to_find)

        collection.delete_one(document_to_find)

        # add the document to the new collection
        _, collection = self._get_database_and_collection(final_path)

        collection.insert_one(result_found)

    @validate_active
    def delete(self, storage_path: str, job_id: str) -> None:
        """
        Remove the file from the mongodb database

        Args:
            storage_path: the path where the file is currently stored, but excluding the file name
            job_id: the name of the file

        Returns:
            None
        """
        _, collection = self._get_database_and_collection(storage_path)

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

    def _get_database_and_collection(
        self, storage_path: str
    ) -> tuple[Database, Collection]:
        """
        Get the database and the collection on which we work.

        Args:
            storage_path: the path where the file is currently stored, but excluding the file name

        Returns:
            The database and the collection on which we work
        """
        # strip the path from leading and trailing slashes
        storage_path = storage_path.strip("/")

        # get the database on which we work
        database = self.client[storage_path.split("/")[0]]

        # get the collection on which we work
        collection_name = ".".join(storage_path.split("/")[1:])
        collection = database[collection_name]
        return database, collection


class MongodbProviderExtended(StorageProvider, MongodbCore):
    """
    The access to the mongodb

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
            username: The username of the user

        Returns:
            The path to the results of the device.
        """

        match attribute_name:
            case "configs":
                path = self.configs_path
            case "results":
                path = f"{self.results_path}/{display_name}"
            case "running":
                path = self.running_path
            case "status":
                path = f"{self.status_path}/{display_name}"
            case "queue":
                path = f"{self.queue_path}/{display_name}"
            case "deleted":
                path = self.deleted_path
            case "finished":
                path = f"{self.finished_path}/{display_name}"
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
                raise ValueError(f"The attribute name {attribute_name} is not valid.")
            case "job":
                _id = job_id
            case "results":
                _id = job_id
            case "status":
                _id = job_id
            case _:
                raise ValueError(f"The attribute name {attribute_name} is not valid.")
        return _id

    @validate_active
    def get_backends(self) -> list[DisplayNameStr]:
        """
        Get a list of all the backends that the provider offers.
        """

        # get the collection on which we work
        _, config_collection = self._get_database_and_collection(self.configs_path)

        # get all the documents in the collection configs and save the disply_name in a list
        backend_names: list[DisplayNameStr] = []
        for config_dict in config_collection.find():
            config_dict.pop("_id")
            expected_keys_for_jws = {"header", "payload", "signature"}
            if set(config_dict.keys()) == expected_keys_for_jws:
                backend_names.append(config_dict["payload"]["display_name"])
            else:
                backend_names.append(config_dict["display_name"])
        return backend_names

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
            private_jwk: The private JWK to sign the configuration with

        Returns:
            None
        """
        config_dict = self._verify_config(config_dict, display_name)

        # first we have to check if the device already exists in the database

        document_to_find = {"display_name": display_name}

        # get the collection on which we work
        _, collection = self._get_database_and_collection(self.configs_path)

        document_to_find = {"display_name": display_name}
        result_found = collection.find_one(document_to_find)
        if result_found:
            raise FileExistsError(
                f"The configuration for {display_name} already exists and should not be overwritten."
            )

        # now also look for signed configurations
        signed_document_to_find = {"payload.display_name": display_name}
        result_found = collection.find_one(signed_document_to_find)
        if result_found:
            raise FileExistsError(
                f"The configuration for {display_name} already exists and should not be overwritten."
            )

        upload_dict = self._format_config_dict(config_dict, private_jwk)
        config_id = uuid.uuid4().hex[:24]
        self.upload(upload_dict, self.configs_path, config_id)

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

        _, collection = self._get_database_and_collection(self.configs_path)

        # now make sure that we add the timezone as we open the file
        collection_with_tz = collection.with_options(
            codec_options=CodecOptions(tz_aware=True, tzinfo=timezone.utc)
        )
        # first we have to check if the device already exists in the database
        document_to_find = {"display_name": display_name}
        result_found = collection_with_tz.find_one(document_to_find)

        signed_document_to_find = {"payload.display_name": display_name}
        signed_backend_config_dict = collection_with_tz.find_one(
            signed_document_to_find
        )

        if result_found:
            old_config_jws = result_found
            job_id = result_found["_id"]
        elif signed_backend_config_dict:
            old_config_jws = signed_backend_config_dict
            job_id = signed_backend_config_dict["_id"]
            old_config_jws.pop("_id")
        else:
            raise FileNotFoundError(
                (
                    f"The config for {display_name} does not exist and should not be updated."
                    "Use the upload_config method instead."
                )
            )
        upload_dict = self._format_update_config(
            old_config_jws, config_dict, private_jwk
        )

        self.update(
            content_dict=upload_dict,
            storage_path=self.configs_path,
            job_id=job_id,
        )

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
        # get the collection on which we work
        _, config_collection = self._get_database_and_collection(self.configs_path)

        # create the filter for the document with display_name that is equal to display_name
        document_to_find = {"display_name": display_name}
        backend_config_dict = config_collection.find_one(document_to_find)

        signed_document_to_find = {"payload.display_name": display_name}
        signed_backend_config_dict = config_collection.find_one(signed_document_to_find)

        # work with the unsigned backend
        if backend_config_dict:
            backend_config_dict.pop("_id")
            return BackendConfigSchemaIn(**backend_config_dict)

        # work with the signed backend this is working normally due to the mongodb API, but to make
        # mypy happy, we have to check if the signed_backend_config_dict is not None
        elif signed_backend_config_dict:
            payload = signed_backend_config_dict["payload"]
            return BackendConfigSchemaIn(**payload)

        raise FileNotFoundError("The backend does not exist for the given storage.")

    def _delete_config(self, display_name: DisplayNameStr) -> bool:
        """
        Delete a config from the storage. This is only intended for test purposes.

        Args:
            display_name: The name of the backend to which we want to upload the job

        Raises:
            FileNotFoundError: If the config does not exist.

        Returns:
            Success if the file was deleted successfully
        """

        config_dict = self.get_config(display_name)
        _, collection = self._get_database_and_collection(self.configs_path)

        if not config_dict.sign:
            document_to_find = {"display_name": display_name}
        else:
            document_to_find = {"payload.display_name": display_name}

        result_found = collection.find_one(document_to_find)
        if result_found is None:
            raise FileNotFoundError(f"the config for {display_name} does not exist.")
        self.delete(self.configs_path, str(result_found["_id"]))

        return True

    def create_job_id(self, display_name: DisplayNameStr, username: str) -> str:
        """
        Create a job id for the job.

        Returns:
            The job id
        """
        return (uuid.uuid4().hex)[:24]

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
        status_json_dir = self.get_attribute_path("status", display_name)

        self.delete(storage_path=status_json_dir, job_id=job_id)
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
        result_json_dir = self.get_attribute_path("results", display_name, job_id)

        self.delete(storage_path=result_json_dir, job_id=job_id)
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
        _, collection = self._get_database_and_collection(pks_path)

        # first we have to check if the device already exists in the database
        document_to_find = {"kid": config_dict.kid}

        result_found = collection.find_one(document_to_find)
        if result_found:
            # update the file
            self.update(
                content_dict=public_jwk.model_dump(),
                storage_path=pks_path,
                job_id=result_found["_id"],
            )
            return

        # if the device does not exist, we have to create it
        config_id = uuid.uuid4().hex[:24]
        self.upload(public_jwk.model_dump(), pks_path, config_id)

    def get_public_key(self, display_name: DisplayNameStr) -> JWK:
        """
        The function that gets the spooler public JWK for the device.

        Args:
            display_name : The name of the backend

        Returns:
            JWk : The public JWK object
        """

        # get the database on which we work
        pks_path = self.get_attribute_path("pks")
        _, collection = self._get_database_and_collection(pks_path)

        # now get the appropiate kid
        config_dict = self.get_config(display_name)
        if config_dict.kid is None:
            raise ValueError("The kid is not set in the backend configuration.")

        # create the filter for the document with display_name that is equal to display_name
        document_to_find = {"kid": config_dict.kid}
        public_jwk_dict = collection.find_one(document_to_find)

        if not public_jwk_dict:
            raise FileNotFoundError("The backend does not exist for the given storage.")

        public_jwk_dict.pop("_id")
        return JWK(**public_jwk_dict)

    def _delete_public_key(self, kid: str) -> bool:
        """
        Delete a public key from the storage. This is only intended for test purposes.

        Args:
            kid: The key id of the public key

        Raises:
            FileNotFoundError: If the public key does not exist.

        Returns:
            Success if the file was deleted successfully
        """
        document_to_find = {"kid": kid}
        # get the database on which we work
        pks_path = self.get_attribute_path("pks")
        _, collection = self._get_database_and_collection(pks_path)

        result_found = collection.find_one(document_to_find)
        if result_found is None:
            raise FileNotFoundError(f"The public key with kid {kid} does not exist")
        self.delete(pks_path, str(result_found["_id"]))
        return True

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

        job_json_start_dir = self.get_attribute_path("running")
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
            job_finished_json_dir = self.get_attribute_path(
                "finished", display_name=display_name
            )
            self.move(job_json_start_dir, job_finished_json_dir, job_id)

        elif status_msg_dict.status == "ERROR":
            # because there was an error, we move the job to the deleted jobs
            deleted_json_dir = self.get_attribute_path("deleted")
            self.move(job_json_start_dir, deleted_json_dir, job_id)

        # TODO: most likely we should raise an error if the status of the job is not DONE or ERROR

        # and create the status json file
        status_json_dir = self.get_attribute_path("status", display_name)

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
        Get a list of documents in the collection of all the queued jobs.

        Args:
            storage_path: Where are we looking for the files.

        Returns:
            A list of files that was found.
        """

        _, collection = self._get_database_and_collection(storage_path)

        # now get the id of all the documents in the collection
        results = collection.find({}, {"_id": 1})
        file_list = []
        for result in results:
            file_list.append(str(result["_id"]))
        return file_list


class MongodbProvider(MongodbProviderExtended):
    """
    The access to the mongodb. This is the simplified version for people that are running devices.
    """

    def __init__(self, login_dict: MongodbLoginInformation) -> None:
        """
        Set up the neccessary keys and create the client through which all the connections will run.
        """
        super().__init__(login_dict, name="default", is_active=True)
