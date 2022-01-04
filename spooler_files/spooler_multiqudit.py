"""
The module that contains all the necessary logic for the multiqudit.
"""

from typing import List
from jsonschema import validate
from jsonschema.exceptions import ValidationError
import numpy as np
from scipy.sparse import identity
from scipy.sparse import diags
from scipy.sparse import csc_matrix
from scipy import sparse
from scipy.sparse.linalg import expm_multiply


MAX_NUM_WIRES = 16

exper_schema = {
    "type": "object",
    "required": ["instructions", "shots", "num_wires"],
    "properties": {
        "instructions": {"type": "array", "items": {"type": "array"}},
        "shots": {"type": "number", "minimum": 0, "maximum": 1000},
        "num_wires": {"type": "number", "minimum": 1, "maximum": MAX_NUM_WIRES},
        "seed": {"type": "number"},
        "wire_order": {"type": "string", "enum": ["interleaved", "sequential"]},
    },
    "additionalProperties": False,
}

rlx_schema = {
    "type": "array",
    "minItems": 3,
    "maxItems": 3,
    "items": [
        {"type": "string", "enum": ["rlx"]},
        {
            "type": "array",
            "maxItems": 1,
            "items": [{"type": "number", "minimum": 0, "maximum": MAX_NUM_WIRES - 1}],
        },
        {
            "type": "array",
            "items": [{"type": "number", "minimum": 0, "maximum": 6.284}],
        },
    ],
}

rlz_schema = {
    "type": "array",
    "minItems": 3,
    "maxItems": 3,
    "items": [
        {"type": "string", "enum": ["rlz"]},
        {
            "type": "array",
            "maxItems": 1,
            "items": [{"type": "number", "minimum": 0, "maximum": MAX_NUM_WIRES - 1}],
        },
        {
            "type": "array",
            "items": [{"type": "number", "minimum": 0, "maximum": 6.284}],
        },
    ],
}

rlz2_schema = {
    "type": "array",
    "minItems": 3,
    "maxItems": 3,
    "items": [
        {"type": "string", "enum": ["rlz2"]},
        {
            "type": "array",
            "maxItems": 1,
            "items": [{"type": "number", "minimum": 0, "maximum": MAX_NUM_WIRES - 1}],
        },
        {
            "type": "array",
            "items": [{"type": "number", "minimum": 0, "maximum": 10 * 6.284}],
        },
    ],
}

lxly_schema = {
    "type": "array",
    "minItems": 3,
    "maxItems": 3,
    "items": [
        {"type": "string", "enum": ["rlxly"]},
        {
            "type": "array",
            "maxItems": MAX_NUM_WIRES,
            "items": [{"type": "number", "minimum": 0, "maximum": MAX_NUM_WIRES - 1}],
        },
        {
            "type": "array",
            "maxItems": 1,
            "items": [{"type": "number", "minimum": 0, "maximum": 10 * 6.284}],
        },
    ],
}

lzlz_schema = {
    "type": "array",
    "minItems": 3,
    "maxItems": 3,
    "items": [
        {"type": "string", "enum": ["rlzlz"]},
        {
            "type": "array",
            "maxItems": MAX_NUM_WIRES,
            "items": [{"type": "number", "minimum": 0, "maximum": MAX_NUM_WIRES - 1}],
        },
        {
            "type": "array",
            "maxItems": 1,
            "items": [{"type": "number", "minimum": 0, "maximum": 10 * 6.284}],
        },
    ],
}

load_schema = {
    "type": "array",
    "minItems": 3,
    "maxItems": 3,
    "items": [
        {"type": "string", "enum": ["load"]},
        {
            "type": "array",
            "maxItems": 1,
            "items": [{"type": "number", "minimum": 0, "maximum": MAX_NUM_WIRES - 1}],
        },
        {
            "type": "array",
            # set the upper limit for the number of atoms that can be loaded
            # into the single qudit
            "items": [{"type": "number", "minimum": 0, "maximum": 500}],
        },
    ],
}

measure_schema = {
    "type": "array",
    "minItems": 3,
    "maxItems": 3,
    "items": [
        {"type": "string", "enum": ["measure"]},
        {
            "type": "array",
            "maxItems": 1,
            "items": [{"type": "number", "minimum": 0, "maximum": MAX_NUM_WIRES - 1}],
        },
        {"type": "array", "maxItems": 0},
    ],
}


barrier_schema = {
    "type": "array",
    "minItems": 3,
    "maxItems": 3,
    "items": [
        {"type": "string", "enum": ["barrier"]},
        {
            "type": "array",
            "maxItems": MAX_NUM_WIRES,
            "items": [{"type": "number", "minimum": 0, "maximum": MAX_NUM_WIRES - 1}],
        },
        {"type": "array", "maxItems": 0},
    ],
}


def check_with_schema(obj: dict, schm: dict):
    """
    Caller for the validate function of jsonschema
    Args:
        obj (dict): the object that should be checked.
        schm (dict): the schema that defines the object properties.
    Returns:
        boolean flag tellings if dictionary matches schema syntax.
    """
    try:
        validate(instance=obj, schema=schm)
        return "", True
    except ValidationError as exc:
        return str(exc), False


def check_json_dict(json_dict):
    """
    Check if the json file has the appropiate syntax.
    """
    ins_schema_dict = {
        "rlx": rlx_schema,
        "rlz": rlz_schema,
        "rlz2": rlz2_schema,
        "rlxly": lxly_schema,
        "barrier": barrier_schema,
        "measure": measure_schema,
        "load": load_schema,
        "rlzlz": lzlz_schema,
    }
    max_exps = 15
    for expr in json_dict:
        dim_ok = False
        err_code = "Wrong experiment name or too many experiments"
        # pylint: disable=W0703, W0702
        # the following code is right now just weird, but I raised an issue (#16)
        # for anyone to clean it up later.
        try:
            exp_ok = (
                expr.startswith("experiment_")
                and expr[11:].isdigit()
                and (int(expr[11:]) <= max_exps)
            )
        except:
            exp_ok = False
            break
        if not exp_ok:
            break
        err_code, exp_ok = check_with_schema(json_dict[expr], exper_schema)
        if not exp_ok:
            break
        ins_list = json_dict[expr]["instructions"]
        ## Check for schemes
        for ins in ins_list:
            try:
                err_code, exp_ok = check_with_schema(ins, ins_schema_dict[ins[0]])
            except Exception as exc:
                err_code = "Error in instruction " + str(exc)
                exp_ok = False
            if not exp_ok:
                break
        if not exp_ok:
            break
        # Check for load configurations and limit the Hilbert space dimension
        num_wires = json_dict[expr]["num_wires"]
        dim_hilbert = 1
        qubit_wires = num_wires
        for ins in ins_list:
            if ins[0] == "load":
                qubit_wires = qubit_wires - 1
                dim_hilbert = dim_hilbert * ins[2][0]
        dim_hilbert = dim_hilbert * (2 ** qubit_wires)
        dim_ok = dim_hilbert < (2 ** 12) + 1
        if not dim_ok:
            err_code = "Hilbert space dimension too large!"
            break
    return err_code.replace("\n", ".."), exp_ok and dim_ok


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


def create_memory_data(shots_array, exp_name, n_shots):
    """
    The function to create memeory key in results dictionary
    with proprer formatting.
    """
    exp_sub_dict = {
        "header": {"name": "experiment_0", "extra metadata": "text"},
        "shots": 3,
        "success": True,
        "data": {"memory": None},  # slot 1 (Na)      # slot 2 (Li)
    }
    exp_sub_dict["header"]["name"] = exp_name
    exp_sub_dict["shots"] = n_shots
    memory_list = [
        str(shot).replace("[", "").replace("]", "").replace(",", "")
        for shot in shots_array
    ]
    exp_sub_dict["data"]["memory"] = memory_list
    return exp_sub_dict


def gen_circuit(json_dict):
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

        lx_list.append(op_at_wire(lx, i1, dim_per_wire))
        ly_list.append(op_at_wire(ly, i1, dim_per_wire))
        lz_list.append(op_at_wire(lz, i1, dim_per_wire))
        lz2_list.append(op_at_wire(lz2, i1, dim_per_wire))

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
        probs = np.squeeze(abs(psi.toarray()) ** 2)
        result_ind = np.random.choice(dim_hilbert, p=probs, size=n_shots)
        measurements = np.zeros((n_shots, len(measurement_indices)), dtype=int)
        for i1 in range(n_shots):
            observed = np.unravel_index(result_ind[i1], dim_per_wire)
            observed = np.array(observed)
            measurements[i1, :] = observed[measurement_indices]
        shots_array = measurements.tolist()

    exp_sub_dict = create_memory_data(shots_array, exp_name, n_shots)
    return exp_sub_dict


def add_job(json_dict: dict, status_msg_dict: dict):
    """
    The function that translates the json with the instructions into some circuit and executes it.

    It performs several checks for the job to see if it is properly working.
    If things are fine the job gets added the list of things that should be executed.

    json_dict: A dictonary of all the instructions.
    status_msg_dict:  WHAT IS THIS FOR ?
    """
    job_id = status_msg_dict["job_id"]

    result_dict = {
        "backend_name": "synqs_multi_qudit_simulator",
        "backend_version": "0.0.1",
        "job_id": job_id,
        "qobj_id": None,
        "success": True,
        "status": "finished",
        "header": {},
        "results": [],
    }
    err_msg, json_is_fine = check_json_dict(json_dict)
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
