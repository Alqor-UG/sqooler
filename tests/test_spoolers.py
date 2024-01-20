"""
Here we test the spooler class and its functions.
"""

from typing import Literal, Optional, Iterator, Callable
from pydantic import ValidationError, BaseModel, Field
import shutil
import os

from icecream import ic
from typing_extensions import Annotated
import pytest
from sqooler.schemes import (
    StatusMsgDict,
    ExperimentDict,
    LabscriptParams,
)

from sqooler.spoolers import (
    Spooler,
    gate_dict_from_list,
    LabscriptSpooler,
)


class DummyExperiment(BaseModel):
    """
    The class that defines some basic properties for a test experiment
    """

    wire_order: Literal["interleaved", "sequential"] = "sequential"

    # mypy keeps throwing errors here because it does not understand the type.
    # not sure how to fix it, so we leave it as is for the moment
    # HINT: Annotated does not work
    shots: Annotated[int, Field(gt=0, le=5)]
    num_wires: Annotated[int, Field(ge=1, le=5)]
    instructions: list[list]
    seed: Optional[int] = None


class DummyRemoteClient:
    """
    This is simply a dummy the implements the basic functionality of the remote client.
    """

    def __init__(self) -> None:
        """
        Initialize the dummy remote client.
        """
        self._shot_output_folder = "test"

    def reset_shot_output_folder(self) -> None:
        """
        Reset the shot output folder.
        """
        self._shot_output_folder = "test"

    def get_shot_output_folder(self) -> str:
        """
        Get the shot output folder.
        """
        return self._shot_output_folder

    def set_shot_output_folder(self, folder_name: str) -> None:
        """
        Set the shot output folder.
        """
        self._shot_output_folder = folder_name

    def set_globals(self, globals_dict: dict) -> None:
        """
        Set the globals dict.
        """
        pass

    def set_labscript_file(self, labscript_file: str) -> None:
        """
        Set the labscript file.
        """
        pass

    def engage(self) -> None:
        """
        Engage the remote client.
        """
        pass


class DummyRun:
    """
    This is simply a dummy the implements the basic functionality of the lyse Run class.
    """

    def __init__(self, run_file: str) -> None:
        """
        Initialize the dummy run.

        Args:
            run_file: The path for the file that should be used for the run.
        """
        self.run_file = run_file

    def get_results(self, group: str, name: str) -> int:
        """
        Get the results from the run.
        """
        return 5


class DummyInstruction(BaseModel):
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


def dummy_gen_circuit(
    experiment: dict,  # pylint: disable=unused-argument
    job_id: Optional[str] = None,  # pylint: disable=unused-argument
) -> ExperimentDict:
    """
    A dummy function to generate a circuit from the experiment dict.
    """
    return ExperimentDict(header={}, shots=0, success=True, data={})


def test_spooler_config() -> None:
    """
    Test that it is possible to get the config of the spooler.
    """
    test_spooler = Spooler(ins_schema_dict={}, device_config=DummyExperiment, n_wires=2)

    spooler_config = test_spooler.get_configuration()
    assert spooler_config.num_wires == 2
    assert spooler_config.operational


def test_spooler_operational() -> None:
    """
    Test that it is possible to set the operational status of the spooler.
    """
    test_spooler = Spooler(
        ins_schema_dict={}, device_config=DummyExperiment, n_wires=2, operational=False
    )

    spooler_config = test_spooler.get_configuration()
    assert spooler_config.num_wires == 2
    assert not spooler_config.operational


def test_spooler_add_job_fail() -> None:
    """
    Test that it is possible to add a job to the spooler.
    """

    test_spooler = Spooler(
        ins_schema_dict={}, device_config=DummyExperiment, n_wires=2, operational=False
    )
    status_msg_draft = {
        "job_id": "Test_ID",
        "status": "None",
        "detail": "None",
        "error_message": "None",
    }

    job_payload = {
        "experiment_0": {
            "instructions": [],
            "num_wires": 2,
            "shots": 4,
            "wire_order": "interleaved",
        },
    }
    status_msg_dict = StatusMsgDict(**status_msg_draft)
    result_dict, status_msg_dict = test_spooler.add_job(job_payload, status_msg_dict)
    assert status_msg_dict.status == "ERROR", "Job failed"
    assert result_dict is not None


def test_spooler_add_job() -> None:
    """
    Test that it is possible to add a job to the spooler.
    """

    test_spooler = Spooler(
        ins_schema_dict={"test": DummyInstruction},
        device_config=DummyExperiment,
        n_wires=2,
        operational=False,
    )
    status_msg_draft = {
        "job_id": "Test_ID",
        "status": "None",
        "detail": "None",
        "error_message": "None",
    }

    job_payload = {
        "experiment_0": {
            "instructions": [["test", [0], [2]]],
            "num_wires": 2,
            "shots": 4,
            "wire_order": "interleaved",
        },
    }
    status_msg_dict = StatusMsgDict(**status_msg_draft)
    # should fail gracefully as no  gen_circuit function is defined
    _, status_msg_dict = test_spooler.add_job(job_payload, status_msg_dict)
    assert status_msg_dict.status == "ERROR", "Job failed"
    assert status_msg_dict.error_message == "None; gen_circuit must be set"

    test_spooler.gen_circuit = dummy_gen_circuit
    _, status_msg_dict = test_spooler.add_job(job_payload, status_msg_dict)
    assert status_msg_dict.status == "DONE", "Job failed"


def test_gate_dict() -> None:
    """
    Test that it is possible to create the a nice instruction.
    """
    inst_list = ["test", [1, 2], [0.1, 0.2]]
    gate_dict = gate_dict_from_list(inst_list)
    assert gate_dict.name == "test"

    # test that it fails if the list is too short
    inst_list = ["test", [1, 2]]
    with pytest.raises(IndexError):
        gate_dict_from_list(inst_list)

    # test that it fails if the types doe not work out
    inst_list = ["test", [1, 2], "test"]
    with pytest.raises(ValidationError):
        gate_dict_from_list(inst_list)


def test_spooler_check_json() -> None:
    """
    Test that it is possible to verify the validity of the json.
    """
    test_spooler = Spooler(
        ins_schema_dict={"test": DummyInstruction},
        device_config=DummyExperiment,
        n_wires=2,
        operational=False,
    )

    job_payload = {
        "experiment_0": {
            "instructions": [["test", [0], [2]]],
            "num_wires": 2,
            "shots": 4,
            "wire_order": "interleaved",
        },
    }
    # test that it works if the instructions are not valid as the key is not known

    _, exp_ok = test_spooler.check_json_dict(job_payload)
    assert exp_ok is True

    # test that it works if the instructions are not valid
    job_payload = {
        "experiment_0": {
            "instructions": [["test", [1, 2], [0.1, 0.2]]],
            "num_wires": 2,
            "shots": 4,
            "wire_order": "interleaved",
        },
    }
    # test that it works if the instructions are not valid as the key is not known

    _, exp_ok = test_spooler.check_json_dict(job_payload)
    assert exp_ok is not True


def test_spooler_instructions() -> None:
    """
    Test that it is possible to verify the validity of the instructions.
    """
    test_spooler = Spooler(
        ins_schema_dict={},
        device_config=DummyExperiment,
        n_wires=2,
        operational=False,
    )

    # test that it works if the instructions are not valid as the key is not known
    inst_list = [["load", [0], [1]]]
    err_code, exp_ok = test_spooler.check_instructions(inst_list)
    assert exp_ok is not True
    assert err_code == "No instructions allowed. Add instructions to the spooler."

    # work with a valid instruction and make sure that it verifies that instructions
    # exist
    inst_list = [["test", [0], [1]]]
    err_code, exp_ok = test_spooler.check_instructions(inst_list)
    assert exp_ok is False
    assert err_code == "No instructions allowed. Add instructions to the spooler."

    # test that it works if the instructions are valid
    test_spooler = Spooler(
        ins_schema_dict={"test": DummyInstruction},
        device_config=DummyExperiment,
        n_wires=2,
        operational=False,
    )

    inst_list = [["test", [0], [1]]]
    err_code, exp_ok = test_spooler.check_instructions(inst_list)
    assert exp_ok is True
    assert err_code == ""

    # test that it works if the instructions are valid
    inst_list = [["test", [0], [1]]]
    err_code, exp_ok = test_spooler.check_instructions(inst_list)
    assert exp_ok is True


## Test the labscript spooler
@pytest.fixture
def labscript_storage_setup_teardown() -> Iterator[None]:
    """
    Make sure that the storage folder is empty before and after the test.
    """
    # setup code here if required one day
    # ...

    yield  # this is where the testing happens

    # teardown code here
    shutil.rmtree("test_exp", ignore_errors=True)
    shutil.rmtree("test", ignore_errors=True)


def test_labscript_spooler_config(labscript_storage_setup_teardown: Callable) -> None:
    """
    Test that it is possible to get the config of the spooler.
    """
    labscript_params = LabscriptParams(exp_script_folder="test", t_wait=2)
    test_spooler = LabscriptSpooler(
        ins_schema_dict={},
        device_config=DummyExperiment,
        remote_client=DummyRemoteClient(),
        run=DummyRun,
        n_wires=2,
        labscript_params=labscript_params,
    )

    spooler_config = test_spooler.get_configuration()
    assert spooler_config.num_wires == 2
    assert spooler_config.operational


def test_labscript_spooler_op(labscript_storage_setup_teardown: Callable) -> None:
    """
    Test that it is possible to set the operational status of the spooler.
    """
    labscript_params = LabscriptParams(exp_script_folder="test", t_wait=2)
    test_spooler = LabscriptSpooler(
        ins_schema_dict={},
        device_config=DummyExperiment,
        remote_client=DummyRemoteClient(),
        run=DummyRun,
        n_wires=2,
        operational=False,
        labscript_params=labscript_params,
    )

    spooler_config = test_spooler.get_configuration()
    assert spooler_config.num_wires == 2
    assert not spooler_config.operational


def test_labscript_spooler_modify(labscript_storage_setup_teardown: Callable) -> None:
    """
    Test that it is possible to modify the labscript folder.
    """
    labsript_params = LabscriptParams(exp_script_folder="test_exp", t_wait=2)
    test_spooler = LabscriptSpooler(
        ins_schema_dict={"test": DummyInstruction},
        device_config=DummyExperiment,
        remote_client=DummyRemoteClient(),
        run=DummyRun,
        n_wires=2,
        operational=False,
        labscript_params=labsript_params,
    )
    new_dir = "test_dir"

    modified_path = test_spooler._modify_shot_output_folder(new_dir)
    assert modified_path == "test/test_dir"
    ic(modified_path)


def test_labscript_spooler_add_job(labscript_storage_setup_teardown: Callable) -> None:
    """
    Test that it is possible to add a job to the spooler.
    """
    labsript_params = LabscriptParams(exp_script_folder="test_exp", t_wait=2)
    test_spooler = LabscriptSpooler(
        ins_schema_dict={"test": DummyInstruction},
        device_config=DummyExperiment,
        remote_client=DummyRemoteClient(),
        run=DummyRun,
        n_wires=2,
        operational=False,
        labscript_params=labsript_params,
    )
    status_msg_draft = {
        "job_id": "Test_ID",
        "status": "None",
        "detail": "None",
        "error_message": "None",
    }
    n_shots = 4
    job_payload = {
        "experiment_0": {
            "instructions": [["test", [0], [1.0]]],
            "num_wires": 1,
            "shots": n_shots,
            "wire_order": "interleaved",
        },
    }
    status_msg_dict = StatusMsgDict(**status_msg_draft)

    result_dict, status_msg_dict = test_spooler.add_job(job_payload, status_msg_dict)
    assert status_msg_dict.status == "ERROR", "Job should have failed"
    assert result_dict is not None
    # now add the header at the right position by copying the dummy_header.py file into the exp_script_folder
    # and then run the test again

    # Define the source and destination paths
    source_path = "tests/dummy_header.py"
    destination_path = f"{labsript_params.exp_script_folder}/header.py"
    # make sure that the destination folder exists
    os.makedirs(labsript_params.exp_script_folder, exist_ok=True)
    # Copy the file
    shutil.copy(source_path, destination_path)
    assert os.path.exists(destination_path)

    # now also make sure that the folder where we are looking for files exists
    file_queue_path = "test/Test_ID/experiment_0"
    os.makedirs(file_queue_path, exist_ok=True)
    assert os.path.exists(file_queue_path)

    # now also a mock files to the folder
    for ii in range(n_shots):
        file_path = f"{file_queue_path}/test_{ii}.py"
        with open(file_path, "w") as file:
            file.write("test")
    result_dict, status_msg_dict = test_spooler.add_job(job_payload, status_msg_dict)
    assert status_msg_dict.status == "DONE", "Job should have failed"
