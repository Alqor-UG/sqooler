import json

# import os
# import time
# mport shutil
from jsonschema import validate
from drpbx import *

# from .models import Job


import numpy as np
from scipy.sparse.linalg import expm
from scipy.sparse import identity
from scipy.sparse import diags
from scipy.sparse import coo_matrix
from scipy.sparse import csc_matrix

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

barrier_measure_schema = {
    "type": "array",
    "minItems": 3,
    "maxItems": 3,
    "items": [
        {"type": "string", "enum": ["load", "measure", "barrier"]},
        {
            "type": "array",
            "maxItems": 2,
            "items": [{"type": "number", "minimum": 0, "maximum": 7}],
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
    try:
        validate(instance=obj, schema=schm)
        return "", True
    except Exception as e:
        return str(e), False


def check_json_dict(json_dict):
    """
    Check if the json file has the appropiate syntax.

    Args:
        json_dict (dict): the dictonary that we will test.

    Returns:
        bool: is the expression having the appropiate syntax ?
    """
    ins_schema_dict = {
        "load": barrier_measure_schema,
        "barrier": barrier_measure_schema,
        "fhop": hop_schema,
        "fint": int_schema,
        "fphase": int_schema,
        "measure": barrier_measure_schema,
    }
    max_exps = 50
    for e in json_dict:
        err_code = "Wrong experiment name or too many experiments"
        try:
            exp_ok = (
                e.startswith("experiment_")
                and e[11:].isdigit()
                and (int(e[11:]) <= max_exps)
            )
        except:
            exp_ok = False
            break
        if not exp_ok:
            break
        err_code, exp_ok = check_with_schema(json_dict[e], exper_schema)
        if not exp_ok:
            break
        ins_list = json_dict[e]["instructions"]
        for ins in ins_list:
            try:
                err_code, exp_ok = check_with_schema(ins, ins_schema_dict[ins[0]])
            except Exception as e:
                err_code = "Error in instruction " + str(e)
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


def jordan_wigner_transform(j, lattice_length):
    """
    Builds up the fermionic operators in a 1D lattice. For details see : https://arxiv.org/abs/0705.1928

    Args:
        j (int): site index
        lattice_length: how many sites does the lattice have ?

    Returns:
        psi_x: the field operator of creating a fermion on size j
    """
    P = np.array([[0, 1], [0, 0]])
    Z = np.array([[1, 0], [0, -1]])
    I = np.eye(2)
    operators = []
    for k in range(j):
        operators.append(Z)
    operators.append(P)
    for k in range(lattice_length - j - 1):
        operators.append(I)
    return nested_kronecker_product(operators)


def create_memory_data(shots_array, exp_name, n_shots):
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


def gen_circuit(json_dict, job_id):
    """The function the creates the instructions for the circuit.

    json_dict: The list of instructions for the specific run.
    job_id: The id of the job that we are treating right now.
    """
    exp_name = next(iter(json_dict))
    ins_list = json_dict[next(iter(json_dict))]["instructions"]
    n_shots = json_dict[next(iter(json_dict))]["shots"]
    if "seed" in json_dict[next(iter(json_dict))]:
        np.random.seed(json_dict[next(iter(json_dict))]["seed"])
    l = 4  # length of the tweezer array
    Nstates = 2 ** (2 * l)

    # create all the raising and lowering operators
    lattice_length = 2 * l
    loweringOp = []
    for i in range(lattice_length):
        loweringOp.append(jordan_wigner_transform(i, lattice_length))

    number_operators = []
    for i in range(lattice_length):
        number_operators.append(loweringOp[i].T.conj().dot(loweringOp[i]))
    # interaction Hamiltonian
    Hint = 0 * number_operators[0]
    for ii in range(l):
        spindown_ind = 2 * ii
        spinup_ind = 2 * ii + 1
        Hint += number_operators[spindown_ind].dot(number_operators[spinup_ind])

    # work our way through the instructions
    psi = 1j * np.zeros(Nstates)
    psi[0] = 1
    measurement_indices = []
    shots_array = []
    for i in range(len(ins_list)):
        inst = ins_list[i]
        if inst[0] == "load":
            latt_ind = inst[1][0]
            psi = np.dot(loweringOp[latt_ind].T, psi)
        if inst[0] == "fhop":
            # the first two indices are the starting points
            # the other two indices are the end points
            latt_ind = inst[1]
            theta = inst[2][0]
            # couple
            Hhop = loweringOp[latt_ind[0]].T.dot(loweringOp[latt_ind[2]]) + loweringOp[
                latt_ind[2]
            ].T.dot(loweringOp[latt_ind[0]])
            Hhop += loweringOp[latt_ind[1]].T.dot(loweringOp[latt_ind[3]]) + loweringOp[
                latt_ind[3]
            ].T.dot(loweringOp[latt_ind[1]])
            Uhop = expm(-1j * theta * Hhop)
            psi = np.dot(Uhop, psi)
        if inst[0] == "fint":
            # the first two indices are the starting points
            # the other two indices are the end points
            theta = inst[2][0]
            Uint = expm(-1j * theta * Hint)
            # theta = inst[2][0]
            psi = np.dot(Uint, psi)
        if inst[0] == "fphase":
            # the first two indices are the starting points
            # the other two indices are the end points
            Hphase = 0 * number_operators[0]
            for ii in inst[1]:  # np.arange(len(inst[1])):
                Hphase += number_operators[ii]
            theta = inst[2][0]
            Uphase = expm(-1j * theta * Hphase)
            psi = np.dot(Uphase, psi)
        if inst[0] == "measure":
            measurement_indices.append(inst[1][0])

    # only give back the needed measurments
    if measurement_indices:
        probs = np.abs(psi) ** 2
        resultInd = np.random.choice(np.arange(Nstates), p=probs, size=n_shots)

        measurements = np.zeros((n_shots, len(measurement_indices)), dtype=int)
        for jj in range(n_shots):
            result = np.zeros(Nstates)
            result[resultInd[jj]] = 1

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

    It performs several checks for the job to see if it is properly working. If things are fine the job gets added the list of things that should be executed.

    json_dict: A dictonary of all the instructions.
    job_id: the ID of the job we are treating.
    """
    job_id = status_msg_dict["job_id"]
    extracted_username = job_id.split("-")[2]
    requested_backend = job_id.split("-")[1]

    status_json_dir = (
        "/Backend_files/Status/" + requested_backend + "/" + extracted_username + "/"
    )
    status_json_name = "status-" + job_id + ".json"
    status_json_path = status_json_dir + status_json_name

    job_json_name = "job-" + job_id + ".json"
    job_json_start_path = "/Backend_files/Running_Jobs/" + job_json_name

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
            result_dict["results"].append(gen_circuit(exp_dict, job_id))

        result_json_dir = (
            "/Backend_files/Result/"
            + requested_backend
            + "/"
            + extracted_username
            + "/"
        )
        result_json_name = "result-" + job_id + ".json"
        result_json_path = result_json_dir + result_json_name
        result_binary = json.dumps(result_dict).encode("utf-8")
        upload(DUMPSTRING=result_binary, DROPBOXPATH=result_json_path)

        status_msg_dict[
            "detail"
        ] += "; Passed json sanity check; Compilation done. Shots sent to solver."
        status_msg_dict["status"] = "DONE"
        status_binary = json.dumps(status_msg_dict).encode("utf-8")
        upload(DUMPSTRING=status_binary, DROPBOXPATH=status_json_path)

        finished_json_dir = (
            "/Backend_files/Finished_Jobs/"
            + requested_backend
            + "/"
            + extracted_username
            + "/"
        )
        job_json_final_path = finished_json_dir + job_json_name
        move_file(STARTPATH=job_json_start_path, FINALPATH=job_json_final_path)
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
        status_binary = json.dumps(status_msg_dict).encode("utf-8")
        upload(DUMPSTRING=status_binary, DROPBOXPATH=status_json_path)

        deleted_json_dir = "/Backend_files/Deleted_Jobs/"
        job_json_final_path = deleted_json_dir + job_json_name
        move_file(STARTPATH=job_json_start_path, FINALPATH=job_json_final_path)
