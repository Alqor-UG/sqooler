"""
In this module we define all the configuration parameters for the singlequdit package. 

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

N_MAX_SHOTS = 1000000
N_MAX_ATOMS = 500
MAX_EXPERIMENTS = 1000


class RlxInstruction(GateInstruction):
    """
    The rlx instruction. As each instruction it requires the

    Attributes:
        name: The string to identify the instruction
        wires: The wire on which the instruction should be applied
            so the indices should be between 0 and N_MAX_WIRES-1
        params: has to be empty
    """

    name: Literal["rlx"] = "rlx"
    wires: conlist(conint(ge=0, le=0), min_items=0, max_items=1)  # type: ignore
    params: conlist(confloat(ge=0, le=2 * np.pi), min_items=1, max_items=1)  # type: ignore

    # a string that is sent over to the config dict and that is necessary for compatibility with QISKIT.
    parameters: str = "omega"
    description: str = "Evolution under Lx"
    # TODO: This should become most likely a type that is then used for the enforcement of the wires.
    coupling_map: List = [[0], [1], [2], [3], [4]]
    qasm_def = "gate lrx(omega) {}"


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
    wires: conlist(conint(ge=0, le=0), min_items=0, max_items=1)  # type: ignore
    params: conlist(confloat(ge=0, le=2 * np.pi), min_items=1, max_items=1)  # type: ignore

    # a string that is sent over to the config dict and that is necessary for compatibility with QISKIT.
    parameters: str = "delta"
    description: str = "Evolution under the Z gate"
    # TODO: This should become most likely a type that is then used for the enforcement of the wires.
    coupling_map: List = [[0], [1], [2], [3], [4]]
    qasm_def = "gate rlz(delta) {}"


class LocalSqueezingInstruction(GateInstruction):
    """
    The rlz2 instruction. As each instruction it requires the

    Attributes:
        name: The string to identify the instruction
        wires: The wire on which the instruction should be applied
            so the indices should be between 0 and N_MAX_WIRES-1
        params: has to be empty
    """

    name: Literal["rlz2"] = "rlz2"
    wires: conlist(conint(ge=0, le=0), min_items=0, max_items=1)  # type: ignore
    params: conlist(confloat(ge=0, le=10 * 2 * np.pi), min_items=1, max_items=1)  # type: ignore

    # a string that is sent over to the config dict and that is necessary for compatibility with QISKIT.
    parameters: str = "chi"
    description: str = "Evolution under lz2"
    # TODO: This should become most likely a type that is then used for the enforcement of the wires.
    coupling_map: List = [[0], [1], [2], [3], [4]]
    qasm_def = "gate rlz2(chi) {}"


class LoadInstruction(BaseModel):
    """
    The load instruction. As each instruction it requires the

    Attributes:
        name: The string to identify the instruction
        wires: The wire on which the instruction should be applied
            so the indices should be between 0 and N_MAX_WIRES-1
        params: has to be empty
    """

    name: Literal["load"]
    wires: conlist(conint(ge=0, le=0), min_items=0, max_items=1)  # type: ignore
    params: conlist(conint(ge=1, le=N_MAX_ATOMS), min_items=1, max_items=1)  # type: ignore


class MeasureBarrierInstruction(BaseModel):
    """
    The measure and barrier instruction. As each instruction it requires the

    Attributes:
        name: The string to identify the instruction
        wires: The wire on which the instruction should be applied
            so the indices should be between 0 and N_MAX_WIRES-1
        params: has to be empty
    """

    name: Literal["measure", "barrier"]
    wires: conlist(conint(ge=0, le=0), min_items=0, max_items=1)  # type: ignore
    params: conlist(float, min_items=0, max_items=0)  # type: ignore


class SingleQuditExperiment(BaseModel):
    """
    The class that defines the single qudit experiments
    """

    wire_order: Literal["interleaved", "sequential"] = "sequential"
    # mypy keeps throwing errors here because it does not understand the type.
    # not sure how to fix it, so we leave it as is for the moment
    # HINT: Annotated does not work
    shots: conint(gt=0, le=N_MAX_SHOTS)  # type: ignore
    num_wires: Literal[1]
    instructions: List[list]
    seed: Optional[int]


class SingleQuditSpooler(Spooler):
    """
    The spooler class that handles all the circuit logic.
    """

    def check_experiment(self, exper_dict: dict) -> Tuple[str, bool]:
        """
        Check the validity of the experiment.
        """
        try:
            SingleQuditExperiment(**exper_dict)
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


# This is the spooler object that is used by the main function.
spooler_object = SingleQuditSpooler(
    ins_schema_dict={
        "rlx": RlxInstruction,
        "rlz": RlzInstruction,
        "rlz2": LocalSqueezingInstruction,
        "barrier": MeasureBarrierInstruction,
        "measure": MeasureBarrierInstruction,
        "load": LoadInstruction,
    },
    n_wires=1,
    version="0.0.2",
    description="Setup of a cold atomic gas experiment with a single qudit.",
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
