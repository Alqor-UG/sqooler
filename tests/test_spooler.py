"""
Here we test the spooler class and its functions.
"""

from typing import Literal, Optional
from pydantic import ValidationError, BaseModel, Field

from typing_extensions import Annotated
import pytest

from sqooler.schemes import (
    Spooler,
    LabscriptSpooler,
    StatusMsgDict,
    gate_dict_from_list,
)

from icecream import ic


class TestInstruction(BaseModel):
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


class TestExperiment(BaseModel):
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


def test_spooler_config() -> None:
    """
    Test that it is possible to get the config of the spooler.
    """
    test_spooler = Spooler(ins_schema_dict={}, device_config=TestExperiment, n_wires=2)

    spooler_config = test_spooler.get_configuration()
    assert spooler_config.num_wires == 2
    assert spooler_config.operational


def test_spooler_operational() -> None:
    """
    Test that it is possible to set the operational status of the spooler.
    """
    test_spooler = Spooler(
        ins_schema_dict={}, device_config=TestExperiment, n_wires=2, operational=False
    )

    spooler_config = test_spooler.get_configuration()
    assert spooler_config.num_wires == 2
    assert not spooler_config.operational


def test_spooler_add_job() -> None:
    """
    Test that it is possible to add a job to the spooler.
    """

    test_spooler = Spooler(
        ins_schema_dict={}, device_config=TestExperiment, n_wires=2, operational=False
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
    assert result_dict is not None


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


def test_spooler_instructions() -> None:
    """
    Test that it is possible to verify the validity of the instructions.
    """
    test_spooler = Spooler(
        ins_schema_dict={"test": TestInstruction},
        device_config=TestExperiment,
        n_wires=2,
        operational=False,
    )

    # test that it works if the instructions are not valid as the key is not known
    inst_list = [["load", [0], [1]]]
    err_code, exp_ok = test_spooler.check_instructions(inst_list)
    assert exp_ok is not True
    assert err_code == "Instruction not allowed."

    # test that it works if the instructions are valid
    inst_list = [["test", [0], [1]]]
    err_code, exp_ok = test_spooler.check_instructions(inst_list)
    assert exp_ok is True


## Test the labscript spooler


def test_labscript_spooler_config() -> None:
    """
    Test that it is possible to get the config of the spooler.
    """
    test_spooler = LabscriptSpooler(
        ins_schema_dict={},
        device_config=TestExperiment,
        remote_client=DummyRemoteClient(),
        n_wires=2,
    )

    spooler_config = test_spooler.get_configuration()
    assert spooler_config.num_wires == 2
    assert spooler_config.operational


def test_labscript_spooler_operational() -> None:
    """
    Test that it is possible to set the operational status of the spooler.
    """
    test_spooler = LabscriptSpooler(
        ins_schema_dict={},
        device_config=TestExperiment,
        remote_client=DummyRemoteClient(),
        n_wires=2,
        operational=False,
    )

    spooler_config = test_spooler.get_configuration()
    assert spooler_config.num_wires == 2
    assert not spooler_config.operational


def test_labscript_spooler_add_job() -> None:
    """
    Test that it is possible to add a job to the spooler.
    """

    test_spooler = LabscriptSpooler(
        ins_schema_dict={"test": TestInstruction},
        device_config=TestExperiment,
        remote_client=DummyRemoteClient(),
        n_wires=2,
        operational=False,
    )
    status_msg_draft = {
        "job_id": "Test_ID",
        "status": "None",
        "detail": "None",
        "error_message": "None",
    }
    ic("Test payload")
    job_payload = {
        "experiment_0": {
            "instructions": [["test", [0], [1.0]]],
            "num_wires": 1,
            "shots": 4,
            "wire_order": "interleaved",
        },
    }
    status_msg_dict = StatusMsgDict(**status_msg_draft)
    result_dict, status_msg_dict = test_spooler.add_job(job_payload, status_msg_dict)
    assert status_msg_dict.status == "ERROR", "Job should have failed"
    ic(status_msg_dict.error_message)
    assert result_dict is not None

    # to make this test useful we need to have code that gets up to the point where
    # the remote_client is called
