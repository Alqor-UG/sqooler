---
comments: true
---

# Security and signing

In this section we will discuss some of the cryptographic work that we started and how we can sign our results. All of the code in this regard can be found in the `security` module.  For the moment, we have decided to only sign results and not encrypt them. This allows everyone to establish the authenticity of the results, but does not put the burden of always keeping the keys around on the owners of the data. For simplicity, we have further focused on the asymmetric signing with [ED25519](https://cryptography.io/en/latest/hazmat/primitives/asymmetric/ed25519/). 

## Setting up the key

We have decided to work with the widely used crypotgraphic python library [cryptography](https://cryptography.io/en/latest/). To use it, we first need to create and store a private key. This is best done This is done by running the following code in the terminal:

```python

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

# to save the private key
from cryptography.hazmat.primitives.serialization import (
    Encoding,
    PrivateFormat,
    NoEncryption,
)

private_key = Ed25519PrivateKey.generate()
private_key_file_name = "private_key_test.pem"
private_bytes = private_key.private_bytes(
    encoding=Encoding.PEM, format=PrivateFormat.PKCS8, encryption_algorithm=NoEncryption()
)

with open(private_key_file_name, "wb") as pem_file:
    pem_file.write(private_bytes)
```

This will create a private key and store it in a file called `private_key_test.pem`. A second option to store the private key is to have it directly printed out as a b64 encoded string. This can be done by running the following code:

```python
import base64

private_key = Ed25519PrivateKey.generate()
private_bytes = private_key.private_bytes_raw()

private_b64 = base64.urlsafe_b64encode(private_bytes).decode("utf-8")

print(private_b64)
```
You might then safe the output to the `PRIVATE_RESULT_KEY`in your `.env` file.


!!! warning
    The private key should be kept secret and should not be shared with anyone. Never ever ever. Don't do it.
    Even if you are a good person and you want to share it with your friends, don't do it.
