"""
This is the test schemes module.
"""

import pytest
from pydantic import ValidationError

from sqooler.schemes import (
    BackendConfigSchemaIn,
    ResultDict,
    get_init_results,
    get_init_status,
)


def test_backend_name() -> None:
    """
    Test that the backend name is correct.
    """
    # test that the db name is all lowercase
    result_dict = get_init_results()
    result_dict.display_name = "test"
    assert result_dict.display_name == "test"

    # test what happens if the name contains contains underscores
    with pytest.raises(ValidationError):
        ResultDict(
            display_name="Whatever_is_wrong",
            backend_version="1.0.0",
            job_id="1",
            status="INITIALIZING",
        )
    # test what happens if the name contains contains underscores
    with pytest.raises(ValidationError):
        ResultDict(
            display_name="Whatever%/iswrong",
            backend_version="1.0.0",
            job_id="1",
            status="INITIALIZING",
        )


def test_config_in_out() -> None:
    """
    Test that the backend name is correct.
    """
    # test what happens if the name contains contains underscores

    BackendConfigSchemaIn(
        description="Whatever",
        version="1.0.0",
        display_name="nicename",
        cold_atom_type="fermion",
        gates=[],
        max_experiments=1,
        max_shots=1,
        simulator=True,
        supported_instructions=[],
        num_wires=1,
        wire_order="interleaved",
        num_species=1,
        pending_jobs=1,
        status_msg="test",
    )

    with pytest.raises(ValidationError):
        BackendConfigSchemaIn(
            description="Whatever",
            version="1.0.0",
            display_name="nicename_23&",
            cold_atom_type="fermion",
            gates=[],
            max_experiments=1,
            max_shots=1,
            simulator=True,
            supported_instructions=[],
            num_wires=1,
            wire_order="interleaved",
            num_species=1,
            pending_jobs=1,
            status_msg="test",
        )

    with pytest.raises(ValidationError):
        BackendConfigSchemaIn(
            description="Whatever",
            version="1.0.0",
            display_name="nice_name",
            cold_atom_type="fermion",
            gates=[],
            max_experiments=1,
            max_shots=1,
            simulator=True,
            supported_instructions=[],
            num_wires=1,
            wire_order="interleaved",
            num_species=1,
            pending_jobs=1,
            status_msg="test",
        )

    # test that we can append a public key
    backend_info = BackendConfigSchemaIn(
        description="Whatever",
        version="1.0.0",
        display_name="nicename",
        cold_atom_type="fermion",
        gates=[],
        max_experiments=1,
        max_shots=1,
        simulator=True,
        supported_instructions=[],
        num_wires=1,
        wire_order="interleaved",
        num_species=1,
        pending_jobs=1,
        status_msg="test",
        sign=True,
    )

    # the following is important for compatibility with the old version
    with pytest.warns(DeprecationWarning):
        assert backend_info.operational is True

    # now test the model dump
    backend_dict = backend_info.model_dump()
    assert backend_dict["operational"] is True


def test_get_init_status() -> None:
    """
    Test that we can get the initial status.
    """
    status = get_init_status()
    assert status.status == "INITIALIZING"
    assert status.detail == "Got your json."
    assert status.error_message == "None"
    assert status.job_id == "None"


def test_get_init_results() -> None:
    """
    Test that we can get the initial results.
    """
    results = get_init_results()
    assert results.status == "INITIALIZING"
