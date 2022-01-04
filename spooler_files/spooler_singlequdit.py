"""
The module that contains all the necessary logic for the singlequdit.
"""

from jsonschema import validate
import numpy as np
from scipy.sparse.linalg import expm_multiply
from scipy.sparse import diags
from scipy.sparse import csc_matrix

exper_schema = {
    "type": "object",
    "required": ["instructions", "shots", "num_wires"],
    "properties": {
        "instructions": {"type": "array", "items": {"type": "array"}},
        "shots": {"type": "number", "minimum": 0, "maximum": 1000},
        "num_wires": {"type": "number", "minimum": 1, "maximum": 2},
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


def add_job(json_dict, status_msg_dict):
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
