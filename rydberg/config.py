"""
In this module we define all the configuration parameters for the Rydberg package. 

No simulation is performed here. The entire logic is implemented in the `spooler.py` module.
"""

from typing import Tuple, Literal, List, Optional

from pydantic import conint, BaseModel, ValidationError, conlist, confloat


import numpy as np

from utils.schemes import (
    Spooler,
    gate_dict_from_list,
    GateInstruction,
)

from .spooler import gen_circuit

N_MAX_WIRES = 5
N_MAX_SHOTS = 1000000
MAX_EXPERIMENTS = 1000


class RlxInstruction(GateInstruction):
    """
    The rlx instruction. As each instruction it requires the following attributes

    Attributes:
        name: The string to identify the instruction
        wires: The wire on which the instruction should be applied
            so the indices should be between 0 and N_MAX_WIRES-1
        params: has to be empty
    """

    name: Literal["rlx"] = "rlx"
    wires: conlist(conint(ge=0, le=N_MAX_WIRES - 1), min_items=1, max_items=1)  # type: ignore
    params: conlist(confloat(ge=0, le=2 * np.pi), min_items=1, max_items=1)  # type: ignore

    # a string that is sent over to the config dict and that is necessary for compatibility with QISKIT.
    parameters: str = "omega"
    description: str = "Evolution under Rlx"
    # TODO: This should become most likely a type that is then used for the enforcement of the wires.
    coupling_map: List = [[0], [1], [2], [3], [4]]
    qasm_def = "gate rlx(omega) {}"


class RlzInstruction(GateInstruction):
    """
    The rlz instruction. As each instruction it requires the

    Attributes:
        name: The string to identify the instruction
        wires: The wire on which the instruction should be applied
            so the indices should be between 0 and N_MAX_WIRES-1
        params: has to be empty
    """

    name: Literal["rlz"] = "rlz"
    wires: conlist(conint(ge=0, le=N_MAX_WIRES - 1), min_items=1, max_items=1)  # type: ignore
    params: conlist(confloat(ge=0, le=2 * np.pi), min_items=1, max_items=1)  # type: ignore

    # a string that is sent over to the config dict and that is necessary for compatibility with QISKIT.
    parameters: str = "delta"
    description: str = "Evolution under the Rlz gate"
    # TODO: This should become most likely a type that is then used for the enforcement of the wires.
    coupling_map: List = [[0], [1], [2], [3], [4]]
    qasm_def = "gate rlz(delta) {}"


class RydbergBlockInstruction(GateInstruction):
    """
    The Rydberg blockade instruction. As each instruction it requires the

    Attributes:
        name: The string to identify the instruction
        wires: The wire on which the instruction should be applied
            so the indices should be between 0 and N_MAX_WIRES-1
        params: has to be empty
    """

    name: Literal["rydberg_block"] = "rydberg_block"
    wires: conlist(conint(ge=0, le=N_MAX_WIRES - 1), min_items=2, max_items=N_MAX_WIRES)  # type: ignore
    params: conlist(confloat(ge=0, le=2 * np.pi), min_items=1, max_items=1)  # type: ignore

    # a string that is sent over to the config dict and that is necessary for compatibility with QISKIT.
    parameters: str = "phi"
    description: str = "Apply the Rydberg blockade over the whole array"
    # TODO: This should become most likely a type that is then used for the enforcement of the wires.
    coupling_map: List = [[0, 1, 2, 3, 4]]
    qasm_def = "gate rydberg_block(phi) {}"


class RydbergFullInstruction(GateInstruction):
    """
    The time evolution under the global Hamiltonian. It does not allow for any local control.

    Attributes:
        name: The string to identify the instruction
        wires: The wire on which the instruction should be applied
            so the indices should be between 0 and N_MAX_WIRES-1
        params: Define the paramert for `RX`, `RZ`and `RydbergBlock` in this order
    """

    name: Literal["rydberg_full"] = "rydberg_full"
    wires: conlist(conint(ge=0, le=N_MAX_WIRES - 1), min_items=2, max_items=N_MAX_WIRES)  # type: ignore
    params: conlist(confloat(ge=0, le=5e6 * np.pi), min_items=3, max_items=3)  # type: ignore

    # a string that is sent over to the config dict and that is necessary for compatibility with QISKIT.
    parameters: str = "omega, delta, phi"
    description: str = "Apply the Rydberg and Rabi coupling over the whole array."
    # TODO: This should become most likely a type that is then used for the enforcement of the wires.
    coupling_map: List = [[0, 1, 2, 3, 4]]
    qasm_def = "gate rydberg_full(omega, delta, phi) {}"


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
    wires: conlist(conint(ge=0, le=N_MAX_WIRES - 1), min_items=0, max_items=N_MAX_WIRES)  # type: ignore
    params: conlist(float, max_items=0)  # type: ignore


class MeasureInstruction(BaseModel):
    """
    The measure instruction.

    Attributes:
        name: How to identify the instruction
        wires: Exactly one wire has to be given.
        params: Has to be empty
    """

    name: Literal["measure"]
    wires: conlist(conint(ge=0, le=N_MAX_WIRES - 1), min_items=1, max_items=1)  # type: ignore
    params: conlist(float, max_items=0)  # type: ignore


class RydbergExperiment(BaseModel):
    """
    The class that defines the Rydberg experiments. Each of those
    `RydbergExperiment`s is executed on a `RydbergSpooler`.
    """

    wire_order: Literal["interleaved", "sequential"] = "sequential"
    # mypy keeps throwing errors here because it does not understand the type.
    # not sure how to fix it, so we leave it as is for the moment
    # HINT: Annotated does not work
    shots: conint(gt=0, le=N_MAX_SHOTS)  # type: ignore
    num_wires: conint(ge=1, le=N_MAX_WIRES)  # type: ignore
    instructions: List[list]
    seed: Optional[int]


class RydbergSpooler(Spooler):
    """
    The sppoler class that handles all the circuit logic.
    """

    def check_experiment(self, exper_dict: dict) -> Tuple[str, bool]:
        """
        Check the validity of the experiment.
        """
        try:
            RydbergExperiment(**exper_dict)
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


spooler_object = RydbergSpooler(
    ins_schema_dict={
        "rlx": RlxInstruction,
        "rlz": RlzInstruction,
        "rydberg_block": RydbergBlockInstruction,
        "rydberg_full": RydbergFullInstruction,
        "barrier": BarrierInstruction,
        "measure": MeasureInstruction,
    },
    n_wires=N_MAX_WIRES,
    name="alqor_rydberg_simulator",
    version="0.0.3",
    description="A chain of qubits realized through Rydberg atoms.",
    n_max_experiments=MAX_EXPERIMENTS,
    n_max_shots=N_MAX_SHOTS,
)


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
        "backend_name": spooler_object.name,
        "backend_version": spooler_object.version,
        "job_id": job_id,
        "qobj_id": None,
        "success": True,
        "status": "finished",
        "header": {},
        "results": [],
    }
    err_msg, json_is_fine = spooler_object.check_json_dict(json_dict)
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
