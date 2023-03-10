"""
The module that contains all the necessary logic for processing jobs in the database queue.
"""
import importlib
import json
import time
import os
import shutil
import traceback
import regex as re

from utils import drpbx

from singlequdit.spooler_singlequdit import sq_spooler
from multiqudit.spooler_multiqudit import mq_spooler
from fermions.spooler_fermions import f_spooler
from rydberg.spooler_rydberg import ryd_spooler

backends = {
    "singlequdit": sq_spooler,
    "multiqudit": mq_spooler,
    "fermions": f_spooler,
    "rydberg": ryd_spooler,
}


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
        # the path and name
        dbx_path = "/Backend_files/Config/" + requested_backend + "/config.json"

        # the content
        backend_config_dict = spooler.get_configuration()

        result_binary = json.dumps(backend_config_dict).encode("utf-8")
        # upload the content
        drpbx.upload(result_binary, dbx_path)


def main() -> None:
    """
    Function for processing jobs continuously.
    """
    # TODO: This should be pull in automatically from the back-end config at some point.
    backends_list = list(backends.keys())

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
        job_dict = drpbx.get_next_job_in_queue(requested_backend)
        if job_dict["job_json_path"] == "None":
            continue
        job_json_dict = json.loads(
            drpbx.get_file_content(dbx_path=job_dict["job_json_path"])
        )

        requested_spooler = importlib.import_module(
            f"{requested_backend}.spooler_" + requested_backend
        )
        add_job = getattr(requested_spooler, "add_job")
        result_dict = {}
        status_msg_dict = {
            "job_id": job_dict["job_id"],
            "status": "None",
            "detail": "None",
            "error_message": "None",
        }

        # Fix this pylint issue whenever you have time, but be careful !
        # pylint: disable=W0703
        try:
            result_dict, status_msg_dict = add_job(job_json_dict, status_msg_dict)
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
        drpbx.update_in_database(result_dict, status_msg_dict, job_dict["job_id"])


if __name__ == "__main__":
    print("Update")
    update_backends()
    print("Now run as usual.")
    main()
