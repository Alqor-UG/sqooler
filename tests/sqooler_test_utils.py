"""
In this file, we define some utility functions that are used in the 
tests that invole the sqooler and the utils.
"""

from typing import Literal, Optional

from typing_extensions import Annotated
from pydantic import Field
from sqooler.schemes import (
    ExperimentDict,
    ExperimentalInputDict,
    GateInstruction,
)

from sqooler.spoolers import (
    create_memory_data,
)


class DummyInstruction(GateInstruction):
    """
    The test instruction for testing the whole system.

    Attributes:
        name: The string to identify the instruction
        wires: The wire on which the instruction should be applied
            so the indices should be between 0 and N_MAX_WIRES-1
        params: has to be empty
    """

    name: Literal["test"]
    wires: Annotated[
        list[Annotated[int, Field(ge=0, le=0)]], Field(min_length=0, max_length=1)
    ]
    params: Annotated[
        list[Annotated[int, Field(ge=1, le=10)]],
        Field(min_length=1, max_length=1),
    ]
    parameters: str = "omega, delta, phi"
    description: str = "Apply the Rydberg and Rabi coupling over the whole array."
    # TODO: This should become most likely a type that is then used for the enforcement of the wires.
    coupling_map: list = [[0], [1], [2], [0, 1, 2, 3, 4]]
    qasm_def: str = "gate rydberg_full(omega, delta, phi) {}"


class DummyFullInstruction(GateInstruction):
    """
    The time evolution under the global Hamiltonian. It does not allow for any local control.

    Attributes:
        name: The string to identify the instruction
        wires: The wire on which the instruction should be applied
            so the indices should be between 0 and N_MAX_WIRES-1
        params: Define the paramert for `RX`, `RZ`and `RydbergBlock` in this order
    """

    name: Literal["test"] = "test"
    wires: Annotated[
        list[Annotated[int, Field(ge=0, le=5)]],
        Field(min_length=2, max_length=5),
    ]
    params: Annotated[
        list[Annotated[float, Field(ge=0, le=5)]],
        Field(min_length=3, max_length=3),
    ]

    # a string that is sent over to the config dict and that is necessary for compatibility with QISKIT.
    parameters: str = "omega, delta, phi"
    description: str = "Apply the Rydberg and Rabi coupling over the whole array."
    # TODO: This should become most likely a type that is then used for the enforcement of the wires.
    coupling_map: list = [[0], [0, 1, 2, 3, 4]]
    qasm_def: str = "gate rydberg_full(omega, delta, phi) {}"


def dummy_gen_circuit(
    exp_name: str,
    json_dict: ExperimentalInputDict,
    job_id: Optional[str] = None,  # pylint: disable=unused-argument
) -> ExperimentDict:
    """
    A dummy function to generate a circuit from the experiment dict.
    """
    n_shots = json_dict.shots
    ins_list = json_dict.instructions
    _ = json_dict.seed
    shots_array = [1, 2, 3]
    exp_sub_dict = create_memory_data(shots_array, exp_name, n_shots, ins_list)
    return exp_sub_dict
