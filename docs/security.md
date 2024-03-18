---
comments: true
---

# Security and signing

In this section we will discuss some of the cryptographic work that we started and how we can sign our results. All of the code in this regard can be found in the `security` module.  For the moment, we have decided to only sign results and not encrypt them. This allows everyone to establish the authenticity of the results, but does not put the burden of always keeping the keys around on the owners of the data. For simplicity, we have further focused on the asymmetric signing with [ED25519](https://cryptography.io/en/latest/hazmat/primitives/asymmetric/ed25519/). 

## Setting up the key

We have decided to work with the widely used crypotgraphic python library [cryptography](https://cryptography.io/en/latest/). To use it, we first need to create and store a private key. This done with [Json Web Keys](https://datatracker.ietf.org/doc/html/rfc7517) as they allow us also to store some context around the key.

This is done by running the following code in the terminal:

```python

from sqooler.security import create_jwk_pair

private_jwk, public_jwk = create_jwk_pair("doc_example_key")

print(private_jwk.to_config_str())
```

## Signing the result 

Once we have the private key, we can use it to sign the result. This is directly enabled by setting the `sign` flag for your `Spooler` object. The rest has been integrated directly into the code. 

You can then copy this string into your preferred storage from which we load it.

!!! warning
    The private key should be kept secret and should not be shared with anyone. Never ever ever. Don't do it.
    Even if you are a good person and you want to share it with your friends, don't do it.
