"""
The module that contains all the necessary logic for the Rydberg simulator.
"""

from typing import Tuple, Literal, List, Optional

from pydantic import conint, BaseModel, ValidationError, conlist, confloat


import numpy as np
from scipy.sparse import identity, diags, csc_matrix  # type: ignore
from scipy import sparse  # type: ignore
from scipy.sparse.linalg import expm_multiply  # type: ignore

from utils.schemes import (
    ExperimentDict,
    create_memory_data,
    Spooler,
    gate_dict_from_list,
    GateInstruction,
)

N_MAX_WIRES = 5
N_MAX_SHOTS = 1000000
MAX_EXPERIMENTS = 1000


class RXInstruction(GateInstruction):
    """
    The rx instruction. As each instruction it requires the

    Attributes:
        name: The string to identify the instruction
        wires: The wire on which the instruction should be applied
            so the indices should be between 0 and N_MAX_WIRES-1
        params: has to be empty
    """

    name: Literal["rx"] = "rx"
    wires: conlist(conint(ge=0, le=N_MAX_WIRES - 1), min_items=1, max_items=1)  # type: ignore
    params: conlist(confloat(ge=0, le=2 * np.pi), min_items=1, max_items=1)  # type: ignore

    # a string that is sent over to the config dict and that is necessary for compatibility with QISKIT.
    parameters: str = "omega"
    description: str = "Evolution under RX"
    # TODO: This should become most likely a type that is then used for the enforcement of the wires.
    coupling_map: List = [[0], [1], [2], [3], [4]]
    qasm_def = "gate lrx(omega) {}"


class RZInstruction(GateInstruction):
    """
    The rz instruction. As each instruction it requires the

    Attributes:
        name: The string to identify the instruction
        wires: The wire on which the instruction should be applied
            so the indices should be between 0 and N_MAX_WIRES-1
        params: has to be empty
    """

    name: Literal["rz"] = "rz"
    wires: conlist(conint(ge=0, le=N_MAX_WIRES - 1), min_items=1, max_items=1)  # type: ignore
    params: conlist(confloat(ge=0, le=2 * np.pi), min_items=1, max_items=1)  # type: ignore

    # a string that is sent over to the config dict and that is necessary for compatibility with QISKIT.
    parameters: str = "delta"
    description: str = "Evolution under the RZ gate"
    # TODO: This should become most likely a type that is then used for the enforcement of the wires.
    coupling_map: List = [[0], [1], [2], [3], [4]]
    qasm_def = "gate rlz(delta) {}"


class CBlockInstruction(GateInstruction):
    """
    The Rydberg blockade instruction. As each instruction it requires the

    Attributes:
        name: The string to identify the instruction
        wires: The wire on which the instruction should be applied
            so the indices should be between 0 and N_MAX_WIRES-1
        params: has to be empty
    """

    name: Literal["cblock"] = "cblock"
    wires: conlist(conint(ge=0, le=0), min_items=0, max_items=1)  # type: ignore
    params: conlist(confloat(ge=0, le=2 * np.pi), min_items=1, max_items=1)  # type: ignore

    # a string that is sent over to the config dict and that is necessary for compatibility with QISKIT.
    parameters: str = "delta"
    description: str = "Apply the Rydberg blockade over the whole array"
    # TODO: This should become most likely a type that is then used for the enforcement of the wires.
    coupling_map: List = [[0, 1, 2, 3, 4]]
    qasm_def = "gate rlz(delta) {}"


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


class RydbergExperiment(BaseModel):
    """
    The class that defines the Rydberg experiments. Each of those `RydbergExperiment`s is executed on a `RydbergSpooler`
    """

    wire_order: Literal["interleaved", "sequential"] = "sequential"
    # mypy keeps throwing errors here because it does not understand the type.
    # not sure how to fix it, so we leave it as is for the moment
    # HINT: Annotated does not work
    shots: conint(gt=0, le=N_MAX_SHOTS)  # type: ignore
    num_wires: Literal[1]
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


ryd_spooler = RydbergSpooler(
    ins_schema_dict={
        "rx": RXInstruction,
        "rz": RZInstruction,
        "cblock": CBlockInstruction,
        "barrier": MeasureBarrierInstruction,
        "measure": MeasureBarrierInstruction,
    },
    n_wires=N_MAX_WIRES,
    name="alqor_rydberg_simulator",
    version="0.0.1",
    description="A chain of qubits realized through Rydberg atoms.",
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

    dim_per_wire = 2 * spin_per_wire + np.ones(n_wires)
    print(dim_per_wire)
    dim_per_wire = dim_per_wire.astype(int)
    dim_hilbert = np.prod(dim_per_wire)

    # we will need a list of local spin operators as their dimension can change
    # on each wire
    lx_list = []
    ly_list = []
    lz_list = []
    nocc_list = []
    spin_length = 1 / 2
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
                    [(spin_length + m + 1) * (spin_length - m) for m in qudit_range[1:]]
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
                    [(spin_length + m + 1) * (spin_length - m) for m in qudit_range[1:]]
                ),
            ],
            [-1, 1],
        )
    )

    lz = csc_matrix(diags([qudit_range], [0]))
    nocc = csc_matrix(diags([qudit_range + 1 / 2], [0]))
    for i1 in np.arange(0, n_wires):
        # let's put together spin matrices
        lx_list.append(op_at_wire(lx, i1, list(dim_per_wire)))
        ly_list.append(op_at_wire(ly, i1, list(dim_per_wire)))
        lz_list.append(op_at_wire(lz, i1, list(dim_per_wire)))
        nocc_list.append(op_at_wire(nocc, i1, list(dim_per_wire)))

    int_matrix = csc_matrix((dim_hilbert, dim_hilbert))
    for i1 in np.arange(0, n_wires - 1):
        for i2 in np.arange(i1, n_wires - 1):
            int_matrix = (
                int_matrix + nocc_list[i1].dot(nocc_list[i2]) / np.abs(i1 - i2) ** 6
            )

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
        if inst[0] == "rx":
            position = inst[1][0]
            theta = inst[2][0]
            psi = expm_multiply(-1j * theta * lx_list[position], psi)
        if inst[0] == "ry":
            position = inst[1][0]
            theta = inst[2][0]
            psi = expm_multiply(-1j * theta * ly_list[position], psi)
        if inst[0] == "rz":
            position = inst[1][0]
            theta = inst[2][0]
            psi = expm_multiply(-1j * theta * lz_list[position], psi)
        if inst[0] == "clblock":
            # apply gate on all qubits
            theta = inst[2][0]
            psi = expm_multiply(-1j * theta * int_matrix, psi)
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

    json_dict: The job dictonary of all the instructions.
    job_id: the ID of the job we are treating.
    """
    job_id = status_msg_dict["job_id"]

    result_dict = {
        "backend_name": ryd_spooler.name,
        "backend_version": ryd_spooler.version,
        "job_id": job_id,
        "qobj_id": None,
        "success": True,
        "status": "finished",
        "header": {},
        "results": [],
    }
    err_msg, json_is_fine = ryd_spooler.check_json_dict(json_dict)
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
