import json
from jsonschema import validate
from jsonschema.exceptions import ValidationError
import numpy as np
from scipy.sparse.linalg import expm_multiply
from scipy.sparse import diags
from scipy.sparse import csc_matrix

from drpbx import *
#from .models import Job

exper_schema = {
    "type": "object",
    "required": ["instructions", "shots", "num_wires"],
    "properties": {
        "instructions": {"type": "array", "items": {"type": "array"}},
        "shots": {"type": "number", "minimum": 0, "maximum": 1000},
        "num_wires": {"type": "number", "minimum": 1, "maximum": 2},
        "seed": {"type": "number"},
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
            "maxItems": 2,
            "items": [{"type": "number", "minimum": 0, "maximum": 1}],
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
            "maxItems": 2,
            "items": [{"type": "number", "minimum": 0, "maximum": 1}],
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
            "maxItems": 2,
            "items": [{"type": "number", "minimum": 0, "maximum": 1}],
        },
        {
            "type": "array",
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
            "maxItems": 2,
            "items": [{"type": "number", "minimum": 0, "maximum": 0}],
        },
        {
            "type": "array",
            # set the upper limit for the number of atoms that can be loaded
            # into the single qudit
            "items": [{"type": "number", "minimum": 0, "maximum": 500}],
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
            "maxItems": 2,
            "items": [{"type": "number", "minimum": 0, "maximum": 0}],
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
            "maxItems": 2,
            "items": [{"type": "number", "minimum": 0, "maximum": 1}],
        },
        {"type": "array", "maxItems": 0},
    ],
}


def check_with_schema(obj, schm):
    """
    wrapper for the validate function.
    """
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
        "barrier": barrier_measure_schema,
        "measure": barrier_measure_schema,
        "load": load_schema,
    }
    max_exps = 15
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
    # pylint: disable=R0914
    exp_name = next(iter(json_dict))
    ins_list = json_dict[next(iter(json_dict))]["instructions"]
    n_shots = json_dict[next(iter(json_dict))]["shots"]
    if "seed" in json_dict[next(iter(json_dict))]:
        np.random.seed(json_dict[next(iter(json_dict))]["seed"])

    n_atoms = 1

    l = n_atoms / 2  # spin length

    # let's put together spin matrices
    dim_qudit = n_atoms + 1
    qudit_range = np.arange(l, -(l + 1), -1)

    Lx = csc_matrix(
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
    Lz = csc_matrix(diags([qudit_range], [0]))
    Lz2 = Lz.multiply(Lz)

    psi = 1j * np.zeros(dim_qudit)
    psi[0] = 1 + 1j * 0
    shots_array = []
    # work our way through the instructions
    for inst in ins_list:
        # this must always be the first instruction. Otherwise we should
        # raise some error
        if inst[0] == "load":
            n_atoms = int(inst[2][0])
            l = n_atoms / 2
            # length of the qudit
            dim_qudit = n_atoms + 1
            qudit_range = np.arange(l, -(l + 1), -1)

            Lx = csc_matrix(
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
            Lz = csc_matrix(diags([qudit_range], [0]))

            Lz2 = Lz.multiply(Lz)

            psi = 1j * np.zeros(dim_qudit)
            psi[0] = 1 + 1j * 0

        if inst[0] == "rlx":
            theta = inst[2][0]
            psi = expm_multiply(-1j * theta * Lx, psi)
        if inst[0] == "rlz":
            theta = inst[2][0]
            psi = expm_multiply(-1j * theta * Lz, psi)
        if inst[0] == "rlz2":
            theta = inst[2][0]
            psi = expm_multiply(-1j * theta * Lz2, psi)
        if inst[0] == "measure":
            probs = np.abs(psi) ** 2
            result = np.random.choice(np.arange(dim_qudit), p=probs, size=n_shots)

    shots_array = result.tolist()
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
        "backend_name": "synqs_single_qudit_simulator",
        "backend_version": "0.0.2",
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
