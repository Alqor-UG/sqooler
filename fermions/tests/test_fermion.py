"""
Test module for the spooler_fermion.py file.
"""

from typing import Union
import numpy as np

import pytest
from pydantic import ValidationError

# pylint: disable=C0413, E0401
from fermions.spooler_fermions import (
    gen_circuit,
    gate_dict_from_list,
    f_spooler,
    FermionExperiment,
    BarrierInstruction,
    LoadMeasureInstruction,
    HopInstruction,
    IntInstruction,
    PhaseInstruction,
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
        "backend_name": "alqor_fermionic_tweezer_simulator",
        "backend_version": "0.0.1",
        "job_id": job_id,
        "qobj_id": None,
        "success": True,
        "status": "finished",
        "header": {},
        "results": [],
    }

    err_msg, json_is_fine = f_spooler.check_json_dict(json_dict)
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
            ["load", [7], []],
            ["load", [2], []],
            ["measure", [2], []],
            ["measure", [6], []],
            ["measure", [7], []],
        ],
        "num_wires": 8,
        "shots": 4,
        "wire_order": "interleaved",
    }
    FermionExperiment(**experiment)

    with pytest.raises(ValidationError):
        poor_experiment = {
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
        }
        FermionExperiment(**poor_experiment)


def test_barrier_instruction():
    """
    Test that the barrier instruction is properly constrained.
    """
    inst_list = ["barrier", [7], []]
    gate_dict = gate_dict_from_list(inst_list)
    assert gate_dict == {
        "name": inst_list[0],
        "wires": inst_list[1],
        "params": inst_list[2],
    }
    BarrierInstruction(**gate_dict)
    # test that the name is nicely fixed
    with pytest.raises(ValidationError):
        poor_inst_list = ["barriers", [7], []]
        gate_dict = gate_dict_from_list(poor_inst_list)
        BarrierInstruction(**gate_dict)

    # test that we cannot give too many wires
    with pytest.raises(ValidationError):
        poor_inst_list = ["barrier", [0, 1, 2, 3, 4, 5, 6, 7, 8], []]
        gate_dict = gate_dict_from_list(poor_inst_list)
        BarrierInstruction(**gate_dict)

    # make sure that the wires cannot be above the limit
    with pytest.raises(ValidationError):
        poor_inst_list = ["barrier", [8], []]
        gate_dict = gate_dict_from_list(poor_inst_list)
        BarrierInstruction(**gate_dict)

    # make sure that the parameters are enforced to be empty
    with pytest.raises(ValidationError):
        poor_inst_list = ["barrier", [7], [2.3]]
        gate_dict = gate_dict_from_list(poor_inst_list)
        BarrierInstruction(**gate_dict)


def test_load_measure_instruction():
    """
    Test that the barrier instruction is properly constrained.
    """
    inst_list = ["load", [7], []]
    gate_dict = gate_dict_from_list(inst_list)
    assert gate_dict == {
        "name": inst_list[0],
        "wires": inst_list[1],
        "params": inst_list[2],
    }
    LoadMeasureInstruction(**gate_dict)

    inst_list = ["measure", [7], []]
    gate_dict = gate_dict_from_list(inst_list)
    assert gate_dict == {
        "name": inst_list[0],
        "wires": inst_list[1],
        "params": inst_list[2],
    }
    LoadMeasureInstruction(**gate_dict)

    # test that the name is nicely fixed
    with pytest.raises(ValidationError):
        poor_inst_list = ["loads", [7], []]
        gate_dict = gate_dict_from_list(poor_inst_list)
        LoadMeasureInstruction(**gate_dict)

    # test that we cannot give too many wires
    with pytest.raises(ValidationError):
        poor_inst_list = ["load", [0, 1], []]
        gate_dict = gate_dict_from_list(poor_inst_list)
        LoadMeasureInstruction(**gate_dict)

    # make sure that the wires cannot be above the limit
    with pytest.raises(ValidationError):
        poor_inst_list = ["load", [8], []]
        gate_dict = gate_dict_from_list(poor_inst_list)
        LoadMeasureInstruction(**gate_dict)

    # make sure that the parameters are enforced to be empty
    with pytest.raises(ValidationError):
        poor_inst_list = ["load", [7], [2.3]]
        gate_dict = gate_dict_from_list(poor_inst_list)
        LoadMeasureInstruction(**gate_dict)


def test_hop_instruction():
    """
    Test that the hop instruction instruction is properly constrained.
    """
    inst_list = ["fhop", [0, 4, 1, 5], [np.pi / 2]]
    gate_dict = gate_dict_from_list(inst_list)
    assert gate_dict == {
        "name": inst_list[0],
        "wires": inst_list[1],
        "params": inst_list[2],
    }
    HopInstruction(**gate_dict)

    # test that the name is nicely fixed
    with pytest.raises(ValidationError):
        poor_inst_list = ["fhops", [0, 4, 1, 5], [np.pi / 2]]
        gate_dict = gate_dict_from_list(poor_inst_list)
        HopInstruction(**gate_dict)

    # test that we cannot give too many wires
    with pytest.raises(ValidationError):
        poor_inst_list = ["fhop", [0, 4, 2], [np.pi / 2]]
        gate_dict = gate_dict_from_list(poor_inst_list)
        HopInstruction(**gate_dict)

    # make sure that the wires cannot be above the limit
    with pytest.raises(ValidationError):
        poor_inst_list = ["fhop", [0, 4, 1, 8], [np.pi / 2]]
        gate_dict = gate_dict_from_list(poor_inst_list)
        HopInstruction(**gate_dict)

    # make sure that the parameters are enforced to be within the limits
    with pytest.raises(ValidationError):
        poor_inst_list = ["fhop", [0, 4, 1, 5], [3 * np.pi]]
        gate_dict = gate_dict_from_list(poor_inst_list)
        HopInstruction(**gate_dict)

    # also look into the config dict
    inst_config = {
        "coupling_map": [
            [0, 1, 2, 3],
            [2, 3, 4, 5],
            [4, 5, 6, 7],
            [0, 1, 2, 3, 4, 5, 6, 7],
        ],
        "description": "hopping of atoms to neighboring tweezers",
        "name": "fhop",
        "parameters": ["j_i"],
        "qasm_def": "{}",
    }
    assert inst_config == HopInstruction.config_dict()


def test_interaction_instruction():
    """
    Test that the hop instruction instruction is properly constrained.
    """
    inst_list = ["fint", [0, 4], [np.pi / 2]]
    gate_dict = gate_dict_from_list(inst_list)
    assert gate_dict == {
        "name": inst_list[0],
        "wires": inst_list[1],
        "params": inst_list[2],
    }
    IntInstruction(**gate_dict)

    # test that the name is nicely fixed
    with pytest.raises(ValidationError):
        poor_inst_list = ["fints", [0, 4], [np.pi / 2]]
        gate_dict = gate_dict_from_list(poor_inst_list)
        IntInstruction(**gate_dict)

    # test that we can give all wires
    inst_list = ["fint", [0, 1, 2, 3, 4, 5, 6, 7], [0.030069529684359445]]
    gate_dict = gate_dict_from_list(inst_list)
    assert gate_dict == {
        "name": inst_list[0],
        "wires": inst_list[1],
        "params": inst_list[2],
    }
    IntInstruction(**gate_dict)

    # make sure that the wires cannot be above the limit
    with pytest.raises(ValidationError):
        poor_inst_list = ["fint", [0, 8], [np.pi / 2]]
        gate_dict = gate_dict_from_list(poor_inst_list)
        IntInstruction(**gate_dict)

    # make sure that the parameters are enforced to be within the limits
    with pytest.raises(ValidationError):
        poor_inst_list = ["fint", [0, 4], [3 * np.pi]]
        gate_dict = gate_dict_from_list(poor_inst_list)
        HopInstruction(**gate_dict)

    # also look into the config dict
    inst_config = {
        "coupling_map": [[0, 1, 2, 3, 4, 5, 6, 7]],
        "description": "on-site interaction of atoms of opposite spin state",
        "name": "fint",
        "parameters": ["u"],
        "qasm_def": "{}",
    }
    assert inst_config == IntInstruction.config_dict()


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

    with pytest.raises(AssertionError):
        dummy = run_json_circuit(job_payload, job_id)


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
                ["fhop", [0, 4, 1, 5], [np.pi / 2]],
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


def test_number_experiments():
    """
    Make sure that we cannot submit too many experiments.
    """

    # first test the system that is fine.
    job_payload = {
        "experiment_0": {
            "instructions": [
                ["load", [0], []],
                ["load", [4], []],
                ["fhop", [0, 4, 1, 5], [np.pi / 2]],
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
    assert len(shots_array) > 0, "shots_array got messed up"
    inst_dict = {
        "instructions": [
            ["load", [0], []],
            ["load", [4], []],
            ["fhop", [0, 4, 1, 5], [np.pi / 2]],
            ["measure", [0], []],
            ["measure", [1], []],
            ["measure", [4], []],
            ["measure", [5], []],
        ],
        "num_wires": 8,
        "shots": 4,
        "wire_order": "interleaved",
    }

    # and now run too many experiments
    n_exp = 2000
    job_payload = {}
    for ii in range(n_exp):
        job_payload[f"experiment_{ii}"] = inst_dict
    job_id = 1
    with pytest.raises(AssertionError):
        data = run_json_circuit(job_payload, job_id)


def test_phase_gate():
    """
    Test that the phase gate is properly working.
    """

    # first submit the job
    job_payload = {
        "experiment_0": {
            "instructions": [
                ["load", [0], []],
                ["fhop", [0, 4, 1, 5], [np.pi / 4]],
                ["fphase", [2, 6], [np.pi]],
                ["fhop", [0, 4, 1, 5], [np.pi / 4]],
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

    # also look into the config dict
    inst_config = {
        "coupling_map": [[0, 1], [2, 3], [4, 5], [6, 7], [0, 1, 2, 3, 4, 5, 6, 7]],
        "description": "Applying a local phase to tweezers through an external potential",
        "name": "fphase",
        "parameters": ["mu_i"],
        "qasm_def": "{}",
    }
    assert inst_config == PhaseInstruction.config_dict()


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
                ["fhop", [0, 4, 1, 5], [np.pi / 4]],
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
                ["fhop", [0, 4, 1, 5], [np.pi / 4]],
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


def test_spooler_config():
    """
    Test that the back-end is properly configured and we can indeed provide those parameters
     as we would like.
    """
    fermion_config_dict = {
        "name": "alqor_fermionic_tweezer_simulator",
        "description": (
            "simulator of a fermionic tweezer hardware. "
            "The even wires denote the occupations of the spin-up fermions"
            " and the odd wires denote the spin-down fermions"
        ),
        "version": "0.0.1",
        "cold_atom_type": "fermion",
        "gates": [
            {
                "coupling_map": [
                    [0, 1, 2, 3],
                    [2, 3, 4, 5],
                    [4, 5, 6, 7],
                    [0, 1, 2, 3, 4, 5, 6, 7],
                ],
                "description": "hopping of atoms to neighboring tweezers",
                "name": "fhop",
                "parameters": ["j_i"],
                "qasm_def": "{}",
            },
            {
                "coupling_map": [[0, 1, 2, 3, 4, 5, 6, 7]],
                "description": "on-site interaction of atoms of opposite spin state",
                "name": "fint",
                "parameters": ["u"],
                "qasm_def": "{}",
            },
            {
                "coupling_map": [
                    [0, 1],
                    [2, 3],
                    [4, 5],
                    [6, 7],
                    [0, 1, 2, 3, 4, 5, 6, 7],
                ],
                "description": "Applying a local phase to tweezers through an external potential",
                "name": "fphase",
                "parameters": ["mu_i"],
                "qasm_def": "{}",
            },
        ],
        "max_experiments": 1000,
        "max_shots": 1000000,
        "simulator": True,
        "supported_instructions": [
            "load",
            "barrier",
            "fhop",
            "fint",
            "fphase",
            "measure",
        ],
        "num_wires": 8,
        "wire_order": "interleaved",
        "num_species": 2,
    }
    spooler_config_dict = f_spooler.get_configuration()
    assert spooler_config_dict == fermion_config_dict
