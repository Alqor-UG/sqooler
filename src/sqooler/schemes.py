"""
The module that contains common logic for schemes, validation etc.
There is no obvious need, why this code should be touch in a new back-end.
"""

from typing import Optional

from pydantic import BaseModel, Field


class ExperimentDict(BaseModel):
    """
    A class that defines the structure of the experiments.
    """

    header: dict = Field(description="Contains centralized information about the job.")
    shots: int = Field(description="number of shots in the experiment.")
    success: bool = Field(description="True if experiment ran successfully.")
    data: dict = Field(description="dictionary of results for the experiment.")


class StatusMsgDict(BaseModel):
    """
    A class that defines the structure of the status messages.
    """

    job_id: str = Field(description="unique execution id from the backend.")
    status: str = Field(description="status of job execution.")
    detail: str = Field(description="detailed status of job execution.")
    error_message: str = Field(description="error message of job execution.")


class ResultDict(BaseModel):
    """
    A class that defines the structure of results. It is closely related to the
    qiskit class qiskit.result.Result.
    """

    backend_name: Optional[str] = Field(
        default=None, description="The name of the backend"
    )
    display_name: str = Field(description="alternate name field for the backend")
    backend_version: str = Field(description="backend version, in the form X.Y.Z.")
    job_id: str = Field(description="unique execution id from the backend.")
    qobj_id: Optional[str] = Field(default=None, description="user-generated Qobj id.")
    success: bool = Field(description="True if complete input qobj executed correctly.")
    status: str = Field(description="status of job execution.")
    header: dict = Field(description="Contains centralized information about the job.")
    results: list[ExperimentDict] = Field(
        description="corresponding results for array of experiments of the input qobj"
    )


class DropboxLoginInformation(BaseModel):
    """
    The login information for the dropbox
    """

    app_key: str
    app_secret: str
    refresh_token: str


class MongodbLoginInformation(BaseModel):
    """
    The login information for MongoDB
    """

    mongodb_username: str
    mongodb_password: str
    mongodb_database_url: str


class LocalLoginInformation(BaseModel):
    """
    The login information for a local storage provider.
    """

    base_path: str = Field(
        description="The base path of the storage provider on your local file system."
    )


class BackendStatusSchemaOut(BaseModel):
    """
    The schema for the status of a backend. Follows the conventions of the
    `qiskit.providers.models.BackendStatus`.
    """

    backend_name: str = Field(description="The name of the backend")
    backend_version: str = Field(
        description="The version of the backend. Of the form X.Y.Z"
    )
    operational: bool = Field(description="True if the backend is operational")
    pending_jobs: int = Field(description="The number of pending jobs on the backend")
    status_msg: str = Field(description="The status message for the backend")


class BackendConfigSchemaIn(BaseModel):
    """
    The schema send in to detail the configuration of the backend.
    This is uploaded to the storage provider.
    """

    description: str = Field(description="A description for the backend")
    version: str = Field(description="The backend version in the form X.Y.Z")
    display_name: Optional[str] = Field(
        description=" Alternate name field for the backend"
    )
    cold_atom_type: str = Field(
        description="The type of cold atom system that is simulated. Non standard qiskit field."
    )
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
    wire_order: str = Field(
        description="The wire order of the backend. Either linear or interleaved."
    )
    num_species: int = Field(description="The number of species in the system.")
    operational: bool = Field(description="True if the backend is operational")
    pending_jobs: Optional[int] = Field(
        default=None, description="The number of pending jobs on the backend"
    )
    status_msg: Optional[str] = Field(
        default=None, description="The status message for the backend"
    )


class BackendConfigSchemaOut(BaseModel):
    """
    The schema send out to detail the configuration of the backend. We follow the
    conventions of the qiskit configuration dictionary here.

    Will becomes compatible with qiskit.providers.models.BackendConfiguration
    """

    description: str = Field(description="A description for the backend")
    display_name: str = Field(description=" Alternate name field for the backend")
    conditional: bool = Field(
        default=False, description="True if the backend supports conditional operations"
    )
    coupling_map: str = Field(
        default="linear", description="The coupling map for the device"
    )
    dynamic_reprate_enabled: bool = Field(
        default=False,
        description="whether delay between programs can be set dynamically ",
    )
    local: bool = Field(
        default=False, description="True if the backend is local or False if remote"
    )
    memory: bool = Field(default=False, description="True if backend supports memory")
    open_pulse: bool = Field(default=False, description="True if backend is OpenPulse")
    backend_version: str = Field(description="The backend version in the form X.Y.Z")
    n_qubits: int = Field(description="The number of qubits / wires for the backend")
    backend_name: str = Field(description="The backend name")
    basis_gates: list[str] = Field(
        description="The list of strings for the basis gates of the backends"
    )
    max_experiments: int = Field(
        description="The maximum number of experiments per job"
    )
    max_shots: int = Field(
        description="The maximum number of shots allowed on the backend"
    )
    simulator: bool = Field(description="True if the backend is a simulator")
    gates: list = Field(
        description="The list of GateConfig objects for the basis gates of the backend"
    )
    supported_instructions: list[str] = Field(
        description="Instructions supported by the backend."
    )
    cold_atom_type: str = Field(
        description="The type of cold atom system that is simulated. Non standard qiskit field."
    )
    wire_order: str = Field(
        description=(
            "The wire order of the backend. Either linear or interleaved."
            " Non standard qiskit field."
        )
    )
    num_species: int = Field(
        description="The number of species in the system. Non standard qiskit field."
    )
    url: Optional[str] = Field(default=None, description="The url of the backend")


class GateDict(BaseModel):
    """
    The most basic class for a gate as it is communicated in
    the json API.
    """

    name: str = Field(description="The name of the gate")
    wires: list[int] = Field(description="The wires on which the gate acts")
    params: list[float] = Field(description="The parameters of the gate")


class GateInstruction(BaseModel):
    """
    The basic class for all the gate intructions of a backend.
    Any gate has to have the following attributes.
    """

    name: str
    parameters: str
    description: str
    coupling_map: list
    qasm_def: str = "{}"
    is_gate: bool = True

    @classmethod
    def config_dict(cls) -> dict:
        """
        Give back the properties of the instruction such as needed for the server.
        """
        return {
            "coupling_map": cls.model_fields["coupling_map"].default,
            "description": cls.model_fields["description"].default,
            "name": cls.model_fields["name"].default,
            "parameters": [cls.model_fields["parameters"].default],
            "qasm_def": cls.model_fields["qasm_def"].default,
        }


class LabscriptParams(BaseModel):
    """
    A class that defines the parameters for the labscript folders.
    """

    exp_script_folder: str = Field(
        description="The relative path to the experimental scripts."
    )
    t_wait: float = Field(description="The time to wait between checks.")
