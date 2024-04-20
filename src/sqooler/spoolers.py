"""
This module contains the code for the Spooler classes and its helpers. So it mainly meant to be deployed
on the back-end side for people that would like to perform calculations and work through the job queue.

The main class is the `Spooler` class. It is the class that is used for the simulators. 
The `LabscriptSpooler` class is a specialized version of the `Spooler` class that allows us to execute 
jobs in labscript directly.
"""

import logging
import os
from abc import ABC
from binascii import Error as BinasciiError
from time import sleep
from typing import Any, Callable, Optional, Type

from decouple import config
from pydantic import BaseModel, ValidationError

from .schemes import (
    BackendConfigSchemaIn,
    ColdAtomStr,
    ExperimentalInputDict,
    ExperimentDict,
    GateDict,
    LabscriptParams,
    ResultDict,
    StatusMsgDict,
    WireOrderStr,
    get_init_status,
)
from .security import JWK, jwk_from_config_str


class BaseSpooler(ABC):
    """
    Abstract base class for spoolers. They are the main logic of the back-end.

    Attributes:
        ins_schema_dict : A dictionary the contains all the allowed instructions for this spooler.
        device_config: A dictionary that some main config params for the experiment.
        n_wires: maximum number of wires for the spooler
        n_max_shots: the maximum number of shots for the spooler
        version: the version of the backend
        cold_atom_type: the type of cold atom that is used in the experiment
        n_max_experiments: the maximum number of experiments that can be executed
        wire_order: the order of the wires
        num_species: the number of atomic species in the experiment
        sign: sign the results of the job
    """

    def __init__(
        self,
        ins_schema_dict: dict,
        device_config: Type[BaseModel],
        n_wires: int,
        description: str = "",
        n_max_shots: int = 1000,
        version: str = "0.0.1",
        cold_atom_type: ColdAtomStr = "spin",
        n_max_experiments: int = 15,
        wire_order: WireOrderStr = "interleaved",
        num_species: int = 1,
        sign: bool = False,
    ):
        """
        The constructor of the class.
        """
        self.ins_schema_dict = ins_schema_dict
        self.device_config = device_config
        self.n_max_shots = n_max_shots
        self.n_wires = n_wires
        self.description = description
        self.version = version
        self.cold_atom_type = cold_atom_type
        self.n_max_experiments = n_max_experiments
        self.wire_order = wire_order
        self.num_species = num_species
        self._display_name: str = ""
        self.sign = sign

    def check_experiment(self, exper_dict: dict) -> tuple[str, bool]:
        """
        Check the validity of the experiment. It checks if the the instructions are valid
        based on the device configuration of the spooler.

        Args:
            exper_dict: The dictionary that contains the logic and should
                be verified.

        Returns:
            str: The error message
            bool: Is the experiment ok ?
        """
        try:
            self.device_config(**exper_dict)
            return "", True
        except ValidationError as err:
            return str(err), False

    def get_configuration(self) -> BackendConfigSchemaIn:
        """
        Sends back the configuration dictionary of the spooler.

        This creates the configuration of the Spooler. However, it does not contain
        any information about the operational status. This is not really connected to
        the machine but much rather to the queue etc. So items of the `BackendConfigSchemaIn`
        like `operational` or `last_queue_check` are not set here at just the default values.
        ``

        Returns:
            The configuration dictionary of the spooler.
        """
        gate_list = []
        for _, ins_obj in self.ins_schema_dict.items():
            if "is_gate" in ins_obj.model_fields:
                gate_list.append(ins_obj.config_dict())
        backend_config_dict = {
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
            "display_name": self.display_name,
            "sign": self.sign,
        }
        return BackendConfigSchemaIn(**backend_config_dict)

    def check_instructions(self, ins_list: list) -> tuple[str, bool]:
        """
        Check all the instruction to make sure that they are valid and part
        of the allowed instructions.

        Args:
            ins_list: The list of instructions that should be checked.

        Returns:
            str: The error message
            bool: Are the instructions ok ?
        """
        err_code = ""
        exp_ok = False
        # first check that we actually have any instructions safed in the ins_schema_dict
        if len(self.ins_schema_dict) == 0:
            err_code = "No instructions allowed. Add instructions to the spooler."
            exp_ok = False
            return err_code, exp_ok

        for ins in ins_list:
            try:
                gate_instr = gate_dict_from_list(ins)
                # see if the instruction is part of the allowed instructions
                if gate_instr.name not in self.ins_schema_dict.keys():
                    err_code = f"Instruction {gate_instr.name} not allowed."
                    exp_ok = False
                    return err_code, exp_ok

                # now verify that the parameters are ok
                gate_dict = gate_instr.model_dump()
                self.ins_schema_dict[gate_instr.name](**gate_dict)
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

    def check_json_dict(
        self, json_dict: dict[str, dict]
    ) -> tuple[str, bool, dict[str, ExperimentalInputDict]]:
        """
        Check if the json file has the appropiate syntax.

        Args:
            json_dict (dict): the dictonary that we will test.

        Returns:
            str: the error message
            bool: is the expression having the appropiate syntax ?
            dict: the cleaned dictionary with proper typing
        """
        err_code = "No instructions received."
        exp_ok = False
        clean_dict: dict[str, ExperimentalInputDict] = {}
        for expr in json_dict:
            err_code = "Wrong experiment name or too many experiments"
            # test the name of the experiment
            if not expr.startswith("experiment_"):
                err_code = "Experiment name must start with experiment_"
                exp_ok = False
                break
            if not expr[11:].isdigit():
                err_code = "Experiment name must end with a number"
                exp_ok = False
                break
            if int(expr[11:]) > self.n_max_experiments:
                err_code = f"Experiment number too high. Must be less than {self.n_max_experiments}"
                exp_ok = False
                break
            exp_ok = True

            # test the structure of the experiment
            err_code, exp_ok = self.check_experiment(json_dict[expr])
            if not exp_ok:
                break
            # time to check the structure of the instructions
            ins_list = json_dict[expr]["instructions"]
            err_code, exp_ok = self.check_instructions(ins_list)
            if not exp_ok:
                break
            clean_dict[expr] = self.get_exp_input_dict(json_dict[expr])
        return err_code.replace("\n", ".."), exp_ok, clean_dict

    def _prep_job(
        self, json_dict: dict, job_id: str
    ) -> tuple[ResultDict, StatusMsgDict, dict]:
        """
        Prepare the job for execution. It checks the json file and prepares the
        result and status dictionaries.

        Args:
            json_dict: The dictionary with the instructions.
            job_id: The id of the job.

        Returns:
            result_dict: The dictionary with the results of the job.
            status_msg_dict: The status dictionary of the job.
            clean_dict: The cleaned dictionary with the instructions.
        """
        status_msg_dict = get_init_status()
        status_msg_dict.job_id = job_id

        result_dict = ResultDict(
            display_name=self.display_name,
            backend_version=self.version,
            job_id=job_id,
            status="INITIALIZING",
        )

        result_dict.results = []  # this simply helps pylint to understand the code

        # check that the json_dict is indeed well behaved
        err_msg, json_is_fine, clean_dict = self.check_json_dict(json_dict)

        if not json_is_fine:
            status_msg_dict.detail += (
                "; Failed json sanity check. File will be deleted. Error message : "
                + err_msg
            )
            status_msg_dict.error_message += (
                "; Failed json sanity check. File will be deleted. Error message : "
                + err_msg
            )
            status_msg_dict.status = "ERROR"
            logging.error(
                "Error in json compatibility test.",
                extra={"error_message": status_msg_dict.error_message},
            )
            return result_dict, status_msg_dict, clean_dict

        # now we need to check the dimensionality of the experiment
        dim_err_msg, dim_ok = self.check_dimension(json_dict)
        if not dim_ok:
            status_msg_dict.detail += (
                "; Failed dimensionality test. Too many atoms. File will be deleted. Error message : "
                + dim_err_msg
            )
            status_msg_dict.error_message += (
                "; Failed dimensionality test. Too many atoms. File will be deleted. Error message :  "
                + dim_err_msg
            )
            status_msg_dict.status = "ERROR"
            logging.error(
                "Error in dimensionality test.",
                extra={"error_message": status_msg_dict.error_message},
            )
            return result_dict, status_msg_dict, clean_dict

        return result_dict, status_msg_dict, clean_dict

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

    def get_exp_input_dict(self, json_dict: dict) -> ExperimentalInputDict:
        """
        Transforms the dictionary into an ExperimentalInputDict object.

        Args:
            json_dict: The dictionary that should be transformed.

        Returns:
            A ExperimentalInputDict object.
        """
        raw_ins_list = json_dict["instructions"]
        ins_list = [gate_dict_from_list(instr) for instr in raw_ins_list]
        exp_info = ExperimentalInputDict(
            instructions=ins_list,
            shots=json_dict["shots"],
            wire_order=json_dict["wire_order"],
            num_wires=json_dict["num_wires"],
        )
        exp_info = ExperimentalInputDict(
            instructions=ins_list,
            shots=json_dict["shots"],
            wire_order=json_dict["wire_order"],
            num_wires=json_dict["num_wires"],
            seed=json_dict.get("seed", None),
        )
        return exp_info

    def get_private_jwk(self) -> JWK:
        """
        Get the private JWK for the spooler.

        Returns:
            The private JWK for the spooler.

        Raises:
            ValueError: If the private JWK is not set.
        """
        private_jwk_str = config("PRIVATE_JWK_STR", default=None)
        if private_jwk_str == "":
            logging.error("PRIVATE_JWK_STR must not be empty.")

            raise ValueError("PRIVATE_JWK_STR must not be empty.")

        if private_jwk_str is None:
            logging.error("PRIVATE_JWK_STR is not set and available.")
            raise ValueError("PRIVATE_JWK_STR is not set and available.")
        try:
            return jwk_from_config_str(private_jwk_str)
        except BinasciiError as bin_err:
            logging.error("PRIVATE_JWK_STR is invalid.")
            raise ValueError("PRIVATE_JWK_STR is invalid.") from bin_err


class Spooler(BaseSpooler):
    """
    The class for the spooler as it can be used for simulators.
    """

    @property
    def gen_circuit(self) -> Callable[[str, ExperimentalInputDict], ExperimentDict]:
        """
        The function that generates the circuit.
        It can be basically anything that allows the execution of the circuit.

        Returns:
            The function that generates the circuit.

        Raises:
            ValueError: if the gen_circuit is not a callable function
        """
        if not hasattr(self, "_gen_circuit"):
            raise ValueError("gen_circuit must be set")
        return self._gen_circuit

    @gen_circuit.setter
    def gen_circuit(
        self, value: Callable[[str, ExperimentalInputDict], ExperimentDict]
    ) -> None:
        """
        The setter for the gen_circuit function. The first argument is the name of the
        experiment and the second argument is the dictionary with the instructions.

        Args:
            value: The function that generates the circuit.
        """
        if callable(value):  # Check if the provided value is a callable (function)
            self._gen_circuit = value
        else:
            raise ValueError("gen_circuit must be a callable function")

    def add_job(
        self, json_dict: dict[str, dict], job_id: str
    ) -> tuple[ResultDict, StatusMsgDict]:
        """
        The function that translates the json with the instructions into some circuit and executes it.
        It performs several checks for the job to see if it is properly working.
        If things are fine the job gets added the list of things that should be executed.

        Args:
            json_dict: The job dictonary of all the instructions.
            job_id: the id of the the job we are treating.

        Returns:
            result_dict: The dictionary with the results of the job.
            status_msg_dict: The status dictionary of the job.
        """
        result_dict, status_msg_dict, clean_dict = self._prep_job(json_dict, job_id)
        if status_msg_dict.status == "ERROR":
            return result_dict, status_msg_dict
        # now we can generate the circuit for each experiment
        for exp_name, exp_info in clean_dict.items():
            try:
                result_dict.results.append(self.gen_circuit(exp_name, exp_info))
                logging.info("Experiment %s done.", exp_name)
            except ValueError as err:
                status_msg_dict.detail += "; " + str(err)
                status_msg_dict.error_message += "; " + str(err)
                status_msg_dict.status = "ERROR"
                logging.exception(
                    "Error in gen_circuit.",
                    extra={"error_message": status_msg_dict.error_message},
                )
                return result_dict, status_msg_dict
        status_msg_dict.detail += "; Passed json sanity check; Compilation done. \
                    Shots sent to solver."
        status_msg_dict.status = "DONE"
        return result_dict, status_msg_dict


class LabscriptSpooler(BaseSpooler):
    """
    A specialized spooler class that allows us to execute jobs in labscript directly.
    The main changes are that we need to add the job in a different way and connect it to a
     `runmanager.remoteClient`. It adds three new attributes to the `BaseSpooler` class.

    Attributes:
        remote_client: The remote client that is used to connect to the labscript server.
        labscript_params: The parameters that are used to generate the folder for the shots.
        run: The run object that is used to execute the labscript file.
    """

    def __init__(
        self,
        ins_schema_dict: dict,
        device_config: Type[BaseModel],
        n_wires: int,
        remote_client: Any,  # it would be really nice to fix this type
        labscript_params: LabscriptParams,
        run: Any,  # it would be really nice to fix this type
        description: str = "",
        n_max_shots: int = 1000,
        version: str = "0.0.1",
        cold_atom_type: ColdAtomStr = "spin",
        n_max_experiments: int = 15,
        wire_order: WireOrderStr = "interleaved",
        num_species: int = 1,
        sign: bool = False,
    ):
        """
        The constructor of the class. The  arguments are the same as for the Spooler
        class with two additions.


        """
        super().__init__(
            ins_schema_dict,
            device_config,
            n_wires,
            description,
            n_max_shots,
            version,
            cold_atom_type,
            n_max_experiments,
            wire_order,
            num_species,
            sign,
        )
        self.remote_client = remote_client
        self.labscript_params = labscript_params
        self.run = run

    def add_job(
        self, json_dict: dict[str, dict], job_id: str
    ) -> tuple[ResultDict, StatusMsgDict]:
        """
        The function that translates the json with the instructions into some circuit
        and executes it. It performs several checks for the job to see if it is properly
        working. If things are fine the job gets added the list of things that should be
        executed.

        Args:
            json_dict: The job dictonary of all the instructions.
            job_id: the id of the the job we are treating.

        Returns:
            result_dict: The dictionary with the results of the job.
            status_msg_dict: The status dictionary of the job.
        """
        result_dict, status_msg_dict, clean_dict = self._prep_job(json_dict, job_id)

        if status_msg_dict.status == "ERROR":
            return result_dict, status_msg_dict

        for exp_name, exp_info in clean_dict.items():
            # prepare the shots folder
            self.remote_client.reset_shot_output_folder()
            self._modify_shot_output_folder(job_id + "/" + str(exp_name))

            try:
                result_dict.results.append(self.gen_circuit(exp_name, exp_info, job_id))
            except FileNotFoundError as err:
                error_message = str(err)
                status_msg_dict.detail += "; Failed to generate labscript file."
                status_msg_dict.error_message += f"; Failed to generate labscript \
                            file. Error: {error_message}"
                status_msg_dict.status = "ERROR"
                return result_dict, status_msg_dict
        status_msg_dict.detail += "; Passed json sanity check; Compilation done. \
                    Shots sent to solver."
        status_msg_dict.status = "DONE"
        return result_dict, status_msg_dict

    def _modify_shot_output_folder(self, new_dir: str) -> str:
        """
        I am not sure what this function does.

        Args:
            new_dir: The new directory under which we save the shots.

        Returns:
            The path to the new directory.
        """

        # we should simplify this at some point
        defaut_shot_folder = str(self.remote_client.get_shot_output_folder())

        modified_shot_folder = (defaut_shot_folder.rsplit("\\", 1)[0]) + "/" + new_dir
        # suggested better emthod whcih works the same way on all platforms
        # modified_shot_folder = os.path.join(
        #    os.path.dirname(defaut_shot_folder), new_dir
        # )
        self.remote_client.set_shot_output_folder(modified_shot_folder)
        return modified_shot_folder

    def gen_circuit(
        self, exp_name: str, json_dict: ExperimentalInputDict, job_id: str
    ) -> ExperimentDict:
        """
        This is the main script that generates the labscript file.

        Args:
            exp_name: The name of the experiment
            json_dict: The dictionary that contains the instructions for the circuit.
            job_id: The user id of the user that is running the experiment.

        Returns:
            The path to the labscript file.
        """
        # parameters for the function
        exp_script_folder = self.labscript_params.exp_script_folder

        # local files
        header_path = f"{exp_script_folder}/header.py"
        remote_experiments_path = f"{exp_script_folder}/remote_experiments"
        # make sure that the folder exists
        if not os.path.exists(remote_experiments_path):
            raise FileNotFoundError(
                f"The path {remote_experiments_path} does not exist."
            )

        n_shots = json_dict.shots
        ins_list = json_dict.instructions

        globals_dict = {
            "job_id": "guest",
            "shots": 4,
        }
        globals_dict["shots"] = list(range(n_shots))
        globals_dict["job_id"] = job_id

        self.remote_client.set_globals(globals_dict)
        script_name = f"experiment_{globals_dict['job_id']}.py"
        exp_script = os.path.join(remote_experiments_path, script_name)
        code = ""
        # this is the top part of the script it allows us to import the
        # typical functions that we require for each single sequence
        # first have a look if the file exists
        if not os.path.exists(header_path):
            raise FileNotFoundError(f"Header file not found at {header_path}")

        with open(header_path, "r", encoding="UTF-8") as header_file:
            code = header_file.read()

        # add a line break to the code
        code += "\n"

        with open(exp_script, "w", encoding="UTF-8") as script_file:
            script_file.write(code)

        for inst in ins_list:
            # we can directly use the function name as we have already verified
            # that the function exists in the `add_job` function
            code = f"Experiment.{inst.name}({inst.wires}, {inst.params})\n"
            # we should add proper error handling here
            # pylint: disable=bare-except
            try:
                with open(exp_script, "a", encoding="UTF-8") as script_file:
                    script_file.write(code)
            except:
                logging.error("Something wrong. Does file path exists?")

        code = "Experiment.final_action()" + "\n" + "stop(Experiment.t+0.1)"
        # pylint: disable=bare-except
        try:
            with open(exp_script, "a", encoding="UTF-8") as script_file:
                script_file.write(code)
        except:
            logging.error("Something wrong. Does file path exists?")
        self.remote_client.set_labscript_file(
            exp_script
        )  # CAUTION !! This command only selects the file. It does not generate it!

        # be careful. This is not a blocking command
        self.remote_client.engage()

        # now that we have engaged the calculation we need to wait for the
        # calculation to be done

        # we need to get the current shot output folder
        current_shot_folder = self.remote_client.get_shot_output_folder()
        # we need to get the list of files in the folder
        hdf5_files = get_file_queue(current_shot_folder)

        # we need to wait until we have the right number of files
        while len(hdf5_files) < n_shots:
            sleep(self.labscript_params.t_wait)
            hdf5_files = get_file_queue(current_shot_folder)

        shots_array = []
        # once the files are there we can read them
        for file in hdf5_files:
            this_run = self.run(current_shot_folder + "/" + file)
            got_nat = False
            n_tries = 0
            # sometimes the file is not ready yet. We need to wait a bit
            while not got_nat and n_tries < 15:
                # the exception is raised if the file is not ready yet
                # it is broadly defined within labscript so we cannot do anything about
                # it here.
                # pylint: disable=W0718
                try:
                    # append the result to the array
                    shots_array.append(this_run.get_results("/measure", "nat"))
                    got_nat = True
                except Exception as exc:
                    logging.exception(exc)
                    sleep(self.labscript_params.t_wait)
                    n_tries += 1
        exp_sub_dict = create_memory_data(shots_array, exp_name, n_shots, ins_list)
        return exp_sub_dict


def gate_dict_from_list(inst_list: list) -> GateDict:
    """
    Transforms a list into an appropiate dictionnary for instructions. The list
    is assumed to be in the format [name, wires, params].

    Args:
        inst_list: The list that should be transformed.

    Returns:
        A GateDict object.
    """
    gate_draft = {"name": inst_list[0], "wires": inst_list[1], "params": inst_list[2]}
    return GateDict(**gate_draft)


def get_file_queue(dir_path: str) -> list[str]:
    """
    A function that returns the list of files in the directory.

    Args:
        dir_path: The path to the directory.

    Returns:
        A list of files in the directory. It excludes directories.

    Raises:
        ValueError: If the path is not a directory.
    """

    # make sure that the path is an existing directory
    if not os.path.isdir(dir_path):
        raise ValueError(f"The path {dir_path} is not a directory.")
    files = [
        file
        for file in os.listdir(dir_path)
        if os.path.isfile(os.path.join(dir_path, file))
    ]
    return files


def create_memory_data(
    shots_array: list,
    exp_name: str,
    n_shots: int,
    instructions: Optional[list[GateDict]] = None,
) -> ExperimentDict:
    """
    The function to create memory key in results dictionary
    with proprer formatting.

    Args:
        shots_array: The array with the shots.
        exp_name: The name of the experiment.
        n_shots: The number of shots.
        instructions: The list of instructions that were executed

    Returns:
        The ExperimentDict object describing the results.
    """
    exp_sub_dict: dict = {
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
    if instructions is not None:
        exp_sub_dict["data"]["instructions"] = instructions
    return ExperimentDict(**exp_sub_dict)
