"""
This is the test tool for the utils module.
"""
import os
import uuid
import shutil
from typing import Iterator, Callable

import pytest

from sqooler.utils import update_backends, main
from sqooler.schemes import LocalLoginInformation, Spooler
from sqooler.storage_providers import LocalProvider


local_login = LocalLoginInformation(base_path="utils_storage")
storage_provider = LocalProvider(local_login)

test_spooler = Spooler(ins_schema_dict={}, n_wires=2)

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
