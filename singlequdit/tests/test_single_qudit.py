"""
Test module for the spooler_singlequdit.py file.
"""

from typing import Union
import pytest
from pydantic import ValidationError
import numpy as np

# pylint: disable=C0413, E0401
from singlequdit.spooler_singlequdit import (
    sq_spooler,
    gen_circuit,
    gate_dict_from_list,
    SingleQuditExperiment,
    LoadInstruction,
    MeasureBarrierInstruction,
    LocalSqueezingInstruction,
    RlzInstruction,
    RlxInstruction,
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
        "backend_name": "alqor_single_qudit_simulator",
        "backend_version": "0.0.1",
        "job_id": job_id,
        "qobj_id": None,
        "success": True,
        "status": "finished",
        "header": {},
        "results": [],
    }
    err_msg, json_is_fine = sq_spooler.check_json_dict(json_dict)
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
    SingleQuditExperiment(**experiment)

    with pytest.raises(ValidationError):
        poor_experiment = {
            "instructions": [
                ["load", [7], []],
                ["load", [2], []],
                ["measure", [2], []],
                ["measure", [6], []],
                ["measure", [7], []],
            ],
            "num_wires": 2,
            "shots": 4,
            "wire_order": "sequential",
        }
        SingleQuditExperiment(**poor_experiment)

    with pytest.raises(ValidationError):
        poor_experiment = {
            "instructions": [
                ["load", [7], []],
                ["load", [2], []],
                ["measure", [2], []],
                ["measure", [6], []],
                ["measure", [7], []],
            ],
            "num_wires": 1,
            "shots": 1e7,
            "wire_order": "sequential",
        }
        SingleQuditExperiment(**poor_experiment)

    inst_config = {
        "name": "rlx",
        "parameters": ["omega"],
        "qasm_def": "gate lrx(omega) {}",
        "coupling_map": [[0], [1], [2], [3], [4]],
        "description": "Evolution under Lx",
    }
    assert inst_config == RlxInstruction.config_dict()


def test_load_instruction():
    """
    Test that the load instruction instruction is properly constrained.
    """
    inst_list = ["load", [0], [200.0]]
    gate_dict = gate_dict_from_list(inst_list)
    assert gate_dict == {
        "name": inst_list[0],
        "wires": inst_list[1],
        "params": inst_list[2],
    }
    LoadInstruction(**gate_dict)

    # test that the name is nicely fixed
    with pytest.raises(ValidationError):
        poor_inst_list = ["loads", [0], [200.0]]
        gate_dict = gate_dict_from_list(poor_inst_list)
        LoadInstruction(**gate_dict)

    # test that we cannot give too many wires
    with pytest.raises(ValidationError):
        poor_inst_list = ["load", [0, 1], [200.0]]
        gate_dict = gate_dict_from_list(poor_inst_list)
        LoadInstruction(**gate_dict)

    # make sure that the wires cannot be above the limit
    with pytest.raises(ValidationError):
        poor_inst_list = ["load", [1], [200.0]]
        gate_dict = gate_dict_from_list(poor_inst_list)
        LoadInstruction(**gate_dict)

    # make sure that the parameters are enforced to be within the limits
    with pytest.raises(ValidationError):
        poor_inst_list = ["load", [0], [7e9]]
        gate_dict = gate_dict_from_list(poor_inst_list)
        LoadInstruction(**gate_dict)


def test_local_rot_instruction():
    """
    Test that the rotation instruction is properly constrained.
    """
    inst_list = ["rlx", [0], [np.pi / 2]]
    gate_dict = gate_dict_from_list(inst_list)
    assert gate_dict == {
        "name": inst_list[0],
        "wires": inst_list[1],
        "params": inst_list[2],
    }
    RlxInstruction(**gate_dict)

    inst_list = ["rlz", [0], [np.pi / 2]]
    gate_dict = gate_dict_from_list(inst_list)
    RlzInstruction(**gate_dict)

    # test that the name is nicely fixed
    with pytest.raises(ValidationError):
        poor_inst_list = ["rly", [0], [np.pi / 2]]
        gate_dict = gate_dict_from_list(poor_inst_list)
        RlxInstruction(**gate_dict)

    # test that we cannot give too many wires
    with pytest.raises(ValidationError):
        poor_inst_list = ["rlx", [0, 1], [np.pi / 2]]
        gate_dict = gate_dict_from_list(poor_inst_list)
        RlxInstruction(**gate_dict)

    # make sure that the wires cannot be above the limit
    with pytest.raises(ValidationError):
        poor_inst_list = ["rlx", [1], [np.pi / 2]]
        gate_dict = gate_dict_from_list(poor_inst_list)
        RlxInstruction(**gate_dict)

    # make sure that the parameters are enforced to be within the limits
    with pytest.raises(ValidationError):
        poor_inst_list = ["rlx", [0], [4 * np.pi]]
        gate_dict = gate_dict_from_list(poor_inst_list)
        RlxInstruction(**gate_dict)


def test_squeezing_instruction():
    """
    Test that the rotation instruction is properly constrained.
    """
    inst_list = ["rlz2", [0], [np.pi / 2]]
    gate_dict = gate_dict_from_list(inst_list)
    assert gate_dict == {
        "name": inst_list[0],
        "wires": inst_list[1],
        "params": inst_list[2],
    }
    LocalSqueezingInstruction(**gate_dict)

    # test that the name is nicely fixed
    with pytest.raises(ValidationError):
        poor_inst_list = ["rlz", [0], [np.pi / 2]]
        gate_dict = gate_dict_from_list(poor_inst_list)
        LocalSqueezingInstruction(**gate_dict)

    # test that we cannot give too many wires
    with pytest.raises(ValidationError):
        poor_inst_list = ["rlz2", [0, 1], [np.pi / 2]]
        gate_dict = gate_dict_from_list(poor_inst_list)
        LocalSqueezingInstruction(**gate_dict)

    # make sure that the wires cannot be above the limit
    with pytest.raises(ValidationError):
        poor_inst_list = ["rlz2", [1], [np.pi / 2]]
        gate_dict = gate_dict_from_list(poor_inst_list)
        LocalSqueezingInstruction(**gate_dict)

    # make sure that the parameters are enforced to be within the limits
    with pytest.raises(ValidationError):
        poor_inst_list = ["rlz2", [0], [400 * np.pi]]
        gate_dict = gate_dict_from_list(poor_inst_list)
        LocalSqueezingInstruction(**gate_dict)

    # test the config
    inst_config = {
        "name": "rlz2",
        "parameters": ["chi"],
        "qasm_def": "gate rlz2(chi) {}",
        "coupling_map": [[0], [1], [2], [3], [4]],
        "description": "Evolution under lz2",
    }
    assert inst_config == LocalSqueezingInstruction.config_dict()


def test_measure_instruction():
    """
    Test that the rotation instruction is properly constrained.
    """
    inst_list = ["measure", [0], []]
    gate_dict = gate_dict_from_list(inst_list)
    assert gate_dict == {
        "name": inst_list[0],
        "wires": inst_list[1],
        "params": inst_list[2],
    }
    MeasureBarrierInstruction(**gate_dict)

    # test that the name is nicely fixed
    with pytest.raises(ValidationError):
        poor_inst_list = ["measures", [0], []]
        gate_dict = gate_dict_from_list(poor_inst_list)
        MeasureBarrierInstruction(**gate_dict)

    # test that we cannot give too many wires
    with pytest.raises(ValidationError):
        poor_inst_list = ["measure", [0, 1], []]
        gate_dict = gate_dict_from_list(poor_inst_list)
        MeasureBarrierInstruction(**gate_dict)

    # make sure that the wires cannot be above the limit
    with pytest.raises(ValidationError):
        poor_inst_list = ["measure", [1], []]
        gate_dict = gate_dict_from_list(poor_inst_list)
        MeasureBarrierInstruction(**gate_dict)

    # make sure that the parameters are enforced to be within the limits
    with pytest.raises(ValidationError):
        poor_inst_list = ["measure", [0], [np.pi]]
        gate_dict = gate_dict_from_list(poor_inst_list)
        MeasureBarrierInstruction(**gate_dict)


def test_check_json_dict():
    """
    See if the check of the json dict works out properly.
    """
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
    _, json_is_fine = sq_spooler.check_json_dict(job_payload)
    assert json_is_fine


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

    # test the config
    inst_config = {
        "name": "rlz",
        "parameters": ["delta"],
        "qasm_def": "gate rlz(delta) {}",
        "coupling_map": [[0], [1], [2], [3], [4]],
        "description": "Evolution under the Z gate",
    }
    assert inst_config == RlzInstruction.config_dict()


def test_spooler_config():
    """
    Test that the back-end is properly configured and we can indeed provide those parameters
     as we would like.
    """
    sq_config_dict = {
        "name": "alqor_singlequdit_simulator",
        "description": "Setup of a cold atomic gas experiment with a single qudit.",
        "version": "0.0.2",
        "cold_atom_type": "spin",
        "gates": [
            {
                "name": "rlx",
                "parameters": ["omega"],
                "qasm_def": "gate lrx(omega) {}",
                "coupling_map": [[0], [1], [2], [3], [4]],
                "description": "Evolution under Lx",
            },
            {
                "name": "rlz",
                "parameters": ["delta"],
                "qasm_def": "gate rlz(delta) {}",
                "coupling_map": [[0], [1], [2], [3], [4]],
                "description": "Evolution under the Z gate",
            },
            {
                "name": "rlz2",
                "parameters": ["chi"],
                "qasm_def": "gate rlz2(chi) {}",
                "coupling_map": [[0], [1], [2], [3], [4]],
                "description": "Evolution under lz2",
            },
        ],
        "max_experiments": 1000,
        "max_shots": 1000000,
        "simulator": True,
        "supported_instructions": ["rlx", "rlz", "rlz2", "barrier", "measure", "load"],
        "num_wires": 1,
        "wire_order": "interleaved",
        "num_species": 1,
    }
    spooler_config_dict = sq_spooler.get_configuration()
    assert spooler_config_dict == sq_config_dict


def test_number_experiments():
    """
    Make sure that we cannot submit too many experiments.
    """

    # first test the system that is fine.

    inst_dict = {
        "instructions": [
            ["rlz", [0], [0.7]],
            ["measure", [0], []],
        ],
        "num_wires": 1,
        "shots": 3,
        "wire_order": "sequential",
    }
    job_payload = {"experiment_0": inst_dict}
    job_id = 1
    data = run_json_circuit(job_payload, job_id)

    shots_array = data["results"][0]["data"]["memory"]
    assert len(shots_array) > 0, "shots_array got messed up"

    # and now run too many experiments
    n_exp = 2000
    job_payload = {}
    for ii in range(n_exp):
        job_payload[f"experiment_{ii}"] = inst_dict
    job_id = 1
    with pytest.raises(AssertionError):
        data = run_json_circuit(job_payload, job_id)
