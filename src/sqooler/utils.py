"""
This module contains some functions that are especially helpful for deployment of the 
sqooler package.
"""

import time
import traceback
import regex as re

from .schemes import Spooler, ResultDict
from .storage_providers import StorageProvider


def update_backends(
    storage_provider: StorageProvider, backends: dict[str, Spooler]
) -> None:
    """
    Update the backends on the storage.

    Args:
        storage_provider: The storage provider that should be used.
        backends: A dictionary of all the backends that should be updated.

    Returns:
        None
    """
    for requested_backend, spooler in backends.items():
        # the content
        backend_config_dict = spooler.get_configuration()
        # set the display name
        backend_config_dict.display_name = requested_backend

        # upload the content through the storage provider
        storage_provider.upload_config(backend_config_dict, requested_backend)


def main(
    storage_provider: StorageProvider,
    backends: dict[str, Spooler],
    num_iter: int = 0,
) -> None:
    """
    Function for processing jobs continuously.

    Args:
        storage_provider: The storage provider that should be used.
        backends: A dictionary of all the backends that should be updated.
        num_iter: The number of iterations that should be done. If 0, then the loop
            will run forever.
    """
    backends_list = list(backends.keys())

    # set the appropiate display names for all the back-ends
    for requested_backend, spooler in backends.items():
        # the content
        spooler.display_name = requested_backend

    counter = 0
    # loop which is looking for the jobs
    while num_iter == 0 or counter < num_iter:
        time.sleep(0.2)

        # the following a fancy for loop of going through all the back-ends in the list
        requested_backend = backends_list[0]
        backends_list.append(backends_list.pop(0))
        # let us first see if jobs are waiting
        job_dict = storage_provider.get_next_job_in_queue(requested_backend)
        if job_dict["job_json_path"] == "None":
            continue
        job_json_dict = storage_provider.get_job_content(
            storage_path=job_dict["job_json_path"], job_id=job_dict["job_id"]
        )

        result_draft: dict = {
            "display_name": "",
            "backend_version": "",
            "job_id": "",
            "qobj_id": None,
            "success": True,
            "status": "finished",
            "header": {},
            "results": [],
        }

        result_dict = ResultDict(**result_draft)
        status_msg_dict = {
            "job_id": job_dict["job_id"],
            "status": "None",
            "detail": "None",
            "error_message": "None",
        }

        # Fix this pylint issue whenever you have time, but be careful !
        # pylint: disable=W0703
        try:
            result_dict, status_msg_dict = backends[requested_backend].add_job(
                job_json_dict, status_msg_dict
            )

        except Exception:
            # Remove sensitive info like filepaths
            tb_list = traceback.format_exc().splitlines()
            for i, dummy in enumerate(tb_list):
                tb_list[i] = re.sub(
                    r'File ".*[\\/]([^\\/]+.py)"', r'File "\1"', tb_list[i]
                )  # Regex for repalcing absolute filepath with only filename.
                # Basically search for slashes and replace with the first group or
                # bracketed expression which is obviously the filename.
            slimmed_tb = " ".join(tb_list)
            # Update status dict
            status_msg_dict["status"] = "ERROR"
            status_msg_dict["detail"] += "; " + slimmed_tb
            status_msg_dict["error_message"] += "; " + slimmed_tb

        storage_provider.update_in_database(
            result_dict, status_msg_dict, job_dict["job_id"], requested_backend
        )

        counter += 1
