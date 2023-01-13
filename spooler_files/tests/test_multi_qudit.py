"""
Test module for the spooler_multiqudit.py file.
"""

from typing import Union
import numpy as np
import pytest

from pydantic import ValidationError

# pylint: disable=C0413, E0401
from spooler_files.schemes import gate_dict_from_list
from spooler_files.spooler_multiqudit import mq_spooler, gen_circuit
from spooler_files.spooler_multiqudit import (
    MultiQuditExperiment,
    LocalRotationInstruction,
    LocalSqueezingInstruction,
    QuditQuditInstruction,
)


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
        "backend_name": "synqs_multi_qudit_simulator",
        "backend_version": "0.0.1",
        "job_id": job_id,
        "qobj_id": None,
        "success": True,
        "status": "finished",
        "header": {},
        "results": [],
    }
    err_msg, json_is_fine = mq_spooler.check_json_dict(json_dict)
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


def test_pydantic_exp_validation():
    """
    Test that the validation of the experiment is working
    """
    experiment = {
        "instructions": [
            ["rlz", [0], [0.7]],
            ["measure", [0], []],
        ],
        "num_wires": 1,
        "shots": 3,
    }
    MultiQuditExperiment(**experiment)

    with pytest.raises(ValidationError):
        poor_experiment = {
            "instructions": [
                ["load", [7], []],
                ["load", [2], []],
                ["measure", [2], []],
                ["measure", [6], []],
                ["measure", [7], []],
            ],
            "num_wires": 400,
            "shots": 4,
            "wire_order": "sequential",
        }
        MultiQuditExperiment(**poor_experiment)


def test_local_rot_instruction():
    """
    Test that the hop instruction instruction is properly constrained.
    """
    inst_list = ["rlx", [0], [0.7]]
    gate_dict = gate_dict_from_list(inst_list)
    assert gate_dict == {
        "name": inst_list[0],
        "wires": inst_list[1],
        "params": inst_list[2],
    }
    LocalRotationInstruction(**gate_dict)

    inst_list = ["rlz", [0], [0.7]]
    gate_dict = gate_dict_from_list(inst_list)
    LocalRotationInstruction(**gate_dict)

    # test that the name is nicely fixed
    with pytest.raises(ValidationError):
        poor_inst_list = ["rly", [0], [0.7]]
        gate_dict = gate_dict_from_list(poor_inst_list)
        LocalRotationInstruction(**gate_dict)

    # test that we cannot give too many wires
    with pytest.raises(ValidationError):
        poor_inst_list = ["rlx", [0, 1], [0.7]]
        gate_dict = gate_dict_from_list(poor_inst_list)
        LocalRotationInstruction(**gate_dict)

    # make sure that the wires cannot be above the limit
    with pytest.raises(ValidationError):
        poor_inst_list = ["rlx", [200], [0.7]]
        gate_dict = gate_dict_from_list(poor_inst_list)
        LocalRotationInstruction(**gate_dict)

    # make sure that the parameters are enforced to be within the limits
    with pytest.raises(ValidationError):
        poor_inst_list = ["rlx", [0], [3 * np.pi]]
        gate_dict = gate_dict_from_list(poor_inst_list)
        LocalRotationInstruction(**gate_dict)


def test_squeezing_instruction():
    """
    Test that the local squeezing instruction constrained.
    """
    inst_list = ["rlz2", [0], [0.7]]
    gate_dict = gate_dict_from_list(inst_list)
    assert gate_dict == {
        "name": inst_list[0],
        "wires": inst_list[1],
        "params": inst_list[2],
    }
    LocalSqueezingInstruction(**gate_dict)

    # test that the name is nicely fixed
    with pytest.raises(ValidationError):
        poor_inst_list = ["rlz22", [0], [0.7]]
        gate_dict = gate_dict_from_list(poor_inst_list)
        LocalSqueezingInstruction(**gate_dict)

    # test that we cannot give too many wires
    with pytest.raises(ValidationError):
        poor_inst_list = ["rlz2", [0, 1], [0.7]]
        gate_dict = gate_dict_from_list(poor_inst_list)
        LocalSqueezingInstruction(**gate_dict)

    # make sure that the wires cannot be above the limit
    with pytest.raises(ValidationError):
        poor_inst_list = ["rlz2", [200], [0.7]]
        gate_dict = gate_dict_from_list(poor_inst_list)
        LocalSqueezingInstruction(**gate_dict)

    # make sure that the parameters are enforced to be within the limits
    with pytest.raises(ValidationError):
        poor_inst_list = ["rlz2", [0], [200 * np.pi]]
        gate_dict = gate_dict_from_list(poor_inst_list)
        LocalSqueezingInstruction(**gate_dict)


def test_qudit_qudit_instruction():
    """
    Test that the qudit qudit instruction instruction is properly constrained.
    """
    inst_list = ["rlxly", [0, 1], [0.7]]
    gate_dict = gate_dict_from_list(inst_list)
    assert gate_dict == {
        "name": inst_list[0],
        "wires": inst_list[1],
        "params": inst_list[2],
    }
    QuditQuditInstruction(**gate_dict)

    inst_list = ["rlzlz", [0, 1], [0.7]]
    gate_dict = gate_dict_from_list(inst_list)
    QuditQuditInstruction(**gate_dict)

    # test that the name is nicely fixed
    with pytest.raises(ValidationError):
        poor_inst_list = ["rlzls", [0, 1], [0.7]]
        gate_dict = gate_dict_from_list(poor_inst_list)
        QuditQuditInstruction(**gate_dict)

    # test that we cannot give too few wires
    with pytest.raises(ValidationError):
        poor_inst_list = ["rlxly", [0], [0.7]]
        gate_dict = gate_dict_from_list(poor_inst_list)
        QuditQuditInstruction(**gate_dict)

    # make sure that the wires cannot be above the limit
    with pytest.raises(ValidationError):
        poor_inst_list = ["rlxly", [0, 200], [0.7]]
        gate_dict = gate_dict_from_list(poor_inst_list)
        QuditQuditInstruction(**gate_dict)

    # make sure that the parameters are enforced to be within the limits
    with pytest.raises(ValidationError):
        poor_inst_list = ["rlxly", [0, 1], [200 * np.pi]]
        gate_dict = gate_dict_from_list(poor_inst_list)
        QuditQuditInstruction(**gate_dict)


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


def test_barrier_gate():
    """
    Test that the barrier can be properly applied.
    """

    # first submit the job
    job_payload = {
        "experiment_0": {
            "instructions": [
                ["barrier", [0, 1], []],
                ["measure", [0], []],
            ],
            "num_wires": 2,
            "shots": 3,
            "wire_order": "sequential",
        }
    }

    job_id = 1
    data = run_json_circuit(job_payload, job_id)

    shots_array = data["results"][0]["data"]["memory"]
    assert data["job_id"] == 1, "job_id got messed up"
    assert len(shots_array) > 0, "shots_array got messed up"


def test_rlxly_gate():
    """
    Test that the barrier can be properly applied.
    """

    # first submit the job
    job_payload = {
        "experiment_0": {
            "instructions": [
                ["load", [0], [10.0]],
                ["load", [1], [1.0]],
                ["rlx", [0], [1.5707963267948966]],
                ["barrier", [0, 1], []],
                ["rlz2", [0], [0.0]],
                ["rlz", [1], [0.0]],
                ["rlxly", [0, 1], [0.0]],
                ["barrier", [0, 1], []],
                ["measure", [0], []],
                ["measure", [1], []],
            ],
            "num_wires": 2,
            "shots": 150,
            "wire_order": "sequential",
        }
    }

    job_id = 1
    data = run_json_circuit(job_payload, job_id)

    shots_array = data["results"][0]["data"]["memory"]
    assert data["job_id"] == 1, "job_id got messed up"
    assert len(shots_array) > 0, "shots_array got messed up"

    # also spins of same length
    job_payload = {
        "experiment_0": {
            "instructions": [
                ["load", [0], [1.0]],
                ["load", [1], [1.0]],
                ["rlx", [0], [np.pi]],
                ["rlxly", [0, 1], [np.pi / 2]],
                ["measure", [0], []],
                ["measure", [1], []],
            ],
            "num_wires": 2,
            "shots": 150,
            "wire_order": "sequential",
        }
    }

    job_id = 2
    data = run_json_circuit(job_payload, job_id)

    shots_array = data["results"][0]["data"]["memory"]
    assert shots_array[0] == "0 1", "job_id got messed up"
    assert data["job_id"] == 2, "job_id got messed up"
    assert len(shots_array) > 0, "shots_array got messed up"