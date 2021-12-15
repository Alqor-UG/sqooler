import pytest

import sys, os

sys.path.append(os.path.join(os.path.dirname(__file__), "..", "Spooler_files"))

from spooler_singlequdit import *


def run_json_circuit(json_dict, job_id):
    result_dict = {
        "backend_name": "synqs_single_qudit_simulator",
        "backend_version": "0.0.1",
        "job_id": job_id,
        "qobj_id": None,
        "success": True,
        "status": "finished",
        "header": {},
        "results": [],
    }
    err_msg, json_is_fine = check_json_dict(json_dict)
    assert json_is_fine == True, "Failed JSON sanity check : " + err_msg
    if json_is_fine:
        for exp in json_dict:
            exp_dict = {exp: json_dict[exp]}
            # Here we
            result_dict["results"].append(gen_circuit(exp_dict, job_id))

    return result_dict


###########################
###########################
# __Put all tests below__#
###########################
###########################


def test_z_gate():
    """
    Test that the z gate is properly applied.
    """

    # first submit the job
    job_payload = {
        "experiment_0": {
            "instructions": [
                ["rlz", [0], [0.7]],
                ["measure", [0], []],
            ],
            "num_wires": 1,
            "shots": 3,
        },
        "experiment_1": {
            "instructions": [
                ["rlz", [0], [0.7]],
                ["measure", [0], []],
            ],
            "num_wires": 1,
            "shots": 3,
        },
    }

    job_id = 1
    data = run_json_circuit(job_payload, job_id)

    shots_array = data["results"][0]["data"]["memory"]
    assert data["job_id"] == 1, "job_id got messed up"
    assert len(shots_array) > 0, "shots_array got messed up"
