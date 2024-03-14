"""
In this module we test the basic ability to sign payloads and verify the signature.
"""

import base64
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.exceptions import InvalidSignature

import json
import pytest

from sqooler.security import (
    JWSHeader,
    JWSDict,
    JWK,
    payload_to_base64url,
    sign_payload,
    jwk_from_config_str,
)

private_key = Ed25519PrivateKey.generate()
public_key = private_key.public_key()


def test_sign_payload() -> None:
    """
    Test the ability to sign a payload
    """
    payload = {"test": "test"}

    header = JWSHeader(kid="test")
    header_base64 = header.to_base64url()
    payload_base64 = payload_to_base64url(payload)
    full_message = header_base64 + b"." + payload_base64

    signature = private_key.sign(full_message)
    signature_base64 = base64.urlsafe_b64encode(signature)
    jws_obj = JWSDict(header=header, payload=payload, signature=signature_base64)

    # and now we can verify the signature
    public_key.verify(signature, full_message)

    # now also test that it fails with the wrong message
    wrong_message = b"wrong message"
    with pytest.raises(InvalidSignature):
        public_key.verify(signature, wrong_message)

    # now test with the signature from the jws object
    signature_from_jws = base64.urlsafe_b64decode(jws_obj.signature)
    public_key.verify(signature_from_jws, full_message)


def test_sign_and_verify_jws() -> None:
    """
    Test the ability to sign a payload and then verify the signature
    """
    payload = {"test": "test"}
    signed_pl = sign_payload(payload, private_key, "test_key")

    # and now we can verify the signature
    assert signed_pl.verify_signature(public_key)

    wrong_private_key = Ed25519PrivateKey.generate()
    wrong_public_key = wrong_private_key.public_key()
    assert not signed_pl.verify_signature(wrong_public_key)
    assert signed_pl.header.alg == "EdDSA"


def test_jwk() -> None:
    """
    Test the ability to create, dump and load a JWK
    """
    private_base64 = base64.urlsafe_b64encode(private_key.private_bytes_raw())
    public_base64 = base64.urlsafe_b64encode(public_key.public_bytes_raw())
    private_jwk = JWK(
        key_ops="sign", kid="testing_key", d=private_base64, x=public_base64
    )
    assert private_jwk.key_ops == "sign"

    # now test that we can dump it to a config string
    private_jwk_base64_str = private_jwk.to_config_str()

    # now test that we can reload it
    reloaded_jwk = jwk_from_config_str(private_jwk_base64_str)
    print(reloaded_jwk)
    assert reloaded_jwk.x == private_jwk.x
    assert reloaded_jwk.kid == private_jwk.kid
