"""
In this module we test the basic ability to sign payloads and verify the signature.
"""

import base64
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.exceptions import InvalidSignature

import pytest

from sqooler.security import (
    JWSHeader,
    JWSDict,
    JWK,
    payload_to_base64url,
    sign_payload,
    jwk_from_config_str,
    create_jwk_pair,
    public_from_private_jwk,
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

    # test with poor payload

    poor_payload = {"test": "test1"}
    poor_payload_base64 = payload_to_base64url(poor_payload)
    poor_message = header_base64 + b"." + poor_payload_base64
    with pytest.raises(InvalidSignature):
        public_key.verify(signature, poor_message)


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
    assert reloaded_jwk.x == private_jwk.x
    assert reloaded_jwk.kid == private_jwk.kid

    # can we also get the public key from the private key?
    reloaded_public = public_from_private_jwk(reloaded_jwk)
    assert reloaded_public.d is None
    assert reloaded_public.x == public_base64


def test_sign_and_verify_jws() -> None:
    """
    Test the ability to sign and verify a payload with a JWK
    """
    payload = {"test": "test"}
    private_jwk, public_jwk = create_jwk_pair("test_kid")

    signed_pl = sign_payload(payload, private_jwk)

    # and now we can verify the signature
    assert signed_pl.verify_signature(public_jwk)

    _, wrong_public_jwk = create_jwk_pair("test_kid")

    assert not signed_pl.verify_signature(wrong_public_jwk)
    assert signed_pl.header.alg == "EdDSA"  # pylint: disable=no-member

    # also test with the wrong payload
    signed_pl.payload = {"test": "test1"}

    assert not signed_pl.verify_signature(public_jwk)


def test_jws_serialization() -> None:
    """
    Test the possibility to serialize a jws object
    """
    payload = {"test": "test"}
    private_jwk, _ = create_jwk_pair("test_kid")

    signed_pl = sign_payload(payload, private_jwk)
    signed_pl.model_dump_json()
