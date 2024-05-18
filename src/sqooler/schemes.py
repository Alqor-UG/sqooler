"""
The module that contains common logic for schemes, validation etc.
There is no obvious need, why this code should be touch in a new back-end.
"""

from datetime import datetime
from typing import Annotated, Literal, Optional

from pydantic import BaseModel, Field, field_validator

# the strings that are allowed for the status
StatusStr = Annotated[
    Literal["INITIALIZING", "QUEUED", "DONE", "ERROR"],
    Field(description="status of job execution."),
]

# the strings that are allowed for the cold_atom_type
ColdAtomStr = Annotated[
    Literal["fermion", "boson", "spin", "mixed"],
    Field(
        description="The type of cold atom system that is simulated. Non standard qiskit field."
    ),
]

# the strings that are allowed for the display_name
DisplayNameStr = Annotated[
    str,
    Field(
        default="",
        description="The short name for the backend",
        pattern=r"^[a-z0-9]*$",
    ),
]

# the strings that are allowed for the backend_name
BackendNameStr = Annotated[
    str,
    Field(
        description="The full name of the backend including the storage provider.",
        pattern=r"^$|^[a-z0-9]+_[a-z0-9]+_[a-z0-9]+$",
    ),
]

# the strings that are allowed for the wire_order
WireOrderStr = Annotated[
    Literal["sequential", "interleaved"],
    Field(
        description="The wire order of the backend. Either sequential or interleaved."
        " Non standard qiskit field."
    ),
]

# a string that is allowed for paths without leading and trailing slashes
PathStr = Annotated[
    str,
    Field(
        description="The path to the file without leading and trailing slashes.",
        pattern=r"^[a-zA-Z0-9_\-\.]+$",
    ),
]


class StatusMsgDict(BaseModel):
    """
    A class that defines the structure of the status messages.
    """

    job_id: str = Field(description="unique execution id from the backend.")
    status: StatusStr
    detail: str = Field(description="detailed status of job execution.")
    error_message: str = Field(description="error message of job execution.")


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

    backend_name: BackendNameStr
    backend_version: str = Field(
        description="The version of the backend. Of the form X.Y.Z"
    )
    operational: bool = Field(description="True if the backend is operational")
    pending_jobs: int = Field(description="The number of pending jobs on the backend")
    status_msg: str = Field(description="The status message for the backend")


class NextJobSchema(BaseModel):
    """
    The schema for the next job to be executed.
    """

    job_id: str = Field(description="unique execution id from the backend.")
    job_json_path: str = Field(description="The path to the job json file.")


class BackendConfigSchemaIn(BaseModel, validate_assignment=True):
    """
    The schema send in to detail the configuration of the backend.
    This is uploaded to the storage provider.
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
    kid: Optional[str] = Field(
        default=None,
        description="The identifier for the public and private key of the backend.",
    )
    operational: Optional[bool] = Field(
        default=True, description="True if the backend is operational", deprecated=True
    )


class BackendConfigSchemaOld(BaseModel, validate_assignment=True):
    """
    The schema send in to detail the configuration of the backend.
    This is uploaded to the storage provider.
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
    kid: Optional[str] = Field(
        default=None,
        description="The identifier for the public and private key of the backend.",
    )
    operational: Optional[bool] = Field(
        default=True, description="True if the backend is operational", deprecated=True
    )


class BackendConfigSchemaOut(BaseModel, validate_assignment=True):
    """
    The schema send out to detail the configuration of the backend. We follow the
    conventions of the qiskit configuration dictionary here.

    Will becomes compatible with qiskit.providers.models.BackendConfiguration
    """

    description: str = Field(description="A description for the backend")
    display_name: DisplayNameStr
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
    backend_name: BackendNameStr
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
    cold_atom_type: ColdAtomStr
    wire_order: WireOrderStr
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


class ExperimentalInputDict(BaseModel):
    """
    The input for the experimental job.
    """

    instructions: list[GateDict] = Field(description="The instructions for the job")
    num_wires: int = Field(description="The number of wires for the job")
    shots: int = Field(description="The number of shots for the job")
    wire_order: WireOrderStr
    seed: Optional[int] = Field(
        default=None,
        description="The seed for the random number generator if one might be used",
    )


class DataDict(BaseModel):
    """
    A class that defines the structure of the data within the ExperimentDict.
    """

    memory: list[str] = Field(description="A list of results safed as string.")
    instructions: Optional[list[GateDict]] = Field(
        default=None, description="The indices of the wires that were measured."
    )


class ExperimentDict(BaseModel):
    """
    A class that defines the structure of the experiments. Strongly inspired by the
    qiskit class qiskit.result.ExperimentData.
    """

    header: dict = Field(description="Contains centralized information about the job.")
    shots: int = Field(description="number of shots in the experiment.")
    success: bool = Field(description="True if experiment ran successfully.")
    data: DataDict = Field(description="dictionary of results for the experiment.")


class ResultDict(BaseModel):
    """
    A class that defines the structure of results. It is closely related to the
    qiskit class qiskit.result.Result.
    """

    backend_name: BackendNameStr | None = None
    display_name: DisplayNameStr
    backend_version: str = Field(description="backend version, in the form X.Y.Z.")
    job_id: str = Field(description="unique execution id from the backend.")
    qobj_id: Optional[str] = Field(default=None, description="user-generated Qobj id.")
    success: bool = Field(
        description="True if complete input qobj executed correctly.", default=True
    )
    status: StatusStr
    header: dict = Field(
        description="Contains centralized information about the job.", default={}
    )
    results: list[ExperimentDict] = Field(
        description="corresponding results for array of experiments of the input qobj",
        default=[],
    )


class GateInstruction(BaseModel):
    """
    The basic class for all the gate intructions of a backend.
    Any gate has to have the following attributes.
    """

    name: str
    parameters: str
    wires: list[int] = Field(description="The wires on which the gate acts")
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

    @field_validator("wires")
    @classmethod
    def valid_coupling(cls, wires: list) -> list:
        """
        Validate that the wires are within the coupling map.

        Args:
            wires: the wires of the gate

        Returns:
            the wires if they are valid

        Raises:
            ValueError: if the wires are not within the coupling map
        """
        if not wires in cls.model_fields["coupling_map"].default:
            raise ValueError("The combination of wires is not in the coupling map.")
        return wires


class LabscriptParams(BaseModel):
    """
    A class that defines the parameters for the labscript folders.
    """

    exp_script_folder: str = Field(
        description="The relative path to the experimental scripts."
    )
    t_wait: float = Field(description="The time to wait between checks.")


def get_init_status() -> StatusMsgDict:
    """
    A support function that returns the status message for an initializing job.

    Returns:
        the status message
    """
    return StatusMsgDict(
        job_id="None",
        status="INITIALIZING",
        detail="Got your json.",
        error_message="None",
    )


def get_init_results() -> ResultDict:
    """
    A support function that returns the result dict for an initializing job.

    Returns:
        the result dict
    """
    return ResultDict(
        display_name="",
        backend_version="",
        job_id="",
        qobj_id=None,
        success=True,
        status="INITIALIZING",
    )
