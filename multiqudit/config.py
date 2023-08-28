"""
In this module we define all the configuration parameters for the multiqudit package. 

No simulation is performed here. The entire logic is implemented in the `spooler.py` module.
"""

from typing import List, Tuple, Literal, Optional
from pydantic import Field, BaseModel, ValidationError
from typing_extensions import Annotated

from numpy import pi

from utils.schemes import (
    gate_dict_from_list,
    Spooler,
    GateInstruction,
)

from .spooler import gen_circuit

N_MAX_WIRES = 4
N_MAX_SHOTS = int(1e6)
MAX_EXPERIMENTS = 1000
N_MAX_ATOMS = 500
MAX_HILBERT_SPACE_DIM = 2**12

# define the instructions in the following
# rlx instruction

# define the instructions in the following


class RlxInstruction(GateInstruction):
    """
    The rlz instruction. As each instruction it requires the

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
        List[Annotated[float, Field(ge=0, le=2 * pi)]],
        Field(min_length=1, max_length=1),
    ]

    # a string that is sent over to the config dict and that is necessary for compatibility with QISKIT.
    parameters: str = "omega"
    description: str = "Evolution under Lx"
    # TODO: This should become most likely a type that is then used for the enforcement of the wires.
    coupling_map: List = [[0], [1], [2], [3], [4]]
    qasm_def: str = "gate lrx(omega) {}"


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
        List[Annotated[float, Field(ge=0, le=2 * pi)]],
        Field(min_length=1, max_length=1),
    ]

    # a string that is sent over to the config dict and that is necessary for compatibility with QISKIT.
    parameters: str = "delta"
    description: str = "Evolution under the Z gate"
    # TODO: This should become most likely a type that is then used for the enforcement of the wires.
    coupling_map: List = [[0], [1], [2], [3], [4]]
    qasm_def: str = "gate rlz(delta) {}"


class LocalSqueezingInstruction(GateInstruction):
    """
    The rlz2 instruction. As each instruction it requires the

    Attributes:
        name: The string to identify the instruction
        wires: The wire on which the instruction should be applied
            so the indices should be between 0 and N_MAX_WIRES-1
        params: has to be empty
    """

    name: Literal["rlz2"] = "rlz2"
    wires: Annotated[
        List[Annotated[int, Field(ge=0, le=N_MAX_WIRES - 1)]],
        Field(min_length=1, max_length=1),
    ]
    params: Annotated[
        List[Annotated[float, Field(ge=0, le=10 * 2 * pi)]],
        Field(min_length=1, max_length=1),
    ]

    # a string that is sent over to the config dict and that is necessary for compatibility with QISKIT.
    parameters: str = "chi"
    description: str = "Evolution under lz2"
    # TODO: This should become most likely a type that is then used for the enforcement of the wires.
    coupling_map: List = [[0], [1], [2], [3], [4]]
    qasm_def: str = "gate rlz2(chi) {}"


class RlxlyInstruction(GateInstruction):
    """
    The rlxly or rlzlz instruction. As each instruction it requires the

    Attributes:
        name: The string to identify the instruction
        wires: The wire on which the instruction should be applied
            so the indices should be between 0 and N_MAX_WIRES-1
        params: has to be empty
    """

    name: Literal["rlxly"] = "rlxly"
    wires: Annotated[
        List[Annotated[int, Field(ge=0, le=N_MAX_WIRES - 1)]],
        Field(min_length=2, max_length=N_MAX_WIRES),
    ]
    params: Annotated[
        List[Annotated[float, Field(ge=0, le=10 * 2 * pi)]],
        Field(min_length=1, max_length=1),
    ]

    # a string that is sent over to the config dict and that is necessary for compatibility with QISKIT.
    parameters: str = "J"
    description: str = "Entanglement between neighboring gates with an xy interaction"
    # TODO: This should become most likely a type that is then used for the enforcement of the wires.
    coupling_map: List = [[0, 1], [1, 2], [2, 3], [3, 4], [0, 1, 2, 3, 4]]
    qasm_def: str = "gate rlylx(J) {}"


class RlzlzInstruction(GateInstruction):
    """
    The rlzlz instruction. As each instruction it requires the

    Attributes:
        name: The string to identify the instruction
        wires: The wire on which the instruction should be applied
            so the indices should be between 0 and N_MAX_WIRES-1
        params: has to be empty
    """

    name: Literal["rlzlz"] = "rlzlz"
    wires: Annotated[
        List[Annotated[int, Field(ge=0, le=N_MAX_WIRES - 1)]],
        Field(min_length=2, max_length=N_MAX_WIRES),
    ]
    params: Annotated[
        List[Annotated[float, Field(ge=0, le=10 * 2 * pi)]],
        Field(min_length=1, max_length=1),
    ]

    # a string that is sent over to the config dict and that is necessary for compatibility with QISKIT.
    parameters: str = "J"
    description: str = "Entanglement between neighboring gates with a zz interaction"
    # TODO: This should become most likely a type that is then used for the enforcement of the wires.
    coupling_map: List = [[0, 1], [1, 2], [2, 3], [3, 4], [0, 1, 2, 3, 4]]
    qasm_def: str = "gate rlzlz(J) {}"


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


class LoadInstruction(BaseModel):
    """
    The load instruction.

    Attributes:
        name: How to identify the instruction
        wires: Exactly one wire has to be given.
        params: The number of atoms to be loaded onto the wire.
    """

    name: Literal["load"]
    wires: Annotated[
        List[Annotated[int, Field(ge=0, le=N_MAX_WIRES - 1)]],
        Field(min_length=1, max_length=1),
    ]
    params: Annotated[
        List[Annotated[int, Field(ge=1, le=N_MAX_ATOMS)]],
        Field(min_length=1, max_length=1),
    ]


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


class MultiQuditExperiment(BaseModel):
    """
    The class that defines the multi qudit experiments
    """

    wire_order: Literal["interleaved", "sequential"] = "sequential"

    # mypy keeps throwing errors here because it does not understand the type.
    # not sure how to fix it, so we leave it as is for the moment
    # HINT: Annotated does not work
    shots: Annotated[int, Field(gt=0, le=N_MAX_SHOTS)]
    num_wires: Annotated[int, Field(ge=1, le=N_MAX_WIRES)]
    instructions: List[list]
    seed: Optional[int] = None


class MultiQuditSpooler(Spooler):
    """
    The class that contains the logic of the multiqudit spooler.
    """

    def check_experiment(self, exper_dict: dict) -> Tuple[str, bool]:
        """
        Check the validity of the experiment.
        """
        try:
            MultiQuditExperiment(**exper_dict)
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

    def check_dimension(self, json_dict: dict) -> Tuple[str, bool]:
        """
        Make sure that the Hilbert space dimension is not too large.
        """
        dim_ok = False
        err_code = "Wrong experiment name or too many experiments"
        for expr in json_dict:
            num_wires = json_dict[expr]["num_wires"]
            dim_hilbert = 1
            qubit_wires = num_wires
            ins_list = json_dict[expr]["instructions"]
            for ins in ins_list:
                if ins[0] == "load":
                    qubit_wires = qubit_wires - 1
                    dim_hilbert = dim_hilbert * ins[2][0]
            dim_hilbert = dim_hilbert * (2**qubit_wires)
            dim_ok = dim_hilbert < (MAX_HILBERT_SPACE_DIM) + 1
            if not dim_ok:
                err_code = "Hilbert space dimension too large!"
                break
        return err_code.replace("\n", ".."), dim_ok


spooler_object = MultiQuditSpooler(
    ins_schema_dict={
        "rlx": RlxInstruction,
        "rlz": RlzInstruction,
        "rlz2": LocalSqueezingInstruction,
        "rlxly": RlxlyInstruction,
        "rlzlz": RlzlzInstruction,
        "barrier": BarrierInstruction,
        "measure": MeasureInstruction,
        "load": LoadInstruction,
    },
    n_wires=N_MAX_WIRES,
    description="Setup of a cold atomic gas experiment with a multiple qudits.",
    n_max_experiments=MAX_EXPERIMENTS,
    n_max_shots=N_MAX_SHOTS,
    version="0.1",
)

# Now also add the function that generates the circuit
spooler_object.gen_circuit = gen_circuit
