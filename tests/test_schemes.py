"""
This is the test schemes module.
"""

import pytest
from pydantic import ValidationError
from sqooler.schemes import (
    ResultDict,
    get_init_status,
    get_init_results,
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
