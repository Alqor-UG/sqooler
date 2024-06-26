"""
Here we test the spooler class and its functions.
"""

import logging
import os
import shutil
from typing import Callable, Iterator, Literal, Optional

import pytest
from pydantic import BaseModel, Field, ValidationError
from pytest import LogCaptureFixture
from typing_extensions import Annotated

from sqooler.schemes import LabscriptParams
from sqooler.spoolers import (
    LabscriptSpooler,
    Spooler,
    create_memory_data,
    gate_dict_from_list,
)

from .sqooler_test_utils import DummyInstruction, dummy_gen_circuit


class DummyExperiment(BaseModel):
    """
    The class that defines some basic properties for a test experiment
    """

    wire_order: Literal["interleaved", "sequential"] = "sequential"
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

    def get_results(
        self, group: str, name: str  # pylint: disable=unused-argument
    ) -> int:
        """
        Get the results from the run.
        """
        return 5


@pytest.mark.parametrize("sign_it", [True, False])
def test_spooler_config(sign_it: bool) -> None:
    """
    Test that it is possible to get the config of the spooler.
    """
    test_spooler = Spooler(
        ins_schema_dict={}, device_config=DummyExperiment, n_wires=2, sign=sign_it
    )

    spooler_config = test_spooler.get_configuration()
    assert spooler_config.num_wires == 2

    # and that the signing is properly done
    assert spooler_config.sign == sign_it


def test_spooler_jwk() -> None:
    """
    Test that we can easily get the private jwk.
    """
    test_spooler = Spooler(
        ins_schema_dict={}, device_config=DummyExperiment, n_wires=2, sign=True
    )

    test_spooler.get_private_jwk()

    # old value
    old_private_jwk = os.environ.get("PRIVATE_JWK_STR")
    if old_private_jwk is None:
        raise ValueError("No private key set.")
    # now test what happens if we do not have a private key
    with pytest.raises(ValueError):
        os.environ["PRIVATE_JWK_STR"] = ""
        test_spooler.get_private_jwk()

    # now test what happens if we do not have an appropiate private key
    with pytest.raises(ValueError):
        os.environ["PRIVATE_JWK_STR"] = "sdlkfgjsof"
        test_spooler.get_private_jwk()

    # change back to the old value
    os.environ["PRIVATE_JWK_STR"] = old_private_jwk


def test_spooler_cold_atom() -> None:
    """
    Test that we cannot set the spooler with the wrong cold atom type.
    """

    test_spooler = Spooler(
        ins_schema_dict={},
        device_config=DummyExperiment,
        n_wires=2,
        cold_atom_type="fermion",
    )

    spooler_config = test_spooler.get_configuration()
    assert spooler_config.num_wires == 2

    with pytest.raises(ValidationError):
        test_spooler = Spooler(
            ins_schema_dict={},
            device_config=DummyExperiment,
            n_wires=2,
            cold_atom_type="something",
        )
        spooler_config = test_spooler.get_configuration()


def test_spooler_add_job_fail(
    caplog: LogCaptureFixture,
) -> None:
    """
    Test that it is possible to add a job to the spooler.
    """

    caplog.set_level(logging.INFO)
    test_spooler = Spooler(ins_schema_dict={}, device_config=DummyExperiment, n_wires=2)
    job_id = "Test_ID"

    job_payload = {
        "experiment_0": {
            "instructions": [],
            "num_wires": 2,
            "shots": 4,
            "wire_order": "interleaved",
        },
    }
    result_dict, status_msg_dict = test_spooler.add_job(job_payload, job_id)
    assert status_msg_dict.status == "ERROR", "Job failed"
    assert result_dict is not None
    assert "Error in json compatibility test." in caplog.text


def test_spooler_add_job(
    caplog: LogCaptureFixture,
) -> None:
    """
    Test that it is possible to add a job to the spooler.
    """

    caplog.set_level(logging.INFO)
    test_spooler = Spooler(
        ins_schema_dict={"test": DummyInstruction},
        device_config=DummyExperiment,
        n_wires=2,
    )

    job_id = "Test_ID"

    job_payload = {
        "experiment_0": {
            "instructions": [["test", [0], [2]]],
            "num_wires": 2,
            "shots": 4,
            "wire_order": "interleaved",
        },
    }
    # should fail gracefully as no  gen_circuit function is defined
    _, status_msg_dict = test_spooler.add_job(job_payload, job_id)
    assert status_msg_dict.status == "ERROR", "Job failed"
    assert status_msg_dict.error_message == "None; gen_circuit must be set"

    assert "gen_circuit must be set" in caplog.text
    test_spooler.gen_circuit = dummy_gen_circuit
    _, status_msg_dict = test_spooler.add_job(job_payload, job_id)
    assert status_msg_dict.status == "DONE", "Job failed"
    assert "Experiment experiment_0 done." in caplog.text

    # now also with a seed
    job_payload = {
        "experiment_0": {
            "instructions": [["test", [0], [2]]],
            "num_wires": 2,
            "shots": 4,
            "wire_order": "interleaved",
            "seed": 12345,
        },
    }
    _, status_msg_dict = test_spooler.add_job(job_payload, job_id)
    assert status_msg_dict.status == "DONE", "Job failed"

    # and with a poor seed

    job_payload = {
        "experiment_0": {
            "instructions": [["test", [0], [2]]],
            "num_wires": 2,
            "shots": 4,
            "wire_order": "interleaved",
            "seed": "asbcd",
        },
    }
    _, status_msg_dict = test_spooler.add_job(job_payload, job_id)
    assert status_msg_dict.status == "ERROR", "Job should have failed"
    assert "Error in json compatibility test" in caplog.text


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

    _, exp_ok, _ = test_spooler.check_json_dict(job_payload)
    assert exp_ok is True

    # test that it works if the wires are not in the coupling map
    job_payload = {
        "experiment_0": {
            "instructions": [["test", [0, 1], [2]]],
            "num_wires": 2,
            "shots": 4,
            "wire_order": "interleaved",
        },
    }

    _, exp_ok, _ = test_spooler.check_json_dict(job_payload)
    assert exp_ok is not True

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

    _, exp_ok, _ = test_spooler.check_json_dict(job_payload)
    assert exp_ok is not True


def test_spooler_instructions() -> None:
    """
    Test that it is possible to verify the validity of the instructions.
    """
    test_spooler = Spooler(
        ins_schema_dict={},
        device_config=DummyExperiment,
        n_wires=2,
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
    )

    inst_list = [["test", [0], [1]]]
    err_code, exp_ok = test_spooler.check_instructions(inst_list)
    assert exp_ok is True
    assert err_code == ""

    # test that it works if the instructions are valid
    inst_list = [["test", [0], [1]]]
    err_code, exp_ok = test_spooler.check_instructions(inst_list)
    assert exp_ok is True


def test_wire_orders() -> None:
    """
    Make sure that the wire order is properly tested for.
    """
    test_spooler = Spooler(
        ins_schema_dict={"test": DummyInstruction},
        device_config=DummyExperiment,
        n_wires=2,
        wire_order="interleaved",
    )

    # test that it works if the instructions are valid
    job_payload = {
        "experiment_0": {
            "instructions": [["test", [0], [2]]],
            "num_wires": 2,
            "shots": 4,
            "wire_order": "interleaved",
        },
    }

    _, exp_ok, _ = test_spooler.check_json_dict(job_payload)
    assert exp_ok is True

    # test that it works if the instructions are not valid
    job_payload = {
        "experiment_0": {
            "instructions": [["test", [0], [2]]],
            "num_wires": 2,
            "shots": 4,
            "wire_order": "linear",
        },
    }
    # test that it works if the instructions are not valid as the key is not known

    _, exp_ok, _ = test_spooler.check_json_dict(job_payload)
    assert exp_ok is False

    # and set up a spooler with a different wire order
    test_spooler = Spooler(
        ins_schema_dict={"test": DummyInstruction},
        device_config=DummyExperiment,
        n_wires=2,
        wire_order="sequential",
    )

    job_payload = {
        "experiment_0": {
            "instructions": [["test", [0], [2]]],
            "num_wires": 2,
            "shots": 4,
            "wire_order": "sequential",
        },
    }

    _, exp_ok, _ = test_spooler.check_json_dict(job_payload)
    assert exp_ok is True

    # and with the wrong payload
    job_payload = {
        "experiment_0": {
            "instructions": [["test", [0], [2]]],
            "num_wires": 2,
            "shots": 4,
            "wire_order": "linear",
        },
    }
    _, exp_ok, _ = test_spooler.check_json_dict(job_payload)
    assert exp_ok is False


## Test the labscript spooler
# pylint: disable=W0613, W0621
@pytest.fixture
def ls_storage_setup_td() -> Iterator[None]:
    """
    Make sure that the storage folder is empty before and after the test.
    """
    # setup code here if required one day
    # ...

    yield  # this is where the testing happens

    # teardown code here
    shutil.rmtree("test_exp", ignore_errors=True)
    shutil.rmtree("test", ignore_errors=True)


@pytest.mark.parametrize("sign_it", [True, False])
def test_labscript_spooler_config(sign_it: bool, ls_storage_setup_td: Callable) -> None:
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
        sign=sign_it,
    )

    spooler_config = test_spooler.get_configuration()
    assert spooler_config.num_wires == 2


def test_labscript_spooler_modify(ls_storage_setup_td: Callable) -> None:
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
        labscript_params=labsript_params,
    )
    new_dir = "test_dir"

    modified_path = test_spooler._modify_shot_output_folder(new_dir)
    assert modified_path == "test/test_dir"


@pytest.mark.parametrize("sign_it", [True, False])
def test_labscript_spooler_add_job(
    sign_it: bool, ls_storage_setup_td: Callable
) -> None:
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
        labscript_params=labsript_params,
        sign=sign_it,
    )

    job_id = "Test_ID"
    n_shots = 4
    job_payload = {
        "experiment_0": {
            "instructions": [["test", [0], [1.0]]],
            "num_wires": 1,
            "shots": n_shots,
            "wire_order": "interleaved",
        },
    }

    result_dict, status_msg_dict = test_spooler.add_job(job_payload, job_id)
    assert status_msg_dict.status == "ERROR", "Job should have failed"
    assert result_dict is not None
    # now add the header at the right position by copying
    # the dummy_header.py file into the exp_script_folder
    # and then run the test again

    # Define the source and destination paths
    source_path = "tests/dummy_header.py"
    destination_path = f"{labsript_params.exp_script_folder}/header.py"
    # make sure that the destination folder exists
    os.makedirs(labsript_params.exp_script_folder, exist_ok=True)
    # Copy the file
    shutil.copy(source_path, destination_path)
    assert os.path.exists(destination_path)

    # now also make sure that the folder for the remote experiment exists
    remote_experiments_path = f"{labsript_params.exp_script_folder}/remote_experiments"
    os.makedirs(remote_experiments_path, exist_ok=True)

    # now also make sure that the folder where we are looking for files exists
    file_queue_path = "test/Test_ID/experiment_0"
    os.makedirs(file_queue_path, exist_ok=True)
    assert os.path.exists(file_queue_path)

    # now also a mock files to the folder
    for ii in range(n_shots):
        file_path = f"{file_queue_path}/test_{ii}.py"
        with open(file_path, "w", encoding="UTF-8") as file:
            file.write("test")
    result_dict, status_msg_dict = test_spooler.add_job(job_payload, job_id)
    assert status_msg_dict.status == "DONE", "Job should not have failed"


def test_create_memory_data() -> None:
    """
    Test that it is possible to create the memory data.
    """
    shots_array = [1, 2, 3]
    exp_name = "test"
    n_shots = 3
    exp_dict = create_memory_data(shots_array, exp_name, n_shots)
    assert exp_dict.success is True

    # test with measured wires
    instr = ["test", [0], [1.0]]
    instr_list = [gate_dict_from_list(instr)]
    exp_dict = create_memory_data(shots_array, exp_name, n_shots, instr_list)
    assert exp_dict.success is True

    # test with mixed input
    instr = ["test", [0, "a"], [1.0]]
    with pytest.raises(ValidationError):
        instr_list = [gate_dict_from_list(instr)]
        exp_dict = create_memory_data(shots_array, exp_name, n_shots, instr_list)
