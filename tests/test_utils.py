"""
This is the test tool for the utils module.
"""

import logging
import os
import shutil
import time
import uuid
from typing import Callable, Iterator, Literal, Optional

import pytest
from decouple import config
from pydantic import BaseModel, Field, ValidationError
from pytest import LogCaptureFixture
from typing_extensions import Annotated

from sqooler.schemes import LocalLoginInformation
from sqooler.security import jwk_from_config_str
from sqooler.spoolers import Spooler
from sqooler.storage_providers.local import LocalProvider
from sqooler.utils import get_dummy_config, main, run_json_circuit, update_backends

from .sqooler_test_utils import DummyFullInstruction, dummy_gen_circuit

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


test_spooler = Spooler(
    ins_schema_dict={}, device_config=DummyExperiment, n_wires=2, sign=True
)

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


def test_update_backends(
    caplog: LogCaptureFixture,
    utils_storage_setup_teardown: Callable,
) -> None:
    """
    Test that it is possible to update the backends.
    """
    test_spooler = Spooler(
        ins_schema_dict={}, device_config=DummyExperiment, n_wires=2, sign=True
    )
    backends = {"test": test_spooler}

    # test that it fails with poor names
    # somehow the caplog has some typing issues.
    caplog.set_level(logging.INFO)
    backends_poor = {"test_test_test": test_spooler}
    with pytest.raises(ValidationError):
        update_backends(storage_provider, backends_poor)

    # test that it works with good names
    update_backends(storage_provider, backends)
    config_path = storage_provider.base_path + "/backends/configs"
    full_json_path = config_path + "/" + "test" + ".json"

    # test that the file is there
    assert os.path.exists(full_json_path)

    # test that the keys are there too
    public_jwk = storage_provider.get_public_key("test")
    assert public_jwk.kid == "test_key"

    # assert that the log is there
    # somehow the caplog has some typing issues.
    assert "Uploading it as a new one." in caplog.text

    # test that we can also update it
    update_backends(storage_provider, backends)
    assert "Updated the config for " in caplog.text

    # test with another backend
    sign_it = True
    test_spooler = Spooler(
        ins_schema_dict={"test": DummyFullInstruction},
        device_config=DummyExperiment,
        n_wires=2,
        sign=sign_it,
    )

    test_spooler.gen_circuit = dummy_gen_circuit

    # add it to the backends
    dummy_id = uuid.uuid4().hex[:5]
    backend_name = f"dummy{dummy_id}"
    backends = {backend_name: test_spooler}
    update_backends(storage_provider, backends)


@pytest.mark.parametrize("sign_it", [True, False])
def test_main(
    sign_it: bool, caplog: LogCaptureFixture, utils_storage_setup_teardown: Callable
) -> None:
    """
    Test that it is possible to run the main function.
    """
    backend_name = "test"

    test_spooler = Spooler(
        ins_schema_dict={}, device_config=DummyExperiment, n_wires=2, sign=sign_it
    )

    backends = {backend_name: test_spooler}

    caplog.set_level(logging.INFO)
    # upload the backend
    update_backends(storage_provider, backends)

    # what happens with no jobs?

    main(storage_provider, backends, num_iter=1)

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

    # test if we can get the result
    result_dict = storage_provider.get_result(backend_name, "test", job_id)
    assert result_dict.job_id == job_id

    assert "Looking for jobs" in caplog.text


@pytest.mark.parametrize("sign_it", [True, False])
def test_main_delay(
    sign_it: bool, caplog: LogCaptureFixture, utils_storage_setup_teardown: Callable
) -> None:
    """
    Test that it is change the delay in the main function.
    """
    backend_name = "test"

    test_spooler = Spooler(
        ins_schema_dict={}, device_config=DummyExperiment, n_wires=2, sign=sign_it
    )

    backends = {backend_name: test_spooler}

    caplog.set_level(logging.INFO)
    # upload the backend
    update_backends(storage_provider, backends)

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

    # time the duration of the main function
    start_time = time.time()
    main(storage_provider, backends, num_iter=3)
    end_time = time.time()

    duration = end_time - start_time
    assert 0.8 > duration > 0.4

    # and now also look if we change the waiting time
    os.environ["T_WAIT_MAIN"] = "0.4"
    start_time = time.time()
    main(storage_provider, backends, num_iter=3)
    end_time = time.time()

    duration = end_time - start_time
    assert 1.5 > duration > 0.9

    # going back to the default value
    os.environ["T_WAIT_MAIN"] = "0.2"


@pytest.mark.parametrize("sign_it", [True, False])
def test_main_with_instructions(
    sign_it: bool, caplog: LogCaptureFixture, utils_storage_setup_teardown: Callable
) -> None:
    """
    Test that it is possible to run the main function also with appropiate spooler.
    """
    caplog.set_level(logging.INFO)
    # first prepare the spooler
    test_spooler = Spooler(
        ins_schema_dict={"test": DummyFullInstruction},
        device_config=DummyExperiment,
        n_wires=2,
        sign=sign_it,
    )
    test_spooler.gen_circuit = dummy_gen_circuit

    # add it to the backends
    dummy_id = uuid.uuid4().hex[:5]
    backend_name = f"dummy{dummy_id}"

    backends = {backend_name: test_spooler}
    update_backends(storage_provider, backends)

    # now upload a job
    username = config("TEST_USERNAME")
    job_payload = {
        "experiment_0": {
            "instructions": [["test", [0, 1, 2, 3, 4], [1, 2, 3]]],
            "num_wires": 2,
            "shots": 4,
            "wire_order": "interleaved",
        },
    }

    job_id = storage_provider.upload_job(
        job_dict=job_payload, display_name=backend_name, username=username
    )
    # now also test that we can upload the status
    private_jwk = jwk_from_config_str(config("PRIVATE_JWK_STR"))
    storage_provider.upload_status(
        display_name=backend_name,
        username=username,
        job_id=job_id,
        private_jwk=private_jwk,
    )

    main(storage_provider, backends, num_iter=3)

    # test if we can get the result
    result_dict = storage_provider.get_result(backend_name, "test", job_id)
    assert result_dict.status == "INITIALIZING"


@pytest.mark.parametrize("sign_it", [True, False])
def test_main_without_status(
    sign_it: bool, caplog: LogCaptureFixture, utils_storage_setup_teardown: Callable
) -> None:
    """
    Test that the main function handles missing status dict gracefully without failing.
    """
    caplog.set_level(logging.INFO)
    # first prepare the spooler
    test_spooler = Spooler(
        ins_schema_dict={"test": DummyFullInstruction},
        device_config=DummyExperiment,
        n_wires=2,
        sign=sign_it,
    )
    test_spooler.gen_circuit = dummy_gen_circuit

    # add it to the backends
    dummy_id = uuid.uuid4().hex[:5]
    backend_name = f"dummy{dummy_id}"

    backends = {backend_name: test_spooler}
    update_backends(storage_provider, backends)

    # now upload a job
    username = config("TEST_USERNAME")
    job_payload = {
        "experiment_0": {
            "instructions": [["test", [0, 1, 2, 3, 4], [1, 2, 3]]],
            "num_wires": 2,
            "shots": 4,
            "wire_order": "interleaved",
        },
    }

    job_id = storage_provider.upload_job(
        job_dict=job_payload, display_name=backend_name, username=username
    )

    main(storage_provider, backends, num_iter=3)

    # clean up our mess
    storage_provider._delete_status(backend_name, "", job_id)
    storage_provider._delete_config(backend_name)


@pytest.mark.parametrize("sign_it", [True, False])
def test_main_without_jwk(
    sign_it: bool, caplog: LogCaptureFixture, utils_storage_setup_teardown: Callable
) -> None:
    """
    Test what happens if the private_jwk is not set.
    """

    old_private_jwk = os.environ.get("PRIVATE_JWK_STR")

    if old_private_jwk is None:
        raise ValueError("No private key set.")

    os.environ["PRIVATE_JWK_STR"] = ""

    # first prepare the spooler
    test_spooler = Spooler(
        ins_schema_dict={"test": DummyFullInstruction},
        device_config=DummyExperiment,
        n_wires=2,
        sign=sign_it,
    )
    test_spooler.gen_circuit = dummy_gen_circuit

    # add it to the backends
    dummy_id = uuid.uuid4().hex[:5]
    backend_name = f"dummy{dummy_id}"

    backends = {backend_name: test_spooler}

    if sign_it:
        with pytest.raises(ValueError):
            update_backends(storage_provider, backends)
    else:
        update_backends(storage_provider, backends)

    # now upload a job
    username = config("TEST_USERNAME")
    job_payload = {
        "experiment_0": {
            "instructions": [["test", [0, 1, 2, 3, 4], [1, 2, 3]]],
            "num_wires": 2,
            "shots": 4,
            "wire_order": "interleaved",
        },
    }

    job_id = storage_provider.upload_job(
        job_dict=job_payload, display_name=backend_name, username=username
    )
    # now also test that we can upload the status
    if sign_it:
        with pytest.raises(FileNotFoundError):
            storage_provider.upload_status(
                display_name=backend_name,
                username=username,
                job_id=job_id,
            )
    else:
        storage_provider.upload_status(
            display_name=backend_name,
            username=username,
            job_id=job_id,
        )

    if sign_it:
        with pytest.raises(ValueError):
            main(storage_provider, backends, num_iter=3)
    else:
        main(storage_provider, backends, num_iter=3)

    # change back to the old value
    os.environ["PRIVATE_JWK_STR"] = old_private_jwk


def test_run_json_circuit(
    caplog: LogCaptureFixture, utils_storage_setup_teardown: Callable
) -> None:
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
    assert "Failed json sanity check." in caplog.text


@pytest.mark.parametrize("sign_it", [True, False])
def test_generate_dummy_config(sign_it: bool) -> None:
    """
    Test that it is possible to generate a dummy config.
    """
    display_name, dummy_config = get_dummy_config(sign_it)
    assert "dummy" in dummy_config.display_name

    assert dummy_config.display_name == display_name
    assert dummy_config.sign == sign_it
    assert dummy_config.num_wires == 3
    assert dummy_config.version == "0.0.1"
    assert dummy_config.description == "This is a dummy backend."
    assert dummy_config.cold_atom_type == "fermion"
    assert dummy_config.max_experiments == 1
    assert dummy_config.max_shots == 1
    assert dummy_config.simulator is True
    assert dummy_config.wire_order == "interleaved"
    assert dummy_config.num_species == 1
