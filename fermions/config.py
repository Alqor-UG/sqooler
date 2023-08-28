"""
In this module we define all the configuration parameters for the fermions package. 

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

NUM_WIRES = 8
N_MAX_SHOTS = 10**6
MAX_EXPERIMENTS = 1000
N_MAX_WIRES = 8

# define the instructions in the following


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
        List[Annotated[int, Field(ge=0, le=NUM_WIRES - 1)]],
        Field(min_length=0, max_length=NUM_WIRES),
    ]
    params: Annotated[List[float], Field(max_length=0)]


class LoadMeasureInstruction(BaseModel):
    """
    The load or measure instruction.

    Attributes:
        name: How to identify the instruction
        wires: Exactly one wire has to be given.
        params: Has to be empty
    """

    name: Literal["load", "measure"]
    wires: Annotated[
        List[Annotated[int, Field(ge=0, le=NUM_WIRES - 1)]],
        Field(min_length=1, max_length=1),
    ]
    params: Annotated[List[float], Field(max_length=0)]


class HopInstruction(GateInstruction):
    """
    The instruction that applies the hopping gate.

    Attributes:
        name: How to identify the instruction
        wires: Exactly four wires have to be given.
        params: between 0 and 2 pi
        coupling_map: contains all the allowed configurations. Currently not used
    """

    name: Literal["fhop"] = "fhop"
    wires: Annotated[
        List[Annotated[int, Field(ge=0, le=NUM_WIRES - 1)]],
        Field(min_length=4, max_length=4),
    ]
    params: Annotated[
        List[Annotated[float, Field(ge=0, le=2 * np.pi)]], Field(max_length=1)
    ]

    # a string that is sent over to the config dict and that is necessary for compatibility with QISKIT.
    parameters: str = "j_i"
    description: str = "hopping of atoms to neighboring tweezers"
    # TODO: This should become most likely a type that is then used for the enforcement of the wires.
    coupling_map: List = [
        [0, 1, 2, 3],
        [2, 3, 4, 5],
        [4, 5, 6, 7],
        [0, 1, 2, 3, 4, 5, 6, 7],
    ]


class IntInstruction(GateInstruction):
    """
    The instruction that applies the interaction gate.

    Attributes:
        name: How to identify the instruction
        wires: Exactly one wire has to be given.
        params: Has to be empty
    """

    name: Literal["fint"] = "fint"
    wires: Annotated[
        List[Annotated[int, Field(ge=0, le=NUM_WIRES - 1)]],
        Field(min_length=2, max_length=NUM_WIRES),
    ]
    params: Annotated[
        List[Annotated[float, Field(ge=0, le=2 * np.pi)]], Field(max_length=1)
    ]

    # a string that is sent over to the config dict and that is necessary for compatibility with QISKIT.
    parameters: str = "u"
    description: str = "on-site interaction of atoms of opposite spin state"
    # TODO: This should become most likely a type that is then used for the enforcement of the wires.
    coupling_map: List = [[0, 1, 2, 3, 4, 5, 6, 7]]


class PhaseInstruction(GateInstruction):
    """
    The instruction that applies the interaction gate.

    Attributes:
        name: How to identify the instruction
        wires: Exactly one wire has to be given.
        params: Has to be empty
    """

    name: Literal["fphase"] = "fphase"
    wires: Annotated[
        List[Annotated[int, Field(ge=0, le=NUM_WIRES - 1)]],
        Field(min_length=2, max_length=2),
    ]
    params: Annotated[
        List[Annotated[float, Field(ge=0, le=2 * np.pi)]], Field(max_length=1)
    ]

    # a string that is sent over to the config dict and that is necessary for compatibility with QISKIT.
    parameters: str = "mu_i"
    description: str = (
        "Applying a local phase to tweezers through an external potential"
    )
    # TODO: This should become most likely a type that is then used for the enforcement of the wires.
    coupling_map: List = [[0, 1], [2, 3], [4, 5], [6, 7], [0, 1, 2, 3, 4, 5, 6, 7]]


class FermionExperiment(BaseModel):
    """
    The class that defines the fermion experiments
    """

    wire_order: Literal["interleaved"]
    # we use the Annotated notation to make mypy happy with constrained types
    shots: Annotated[int, Field(gt=0, le=N_MAX_SHOTS)]
    num_wires: Annotated[int, Field(ge=1, le=N_MAX_WIRES)]
    instructions: List[list]
    seed: Optional[int] = None


class FermionSpooler(Spooler):
    """
    The sppoler class that handles all the circuit logic.
    """

    def check_experiment(self, exper_dict: dict) -> Tuple[str, bool]:
        """
        Check the validity of the experiment.
        """
        try:
            FermionExperiment(**exper_dict)
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


spooler_object = FermionSpooler(
    ins_schema_dict={
        "load": LoadMeasureInstruction,
        "barrier": BarrierInstruction,
        "fhop": HopInstruction,
        "fint": IntInstruction,
        "fphase": PhaseInstruction,
        "measure": LoadMeasureInstruction,
    },
    n_wires=N_MAX_WIRES,
    description=(
        "simulator of a fermionic tweezer hardware. "
        "The even wires denote the occupations of the spin-up fermions"
        " and the odd wires denote the spin-down fermions"
    ),
    n_max_shots=N_MAX_SHOTS,
    n_max_experiments=MAX_EXPERIMENTS,
    cold_atom_type="fermion",
    num_species=2,
    version="0.1",
)

# Now also add the function that generates the circuit
spooler_object.gen_circuit = gen_circuit
