import json
from jsonschema import validate
from drpbx import *

# from .models import Job


import numpy as np
from scipy.sparse import identity
from scipy.sparse import diags
from scipy.sparse import csc_matrix
from scipy import sparse

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

rLx_schema = {
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

rLz_schema = {
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

rLz2_schema = {
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

XY_schema = {
    "type": "array",
    "minItems": 3,
    "maxItems": 3,
    "items": [
        {"type": "string", "enum": ["LxLy"]},
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

LzLz_schema = {
    "type": "array",
    "minItems": 3,
    "maxItems": 3,
    "items": [
        {"type": "string", "enum": ["LzLz"]},
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

barrier_measure_schema = {
    "type": "array",
    "minItems": 3,
    "maxItems": 3,
    "items": [
        {"type": "string", "enum": ["measure", "barrier"]},
        {
            "type": "array",
            "maxItems": 1,
            "items": [{"type": "number", "minimum": 0, "maximum": MAX_NUM_WIRES - 1}],
        },
        {"type": "array", "maxItems": 0},
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
    """
    ins_schema_dict = {
        "rlx": rLx_schema,
        "rlz": rLz_schema,
        "rlz2": rLz2_schema,
        "rlxly": XY_schema,
        "barrier": barrier_measure_schema,
        "measure": barrier_measure_schema,
        "load": load_schema,
        "rlzlz": LzLz_schema,
    }
    max_exps = 15
    for e in json_dict:
        dim_ok = False
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
        ## Check for schemes
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
        # Check for load configurations and limit the Hilbert space dimension
        num_wires = json_dict[e]["num_wires"]
        dim_Hilbert = 1
        qubit_wires = num_wires
        for ins in ins_list:
            if ins[0] == "load":
                qubit_wires = qubit_wires - 1
                dim_Hilbert = dim_Hilbert * ins[2][0]
        dim_Hilbert = dim_Hilbert * (2 ** qubit_wires)
        dim_ok = dim_Hilbert < (2 ** 20) + 1
        if not dim_ok:
            err_code = "Hilbert space dimension to large"
            break
    return err_code.replace("\n", ".."), exp_ok and dim_ok


def op_at_wire(op, pos, dim_per_wire):
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
    n_wires = json_dict[next(iter(json_dict))]["num_wires"]
    spin_per_wire = 1 / 2 * np.ones(n_wires)
    if "seed" in json_dict[next(iter(json_dict))]:
        np.random.seed(json_dict[next(iter(json_dict))]["seed"])

    for ins in ins_list:
        if ins[0] == "load":
            spin_per_wire[ins[1][0]] = 1 / 2 * ins[2][0]

    dim_per_wire = 2 * spin_per_wire + np.ones(n_wires)
    dim_per_wire = dim_per_wire.astype(int)
    dim_Hilbert = np.prod(dim_per_wire)

    Lx = []
    Ly = []
    Lz = []
    Lz2 = []

    for i1 in np.arange(0, n_wires):
        # let's put together spin matrices
        l = spin_per_wire[i1]
        dim_qudit = dim_per_wire[i1]
        qudit_range = np.arange(l, -(l + 1), -1)

        lx = csc_matrix(
            1
            / 2
            * diags(
                [
                    np.sqrt([(l - m + 1) * (l + m) for m in qudit_range[:-1]]),
                    np.sqrt([(l + m + 1) * (l - m) for m in qudit_range[1:]]),
                ],
                [-1, 1],
            )
        )
        ly = csc_matrix(
            1
            / (2 * 1j)
            * diags(
                [
                    np.sqrt([(l - m + 1) * (l + m) for m in qudit_range[:-1]]),
                    -1 * np.sqrt([(l + m + 1) * (l - m) for m in qudit_range[1:]]),
                ],
                [-1, 1],
            )
        )
        lz = csc_matrix(diags([qudit_range], [0]))
        lz2 = lz.dot(lz)

        Lx.append(op_at_wire(lx, i1, dim_per_wire))
        Ly.append(op_at_wire(ly, i1, dim_per_wire))
        Lz.append(op_at_wire(lz, i1, dim_per_wire))
        Lz2.append(op_at_wire(lz2, i1, dim_per_wire))

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
    for i in range(len(ins_list)):
        inst = ins_list[i]
        if inst[0] == "rlx":
            position = inst[1][0]
            theta = inst[2][0]
            psi = sparse.linalg.expm_multiply(-1j * theta * Lx[position], psi)
        if inst[0] == "rly":
            position = inst[1][0]
            theta = inst[2][0]
            psi = sparse.linalg.expm_multiply(-1j * theta * Ly[position], psi)
        if inst[0] == "rlz":
            position = inst[1][0]
            theta = inst[2][0]
            psi = sparse.linalg.expm_multiply(-1j * theta * Lz[position], psi)
        if inst[0] == "rlz2":
            position = inst[1][0]
            theta = inst[2][0]
            psi = sparse.linalg.expm_multiply(-1j * theta * Lz2[position], psi)
        if inst[0] == "rlxly":
            # apply gate on two qudits
            if len(inst[1]) == 2:
                position1 = inst[1][0]
                position2 = inst[1][1]
                theta = inst[2][0]
                LP1 = Lx[position1] + 1j * Ly[position1]
                LP2 = Lx[position2] + 1j * Ly[position2]
                XY = LP1.dot(LP2.conjugate().T)
                XY = XY + XY.conjugate().T
                psi = sparse.linalg.expm_multiply(-1j * theta * XY, psi)
            # apply gate on all qudits
            elif len(inst[1]) == n_wires:
                theta = inst[2][0]
                XY = csc_matrix((dim_Hilbert, dim_Hilbert))
                for i1 in np.arange(0, n_wires - 1):
                    LP1 = Lx[i1] + 1j * Ly[i1]
                    LP2 = Lx[i1 + 1] + 1j * Ly[i1 + 1]
                    XY = XY + LP1.dot(LP2.conjugate().T)
                XY = XY + XY.conjugate().T
                psi = sparse.linalg.expm_multiply(-1j * theta * XY, psi)
        if inst[0] == "rlzlz":
            # apply gate on two quadits
            if len(inst[1]) == 2:
                position1 = inst[1][0]
                position2 = inst[1][1]
                theta = inst[2][0]
                LzLz = Lz[position1].dot(Lz[position2])
                psi = sparse.linalg.expm_multiply(-1j * theta * LzLz, psi)
        if inst[0] == "measure":
            measurement_indices.append(inst[1][0])
    if measurement_indices:
        probs = np.squeeze(abs(psi.toarray()) ** 2)
        resultInd = np.random.choice(dim_Hilbert, p=probs, size=n_shots)
        measurements = np.zeros((n_shots, len(measurement_indices)), dtype=int)
        for i1 in range(n_shots):
            observed = np.unravel_index(resultInd[i1], dim_per_wire)
            observed = np.array(observed)
            measurements[i1, :] = observed[measurement_indices]
        shots_array = measurements.tolist()

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
            result_dict["results"].append(gen_circuit(exp_dict, job_id))
        print("done form")
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
