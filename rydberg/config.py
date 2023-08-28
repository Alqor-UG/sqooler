"""
In this module we define all the configuration parameters for the Rydberg package. 

No simulation is performed here. The entire logic is implemented in the `spooler.py` module.
"""

from typing import Tuple, Literal, List, Optional
from pydantic import Field, BaseModel, ValidationError
from typing_extensions import Annotated

import numpy as np

from utils.schemes import (
    Spooler,
    gate_dict_from_list,
    GateInstruction,
)

from .spooler import gen_circuit

N_MAX_WIRES = 5
N_MAX_SHOTS = 1000000
MAX_EXPERIMENTS = 1000


class RlxInstruction(GateInstruction):
    """
    The rlx instruction. As each instruction it requires the following attributes

    Attributes:
        name: The string to identify the instruction
        wires: The wire on which the instruction should be applied
            so the indices should be between 0 and N_MAX_WIRES-1
        params: has to be empty
    """

    name: Literal["rlx"] = "rlx"
    wires: Annotated[
        List[Annotated[int, Field(ge=0, le=N_MAX_WIRES - 1)]],
        Field(min_length=1, max_length=1),
    ]
    params: Annotated[
        List[Annotated[float, Field(ge=0, le=2 * np.pi)]],
        Field(min_length=1, max_length=1),
    ]

    # a string that is sent over to the config dict and that is necessary for compatibility with QISKIT.
    parameters: str = "omega"
    description: str = "Evolution under Rlx"
    # TODO: This should become most likely a type that is then used for the enforcement of the wires.
    coupling_map: List = [[0], [1], [2], [3], [4]]
    qasm_def: str = "gate rlx(omega) {}"


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
    wires: Annotated[
        List[Annotated[int, Field(ge=0, le=N_MAX_WIRES - 1)]],
        Field(min_length=1, max_length=1),
    ]
    params: Annotated[
        List[Annotated[float, Field(ge=0, le=2 * np.pi)]],
        Field(min_length=1, max_length=1),
    ]

    # a string that is sent over to the config dict and that is necessary for compatibility with QISKIT.
    parameters: str = "delta"
    description: str = "Evolution under the Rlz gate"
    # TODO: This should become most likely a type that is then used for the enforcement of the wires.
    coupling_map: List = [[0], [1], [2], [3], [4]]
    qasm_def: str = "gate rlz(delta) {}"


class RydbergBlockInstruction(GateInstruction):
    """
    The Rydberg blockade instruction. As each instruction it requires the

    Attributes:
        name: The string to identify the instruction
        wires: The wire on which the instruction should be applied
            so the indices should be between 0 and N_MAX_WIRES-1
        params: has to be empty
    """

    name: Literal["rydberg_block"] = "rydberg_block"
    wires: Annotated[
        List[Annotated[int, Field(ge=0, le=N_MAX_WIRES - 1)]],
        Field(min_length=2, max_length=N_MAX_WIRES),
    ]
    params: Annotated[
        List[Annotated[float, Field(ge=0, le=2 * np.pi)]],
        Field(min_length=1, max_length=1),
    ]

    # a string that is sent over to the config dict and that is necessary for compatibility with QISKIT.
    parameters: str = "phi"
    description: str = "Apply the Rydberg blockade over the whole array"
    # TODO: This should become most likely a type that is then used for the enforcement of the wires.
    coupling_map: List = [[0, 1, 2, 3, 4]]
    qasm_def: str = "gate rydberg_block(phi) {}"


class RydbergFullInstruction(GateInstruction):
    """
    The time evolution under the global Hamiltonian. It does not allow for any local control.

    Attributes:
        name: The string to identify the instruction
        wires: The wire on which the instruction should be applied
            so the indices should be between 0 and N_MAX_WIRES-1
        params: Define the paramert for `RX`, `RZ`and `RydbergBlock` in this order
    """

    name: Literal["rydberg_full"] = "rydberg_full"
    wires: Annotated[
        List[Annotated[int, Field(ge=0, le=N_MAX_WIRES - 1)]],
        Field(min_length=2, max_length=N_MAX_WIRES),
    ]
    params: Annotated[
        List[Annotated[float, Field(ge=0, le=5e6 * np.pi)]],
        Field(min_length=3, max_length=3),
    ]

    # a string that is sent over to the config dict and that is necessary for compatibility with QISKIT.
    parameters: str = "omega, delta, phi"
    description: str = "Apply the Rydberg and Rabi coupling over the whole array."
    # TODO: This should become most likely a type that is then used for the enforcement of the wires.
    coupling_map: List = [[0, 1, 2, 3, 4]]
    qasm_def: str = "gate rydberg_full(omega, delta, phi) {}"


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
    wires: Annotated[
        List[Annotated[int, Field(ge=0, le=N_MAX_WIRES - 1)]],
        Field(min_length=0, max_length=N_MAX_WIRES),
    ]
    params: Annotated[List[float], Field(max_length=0)]


class MeasureInstruction(BaseModel):
    """
    The measure instruction.

    Attributes:
        name: How to identify the instruction
        wires: Exactly one wire has to be given.
        params: Has to be empty
    """

    name: Literal["measure"]
    wires: Annotated[
        List[Annotated[int, Field(ge=0, le=N_MAX_WIRES - 1)]],
        Field(min_length=1, max_length=1),
    ]
    params: Annotated[List[float], Field(max_length=0)]


class RydbergExperiment(BaseModel):
    """
    The class that defines the Rydberg experiments. Each of those
    `RydbergExperiment`s is executed on a `RydbergSpooler`.
    """

    wire_order: Literal["interleaved", "sequential"] = "sequential"
    # mypy keeps throwing errors here because it does not understand the type.
    # not sure how to fix it, so we leave it as is for the moment
    # HINT: Annotated does not work
    shots: Annotated[int, Field(gt=0, le=N_MAX_SHOTS)]
    num_wires: Annotated[int, Field(ge=1, le=N_MAX_WIRES)]
    instructions: List[list]
    seed: Optional[int] = None


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


spooler_object = RydbergSpooler(
    ins_schema_dict={
        "rlx": RlxInstruction,
        "rlz": RlzInstruction,
        "rydberg_block": RydbergBlockInstruction,
        "rydberg_full": RydbergFullInstruction,
        "barrier": BarrierInstruction,
        "measure": MeasureInstruction,
    },
    n_wires=N_MAX_WIRES,
    version="0.3",
    description="A chain of qubits realized through Rydberg atoms.",
    n_max_experiments=MAX_EXPERIMENTS,
    n_max_shots=N_MAX_SHOTS,
)

# Now also add the function that generates the circuit
spooler_object.gen_circuit = gen_circuit
