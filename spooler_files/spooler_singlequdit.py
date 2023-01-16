"""
The module that contains all the necessary logic for the singlequdit.
"""

from typing import Tuple, Literal, List, Optional

from pydantic import conint, BaseModel, ValidationError, conlist, confloat
import numpy as np
from scipy.sparse.linalg import expm_multiply  # type: ignore
from scipy.sparse import diags, csc_matrix  # type: ignore

from .schemes import (
    ExperimentDict,
    create_memory_data,
    Spooler,
    gate_dict_from_list,
    GateInstruction,
)

N_MAX_SHOTS = 1000
N_MAX_ATOMS = 500


class RlxInstruction(GateInstruction):
    """
    The rlz instruction. As each instruction it requires the

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
    The load instruction. As each instruction it requires the

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
    The sppoler class that handles all the circuit logic.
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


sq_spooler = SingleQuditSpooler(
    ins_schema_dict={
        "rlx": RlxInstruction,
        "rlz": RlzInstruction,
        "rlz2": LocalSqueezingInstruction,
        "barrier": MeasureBarrierInstruction,
        "measure": MeasureBarrierInstruction,
        "load": LoadInstruction,
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
