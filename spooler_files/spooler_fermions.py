"""
The module that contains all the necessary logic for the fermions.
"""
from jsonschema import validate
import numpy as np
from scipy.sparse.linalg import expm

NUM_WIRES = 8

exper_schema = {
    "type": "object",
    "required": ["instructions", "shots", "num_wires", "wire_order"],
    "properties": {
        "instructions": {"type": "array", "items": {"type": "array"}},
        "shots": {"type": "number", "minimum": 0, "maximum": 10 ** 3},
        "num_wires": {"type": "number", "minimum": 1, "maximum": 8},
        "seed": {"type": "number"},
        "wire_order": {"type": "string", "enum": ["interleaved"]},
    },
    "additionalProperties": False,
}

barrier_schema = {
    "type": "array",
    "minItems": 3,
    "maxItems": 3,
    "items": [
        {"type": "string", "enum": ["barrier"]},
        {
            "type": "array",
            "maxItems": NUM_WIRES,
            "items": [{"type": "number", "minimum": 0, "maximum": NUM_WIRES - 1}],
        },
        {"type": "array", "maxItems": 0},
    ],
}

load_measure_schema = {
    "type": "array",
    "minItems": 3,
    "maxItems": 3,
    "items": [
        {"type": "string", "enum": ["load", "measure"]},
        {
            "type": "array",
            "maxItems": 2,
            "items": [{"type": "number", "minimum": 0, "maximum": NUM_WIRES - 1}],
        },
        {"type": "array", "maxItems": 0},
    ],
}

hop_schema = {
    "type": "array",
    "minItems": 3,
    "maxItems": 3,
    "items": [
        {"type": "string", "enum": ["fhop"]},
        {
            "type": "array",
            "maxItems": 4,
            "items": [{"type": "number", "minimum": 0, "maximum": 7}],
        },
        {
            "type": "array",
            "items": [{"type": "number", "minimum": 0, "maximum": 6.284}],
        },
    ],
}

int_schema = {
    "type": "array",
    "minItems": 3,
    "maxItems": 3,
    "items": [
        {"type": "string", "enum": ["fint", "fphase"]},
        {
            "type": "array",
            "maxItems": 8,
            "items": [{"type": "number", "minimum": 0, "maximum": 7}],
        },
        {
            "type": "array",
            "items": [{"type": "number", "minimum": 0, "maximum": 6.284}],
        },
    ],
}


def check_with_schema(obj, schm):
    """
    Caller for the validate function.
    """
    # Fix this pylint issue whenever you have time, but be careful !
    # pylint: disable=W0703
    try:
        validate(instance=obj, schema=schm)
        return "", True
    except Exception as err:
        return str(err), False


def check_json_dict(json_dict):
    """
    Check if the json file has the appropiate syntax.

    Args:
        json_dict (dict): the dictonary that we will test.

    Returns:
        bool: is the expression having the appropiate syntax ?
    """
    ins_schema_dict = {
        "load": load_measure_schema,
        "barrier": barrier_schema,
        "fhop": hop_schema,
        "fint": int_schema,
        "fphase": int_schema,
        "measure": load_measure_schema,
    }
    max_exps = 50
    for expr in json_dict:
        err_code = "Wrong experiment name or too many experiments"
        # Fix this pylint issue whenever you have time, but be careful !
        # pylint: disable=W0702
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
        for ins in ins_list:
            # Fix this pylint issue whenever you have time, but be careful !
            # pylint: disable=W0703
            try:
                err_code, exp_ok = check_with_schema(ins, ins_schema_dict[ins[0]])
            except Exception as err:
                err_code = "Error in instruction " + str(err)
                exp_ok = False
            if not exp_ok:
                break
        if not exp_ok:
            break
    return err_code.replace("\n", ".."), exp_ok


def nested_kronecker_product(a):
    """putting together a large operator from a list of matrices.

    Provide an example here.

    Args:
        a (list): A list of matrices that can connected.

    Returns:
        array: An matrix that operates on the connected Hilbert space.
    """
    if len(a) == 2:
        return np.kron(a[0], a[1])
    else:
        return np.kron(a[0], nested_kronecker_product(a[1:]))


def jordan_wigner_transform(j: int, lattice_length: int) -> np.array:
    """
    Builds up the fermionic operators in a 1D lattice.
    For details see : https://arxiv.org/abs/0705.1928

    Args:
        j : site index
        lattice_length :  how many sites does the lattice have ?

    Returns:
        psi_x: the field operator of creating a fermion on size j
    """
    p_arr = np.array([[0, 1], [0, 0]])
    z_arr = np.array([[1, 0], [0, -1]])
    id_arr = np.eye(2)
    operators = []
    for dummy in range(j):
        operators.append(z_arr)
    operators.append(p_arr)
    for dummy in range(lattice_length - j - 1):
        operators.append(id_arr)
    return nested_kronecker_product(operators)


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
    if "seed" in json_dict[next(iter(json_dict))]:
        np.random.seed(json_dict[next(iter(json_dict))]["seed"])
    tweezer_len = 4  # length of the tweezer array
    n_states = 2 ** (2 * tweezer_len)

    # create all the raising and lowering operators
    lattice_length = 2 * tweezer_len
    lowering_op_list = []
    for i in range(lattice_length):
        lowering_op_list.append(jordan_wigner_transform(i, lattice_length))

    number_operators = []
    for i in range(lattice_length):
        number_operators.append(lowering_op_list[i].T.conj().dot(lowering_op_list[i]))
    # interaction Hamiltonian
    h_int = 0 * number_operators[0]
    for ii in range(tweezer_len):
        spindown_ind = 2 * ii
        spinup_ind = 2 * ii + 1
        h_int += number_operators[spindown_ind].dot(number_operators[spinup_ind])

    # work our way through the instructions
    psi = 1j * np.zeros(n_states)
    psi[0] = 1
    measurement_indices = []
    shots_array = []
    # pylint: disable=C0200
    # Fix this pylint issue whenever you have time, but be careful !
    for i in range(len(ins_list)):
        inst = ins_list[i]
        if inst[0] == "load":
            latt_ind = inst[1][0]
            psi = np.dot(lowering_op_list[latt_ind].T, psi)
        if inst[0] == "fhop":
            # the first two indices are the starting points
            # the other two indices are the end points
            latt_ind = inst[1]
            theta = inst[2][0]
            # couple
            h_hop = lowering_op_list[latt_ind[0]].T.dot(lowering_op_list[latt_ind[2]])
            h_hop += lowering_op_list[latt_ind[2]].T.dot(lowering_op_list[latt_ind[0]])
            h_hop += lowering_op_list[latt_ind[1]].T.dot(lowering_op_list[latt_ind[3]])
            h_hop += lowering_op_list[latt_ind[3]].T.dot(lowering_op_list[latt_ind[1]])
            u_hop = expm(-1j * theta * h_hop)
            psi = np.dot(u_hop, psi)
        if inst[0] == "fint":
            # the first two indices are the starting points
            # the other two indices are the end points
            theta = inst[2][0]
            u_int = expm(-1j * theta * h_int)
            # theta = inst[2][0]
            psi = np.dot(u_int, psi)
        if inst[0] == "fphase":
            # the first two indices are the starting points
            # the other two indices are the end points
            h_phase = 0 * number_operators[0]
            for ii in inst[1]:  # np.arange(len(inst[1])):
                h_phase += number_operators[ii]
            theta = inst[2][0]
            u_phase = expm(-1j * theta * h_phase)
            psi = np.dot(u_phase, psi)
        if inst[0] == "measure":
            measurement_indices.append(inst[1][0])

    # only give back the needed measurments
    if measurement_indices:
        probs = np.abs(psi) ** 2
        result_inds = np.random.choice(np.arange(n_states), p=probs, size=n_shots)

        measurements = np.zeros((n_shots, len(measurement_indices)), dtype=int)
        for jj in range(n_shots):
            result = np.zeros(n_states)
            result[result_inds[jj]] = 1

            for ii, ind in enumerate(measurement_indices):
                observed = number_operators[ind].dot(result)
                observed = observed.dot(result)
                measurements[jj, ii] = int(observed)
        shots_array = measurements.tolist()

    # print("done calc")
    exp_sub_dict = create_memory_data(shots_array, exp_name, n_shots)
    return exp_sub_dict


def add_job(json_dict, status_msg_dict):
    """
    The function that translates the json with the instructions into some circuit and executes it.
    It performs several checks for the job to see if it is properly working.
    If things are fine the job gets added the list of things that should be executed.

    json_dict: A dictonary of all the instructions.
    job_id: the ID of the job we are treating.
    """
    job_id = status_msg_dict["job_id"]

    result_dict = {
        "backend_name": "synqs_fermionic_tweezer_simulator",
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
