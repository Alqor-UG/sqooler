"""
In this module we put together tests that are necessary for a smooth migration between versions.
"""

import shutil
import uuid
from datetime import datetime
from typing import Optional, Tuple

from decouple import config
from icecream import ic
from pydantic import BaseModel, Field

from sqooler.schemes import (
    ColdAtomStr,
    DisplayNameStr,
    LocalLoginInformation,
    WireOrderStr,
)
from sqooler.security import create_jwk_pair, sign_payload
from sqooler.storage_providers.local import LocalProviderExtended


class BackendConfigSchemaOld(BaseModel, validate_assignment=True):
    """
    The previous backend schema as it was in v0.6 .
    """

    description: str = Field(description="A description for the backend")
    version: str = Field(description="The backend version in the form X.Y.Z")
    display_name: Optional[DisplayNameStr]
    cold_atom_type: ColdAtomStr
    gates: list = Field(
        description="The list of GateConfig objects for the basis gates of the backend"
    )
    max_experiments: int = Field(
        description="The maximum number of experiments per job"
    )
    max_shots: int = Field(
        description="The maximum number of shots allowed on the backend"
    )
    simulator: bool = Field(description="True if the backend is a simulator")
    supported_instructions: list[str] = Field(
        description="Instructions supported by the backend."
    )
    num_wires: int = Field(description="The number of qubits / wires for the backend")
    wire_order: WireOrderStr
    num_species: int = Field(description="The number of species in the system.")
    operational: bool = Field(description="True if the backend is operational")
    pending_jobs: Optional[int] = Field(
        default=None, description="The number of pending jobs on the backend"
    )
    status_msg: Optional[str] = Field(
        default=None, description="The status message for the backend"
    )
    last_queue_check: Optional[datetime] = Field(
        default=None, description="The last time the queue was checked."
    )
    sign: bool = Field(
        default=False,
        description="True if the results are signed by the backend provider.",
    )


def get_old_dummy_config(sign: bool = True) -> Tuple[str, BackendConfigSchemaOld]:
    """
    Generate the dummy config of the fermion type.

    Args:
        sign: Whether to sign the files.
    Returns:
        The backend name and the backend config input.
    """

    dummy_id = uuid.uuid4().hex[:5]
    backend_name = f"dummy{dummy_id}"

    dummy_dict: dict = {}
    dummy_dict["gates"] = []
    dummy_dict["display_name"] = backend_name
    dummy_dict["num_wires"] = 3
    dummy_dict["version"] = "0.0.1"
    dummy_dict["description"] = "This is a dummy backend."
    dummy_dict["cold_atom_type"] = "fermion"
    dummy_dict["max_experiments"] = 1
    dummy_dict["max_shots"] = 1
    dummy_dict["simulator"] = True
    dummy_dict["supported_instructions"] = []
    dummy_dict["wire_order"] = "interleaved"
    dummy_dict["num_species"] = 1
    dummy_dict["operational"] = True
    dummy_dict["sign"] = sign

    backend_info = BackendConfigSchemaOld(**dummy_dict)
    return backend_name, backend_info


def test_generate_sign_old_config() -> None:
    """
    Test that we can generate an old configuration and very it anyways.
    """
    login_dict = LocalLoginInformation(base_path=config("BASE_PATH"))
    storage_provider = LocalProviderExtended(login_dict=login_dict, name="test")
    display_name, config_info = get_old_dummy_config(sign=True)
    private_jwk, _ = create_jwk_pair(display_name)

    signed_config = sign_payload(config_info.model_dump(), private_jwk)
    upload_dict = signed_config.model_dump()
    storage_provider.upload(
        content_dict=upload_dict,
        storage_path="backends/configs",
        job_id=display_name,
    )

    # now see what happens if we try to update it
    # first get the config
    config_info = storage_provider.get_config(display_name)
    ic(config_info)
    assert config_info.sign is True
    # now update it
    config_info.version = "0.0.2"
    storage_provider.update_config(config_info, display_name, private_jwk=private_jwk)

    # clean up our mess
    storage_provider._delete_config(display_name)

    shutil.rmtree("storage")
