"""
In this module we test the basic ability to sign payloads and verify the signature.
"""

import base64
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.exceptions import InvalidSignature

import pytest

from sqooler.security import JWSHeader, JWSDict, payload_to_base64url, sign_payload

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
