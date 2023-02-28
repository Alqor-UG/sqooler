"""
Test module for the rydberg simulator.
"""

from typing import Union
import numpy as np
import pytest

from pydantic import ValidationError

# pylint: disable=C0413, E0401
from utils.schemes import gate_dict_from_list
from rydberg.spooler_rydberg import (
    ryd_spooler,
    gen_circuit,
    RydbergExperiment,
    RXInstruction,
    RZInstruction,
    CBlockInstruction,
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
        "backend_name": "alqor_rydberg_simulator",
        "backend_version": "0.0.1",
        "job_id": job_id,
        "qobj_id": None,
        "success": True,
        "status": "finished",
        "header": {},
        "results": [],
    }
    err_msg, json_is_fine = ryd_spooler.check_json_dict(json_dict)
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
            ["rz", [0], [0.7]],
            ["measure", [0], []],
        ],
        "num_wires": 1,
        "shots": 3,
    }
    RydbergExperiment(**experiment)

    with pytest.raises(ValidationError):
        poor_experiment = {
            "instructions": [
                ["measure", [2], []],
                ["measure", [6], []],
                ["measure", [7], []],
            ],
            "num_wires": 400,
            "shots": 4,
            "wire_order": "sequential",
        }
        RydbergExperiment(**poor_experiment)


def test_local_rot_instruction():
    """
    Test that the hop instruction instruction is properly constrained.
    """
    inst_list = ["rx", [0], [0.7]]
    gate_dict = gate_dict_from_list(inst_list)
    assert gate_dict == {
        "name": inst_list[0],
        "wires": inst_list[1],
        "params": inst_list[2],
    }
    RXInstruction(**gate_dict)

    inst_list = ["rz", [0], [0.7]]
    gate_dict = gate_dict_from_list(inst_list)
    RZInstruction(**gate_dict)

    # test that the name is nicely fixed
    with pytest.raises(ValidationError):
        poor_inst_list = ["rly", [0], [0.7]]
        gate_dict = gate_dict_from_list(poor_inst_list)
        RXInstruction(**gate_dict)

    # test that we cannot give too many wires
    with pytest.raises(ValidationError):
        poor_inst_list = ["rx", [0, 1], [0.7]]
        gate_dict = gate_dict_from_list(poor_inst_list)
        RXInstruction(**gate_dict)

    # make sure that the wires cannot be above the limit
    with pytest.raises(ValidationError):
        poor_inst_list = ["rx", [200], [0.7]]
        gate_dict = gate_dict_from_list(poor_inst_list)
        RXInstruction(**gate_dict)

    # make sure that the parameters are enforced to be within the limits
    with pytest.raises(ValidationError):
        poor_inst_list = ["rx", [0], [3 * np.pi]]
        gate_dict = gate_dict_from_list(poor_inst_list)
        RXInstruction(**gate_dict)

    inst_config = {
        "name": "rx",
        "parameters": ["omega"],
        "qasm_def": "gate rx(omega) {}",
        "coupling_map": [[0], [1], [2], [3], [4]],
        "description": "Evolution under RX",
    }
    assert inst_config == RXInstruction.config_dict()

    # also spins of same length
    job_payload = {
        "experiment_0": {
            "instructions": [
                ["rx", [0], [np.pi]],
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
    assert shots_array[0] == "1 0", "job_id got messed up"
    assert data["job_id"] == 2, "job_id got messed up"
    assert len(shots_array) > 0, "shots_array got messed up"

    # also spins of same length
    job_payload = {
        "experiment_0": {
            "instructions": [
                ["rx", [0], [np.pi / 2]],
                ["rz", [0], [np.pi]],
                ["rx", [0], [np.pi / 2]],
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
    assert shots_array[0] == "0 0", "job_id got messed up"
    assert data["job_id"] == 2, "job_id got messed up"
    assert len(shots_array) > 0, "shots_array got messed up"


def test_blockade_instruction():
    """
    Test that the Rydberg blockade instruction is properly constrained.
    """
    inst_list = ["cblock", [0, 1], [0.7]]
    gate_dict = gate_dict_from_list(inst_list)
    assert gate_dict == {
        "name": inst_list[0],
        "wires": inst_list[1],
        "params": inst_list[2],
    }
    CBlockInstruction(**gate_dict)

    inst_list = ["cblock", [0, 1], [0.7]]
    gate_dict = gate_dict_from_list(inst_list)
    CBlockInstruction(**gate_dict)

    # test that the name is nicely fixed
    with pytest.raises(ValidationError):
        poor_inst_list = ["rlzls", [0, 1], [0.7]]
        gate_dict = gate_dict_from_list(poor_inst_list)
        CBlockInstruction(**gate_dict)

    # test that we cannot give too few wires
    with pytest.raises(ValidationError):
        poor_inst_list = ["cblock", [0], [0.7]]
        gate_dict = gate_dict_from_list(poor_inst_list)
        CBlockInstruction(**gate_dict)

    # make sure that the wires cannot be above the limit
    with pytest.raises(ValidationError):
        poor_inst_list = ["cblock", [0, 200], [0.7]]
        gate_dict = gate_dict_from_list(poor_inst_list)
        CBlockInstruction(**gate_dict)

    # make sure that the parameters are enforced to be within the limits
    with pytest.raises(ValidationError):
        poor_inst_list = ["cblock", [0, 1], [200 * np.pi]]
        gate_dict = gate_dict_from_list(poor_inst_list)
        CBlockInstruction(**gate_dict)

    inst_config = {
        "name": "cblock",
        "parameters": ["delta"],
        "qasm_def": "gate cblock(delta) {}",
        "coupling_map": [[0, 1, 2, 3, 4]],
        "description": "Apply the Rydberg blockade over the whole array",
    }
    assert inst_config == CBlockInstruction.config_dict()

    # also spins of same length
    print("Test the blockade")
    job_payload = {
        "experiment_0": {
            "instructions": [
                ["rx", [0], [np.pi / 2]],
                ["rx", [1], [np.pi / 2]],
                ["cblock", [0, 1], [np.pi]],
                ["rx", [0], [np.pi / 2]],
                ["rx", [1], [np.pi / 2]],
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
    print(shots_array)
    assert shots_array[0] == "0 0", "job_id got messed up"
    assert data["job_id"] == 2, "job_id got messed up"
    assert len(shots_array) > 0, "shots_array got messed up"


def test_z_gate():
    """
    Test that the z gate is properly applied.
    """

    # first submit the job
    job_payload = {
        "experiment_0": {
            "instructions": [
                ["rz", [0], [0.7]],
                ["measure", [0], []],
            ],
            "num_wires": 1,
            "shots": 3,
        },
        "experiment_1": {
            "instructions": [
                ["rz", [0], [0.7]],
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
        "name": "rz",
        "parameters": ["delta"],
        "qasm_def": "gate rz(delta) {}",
        "coupling_map": [[0], [1], [2], [3], [4]],
        "description": "Evolution under the RZ gate",
    }
    assert inst_config == RZInstruction.config_dict()


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


def test_measure_gate():
    """
    Test that the measure can be properly applied.
    """

    # first submit the job
    job_payload = {
        "experiment_0": {
            "instructions": [
                ["measure", [0], []],
                ["measure", [1], []],
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

    assert shots_array[0] == "0 0", "job_id got messed up"
    assert len(shots_array) > 0, "shots_array got messed up"


def test_spooler_config():
    """
    Test that the back-end is properly configured and we can indeed provide those parameters
     as we would like.
    """

    mq_config_dict = {
        "name": "alqor_multiqudit_simulator",
        "description": "Setup of a cold atomic gas experiment with a multiple qudits.",
        "version": "0.0.1",
        "cold_atom_type": "spin",
        "gates": [
            {
                "name": "rx",
                "parameters": ["omega"],
                "qasm_def": "gate lrx(omega) {}",
                "coupling_map": [[0], [1], [2], [3], [4]],
                "description": "Evolution under Lx",
            },
            {
                "name": "rz",
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
            {
                "name": "rlxly",
                "parameters": ["J"],
                "qasm_def": "gate rlylx(J) {}",
                "coupling_map": [[0, 1], [1, 2], [2, 3], [3, 4], [0, 1, 2, 3, 4]],
                "description": "Entanglement between neighboring gates with an xy interaction",
            },
            {
                "coupling_map": [[0, 1], [1, 2], [2, 3], [3, 4], [0, 1, 2, 3, 4]],
                "description": "Entanglement between neighboring gates with a zz interaction",
                "name": "rlzlz",
                "parameters": ["J"],
                "qasm_def": "gate rlzlz(J) {}",
            },
        ],
        "max_experiments": 1000,
        "max_shots": 1e6,
        "simulator": True,
        "supported_instructions": [
            "rx",
            "rz",
            "cblock",
            "barrier",
            "measure",
        ],
        "num_wires": 4,
        "wire_order": "interleaved",
        "num_species": 1,
    }
    spooler_config_dict = ryd_spooler.get_configuration()
    assert spooler_config_dict == mq_config_dict


def test_number_experiments():
    """
    Make sure that we cannot submit too many experiments.
    """

    # first test the system that is fine.
    job_payload = {
        "experiment_0": {
            "instructions": [
                ["rx", [0], [np.pi]],
                ["cblock", [0, 1], [np.pi / 2]],
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
    assert len(shots_array) > 0, "shots_array got messed up"
    inst_dict = {
        "instructions": [
            ["rx", [0], [np.pi]],
            ["cblock", [0, 1], [np.pi / 2]],
            ["measure", [0], []],
            ["measure", [1], []],
        ],
        "num_wires": 2,
        "shots": 150,
        "wire_order": "sequential",
    }

    # and now run too many experiments
    n_exp = 2000
    job_payload = {}
    for ii in range(n_exp):
        job_payload[f"experiment_{ii}"] = inst_dict
    job_id = 1
    with pytest.raises(AssertionError):
        data = run_json_circuit(job_payload, job_id)
