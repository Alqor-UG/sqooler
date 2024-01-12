"""
This module contains some functions that are especially helpful for deployment of the 
sqooler package.
"""

import time
import traceback
import regex as re

from .schemes import Spooler, ResultDict, StatusMsgDict, ExperimentDict
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
        status_msg_draft = {
            "job_id": job_dict["job_id"],
            "status": "None",
            "detail": "None",
            "error_message": "None",
        }
        status_msg_dict = StatusMsgDict(**status_msg_draft)
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
            status_msg_dict.status = "ERROR"
            status_msg_dict.detail += "; " + slimmed_tb
            status_msg_dict.error_message += "; " + slimmed_tb

        storage_provider.update_in_database(
            result_dict, status_msg_dict, job_dict["job_id"], requested_backend
        )

        counter += 1


def create_memory_data(
    shots_array: list, exp_name: str, n_shots: int
) -> ExperimentDict:
    """
    The function to create memory key in results dictionary
    with proprer formatting.
    """
    exp_sub_dict: dict = {
        "header": {"name": "experiment_0", "extra metadata": "text"},
        "shots": 3,
        "success": True,
        "data": {"memory": None},
    }

    exp_sub_dict["header"]["name"] = exp_name
    exp_sub_dict["shots"] = n_shots
    memory_list = [
        str(shot).replace("[", "").replace("]", "").replace(",", "")
        for shot in shots_array
    ]
    exp_sub_dict["data"]["memory"] = memory_list
    return ExperimentDict(**exp_sub_dict)


def run_json_circuit(json_dict: dict, job_id: str, spooler: Spooler) -> dict:
    """
    A support function that executes the job. Should be only used for testing.

    Args:
        json_dict: the job dict that will be treated
        job_id: the number of the job
        spooler: the spooler that will be used

    Returns:
        the results dict
    """
    status_msg_draft = {
        "job_id": job_id,
        "status": "None",
        "detail": "None",
        "error_message": "None",
    }
    status_msg_dict = StatusMsgDict(**status_msg_draft)

    result_dict, status_msg_dict = spooler.add_job(json_dict, status_msg_dict)
    assert status_msg_dict.status == "DONE", "Job failed"
    return result_dict.model_dump()
