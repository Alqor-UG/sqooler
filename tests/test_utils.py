"""
This is the test tool for the utils module.
"""
import os
import uuid
import shutil
from typing import Iterator, Callable, Literal, Optional
from pydantic import BaseModel, Field

from typing_extensions import Annotated


import pytest

from sqooler.utils import (
    update_backends,
    main,
    run_json_circuit,
    get_init_status,
    get_init_results,
)
from sqooler.schemes import LocalLoginInformation

from sqooler.spoolers import Spooler
from sqooler.storage_providers.local import LocalProvider


local_login = LocalLoginInformation(base_path="utils_storage")
storage_provider = LocalProvider(local_login)


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


test_spooler = Spooler(ins_schema_dict={}, device_config=DummyExperiment, n_wires=2)

backends = {"test": test_spooler}


# pylint: disable=W0613, W0621
@pytest.fixture
def utils_storage_setup_teardown() -> Iterator[None]:
    """
    Make sure that the storage folder is empty before and after the test.
    """
    # setup code here if required one day
    # ...

    yield  # this is where the testing happens

    # teardown code here
    shutil.rmtree("utils_storage", ignore_errors=True)


def test_update_backends(utils_storage_setup_teardown: Callable) -> None:
    """
    Test that it is possible to update the backends.
    """
    update_backends(storage_provider, backends)

    config_path = storage_provider.base_path + "/backends/configs"
    full_json_path = config_path + "/" + "test" + ".json"

    # test that the file is there
    assert os.path.exists(full_json_path)


def test_main(utils_storage_setup_teardown: Callable) -> None:
    """
    Test that it is possible to run the main function.
    """
    backend_name = "test"
    # first we have to upload a dummy job
    queue_path = "jobs/queued/" + backend_name
    job_id = (uuid.uuid4().hex)[:24]
    job_dict = {"job_id": job_id, "job_json_path": "None"}
    job_dict["job_json_path"] = queue_path
    storage_provider.upload(job_dict, queue_path, job_id=job_id)

    # also upload a status
    status_path = "status/" + backend_name
    status_dict = {
        "job_id": job_id,
        "status": "INITIALIZING",
        "detail": "Got your json.",
        "error_message": "None",
    }
    storage_provider.upload(status_dict, status_path, job_id=job_id)

    main(storage_provider, backends, num_iter=1)


def test_run_json_circuit(utils_storage_setup_teardown: Callable) -> None:
    """
    Test that it is possible to create the memory data.
    """
    job_payload = {
        "experiment_0": {
            "instructions": [],
            "num_wires": 2,
            "shots": 4,
            "wire_order": "interleaved",
        },
    }

    job_id = "1"
    with pytest.raises(AssertionError):
        run_json_circuit(job_payload, job_id, test_spooler)


def test_get_init_status(utils_storage_setup_teardown: Callable) -> None:
    """
    Test that we can get the initial status.
    """
    status = get_init_status()
    assert status.status == "INITIALIZING"
    assert status.detail == "Got your json."
    assert status.error_message == "None"
    assert status.job_id == "None"


def test_get_init_results(utils_storage_setup_teardown: Callable) -> None:
    """
    Test that we can get the initial results.
    """
    results = get_init_results()
    assert results.status == "INITIALIZING"
