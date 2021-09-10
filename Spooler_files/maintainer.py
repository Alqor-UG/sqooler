from drpbx import *
import requests
import importlib
import json
import time

username = "spooler"  #'synqs_test'#
password = "This_APP==*cool*"
server_domain = "http://qsim-drop.herokuapp.com/"
backends_list = ["fermions", "singlequdit", "multiqudit"]
# Loop
while True:
    time.sleep(2)
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
    print(job_json_path)

    job_json_dict = json.loads(get_file_content(DROPBOXPATH=job_json_path))

    requested_spooler = importlib.import_module(
        "spooler_" + requested_backend
    )  # __import__('spooler_' + requested_backend)
    add_job = getattr(requested_spooler, "add_job")
    add_job(job_json_dict, status_msg_dict)
