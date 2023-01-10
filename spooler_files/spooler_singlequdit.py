"""
The module that contains all the necessary logic for the singlequdit.
"""

from typing import Tuple, Literal, List

from pydantic import conint, BaseModel
import numpy as np
from scipy.sparse.linalg import expm_multiply  # type: ignore
from scipy.sparse import diags, csc_matrix  # type: ignore

from .schemes import (
    ExperimentDict,
    create_memory_data,
    ExperimentScheme,
    InstructionScheme,
    Spooler,
    Experiment
)

N_MAX_SHOTS = 1000
N_MAX_ATOMS = 500

properties_dict = {
    "instructions": {"type": "array", "items": {"type": "array"}},
    "shots": {"type": "number", "minimum": 0, "maximum": N_MAX_SHOTS},
    "num_wires": {"type": "number", "minimum": 1, "maximum": 1},
    "seed": {"type": "number"},
    "wire_order": {"type": "string", "enum": ["interleaved", "sequential"]},
}

class SingleQuditExperiment(Experiment):
    """
    The class that defines the multi qudit experiments
    """
    wire_order: Literal['interleaved', "sequential"] = "sequential"
    shots: conint(gt=0, le = N_MAX_SHOTS)
    num_wires: Literal[1]
    instructions: List[list]

rLx_schema = dict(
    InstructionScheme(
        items=[
            {"type": "string", "enum": ["rlx"]},
            {
                "type": "array",
                "maxItems": 2,
                "items": [{"type": "number", "minimum": 0, "maximum": 1}],
            },
            {
                "type": "array",
                "items": [{"type": "number", "minimum": 0, "maximum": 2 * np.pi}],
            },
        ]
    )
)

rLz_schema = dict(
    InstructionScheme(
        items=[
            {"type": "string", "enum": ["rlz"]},
            {
                "type": "array",
                "maxItems": 2,
                "items": [{"type": "number", "minimum": 0, "maximum": 1}],
            },
            {
                "type": "array",
                "items": [{"type": "number", "minimum": 0, "maximum": 2 * np.pi}],
            },
        ]
    )
)

rLz2_schema = dict(
    InstructionScheme(
        items=[
            {"type": "string", "enum": ["rlz2"]},
            {
                "type": "array",
                "maxItems": 2,
                "items": [{"type": "number", "minimum": 0, "maximum": 1}],
            },
            {
                "type": "array",
                "items": [{"type": "number", "minimum": 0, "maximum": 10 * 2 * np.pi}],
            },
        ]
    )
)

load_schema = dict(
    InstructionScheme(
        items=[
            {"type": "string", "enum": ["load"]},
            {
                "type": "array",
                "maxItems": 2,
                "items": [{"type": "number", "minimum": 0, "maximum": 0}],
            },
            {
                "type": "array",
                # set the upper limit for the number of atoms that can be loaded
                # into the single qudit
                "items": [{"type": "number", "minimum": 0, "maximum": N_MAX_ATOMS}],
            },
        ]
    )
)

barrier_measure_schema = dict(
    InstructionScheme(
        items=[
            {"type": "string", "enum": ["measure", "barrier"]},
            {
                "type": "array",
                "maxItems": 2,
                "items": [{"type": "number", "minimum": 0, "maximum": 1}],
            },
            {"type": "array", "maxItems": 0},
        ]
    )
)

sq_spooler = Spooler(
    exper_schema=ExperimentScheme(
        required=["instructions", "shots", "num_wires"],
        properties=properties_dict,
    ),
    ins_schema_dict={
        "rlx": rLx_schema,
        "rlz": rLz_schema,
        "rlz2": rLz2_schema,
        "barrier": barrier_measure_schema,
        "measure": barrier_measure_schema,
        "load": load_schema,
    },
)


def gen_circuit(json_dict: dict) -> ExperimentDict:
    """The function the creates the instructions for the circuit.
    json_dict: The list of instructions for the specific run.
    """
    # pylint: disable=R0914
    exp_name = next(iter(json_dict))
    ins_list = json_dict[next(iter(json_dict))]["instructions"]
    n_shots = json_dict[next(iter(json_dict))]["shots"]
    if "seed" in json_dict[next(iter(json_dict))]:
        np.random.seed(json_dict[next(iter(json_dict))]["seed"])

    n_atoms = 1

    spin_len = n_atoms / 2  # spin length

    # let's put together spin matrices
    dim_qudit = n_atoms + 1
    qudit_range = np.arange(spin_len, -(spin_len + 1), -1)

    lx = csc_matrix(
        1
        / 2
        * diags(
            [
                np.sqrt(
                    [(spin_len - m + 1) * (spin_len + m) for m in qudit_range[:-1]]
                ),
                np.sqrt([(spin_len + m + 1) * (spin_len - m) for m in qudit_range[1:]]),
            ],
            [-1, 1],
        )
    )
    lz = csc_matrix(diags([qudit_range], [0]))
    lz2 = lz.multiply(lz)

    psi = 1j * np.zeros(dim_qudit)
    psi[0] = 1 + 1j * 0
    shots_array = []
    # work our way through the instructions
    for inst in ins_list:
        # this must always be the first instruction. Otherwise we should
        # raise some error
        if inst[0] == "load":
            n_atoms = int(inst[2][0])
            spin_len = n_atoms / 2
            # length of the qudit
            dim_qudit = n_atoms + 1
            qudit_range = np.arange(spin_len, -(spin_len + 1), -1)

            lx = csc_matrix(
                1
                / 2
                * diags(
                    [
                        np.sqrt(
                            [
                                (spin_len - m + 1) * (spin_len + m)
                                for m in qudit_range[:-1]
                            ]
                        ),
                        np.sqrt(
                            [
                                (spin_len + m + 1) * (spin_len - m)
                                for m in qudit_range[1:]
                            ]
                        ),
                    ],
                    [-1, 1],
                )
            )
            lz = csc_matrix(diags([qudit_range], [0]))

            lz2 = lz.multiply(lz)

            psi = 1j * np.zeros(dim_qudit)
            psi[0] = 1 + 1j * 0

        if inst[0] == "rlx":
            theta = inst[2][0]
            psi = expm_multiply(-1j * theta * lx, psi)
        if inst[0] == "rlz":
            theta = inst[2][0]
            psi = expm_multiply(-1j * theta * lz, psi)
        if inst[0] == "rlz2":
            theta = inst[2][0]
            psi = expm_multiply(-1j * theta * lz2, psi)
        if inst[0] == "measure":
            probs = np.abs(psi) ** 2
            result = np.random.choice(np.arange(dim_qudit), p=probs, size=n_shots)

    shots_array = result.tolist()
    exp_sub_dict = create_memory_data(shots_array, exp_name, n_shots)
    return exp_sub_dict


def add_job(json_dict: dict, status_msg_dict: dict) -> Tuple[dict, dict]:
    """
    The function that translates the json with the instructions into some circuit and executes it.
    It performs several checks for the job to see if it is properly working.
    If things are fine the job gets added the list of things that should be executed.

    json_dict: The job dictonary of all the instructions.
    job_id: the ID of the job we are treating.
    """
    job_id = status_msg_dict["job_id"]

    result_dict = {
        "backend_name": "synqs_single_qudit_simulator",
        "backend_version": "0.0.2",
        "job_id": job_id,
        "qobj_id": None,
        "success": True,
        "status": "finished",
        "header": {},
        "results": [],
    }
    err_msg, json_is_fine = sq_spooler.check_json_dict(json_dict)
    if json_is_fine:
        for exp in json_dict:
            exp_dict = {exp: json_dict[exp]}
            # Here we
            result_dict["results"].append(gen_circuit(exp_dict))
        print("done form")

        status_msg_dict[
            "detail"
        ] += "; Passed json sanity check; Compilation done. Shots sent to solver."
        status_msg_dict["status"] = "DONE"
    else:
        status_msg_dict["detail"] += (
            "; Failed json sanity check. File will be deleted. Error message : "
            + err_msg
        )
        status_msg_dict["error_message"] += (
            "; Failed json sanity check. File will be deleted. Error message : "
            + err_msg
        )
        status_msg_dict["status"] = "ERROR"
    return result_dict, status_msg_dict
