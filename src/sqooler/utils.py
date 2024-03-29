"""
This module contains some functions that are especially helpful for deployment of the 
sqooler package.
"""

import time
import traceback
import regex as re

from .schemes import get_init_results, get_init_status
from .spoolers import Spooler
from .storage_providers.base import StorageProvider
from .security import public_from_private_jwk


def update_backends(
    storage_provider: StorageProvider, backends: dict[str, Spooler]
) -> None:
    """
    Update the backends on the storage.

    Args:
        storage_provider: The storage provider that should be used.
        backends: A dictionary of all the backends that should be updated.
    """
    for requested_backend, spooler in backends.items():
        # the content
        backend_config_dict = spooler.get_configuration()
        # set the display name
        backend_config_dict.display_name = requested_backend

        # upload the content through the storage provider
        storage_provider.upload_config(backend_config_dict, requested_backend)

        # upload the public key if the backend has one and is designed to sign
        if spooler.sign:
            private_jwk = spooler.get_private_jwk()
            public_jwk = public_from_private_jwk(private_jwk)
            storage_provider.upload_public_key(public_jwk, requested_backend)


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
        if job_dict.job_json_path == "None":
            continue
        job_json_dict = storage_provider.get_job_content(
            storage_path=job_dict.job_json_path, job_id=job_dict.job_id
        )

        result_dict = get_init_results()
        status_msg_dict = get_init_status()
        status_msg_dict.job_id = job_dict.job_id
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
            result_dict, status_msg_dict, job_dict.job_id, requested_backend
        )

        counter += 1


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
    status_msg_dict = get_init_status()
    status_msg_dict.job_id = job_id

    result_dict, status_msg_dict = spooler.add_job(json_dict, status_msg_dict)
    assert status_msg_dict.status == "DONE", "Job failed"
    return result_dict.model_dump()
