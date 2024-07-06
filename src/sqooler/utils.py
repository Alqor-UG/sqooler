"""
This module contains some functions that are especially helpful for deployment of the 
sqooler package.
"""

import logging
import time
import traceback
import uuid
from typing import Tuple

import regex as re
from decouple import config
from pydantic import ValidationError

from .schemes import (
    BackendConfigSchemaIn,
    NextJobSchema,
    get_init_results,
    get_init_status,
)
from .security import public_from_private_jwk
from .spoolers import Spooler
from .storage_providers.base import StorageProvider


def update_backends(
    storage_provider: StorageProvider, backends: dict[str, Spooler]
) -> None:
    """
    Update the backends on the storage. Uploads it as a new one if it fails.

    Args:
        storage_provider: The storage provider that should be used.
        backends: A dictionary of all the backends that should be updated.
    """
    for requested_backend, spooler in backends.items():
        # the content
        backend_config_dict = spooler.get_configuration()
        # set the display name
        backend_config_dict.display_name = requested_backend
        # upload the public key if the backend has one and is designed to sign
        if spooler.sign:
            private_jwk = spooler.get_private_jwk()
        else:
            private_jwk = None

        # upload the content through the storage provider
        try:
            storage_provider.update_config(
                backend_config_dict, requested_backend, private_jwk=private_jwk
            )

            logging.info(
                "Updated the config for %s .",
                requested_backend,
            )
        except FileNotFoundError:
            # this should become a log
            logging.warning(
                "Failed to update the configuration for %s . Uploading it as a new one.",
                requested_backend,
            )
            storage_provider.upload_config(
                backend_config_dict, requested_backend, private_jwk
            )

        if spooler.sign:
            # this line is IMHO needless but somehow mypy thinks that it could be a
            # None (no idea how this could happen)
            private_jwk = spooler.get_private_jwk()

            # this has to happen after the config was uploaded to be sure
            # the we know the appropiate kid
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

    t_wait_main = config("T_WAIT_MAIN", cast=float, default=0.2)
    while num_iter == 0 or counter < num_iter:
        time.sleep(t_wait_main)
        # the following a fancy for loop of going through all the back-ends in the list
        requested_backend = backends_list[0]
        backends_list.append(backends_list.pop(0))

        spooler = backends[requested_backend]
        # let us first see if jobs are waiting
        logging.info("Looking for jobs in %s", requested_backend)
        if spooler.sign:
            private_jwk = spooler.get_private_jwk()
        else:
            private_jwk = None
        try:
            job_dict = storage_provider.get_next_job_in_queue(
                requested_backend, private_jwk
            )
        except ValidationError as val_err:
            logging.error(
                "Validation error in job queue.",
                extra={"error_message": val_err.errors()},
            )
            job_dict = NextJobSchema(job_id="None", job_json_path="None")

        if job_dict.job_json_path == "None":
            counter += 1
            continue
        logging.debug("Got a job in %s", requested_backend)
        job_json_dict = storage_provider.get_job(
            storage_path=job_dict.job_json_path, job_id=job_dict.job_id
        )

        result_dict = get_init_results()
        # Fix this pylint issue whenever you have time, but be careful !
        # pylint: disable=W0703
        try:
            result_dict, status_msg_dict = backends[requested_backend].add_job(
                job_json_dict, job_dict.job_id
            )

        except Exception:
            # test if the status_msg_dict is already initialized
            if not status_msg_dict:
                status_msg_dict = get_init_status()
                status_msg_dict.job_id = job_dict.job_id
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
            logging.exception("Error in add_job for %s .", requested_backend)

        logging.debug("Updating in database.")
        storage_provider.update_in_database(
            result_dict,
            status_msg_dict,
            job_dict.job_id,
            requested_backend,
            private_jwk,
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

    result_dict, status_msg_dict = spooler.add_job(json_dict, job_id)
    if not status_msg_dict.status == "DONE":
        logging.error(status_msg_dict.error_message)
        raise AssertionError("Job failed")
    return result_dict.model_dump()


def get_dummy_config(sign: bool = True) -> Tuple[str, BackendConfigSchemaIn]:
    """
    Generate the dummy config of the fermion type.

    Args:
        sign: Whether to sign the files.
    Returns:
        The backend name and the backend config input.
    """

    dummy_id = uuid.uuid4().hex[:5]
    backend_name = f"dummy{dummy_id}"

    dummy_dict: dict = {}
    dummy_dict["gates"] = []
    dummy_dict["display_name"] = backend_name
    dummy_dict["num_wires"] = 3
    dummy_dict["version"] = "0.0.1"
    dummy_dict["description"] = "This is a dummy backend."
    dummy_dict["cold_atom_type"] = "fermion"
    dummy_dict["max_experiments"] = 1
    dummy_dict["max_shots"] = 1
    dummy_dict["simulator"] = True
    dummy_dict["supported_instructions"] = []
    dummy_dict["wire_order"] = "interleaved"
    dummy_dict["num_species"] = 1
    dummy_dict["sign"] = sign

    backend_info = BackendConfigSchemaIn(**dummy_dict)
    return backend_name, backend_info
