"""
In this module we test the basic ability to sign payloads and verify the signature.
"""

import base64
import json
from datetime import datetime, timezone

import pytest
from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from icecream import ic

from sqooler.security import (
    JWK,
    JWSDict,
    JWSFlat,
    JWSHeader,
    create_jwk_pair,
    jwk_from_config_str,
    payload_to_base64url,
    public_from_private_jwk,
    sign_payload,
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
    public_key.verify(jws_obj.signature, full_message)

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

    # do we get and error if we try it with a public key input ?
    with pytest.raises(ValueError):
        public_from_private_jwk(reloaded_public)


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

    # test if we can sign a payload with a datetime
    current_time = datetime.now(timezone.utc)
    payload_dt = {"test": "test", "last_queued": current_time}
    sign_payload(payload_dt, private_jwk)

    # test that we raise errors if we try to verify a signature with a private key
    with pytest.raises(ValueError):
        signed_pl.verify_signature(private_jwk)

    # test that we raise erros if we try to sign with a public key
    with pytest.raises(ValueError):
        sign_payload(payload_dt, public_jwk)


def test_jws_serialization() -> None:
    """
    Test the possibility to serialize a jws object
    """
    payload = {"test": "test"}
    private_jwk, _ = create_jwk_pair("test_kid")

    signed_pl = sign_payload(payload, private_jwk)
    signed_pl.model_dump_json()


def test_flat_jws() -> None:
    """
    Test the possibility to serialize a jws object into the flat JWS
    """
    payload = {"test": "test"}
    private_jwk, _ = create_jwk_pair("test_kid")

    signed_pl = sign_payload(payload, private_jwk)

    b64_header_str = signed_pl.header.to_base64url().decode("utf-8")
    b64_payload_str = payload_to_base64url(signed_pl.payload).decode("utf-8")

    # now try to serialize it
    flat_jws = JWSFlat(
        protected=b64_header_str,
        payload=b64_payload_str,
        signature=base64.urlsafe_b64encode(signed_pl.signature),
    )

    assert flat_jws.signature == signed_pl.signature
    assert json.loads(flat_jws.payload) == payload

    # and are we able to dump it into a json ?
    json_jws = flat_jws.model_dump_json()

    # and can we load it back?
    json_dict = json.loads(json_jws)
    loaded_jws = JWSFlat(**json_dict)
    assert loaded_jws.signature == signed_pl.signature
    assert json.loads(loaded_jws.payload) == payload
