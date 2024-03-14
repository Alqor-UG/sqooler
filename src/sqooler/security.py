"""
In this module we define important classes for signing, encryption etc. 
Please be aware that this module has not yet undergone a security audit and is still in an early version.
Any suggestions for improvements will be very welcome."""

import json
import base64
from typing import Literal, Optional

from pydantic import BaseModel, Field
from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric.ed25519 import (
    Ed25519PrivateKey,
    Ed25519PublicKey,
)


class JWSHeader(BaseModel):
    """
    The header of a JWS object
    """

    alg: str = Field(default="EdDSA", description="The algorithm used for signing")
    kid: str = Field(description="The key id of the key used for signing")
    typ: str = Field(default="JWS", description="The type of the signature")
    version: str = Field(
        default="0.1", description="The base64 encoded version of the signature"
    )

    def to_base64url(self) -> bytes:
        """
        Convert the header to a base64url encoded string.

        Returns:
            bytes : The base64url encoded header
        """

        # transform into a json string
        header_json = self.model_dump_json()

        # binary encode the json string
        binary_string = header_json.encode()

        # base64 encode the binary string
        base64_encoded = base64.urlsafe_b64encode(binary_string)
        return base64_encoded


class JWSDict(BaseModel):
    """
    A JSON Web Signature in a dictionary form. We follow the JWS standard as defined in RFC 7515.

    https://datatracker.ietf.org/doc/html/rfc7515
    """

    header: JWSHeader = Field(description="The header of the JWS object")
    payload: dict = Field(description="The payload of the JWS object")
    signature: bytes = Field(description="The signature of the JWS object")

    def verify_signature(self, public_key: Ed25519PublicKey) -> bool:
        """
        Verify the integraty of JWS object.

        Args:
            jws_obj : The JWS object to verify
            public_key: The public key to use for verification

        Returns:
            if the signature can be verified
        """

        signature_decoded = base64.urlsafe_b64decode(self.signature)

        header_base64 = self.header.to_base64url()
        payload_base64 = payload_to_base64url(self.payload)
        full_message = header_base64 + b"." + payload_base64

        try:
            public_key.verify(signature_decoded, full_message)
            return True
        except InvalidSignature:
            return False


def payload_to_base64url(payload: dict) -> bytes:
    """
    Convert an arbitrary payload to a base64url encoded string.

    Args:
        payload : The dictionary to encode

    Returns:
        bytes : The base64url encoded header
    """

    # transform into a json string
    payload_string = json.dumps(payload)

    # binary encode the json string
    binary_string = payload_string.encode()

    # base64 encode the binary string
    base64_encoded = base64.urlsafe_b64encode(binary_string)
    return base64_encoded


def sign_payload(payload: dict, private_key: Ed25519PrivateKey, kid: str) -> JWSDict:
    """
    Convert a payload to a JWS object. We will assumar that

    Args:
        payload : The payload to convert
        private_key: The private key to use for signing
        kid: The key id of the private that you use for signing.

    Returns:
        JWS : The JWS object
    """
    header = JWSHeader(kid=kid)
    header_base64 = header.to_base64url()
    payload_base64 = payload_to_base64url(payload)
    full_message = header_base64 + b"." + payload_base64

    signature = private_key.sign(full_message)
    signature_base64 = base64.urlsafe_b64encode(signature)
    return JWSDict(header=header, payload=payload, signature=signature_base64)


class JWK(BaseModel):
    """
    The JSON Web Key (JWK) for Ed25519 as standardized in

    https://datatracker.ietf.org/doc/html/rfc8037
    """

    x: bytes = Field(
        description="Contain the public key encoded using the base64url encoding"
    )
    key_ops: Literal["sign", "verify"] = Field(
        description="Identifies the operation for which the key is intended to be used"
    )
    kid: str = Field(description="The key id of the key")
    d: Optional[bytes] = Field(
        description="Contains the private key encoded using the base64url encoding."
    )
    kty: Literal["OKP"] = Field(
        default="OKP",
        description="Identifies the cryptographic algorithm family used with the key",
    )
    alg: Literal["EdDSA"] = Field(
        default="EdDSA", description="The algorithm used for signing"
    )
    crv: Literal["Ed25519"] = Field(
        default="Ed25519", description="Identifies the cryptographic curve used"
    )

    def to_config_str(self) -> str:
        """
        Convert the JWK to a string that can be stored in a config file.
        """
        # now it would be nice to have the whole thing as a string
        jwk_string = self.model_dump_json()

        # create a byte string
        jwk_bytes = jwk_string.encode("utf-8")

        # and now we can base64 encode it
        jwk_base64 = base64.urlsafe_b64encode(jwk_bytes)

        # and for storing it in a file we would like to decode it
        jwk_base64_str = jwk_base64.decode("utf-8")
        return jwk_base64_str


def jwk_from_config_str(jwk_base64_str: str) -> JWK:
    """
    Create a JWK from a string that was stored in a config file.

    Args:
        jwk_base64_str : The base64 encoded JWK

    Returns:
        JWK : The JWK object
    """
    jwk_base64 = jwk_base64_str.encode("utf-8")
    jwk_bytes = base64.urlsafe_b64decode(jwk_base64)

    jwk_json_str = jwk_bytes.decode("utf-8")
    jwk_dict = json.loads(jwk_json_str)
    jwk = JWK(**jwk_dict)
    return jwk


def create_key_pair() -> tuple[Ed25519PrivateKey, Ed25519PublicKey]:
    """
    Create a new key pair for signing and verification.

    Returns:
        tuple : A tuple containing the public and private keys
    """

    # create a new key pair
    private_key = Ed25519PrivateKey.generate()
    public_key = private_key.public_key()

    return private_key, public_key
