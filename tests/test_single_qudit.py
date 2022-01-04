"""
Test module for the spooler_singlequdit.py file.
"""

import sys
import os
from typing import Union

# pylint: disable=C0413, E0401
sys.path.append(os.path.join(os.path.dirname(__file__), "..", "spooler_files"))
from spooler_singlequdit import check_json_dict, gen_circuit


def run_json_circuit(json_dict: dict, job_id: Union[int, str]) -> dict:
    """
    A support function that executes the job.

    Args:
        json_dict: the job dict that will be treated
        job_id: the number of the job

    Returns:
        the results dict
    """
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
    assert json_is_fine is True, "Failed JSON sanity check : " + err_msg
    if json_is_fine:
        for exp in json_dict:
            exp_dict = {exp: json_dict[exp]}
            # Here we
            result_dict["results"].append(gen_circuit(exp_dict))

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
            "wire_order": "sequential",
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
