"""
The module that contains all the necessary logic for processing jobs in the database queue.
"""
import time
import os
import shutil
import traceback
import regex as re

# import the storage provider that you would like to use
# currently we have dropbox and mongodb
from utils.storage_providers import MongodbProvider

from singlequdit.config import spooler_object as sq_spooler
from multiqudit.config import spooler_object as mq_spooler
from fermions.config import spooler_object as f_spooler
from rydberg.config import spooler_object as ryd_spooler

# configure the backends
backends = {
    "singlequdit": sq_spooler,
    "multiqudit": mq_spooler,
    "fermions": f_spooler,
    "rydberg": ryd_spooler,
}

# configure the storage provider
storage_provider = MongodbProvider()


def new_files_exist() -> bool:
    """
    Check if new files have come from GitHub.

    This is important if you host it on your own machine and run the system through `keep_running.sh`
    and automatically deploy changes. The more modern way is to run through heroku,
    which handles those issues for you.
    """
    new_files = False
    pulled_dir = "/home/ubuntu/Spooler_files_pulled/spooler_files"
    dst_dir = "/home/ubuntu/Spooler_files"
    if not os.path.isdir(pulled_dir):
        return new_files
    new_files = True
    pulled_files = [os.path.join(pulled_dir, fn) for fn in next(os.walk(pulled_dir))[2]]
    dst_files = [os.path.join(dst_dir, fn) for fn in next(os.walk(pulled_dir))[2]]
    for src_path, dst_path in zip(pulled_files, dst_files):
        shutil.copy(src_path, dst_path)
    shutil.rmtree(pulled_dir)
    return new_files


def update_backends() -> None:
    """
    Update the backends on the storage.
    """
    for requested_backend, spooler in backends.items():
        # the content
        backend_config_dict = spooler.get_configuration()
        # set the display name
        backend_config_dict["display_name"] = requested_backend

        # upload the content through the storage provider
        storage_provider.upload_config(backend_config_dict, requested_backend)


def main() -> None:
    """
    Function for processing jobs continuously.
    """
    # TODO: This should be pull in automatically from the back-end config at some point.
    backends_list = list(backends.keys())

    # set the appropiate display names for all the back-ends
    for requested_backend, spooler in backends.items():
        # the content
        spooler.display_name = requested_backend

    # loop which is looking for the jobs
    while True:
        time.sleep(0.2)
        new_files = new_files_exist()
        if new_files:
            raise ValueError(
                "New files must have come. So break to restart the program!"
            )

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
        result_dict = None
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


if __name__ == "__main__":
    print("Update")
    update_backends()
    print("Now run as usual.")
    main()
