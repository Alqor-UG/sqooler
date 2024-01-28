"""
This is the test schemes module.
"""
from sqooler.schemes import (
    get_init_status,
    get_init_results,
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
