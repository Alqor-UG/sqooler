import pytest

import sys, os

sys.path.append(os.path.join(os.path.dirname(__file__), "..", "spooler_files"))

from spooler_fermions import *


def run_json_circuit(json_dict, job_id):
    result_dict = {
        "backend_name": "synqs_fermionic_tweezer_simulator",
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


def test_wire_order():
    """
    Test that the wire_order is properly working.
    """

    # first submit the job
    job_payload = {
        "experiment_0": {
            "instructions": [
                ["load", [7], []],
                ["load", [2], []],
                ["measure", [2], []],
                ["measure", [6], []],
                ["measure", [7], []],
            ],
            "num_wires": 8,
            "shots": 4,
            "wire_order": "sequential",
        },
    }

    job_id = 1
    try:
        data = run_json_circuit(job_payload, job_id)
    except AssertionError as ass_err:
        print("Sucessfully triggered AssertionError", str(ass_err))


def test_load_gate():
    """
    Test that the loading is properly working.
    """

    # first submit the job
    job_payload = {
        "experiment_0": {
            "instructions": [
                ["load", [7], []],
                ["load", [2], []],
                ["measure", [2], []],
                ["measure", [6], []],
                ["measure", [7], []],
            ],
            "num_wires": 8,
            "shots": 4,
            "wire_order": "interleaved",
        },
    }

    job_id = 1
    data = run_json_circuit(job_payload, job_id)

    shots_array = data["results"][0]["data"]["memory"]
    assert data["job_id"] == 1, "job_id got messed up"
    assert len(shots_array) > 0, "shots_array got messed up"
    assert shots_array[0] == "1 0 1", "shots_array got messed up"


def test_hop_gate():
    """
    Test that the hopping is properly working.
    """

    # first submit the job
    job_payload = {
        "experiment_0": {
            "instructions": [
                ["load", [0], []],
                ["load", [4], []],
                ["hop", [0, 4, 1, 5], [np.pi / 2]],
                ["measure", [0], []],
                ["measure", [1], []],
                ["measure", [4], []],
                ["measure", [5], []],
            ],
            "num_wires": 8,
            "shots": 4,
            "wire_order": "interleaved",
        },
    }

    job_id = 1
    data = run_json_circuit(job_payload, job_id)

    shots_array = data["results"][0]["data"]["memory"]
    assert data["job_id"] == 1, "job_id got messed up"
    assert len(shots_array) > 0, "shots_array got messed up"
    assert shots_array[0] == "0 1 0 1", "shots_array got messed up"


def test_phase_gate():
    """
    Test that the phase gate is properly working.
    """

    # first submit the job
    job_payload = {
        "experiment_0": {
            "instructions": [
                ["load", [0], []],
                ["hop", [0, 4, 1, 5], [np.pi / 4]],
                ["phase", [2, 6], [np.pi]],
                ["hop", [0, 4, 1, 5], [np.pi / 4]],
                ["measure", [0], []],
                ["measure", [1], []],
            ],
            "num_wires": 8,
            "shots": 2,
            "wire_order": "interleaved",
        },
    }

    job_id = 1
    data = run_json_circuit(job_payload, job_id)

    shots_array = data["results"][0]["data"]["memory"]
    assert data["job_id"] == 1, "job_id got messed up"
    assert len(shots_array) > 0, "shots_array got messed up"
    assert shots_array[0] == "0 1", "shots_array got messed up"


def test_seed():
    """
    Test that the hopping is properly working.
    """

    # first submit the job
    job_payload = {
        "experiment_0": {
            "instructions": [
                ["load", [0], []],
                ["load", [1], []],
                ["hop", [0, 4, 1, 5], [np.pi / 4]],
                ["measure", [0], []],
                ["measure", [1], []],
                ["measure", [4], []],
                ["measure", [5], []],
            ],
            "num_wires": 8,
            "shots": 4,
            "wire_order": "interleaved",
            "seed": 12345,
        },
        "experiment_1": {
            "instructions": [
                ["load", [0], []],
                ["load", [1], []],
                ["hop", [0, 4, 1, 5], [np.pi / 4]],
                ["measure", [0], []],
                ["measure", [1], []],
                ["measure", [4], []],
                ["measure", [5], []],
            ],
            "num_wires": 8,
            "shots": 4,
            "wire_order": "interleaved",
            "seed": 12345,
        },
    }

    job_id = 1
    data = run_json_circuit(job_payload, job_id)

    shots_array_1 = data["results"][0]["data"]["memory"]
    shots_array_2 = data["results"][1]["data"]["memory"]
    assert data["job_id"] == 1, "job_id got messed up"
    assert len(shots_array_1) > 0, "shots_array got messed up"
    assert shots_array_1 == shots_array_2, "seed got messed up"
