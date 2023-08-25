"""
In this module we define all the configuration parameters for the multiqudit package. 

No simulation is performed here. The entire logic is implemented in the `spooler.py` module.
"""

from typing import List, Tuple, Literal, Optional
from pydantic import BaseModel, conint, ValidationError, conlist, confloat

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
    wires: conlist(conint(ge=0, le=N_MAX_WIRES - 1), min_items=1, max_items=1)  # type: ignore
    params: conlist(confloat(ge=0, le=2 * pi), min_items=1, max_items=1)  # type: ignore

    # a string that is sent over to the config dict and that is necessary for compatibility with QISKIT.
    parameters: str = "omega"
    description: str = "Evolution under Lx"
    # TODO: This should become most likely a type that is then used for the enforcement of the wires.
    coupling_map: List = [[0], [1], [2], [3], [4]]
    qasm_def = "gate lrx(omega) {}"


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
    wires: conlist(conint(ge=0, le=N_MAX_WIRES - 1), min_items=1, max_items=1)  # type: ignore
    params: conlist(confloat(ge=0, le=2 * pi), min_items=1, max_items=1)  # type: ignore

    # a string that is sent over to the config dict and that is necessary for compatibility with QISKIT.
    parameters: str = "delta"
    description: str = "Evolution under the Z gate"
    # TODO: This should become most likely a type that is then used for the enforcement of the wires.
    coupling_map: List = [[0], [1], [2], [3], [4]]
    qasm_def = "gate rlz(delta) {}"


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
    wires: conlist(conint(ge=0, le=N_MAX_WIRES - 1), min_items=1, max_items=1)  # type: ignore
    params: conlist(confloat(ge=0, le=10 * 2 * pi), min_items=1, max_items=1)  # type: ignore

    # a string that is sent over to the config dict and that is necessary for compatibility with QISKIT.
    parameters: str = "chi"
    description: str = "Evolution under lz2"
    # TODO: This should become most likely a type that is then used for the enforcement of the wires.
    coupling_map: List = [[0], [1], [2], [3], [4]]
    qasm_def = "gate rlz2(chi) {}"


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
    wires: conlist(conint(ge=0, le=N_MAX_WIRES - 1), min_items=2, max_items=N_MAX_WIRES)  # type: ignore
    params: conlist(confloat(ge=0, le=10 * 2 * pi), min_items=1, max_items=1)  # type: ignore

    # a string that is sent over to the config dict and that is necessary for compatibility with QISKIT.
    parameters: str = "J"
    description: str = "Entanglement between neighboring gates with an xy interaction"
    # TODO: This should become most likely a type that is then used for the enforcement of the wires.
    coupling_map: List = [[0, 1], [1, 2], [2, 3], [3, 4], [0, 1, 2, 3, 4]]
    qasm_def = "gate rlylx(J) {}"


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
    wires: conlist(conint(ge=0, le=N_MAX_WIRES - 1), min_items=2, max_items=N_MAX_WIRES)  # type: ignore
    params: conlist(confloat(ge=0, le=10 * 2 * pi), min_items=1, max_items=1)  # type: ignore

    # a string that is sent over to the config dict and that is necessary for compatibility with QISKIT.
    parameters: str = "J"
    description: str = "Entanglement between neighboring gates with a zz interaction"
    # TODO: This should become most likely a type that is then used for the enforcement of the wires.
    coupling_map: List = [[0, 1], [1, 2], [2, 3], [3, 4], [0, 1, 2, 3, 4]]
    qasm_def = "gate rlzlz(J) {}"


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
    wires: conlist(conint(ge=0, le=N_MAX_WIRES - 1), min_items=0, max_items=N_MAX_WIRES)  # type: ignore
    params: conlist(float, max_items=0)  # type: ignore


class LoadInstruction(BaseModel):
    """
    The load instruction.

    Attributes:
        name: How to identify the instruction
        wires: Exactly one wire has to be given.
        params: The number of atoms to be loaded onto the wire.
    """

    name: Literal["load"]
    wires: conlist(conint(ge=0, le=N_MAX_WIRES - 1), min_items=1, max_items=1)  # type: ignore
    params: conlist(conint(ge=1, le=N_MAX_ATOMS), min_items=1, max_items=1)  # type: ignore


class MeasureInstruction(BaseModel):
    """
    The measure instruction.

    Attributes:
        name: How to identify the instruction
        wires: Exactly one wire has to be given.
        params: Has to be empty
    """

    name: Literal["measure"]
    wires: conlist(conint(ge=0, le=N_MAX_WIRES - 1), min_items=1, max_items=1)  # type: ignore
    params: conlist(float, max_items=0)  # type: ignore


class MultiQuditExperiment(BaseModel):
    """
    The class that defines the multi qudit experiments
    """

    wire_order: Literal["interleaved", "sequential"] = "sequential"

    # mypy keeps throwing errors here because it does not understand the type.
    # not sure how to fix it, so we leave it as is for the moment
    # HINT: Annotated does not work
    shots: conint(gt=0, le=N_MAX_SHOTS)  # type: ignore
    num_wires: conint(ge=1, le=N_MAX_WIRES)  # type: ignore
    instructions: List[list]
    seed: Optional[int]


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

    def add_job(self, json_dict: dict, status_msg_dict: dict) -> Tuple[dict, dict]:
        """
        The function that translates the json with the instructions into some circuit and executes it.

        It performs several checks for the job to see if it is properly working.
        If things are fine the job gets added the list of things that should be executed.

        This one is different as it also checks for the size of the Hilbert space.

        json_dict: A dictonary of all the instructions.
        status_msg_dict:  WHAT IS THIS FOR ?
        """
        job_id = status_msg_dict["job_id"]

        result_dict = {
            "backend_name": self.name,
            "backend_version": self.version,
            "job_id": job_id,
            "qobj_id": None,
            "success": True,
            "status": "finished",
            "header": {},
            "results": [],
        }
        err_msg, json_is_fine = self.check_json_dict(json_dict)

        if json_is_fine:
            # check_hilbert_space_dimension
            dim_err_msg, dim_ok = self.check_dimension(json_dict)
            if dim_ok:
                for exp in json_dict:
                    exp_dict = {exp: json_dict[exp]}
                    # Here we
                    result_dict["results"].append(self.gen_circuit(exp_dict))
                print("done form")

                status_msg_dict[
                    "detail"
                ] += "; Passed json sanity check; Compilation done. Shots sent to solver."
                status_msg_dict["status"] = "DONE"
                return result_dict, status_msg_dict

            status_msg_dict["detail"] += (
                "; Failed dimensionality test. Too many atoms. File will be deleted. Error message : "
                + dim_err_msg
            )
            status_msg_dict["error_message"] += (
                "; Failed dimensionality test. Too many atoms. File will be deleted. Error message :  "
                + dim_err_msg
            )
            status_msg_dict["status"] = "ERROR"
            return result_dict, status_msg_dict
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
    name="alqor_multiqudit_simulator",
    description="Setup of a cold atomic gas experiment with a multiple qudits.",
    n_max_experiments=MAX_EXPERIMENTS,
    n_max_shots=N_MAX_SHOTS,
)

# Now also add the function that generates the circuit
spooler_object.gen_circuit = gen_circuit
