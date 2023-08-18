"""
In this module we define all the configuration parameters for the fermions package. 

No simulation is performed here. The entire logic is implemented in the `spooler.py` module.
"""

from typing import Tuple, Literal, List, Optional
from pydantic import BaseModel, conint, ValidationError, conlist, confloat

import numpy as np

from utils.schemes import (
    Spooler,
    gate_dict_from_list,
    GateInstruction,
)

from .spooler import gen_circuit

NUM_WIRES = 8
N_MAX_SHOTS = 10**6
MAX_EXPERIMENTS = 1000
N_MAX_WIRES = 8

# define the instructions in the following


class BarrierInstruction(BaseModel):
    """
    The barrier instruction. As each instruction it requires the

    Attributes:
        name: The string to identify the instruction
        wires: The wires on which the instruction should be applied
            so the indices should be between 0 and NUM_WIRES-1
        params: has to be empty
    """

    name: Literal["barrier"]
    wires: conlist(conint(ge=0, le=NUM_WIRES - 1), min_items=0, max_items=NUM_WIRES)  # type: ignore
    params: conlist(float, max_items=0)  # type: ignore


class LoadMeasureInstruction(BaseModel):
    """
    The load or measure instruction.

    Attributes:
        name: How to identify the instruction
        wires: Exactly one wire has to be given.
        params: Has to be empty
    """

    name: Literal["load", "measure"]
    wires: conlist(conint(ge=0, le=NUM_WIRES - 1), min_items=1, max_items=1)  # type: ignore
    params: conlist(float, max_items=0)  # type: ignore


class HopInstruction(GateInstruction):
    """
    The instruction that applies the hopping gate.

    Attributes:
        name: How to identify the instruction
        wires: Exactly four wires have to be given.
        params: between 0 and 2 pi
        coupling_map: contains all the allowed configurations. Currently not used
    """

    name: Literal["fhop"] = "fhop"
    wires: conlist(conint(ge=0, le=NUM_WIRES - 1), min_items=4, max_items=4)  # type: ignore
    params: conlist(confloat(ge=0, le=2 * np.pi), max_items=1)  # type: ignore

    # a string that is sent over to the config dict and that is necessary for compatibility with QISKIT.
    parameters: str = "j_i"
    description: str = "hopping of atoms to neighboring tweezers"
    # TODO: This should become most likely a type that is then used for the enforcement of the wires.
    coupling_map: List = [
        [0, 1, 2, 3],
        [2, 3, 4, 5],
        [4, 5, 6, 7],
        [0, 1, 2, 3, 4, 5, 6, 7],
    ]


class IntInstruction(GateInstruction):
    """
    The instruction that applies the interaction gate.

    Attributes:
        name: How to identify the instruction
        wires: Exactly one wire has to be given.
        params: Has to be empty
    """

    name: Literal["fint"] = "fint"
    wires: conlist(conint(ge=0, le=NUM_WIRES - 1), min_items=2, max_items=NUM_WIRES)  # type: ignore
    params: conlist(confloat(ge=0, le=2 * np.pi), max_items=1)  # type: ignore

    # a string that is sent over to the config dict and that is necessary for compatibility with QISKIT.
    parameters: str = "u"
    description: str = "on-site interaction of atoms of opposite spin state"
    # TODO: This should become most likely a type that is then used for the enforcement of the wires.
    coupling_map: List = [[0, 1, 2, 3, 4, 5, 6, 7]]


class PhaseInstruction(GateInstruction):
    """
    The instruction that applies the interaction gate.

    Attributes:
        name: How to identify the instruction
        wires: Exactly one wire has to be given.
        params: Has to be empty
    """

    name: Literal["fphase"] = "fphase"
    wires: conlist(conint(ge=0, le=NUM_WIRES - 1), min_items=2, max_items=2)  # type: ignore
    params: conlist(confloat(ge=0, le=2 * np.pi), max_items=1)  # type: ignore

    # a string that is sent over to the config dict and that is necessary for compatibility with QISKIT.
    parameters: str = "mu_i"
    description: str = (
        "Applying a local phase to tweezers through an external potential"
    )
    # TODO: This should become most likely a type that is then used for the enforcement of the wires.
    coupling_map: List = [[0, 1], [2, 3], [4, 5], [6, 7], [0, 1, 2, 3, 4, 5, 6, 7]]


class FermionExperiment(BaseModel):
    """
    The class that defines the fermion experiments
    """

    wire_order: Literal["interleaved"]
    # we use the Annotated notation to make mypy happy with constrained types
    shots: conint(gt=0, le=N_MAX_SHOTS)  # type: ignore
    num_wires: conint(ge=1, le=N_MAX_WIRES)  # type: ignore
    instructions: List[list]
    seed: Optional[int]


class FermionSpooler(Spooler):
    """
    The sppoler class that handles all the circuit logic.
    """

    def check_experiment(self, exper_dict: dict) -> Tuple[str, bool]:
        """
        Check the validity of the experiment.
        """
        try:
            FermionExperiment(**exper_dict)
            return "", True
        except ValidationError as err:
            return str(err), False

    def check_instructions(self, ins_list: list) -> Tuple[str, bool]:
        """
        Check all the instruction to make sure that they are valid.
        """
        err_code = ""
        exp_ok = False
        for ins in ins_list:
            try:
                gate_dict = gate_dict_from_list(ins)
                self.ins_schema_dict[ins[0]](**gate_dict)
                exp_ok = True
            except ValidationError as err:
                err_code = "Error in instruction " + str(err)
                exp_ok = False
            if not exp_ok:
                break
        return err_code, exp_ok


spooler_object = FermionSpooler(
    ins_schema_dict={
        "load": LoadMeasureInstruction,
        "barrier": BarrierInstruction,
        "fhop": HopInstruction,
        "fint": IntInstruction,
        "fphase": PhaseInstruction,
        "measure": LoadMeasureInstruction,
    },
    n_wires=N_MAX_WIRES,
    name="alqor_fermionic_tweezer_simulator",
    description=(
        "simulator of a fermionic tweezer hardware. "
        "The even wires denote the occupations of the spin-up fermions"
        " and the odd wires denote the spin-down fermions"
    ),
    n_max_shots=N_MAX_SHOTS,
    n_max_experiments=MAX_EXPERIMENTS,
    cold_atom_type="fermion",
    num_species=2,
    version="0.1",
)


def common_add_job(
    result_dict: dict, json_dict: dict, status_msg_dict: dict
) -> Tuple[dict, dict]:
    """
    The function that translates the json with the instructions into some circuit and executes it.
    This is the part the gets called by add_job in each spooler.

    Args:
        result_dict: The dictionary that contains the results
        json_dict: A dictonary of all the instructions.
        status_msg_dict: the dict that will contain the status message.
    """
    err_msg, json_is_fine = spooler_object.check_json_dict(json_dict)
    if json_is_fine:
        for exp in json_dict:
            exp_dict = {exp: json_dict[exp]}
            # Here we
            result_dict["results"].append(gen_circuit(exp_dict))
            result_dict["experiments"].append(exp_dict)

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


def add_job(json_dict: dict, status_msg_dict: dict) -> Tuple[dict, dict]:
    """
    The function that translates the json with the instructions into some circuit and executes it.
    It performs several checks for the job to see if it is properly working.
    If things are fine the job gets added the list of things that should be executed.

    json_dict: A dictonary of all the instructions.
    job_id: the ID of the job we are treating.
    """
    job_id = status_msg_dict["job_id"]

    result_dict = {
        "backend_name": spooler_object.name,
        "backend_version": spooler_object.version,
        "job_id": job_id,
        "qobj_id": None,
        "success": True,
        "status": "finished",
        "header": {},
        "results": [],
        "experiments": [],
    }
    return common_add_job(result_dict, json_dict, status_msg_dict)
