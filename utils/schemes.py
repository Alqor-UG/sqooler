"""
The module that contains common logic for schemes, validation etc.
There is no obvious need, why this code should be touch in a new back-end.
"""

from collections.abc import Callable
from pydantic import ValidationError, BaseModel

from typing_extensions import NotRequired, TypedDict


class ExperimentDict(TypedDict):
    """
    A class that defines the structure of the experiments.
    """

    header: dict
    shots: int
    success: bool
    data: dict


class ResultDict(TypedDict):
    """
    A class that defines the structure of results.
    """

    display_name: str
    backend_version: str
    job_id: str
    qobj_id: str | None
    success: bool
    status: str
    header: dict
    results: list
    backend_name: NotRequired[str]


class GateInstruction(BaseModel):
    """
    The basic class for all the gate intructions of a backend.
    Any gate has to have the following attributes.
    """

    name: str
    parameters: str
    description: str
    coupling_map: list
    qasm_def: str = "{}"
    is_gate: bool = True

    @classmethod
    def config_dict(cls) -> dict:
        """
        Give back the properties of the instruction such as needed for the server.
        """
        return {
            "coupling_map": cls.model_fields["coupling_map"].default,
            "description": cls.model_fields["description"].default,
            "name": cls.model_fields["name"].default,
            "parameters": [cls.model_fields["parameters"].default],
            "qasm_def": cls.model_fields["qasm_def"].default,
        }


class Spooler:
    """
    The class for the spooler. So it is not just a scheme, but it also contains some common logic.
    So it should most likely live in another file at some point.

    Attributes:
        n_max_wires: maximum number of wires for the spooler
        n_max_shots: the maximum number of shots for the spooler
        ins_schema_dict : A dictionary the contains all the allowed instructions for this spooler.

    Args:
        exper_schema: Sets the `exper_schema` attribute of the class
        ins_schema_dict : Sets the `ins_schema_dict` attribute of the class
    """

    def __init__(
        self,
        ins_schema_dict: dict,
        n_wires: int,
        description: str = "",
        n_max_shots: int = 1000,
        version: str = "0.0.1",
        cold_atom_type: str = "spin",
        n_max_experiments: int = 15,
        wire_order: str = "interleaved",
        num_species: int = 1,
    ):
        """
        The constructor of the class.
        """
        self.ins_schema_dict = ins_schema_dict
        self.n_max_shots = n_max_shots
        self.n_wires = n_wires
        self.description = description
        self.version = version
        self.cold_atom_type = cold_atom_type
        self.n_max_experiments = n_max_experiments
        self.wire_order = wire_order
        self.num_species = num_species
        self._display_name: str = ""

    def check_experiment(self, exper_dict: dict) -> tuple[str, bool]:
        """
        Check the validity of the experiment.
        This has to be implement in each subclass extra.

        Args:
            exper_dict: The dictionary that contains the logic and should
                be verified.
        """
        raise NotImplementedError("Subclasses should implement this!")

    def get_configuration(self) -> dict:
        """
        Sends back the configuration dictionary of the spooler.
        """
        gate_list = []
        for _, ins_obj in self.ins_schema_dict.items():
            if "is_gate" in ins_obj.model_fields:
                gate_list.append(ins_obj.config_dict())
        return {
            "description": self.description,
            "version": self.version,
            "cold_atom_type": self.cold_atom_type,
            "gates": gate_list,
            "max_experiments": self.n_max_experiments,
            "max_shots": self.n_max_shots,
            "simulator": True,
            "supported_instructions": list(self.ins_schema_dict.keys()),
            "num_wires": self.n_wires,
            "wire_order": self.wire_order,
            "num_species": self.num_species,
        }

    def check_instructions(self, ins_list: list) -> tuple[str, bool]:
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

    def check_dimension(self, json_dict: dict) -> tuple[str, bool]:
        """
        Make sure that the Hilbert space dimension is not too large.

        It can be implemented in the class that inherits, but it is not necessary.
        So this is only a placeholder.

        Args:
            json_dict: the dictonary with the instructions

        Returns:
            str: the error message
            bool: is the dimension ok ?
        """
        # pylint: disable=W0613
        return "", True

    def check_json_dict(self, json_dict: dict) -> tuple[str, bool]:
        """
        Check if the json file has the appropiate syntax.

        Args:
            json_dict (dict): the dictonary that we will test.

        Returns:
            bool: is the expression having the appropiate syntax ?
        """
        for expr in json_dict:
            err_code = "Wrong experiment name or too many experiments"
            # Fix this pylint issue whenever you have time, but be careful !
            # pylint: disable=W0702
            try:
                exp_ok = (
                    expr.startswith("experiment_")
                    and expr[11:].isdigit()
                    and (int(expr[11:]) <= self.n_max_experiments)
                )
            except:
                exp_ok = False
                break
            if not exp_ok:
                break
            # test the structure of the experiment
            err_code, exp_ok = self.check_experiment(json_dict[expr])
            if not exp_ok:
                break
            # time to check the structure of the instructions
            ins_list = json_dict[expr]["instructions"]
            err_code, exp_ok = self.check_instructions(ins_list)
            if not exp_ok:
                break
        return err_code.replace("\n", ".."), exp_ok

    @property
    def display_name(self) -> str:
        """
        The name of the spooler.
        """
        return self._display_name

    @display_name.setter
    def display_name(self, value: str) -> None:
        if isinstance(value, str):  # Check if the provided value is a string
            self._display_name = value
        else:
            raise ValueError("display_name must be a string")

    @property
    def gen_circuit(self) -> Callable[[dict], ExperimentDict]:
        """
        The function that generates the circuit.
        It can be basically anything that allows the execution of the circuit.
        """
        return self._gen_circuit

    @gen_circuit.setter
    def gen_circuit(self, value: Callable[[dict], ExperimentDict]) -> None:
        if callable(value):  # Check if the provided value is a callable (function)
            self._gen_circuit = value
        else:
            raise ValueError("gen_circuit must be a callable function")

    def add_job(
        self, json_dict: dict, status_msg_dict: dict
    ) -> tuple[ResultDict, dict]:
        """
        The function that translates the json with the instructions into some circuit and executes it.
        It performs several checks for the job to see if it is properly working.
        If things are fine the job gets added the list of things that should be executed.

        json_dict: The job dictonary of all the instructions.
        status_msg_dict: the status dictionary of the job we are treating.
        """
        job_id = status_msg_dict["job_id"]

        result_dict: ResultDict = {
            "display_name": self.display_name,
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


def gate_dict_from_list(inst_list: list) -> dict:
    """
    Transforms a list into an appropiate dictionnary for instructions.
    """
    return {"name": inst_list[0], "wires": inst_list[1], "params": inst_list[2]}


def create_memory_data(
    shots_array: list, exp_name: str, n_shots: int
) -> ExperimentDict:
    """
    The function to create memory key in results dictionary
    with proprer formatting.
    """
    exp_sub_dict: ExperimentDict = {
        "header": {"name": "experiment_0", "extra metadata": "text"},
        "shots": 3,
        "success": True,
        "data": {"memory": None},
    }

    exp_sub_dict["header"]["name"] = exp_name
    exp_sub_dict["shots"] = n_shots
    memory_list = [
        str(shot).replace("[", "").replace("]", "").replace(",", "")
        for shot in shots_array
    ]
    exp_sub_dict["data"]["memory"] = memory_list
    return exp_sub_dict
