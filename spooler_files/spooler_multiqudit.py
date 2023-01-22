"""
The module that contains all the necessary logic for the multiqudit.
"""

from typing import List, Tuple, Literal, Optional
from pydantic import BaseModel, conint, ValidationError, conlist, confloat

import numpy as np
from scipy.sparse import identity, diags, csc_matrix  # type: ignore
from scipy import sparse  # type: ignore
from scipy.sparse.linalg import expm_multiply  # type: ignore

from .schemes import (
    ExperimentDict,
    gate_dict_from_list,
    create_memory_data,
    Spooler,
    GateInstruction,
)

N_MAX_WIRES = 4
N_MAX_SHOTS = 1e6
MAX_EXPERIMENTS = 1000
N_MAX_ATOMS = 500
MAX_HILBERT_SPACE_DIM = 2 ** 12

# define the instructions in the following
# rlx instruction

# define the instructions in the following


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
    wires: conlist(conint(ge=0, le=N_MAX_WIRES - 1), min_items=1, max_items=1)  # type: ignore
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
    wires: conlist(conint(ge=0, le=N_MAX_WIRES - 1), min_items=1, max_items=1)  # type: ignore
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
    wires: conlist(conint(ge=0, le=N_MAX_WIRES - 1), min_items=1, max_items=1)  # type: ignore
    params: conlist(confloat(ge=0, le=10 * 2 * np.pi), min_items=1, max_items=1)  # type: ignore

    # a string that is sent over to the config dict and that is necessary for compatibility with QISKIT.
    parameters: str = "chi"
    description: str = "Evolution under lz2"
    # TODO: This should become most likely a type that is then used for the enforcement of the wires.
    coupling_map: List = [[0], [1], [2], [3], [4]]
    qasm_def = "gate rlz2(chi) {}"


class RlxlyInstruction(GateInstruction):
    """
    The rlxly or rlzlz instruction. As each instruction it requires the

    Attributes:
        name: The string to identify the instruction
        wires: The wire on which the instruction should be applied
            so the indices should be between 0 and N_MAX_WIRES-1
        params: has to be empty
    """

    name: Literal["rlxly"] = "rlxly"
    wires: conlist(conint(ge=0, le=N_MAX_WIRES - 1), min_items=2, max_items=N_MAX_WIRES)  # type: ignore
    params: conlist(confloat(ge=0, le=10 * 2 * np.pi), min_items=1, max_items=1)  # type: ignore

    # a string that is sent over to the config dict and that is necessary for compatibility with QISKIT.
    parameters: str = "J"
    description: str = "Entanglement between neighboring gates with an xy interaction"
    # TODO: This should become most likely a type that is then used for the enforcement of the wires.
    coupling_map: List = [[0, 1], [1, 2], [2, 3], [3, 4], [0, 1, 2, 3, 4]]
    qasm_def = "gate rlylx(J) {}"


class RlzlzInstruction(GateInstruction):
    """
    The rlzlz instruction. As each instruction it requires the

    Attributes:
        name: The string to identify the instruction
        wires: The wire on which the instruction should be applied
            so the indices should be between 0 and N_MAX_WIRES-1
        params: has to be empty
    """

    name: Literal["rlzlz"] = "rlzlz"
    wires: conlist(conint(ge=0, le=N_MAX_WIRES - 1), min_items=2, max_items=N_MAX_WIRES)  # type: ignore
    params: conlist(confloat(ge=0, le=10 * 2 * np.pi), min_items=1, max_items=1)  # type: ignore

    # a string that is sent over to the config dict and that is necessary for compatibility with QISKIT.
    parameters: str = "J"
    description: str = "Entanglement between neighboring gates with a zz interaction"
    # TODO: This should become most likely a type that is then used for the enforcement of the wires.
    coupling_map: List = [[0, 1], [1, 2], [2, 3], [3, 4], [0, 1, 2, 3, 4]]
    qasm_def = "gate rlzlz(J) {}"


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


class LoadInstruction(BaseModel):
    """
    The load instruction.

    Attributes:
        name: How to identify the instruction
        wires: Exactly one wire has to be given.
        params: The number of atoms to be loaded onto the wire.
    """

    name: Literal["load"]
    wires: conlist(conint(ge=0, le=N_MAX_WIRES - 1), min_items=1, max_items=1)  # type: ignore
    params: conlist(conint(ge=1, le=N_MAX_ATOMS), min_items=1, max_items=1)  # type: ignore


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


class MultiQuditExperiment(BaseModel):
    """
    The class that defines the multi qudit experiments
    """

    wire_order: Literal["interleaved", "sequential"] = "sequential"

    # mypy keeps throwing errors here because it does not understand the type.
    # not sure how to fix it, so we leave it as is for the moment
    # HINT: Annotated does not work
    shots: conint(gt=0, le=N_MAX_SHOTS)  # type: ignore
    num_wires: conint(ge=1, le=N_MAX_WIRES)  # type: ignore
    instructions: List[list]
    seed: Optional[int]


class MultiQuditSpooler(Spooler):
    """
    The class that contains the logic of the multiqudit spooler.
    """

    def check_experiment(self, exper_dict: dict) -> Tuple[str, bool]:
        """
        Check the validity of the experiment.
        """
        try:
            MultiQuditExperiment(**exper_dict)
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

    def check_dimension(self, json_dict: dict) -> Tuple[str, bool]:
        """
        Make sure that the Hilbert space dimension is not too large.
        """
        dim_ok = False
        err_code = "Wrong experiment name or too many experiments"
        for expr in json_dict:
            num_wires = json_dict[expr]["num_wires"]
            dim_hilbert = 1
            qubit_wires = num_wires
            ins_list = json_dict[expr]["instructions"]
            for ins in ins_list:
                if ins[0] == "load":
                    qubit_wires = qubit_wires - 1
                    dim_hilbert = dim_hilbert * ins[2][0]
            dim_hilbert = dim_hilbert * (2 ** qubit_wires)
            dim_ok = dim_hilbert < (MAX_HILBERT_SPACE_DIM) + 1
            if not dim_ok:
                err_code = "Hilbert space dimension too large!"
                break
        return err_code.replace("\n", ".."), dim_ok


mq_spooler = MultiQuditSpooler(
    ins_schema_dict={
        "rlx": RlxInstruction,
        "rlz": RlzInstruction,
        "rlz2": LocalSqueezingInstruction,
        "rlxly": RlxlyInstruction,
        "rlzlz": RlzlzInstruction,
        "barrier": BarrierInstruction,
        "measure": MeasureInstruction,
        "load": LoadInstruction,
    },
    n_wires=N_MAX_WIRES,
    name="synqs_multiqudit_simulator",
    description="Setup of a cold atomic gas experiment with a multiple qudits.",
    n_max_experiments=MAX_EXPERIMENTS,
    n_max_shots=N_MAX_SHOTS,
)


def op_at_wire(op: csc_matrix, pos: int, dim_per_wire: List[int]) -> csc_matrix:
    """
    Applies an operation onto the wire and provides unitaries on the other wires.
    Basically this creates the nice tensor products.

    Args:
        op (matrix): The operation that should be applied.
        pos (int): The wire onto which the operation should be applied.
        dim_per_wire (int): What is the local Hilbert space of each wire.

    Returns:
        The tensor product matrix.
    """
    # There are two cases the first wire can be the identity or not
    if pos == 0:
        res = op
    else:
        res = csc_matrix(identity(dim_per_wire[0]))
    # then loop for the rest
    for i1 in np.arange(1, len(dim_per_wire)):
        temp = csc_matrix(identity(dim_per_wire[i1]))
        if i1 == pos:
            temp = op
        res = sparse.kron(res, temp)

    return res


def gen_circuit(json_dict: dict) -> ExperimentDict:
    """The function the creates the instructions for the circuit.

    json_dict: The list of instructions for the specific run.
    """
    exp_name = next(iter(json_dict))
    ins_list = json_dict[next(iter(json_dict))]["instructions"]
    n_shots = json_dict[next(iter(json_dict))]["shots"]
    n_wires = json_dict[next(iter(json_dict))]["num_wires"]
    spin_per_wire = 1 / 2 * np.ones(n_wires)
    if "seed" in json_dict[next(iter(json_dict))]:
        np.random.seed(json_dict[next(iter(json_dict))]["seed"])

    for ins in ins_list:
        if ins[0] == "load":
            spin_per_wire[ins[1][0]] = 1 / 2 * ins[2][0]

    dim_per_wire = 2 * spin_per_wire + np.ones(n_wires)
    dim_per_wire = dim_per_wire.astype(int)
    dim_hilbert = np.prod(dim_per_wire)

    # we will need a list of local spin operators as their dimension can change
    # on each wire
    lx_list = []
    ly_list = []
    lz_list = []
    lz2_list = []

    for i1 in np.arange(0, n_wires):
        # let's put together spin matrices
        spin_length = spin_per_wire[i1]
        qudit_range = np.arange(spin_length, -(spin_length + 1), -1)

        lx = csc_matrix(
            1
            / 2
            * diags(
                [
                    np.sqrt(
                        [
                            (spin_length - m + 1) * (spin_length + m)
                            for m in qudit_range[:-1]
                        ]
                    ),
                    np.sqrt(
                        [
                            (spin_length + m + 1) * (spin_length - m)
                            for m in qudit_range[1:]
                        ]
                    ),
                ],
                [-1, 1],
            )
        )
        ly = csc_matrix(
            1
            / (2 * 1j)
            * diags(
                [
                    np.sqrt(
                        [
                            (spin_length - m + 1) * (spin_length + m)
                            for m in qudit_range[:-1]
                        ]
                    ),
                    -1
                    * np.sqrt(
                        [
                            (spin_length + m + 1) * (spin_length - m)
                            for m in qudit_range[1:]
                        ]
                    ),
                ],
                [-1, 1],
            )
        )
        lz = csc_matrix(diags([qudit_range], [0]))
        lz2 = lz.dot(lz)

        lx_list.append(op_at_wire(lx, i1, list(dim_per_wire)))
        ly_list.append(op_at_wire(ly, i1, list(dim_per_wire)))
        lz_list.append(op_at_wire(lz, i1, list(dim_per_wire)))
        lz2_list.append(op_at_wire(lz2, i1, list(dim_per_wire)))

    initial_state = 1j * np.zeros(dim_per_wire[0])
    initial_state[0] = 1 + 1j * 0
    psi = sparse.csc_matrix(initial_state)
    for i1 in np.arange(1, len(dim_per_wire)):
        initial_state = 1j * np.zeros(dim_per_wire[i1])
        initial_state[0] = 1 + 1j * 0
        psi = sparse.kron(psi, initial_state)
    psi = psi.T

    measurement_indices = []
    shots_array = []
    for inst in ins_list:
        if inst[0] == "rlx":
            position = inst[1][0]
            theta = inst[2][0]
            psi = expm_multiply(-1j * theta * lx_list[position], psi)
        if inst[0] == "rly":
            position = inst[1][0]
            theta = inst[2][0]
            psi = expm_multiply(-1j * theta * ly_list[position], psi)
        if inst[0] == "rlz":
            position = inst[1][0]
            theta = inst[2][0]
            psi = expm_multiply(-1j * theta * lz_list[position], psi)
        if inst[0] == "rlz2":
            position = inst[1][0]
            theta = inst[2][0]
            psi = expm_multiply(-1j * theta * lz2_list[position], psi)
        if inst[0] == "rlxly":
            # apply gate on two qudits
            if len(inst[1]) == 2:
                position1 = inst[1][0]
                position2 = inst[1][1]
                theta = inst[2][0]
                lp1 = lx_list[position1] + 1j * ly_list[position1]
                lp2 = lx_list[position2] + 1j * ly_list[position2]
                lxly = lp1.dot(lp2.conjugate().T)
                lxly = lxly + lxly.conjugate().T
                psi = expm_multiply(-1j * theta * lxly, psi)
            # apply gate on all qudits
            elif len(inst[1]) == n_wires:
                theta = inst[2][0]
                lxly = csc_matrix((dim_hilbert, dim_hilbert))
                for i1 in np.arange(0, n_wires - 1):
                    lp1 = lx_list[i1] + 1j * ly_list[i1]
                    lp2 = lx_list[i1 + 1] + 1j * ly_list[i1 + 1]
                    lxly = lxly + lp1.dot(lp2.conjugate().T)
                lxly = lxly + lxly.conjugate().T
                psi = expm_multiply(-1j * theta * lxly, psi)
        if inst[0] == "rlzlz":
            # apply gate on two quadits
            if len(inst[1]) == 2:
                position1 = inst[1][0]
                position2 = inst[1][1]
                theta = inst[2][0]
                lzlz = lz_list[position1].dot(lz_list[position2])
                psi = expm_multiply(-1j * theta * lzlz, psi)
        if inst[0] == "measure":
            measurement_indices.append(inst[1][0])
    if measurement_indices:
        # the following filters out the results for the indices we prefer.
        probs = np.squeeze(abs(psi.toarray()) ** 2)
        result_ind = np.random.choice(dim_hilbert, p=probs, size=n_shots)
        measurements = np.zeros((n_shots, len(measurement_indices)), dtype=int)
        for i1 in range(n_shots):
            observed = np.unravel_index(result_ind[i1], dim_per_wire)
            # TODO these types are messed up for the moment
            # as ususal we add an ignore until this gets back to bite us in the ...
            # but it simply to tough to find out where the typing goes wrong right now.
            observed = np.array(observed)  # type: ignore
            measurements[i1, :] = observed[measurement_indices]  # type: ignore
        shots_array = measurements.tolist()

    exp_sub_dict = create_memory_data(shots_array, exp_name, n_shots)
    return exp_sub_dict


def add_job(json_dict: dict, status_msg_dict: dict) -> Tuple[dict, dict]:
    """
    The function that translates the json with the instructions into some circuit and executes it.

    It performs several checks for the job to see if it is properly working.
    If things are fine the job gets added the list of things that should be executed.

    json_dict: A dictonary of all the instructions.
    status_msg_dict:  WHAT IS THIS FOR ?
    """
    job_id = status_msg_dict["job_id"]

    result_dict = {
        "backend_name": mq_spooler.name,
        "backend_version": mq_spooler.version,
        "job_id": job_id,
        "qobj_id": None,
        "success": True,
        "status": "finished",
        "header": {},
        "results": [],
    }
    err_msg, json_is_fine = mq_spooler.check_json_dict(json_dict)

    if json_is_fine:
        # check_hilbert_space_dimension
        dim_err_msg, dim_ok = mq_spooler.check_dimension(json_dict)
        if dim_ok:
            for exp in json_dict:
                exp_dict = {exp: json_dict[exp]}
                # Here we
                result_dict["results"].append(gen_circuit(exp_dict))
            print("done form")

            status_msg_dict[
                "detail"
            ] += "; Passed json sanity check; Compilation done. Shots sent to solver."
            status_msg_dict["status"] = "DONE"
            return result_dict, status_msg_dict

        status_msg_dict["detail"] += (
            "; Failed dimensionality test. Too many atoms. File will be deleted. Error message : "
            + dim_err_msg
        )
        status_msg_dict["error_message"] += (
            "; Failed dimensionality test. Too many atoms. File will be deleted. Error message :  "
            + dim_err_msg
        )
        status_msg_dict["status"] = "ERROR"
        return result_dict, status_msg_dict
    status_msg_dict["detail"] += (
        "; Failed json sanity check. File will be deleted. Error message : " + err_msg
    )
    status_msg_dict["error_message"] += (
        "; Failed json sanity check. File will be deleted. Error message : " + err_msg
    )
    status_msg_dict["status"] = "ERROR"
    return result_dict, status_msg_dict
