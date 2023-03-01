"""
The module that contains all the necessary logic for the accessing the database.

This is mostly based on Dropbox for the moment. So it is closely related to the StorageProvider
in `qlued`.
"""

import sys
from typing import List
import json

import dropbox  # type: ignore
from dropbox.files import WriteMode  # type: ignore
from dropbox.exceptions import ApiError, AuthError  # type: ignore

from decouple import config  # type: ignore

APP_KEY = config("APP_KEY")
REFRESH_TOKEN = config("REFRESH_TOKEN")
APP_SECRET = config("APP_SECRET")

# Uploads contents of dump_str to Dropbox
def upload(dump_str: bytes, dbx_path: str) -> None:
    """
    Upload the file identified to the dropbox.

    dump_str: the content that should be written into the file
    """
    # Create an instance of a Dropbox class, which can make requests to the API.
    with dropbox.Dropbox(
        app_key=APP_KEY,
        app_secret=APP_SECRET,
        oauth2_refresh_token=REFRESH_TOKEN,
    ) as dbx:
        # Check that the access token is valid
        try:
            dbx.users_get_current_account()
        except AuthError:
            sys.exit("ERROR: Invalid access token.")
        try:
            dbx.files_upload(dump_str, dbx_path, mode=WriteMode("overwrite"))
        except ApiError as err:
            print(err)
            sys.exit()


def get_file_content(dbx_path: str) -> str:
    """
    Get the file content from the dropbox.
    """
    # Create an instance of a Dropbox class, which can make requests to the API.
    with dropbox.Dropbox(
        app_key=APP_KEY,
        app_secret=APP_SECRET,
        oauth2_refresh_token=REFRESH_TOKEN,
    ) as dbx:
        # Check that the access token is valid
        try:
            dbx.users_get_current_account()
        except AuthError:
            sys.exit("ERROR: Invalid access token.")
        try:
            _, res = dbx.files_download(path=dbx_path)
            data = res.content
            # print(data)
        except ApiError as err:
            print(err)
            sys.exit()
    return data


def move_file(start_path: str, final_path: str) -> None:
    """
    Move the file from start_path to final_path.
    """
    # Create an instance of a Dropbox class, which can make requests to the API.
    with dropbox.Dropbox(
        app_key=APP_KEY,
        app_secret=APP_SECRET,
        oauth2_refresh_token=REFRESH_TOKEN,
    ) as dbx:
        # Check that the access token is valid
        try:
            dbx.users_get_current_account()
        except AuthError:
            sys.exit("ERROR: Invalid access token.")
        try:
            _ = dbx.files_move_v2(start_path, final_path)
            # print(_)
        except ApiError as err:
            print(err)
            sys.exit()


def update_in_database(result_dict: dict, status_msg_dict: dict, job_id: str) -> None:
    """
    Upload the status and result to the dropbox.
    """
    extracted_username = job_id.split("-")[2]
    requested_backend = job_id.split("-")[1]

    status_json_dir = (
        "/Backend_files/Status/" + requested_backend + "/" + extracted_username + "/"
    )
    status_json_name = "status-" + job_id + ".json"
    status_json_path = status_json_dir + status_json_name

    job_json_name = "job-" + job_id + ".json"
    job_json_start_path = "/Backend_files/Running_Jobs/" + job_json_name

    if status_msg_dict["status"] == "DONE":
        result_json_dir = (
            "/Backend_files/Result/"
            + requested_backend
            + "/"
            + extracted_username
            + "/"
        )
        result_json_name = "result-" + job_id + ".json"
        result_json_path = result_json_dir + result_json_name
        result_binary = json.dumps(result_dict).encode("utf-8")
        upload(dump_str=result_binary, dbx_path=result_json_path)
        finished_json_dir = (
            "/Backend_files/Finished_Jobs/"
            + requested_backend
            + "/"
            + extracted_username
            + "/"
        )
        job_json_final_path = finished_json_dir + job_json_name
        move_file(start_path=job_json_start_path, final_path=job_json_final_path)
    elif status_msg_dict["status"] == "ERROR":
        deleted_json_dir = "/Backend_files/Deleted_Jobs/"
        job_json_final_path = deleted_json_dir + job_json_name
        move_file(start_path=job_json_start_path, final_path=job_json_final_path)

    status_binary = json.dumps(status_msg_dict).encode("utf-8")
    upload(dump_str=status_binary, dbx_path=status_json_path)


def get_file_queue(storage_path: str) -> List[str]:
    """
    Get a list of files

    Args:
        storage_path: Where are we looking for the files.

    Returns:
        A list of files that was found.
    """

    # Create an instance of a Dropbox class, which can make requests to the API.
    file_list = []
    with dropbox.Dropbox(
        app_key=APP_KEY,
        app_secret=APP_SECRET,
        oauth2_refresh_token=REFRESH_TOKEN,
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


def get_next_job_in_queue(backend_name: str) -> dict:
    """
    A function that obtains the next job in the queue.

    Args:
        backend_name (str): The name of the backend

    Returns:
        the path towards the job
    """
    job_json_dir = "/Backend_files/Queued_Jobs/" + backend_name + "/"
    job_dict = {"job_id": 0, "job_json_path": "None"}
    job_list = get_file_queue(job_json_dir)
    # if there is a job, we should move it
    if job_list:
        job_json_name = job_list[0]
        job_dict["job_id"] = job_json_name[4:-5]
        job_json_start_path = job_json_dir + job_json_name
        job_json_final_path = "/Backend_files/Running_Jobs/" + job_json_name
        move_file(start_path=job_json_start_path, final_path=job_json_final_path)
        job_dict["job_json_path"] = job_json_final_path
    return job_dict
