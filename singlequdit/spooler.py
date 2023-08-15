"""
The module that contains all the necessary logic to simulate the singlequdit. 
It has to implement the code that is executed for all the instructions that we defined 
in the `conf.py` file.
"""

import numpy as np
from scipy.sparse.linalg import expm_multiply
from scipy.sparse import diags, csc_matrix

from utils.schemes import (
    ExperimentDict,
    create_memory_data,
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
