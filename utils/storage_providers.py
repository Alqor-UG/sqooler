"""
The module that contains all the necessary logic for communication with the external
storage for the jobs. It creates an abstract API layer for the storage providers.
"""
import sys

from abc import ABC, abstractmethod
import json

import dropbox
from dropbox.files import WriteMode
from dropbox.exceptions import ApiError, AuthError

# necessary for the mongodb provider
from pymongo.mongo_client import MongoClient
from bson.objectid import ObjectId

# get the environment variables
from decouple import config


class StorageProvider(ABC):
    """
    The template for accessing any storage providers like dropbox, mongodb, amazon S3 etc.
    """

    @abstractmethod
    def upload(self, content_dict: dict, storage_path: str, job_id: str) -> None:
        """
        Upload the file to the storage
        """

    @abstractmethod
    def get_file_content(self, storage_path: str, job_id: str) -> dict:
        """
        Get the file content from the storage
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
    def update_in_database(
        self, result_dict: dict, status_msg_dict: dict, job_id: str
    ) -> None:
        """
        Upload the status and result to the `StorageProvider`.

        Args:
            result_dict: the dictionary containing the result of the job
            status_msg_dict: the dictionary containing the status message of the job
            job_id: the name of the job

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


class DropboxProvider(StorageProvider):
    """
    The class that implements the dropbox storage provider.
    """

    def __init__(self) -> None:
        """
        Set up the neccessary keys.
        """
        self.app_key = config("APP_KEY")
        self.app_secret = config("APP_SECRET")
        self.refresh_token = config("REFRESH_TOKEN")

    def upload(self, content_dict: dict, storage_path: str, job_id: str) -> None:
        """
        Upload the content_dict as a json file to the dropbox

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

    def update_in_database(
        self, result_dict: dict, status_msg_dict: dict, job_id: str
    ) -> None:
        """
        Upload the status and result to the dropbox.

        Args:
            result_dict: the dictionary containing the result of the job
            status_msg_dict: the dictionary containing the status message of the job
            job_id: the name of the job

        Returns:
            None
        """
        # this should become part of the json file instead of its name in the future
        extracted_username = job_id.split("-")[2]
        requested_backend = job_id.split("-")[1]

        status_json_dir = (
            "/Backend_files/Status/"
            + requested_backend
            + "/"
            + extracted_username
            + "/"
        )
        status_json_name = "status-" + job_id

        job_json_name = "job-" + job_id
        job_json_start_dir = "Backend_files/Running_Jobs"

        if status_msg_dict["status"] == "DONE":
            # let us create the result json file
            result_json_dir = (
                "/Backend_files/Result/"
                + requested_backend
                + "/"
                + extracted_username
                + "/"
            )
            result_json_name = "result-" + job_id
            self.upload(result_dict, result_json_dir, result_json_name)

            # now move the job out of the running jobs into the finished jobs
            job_finished_json_dir = (
                "/Backend_files/Finished_Jobs/"
                + requested_backend
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

class MongodbProvider(StorageProvider):
    """
    The access to the mongodb
    """

    def __init__(self) -> None:
        """
        Set up the neccessary keys and create the client through which all the connections will run.
        """
        mongodb_username = config("MONGODB_USERNAME")
        mongodb_password = config("MONGODB_PASSWORD")
        mongodb_database_url = config("MONGODB_DATABASE_URL")

        uri = f"mongodb+srv://{mongodb_username}:{mongodb_password}@{mongodb_database_url}/?retryWrites=true&w=majority"
        # Create a new client and connect to the server
        self.client: MongoClient = MongoClient(uri)

        # Send a ping to confirm a successful connection
        self.client.admin.command("ping")

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
        return result_found

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

    
    def update_in_database(
        self, result_dict: dict, status_msg_dict: dict, job_id: str
    ) -> None:
        """
        Upload the status and result to the `StorageProvider`.

        Args:
            result_dict: the dictionary containing the result of the job
            status_msg_dict: the dictionary containing the status message of the job
            job_id: the name of the job

        Returns:
            None
        """

    
    def get_file_queue(self, storage_path: str) -> list[str]:
        """
        Get a list of files

        Args:
            storage_path: Where are we looking for the files.

        Returns:
            A list of files that was found.
        """

   
    def get_next_job_in_queue(self, backend_name: str) -> dict:
        """
        A function that obtains the next job in the queue.

        Args:
            backend_name (str): The name of the backend

        Returns:
            the path towards the job
        """