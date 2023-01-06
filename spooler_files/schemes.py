"""
The module that contains common logic for schemes, validation etc.
There is no obvious need, why this code should be touch in a new back-end.
"""

from typing import Tuple, TypedDict

from jsonschema import validate
from jsonschema.exceptions import ValidationError


class ExperimentDict(TypedDict):
    """
    A class that defines the structure of the experiments.
    """

    header: dict
    shots: int
    success: bool
    data: dict


def check_with_schema(obj: dict, schm: dict) -> Tuple[str, bool]:
    """
    Caller for the validate function of jsonschema

    Args:
        obj (dict): the object that should be checked.
        schm (dict): the schema that defines the object properties.

    Returns:
        boolean flag tellings if dictionary matches schema syntax.

    """
    # Fix this pylint issue whenever you have time, but be careful !
    # pylint: disable=W0703
    try:
        validate(instance=obj, schema=schm)
        return "", True
    except ValidationError as err:
        return str(err), False
