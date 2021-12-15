from drpbx import *
import requests
import importlib
import json
import time
import os
import shutil


def new_files_exist():
    new_files = False
    pulled_dir = "/home/ubuntu/Spooler_files_pulled/Spooler_files"
    dst_dir = "/home/ubuntu/Spooler_files"
    if not os.path.isdir(pulled_dir):
        return new_files
    new_files = True
    pulled_files = [os.path.join(pulled_dir, fn) for fn in next(os.walk(pulled_dir))[2]]
    dst_files = [os.path.join(dst_dir, fn) for fn in next(os.walk(pulled_dir))[2]]
    for i in range(len(pulled_files)):
        src_path = pulled_files[i]
        dst_path = dst_files[i]
        shutil.copy(src_path, dst_path)
    shutil.rmtree(pulled_dir)
    return new_files


username = "spooler"  #'synqs_test'#
password = "This_APP==*cool*"
server_domain = "http://coquma-sim.herokuapp.com/"  # "http://qsim-drop.herokuapp.com/"#
backends_list = ["fermions", "singlequdit", "multiqudit"]
# Loop
while True:
    time.sleep(1)
    new_files = new_files_exist()
    if new_files:
        raise ValueError("New files must have come. So break to restart the program!")

    requested_backend = backends_list[0]
    backends_list.append(backends_list.pop(0))

    query_url = server_domain + requested_backend + "/get_next_job_in_queue/"
    queue_response = requests.get(
        query_url, params={"username": username, "password": password}
    )

    job_json_path = (queue_response.json())["job_json"]
    job_id = (queue_response.json())["job_id"]
    if job_json_path == "None":
        continue

    query_url = server_domain + requested_backend + "/get_job_status/"
    status_payload = {"job_id": job_id}
    queue_response = requests.get(
        query_url,
        params={
            "json": json.dumps(status_payload),
            "username": username,
            "password": password,
        },
    )
    status_msg_dict = queue_response.json()
    # print(job_json_path)

    job_json_dict = json.loads(get_file_content(DROPBOXPATH=job_json_path))

    requested_spooler = importlib.import_module(
        "spooler_" + requested_backend
    )  # __import__('spooler_' + requested_backend)
    add_job = getattr(requested_spooler, "add_job")
    add_job(job_json_dict, status_msg_dict)
