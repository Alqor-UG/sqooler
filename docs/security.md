---
comments: true
---

# Security and signing

In this section we will discuss some of the cryptographic work that we started. All of the code in this regard can be found in the `security` module.  Before we go into more detail on the discussion, let us remind ourselves of the general architecture of the workflow:

``` mermaid
flowchart LR
    id1(Alice) -- json API --- id2[qlued]
    id2[qlued] -- sqooler --- id3[(storage)]
    id3[(storage)] -- sqooler --- id4(Bob)
```


## Signing the results
For the moment, we have decided to only sign results and not encrypt them.  For simplicity, we have further focused on the asymmetric signing with [ED25519](https://cryptography.io/en/latest/hazmat/primitives/asymmetric/ed25519/).  This means that only the part at which Bob uploads the results to the storage is signed. Signing / encrypting the other steps of the workflow would be likely desirable, however, it is not implemented yet.

Having chosen the results as a first step allows us to keep the workflow as simple as possible. It further introduces the possibility for Bob to show that he is producer of the results and Alice to verify that the results are authentic through the public key. So for the moment it is only needed for Bob to set up a private key and upload the public key to the storage. Similiar possbilities for Alice might follow in the future.


## Setting up the private key

We have decided to work with the widely used crypotgraphic python library [cryptography](https://cryptography.io/en/latest/). To use it, Bob first needs to create and store a private key. This done with [Json Web Keys](https://datatracker.ietf.org/doc/html/rfc7517) as they allow us also to store some context around the key.

This is done by running the following code in the terminal:

```python

from sqooler.security import create_jwk_pair

private_jwk, public_jwk = create_jwk_pair("doc_example_key")

print(private_jwk.to_config_str())
```
As Bob you can then copy this string into your preferred storage from which we load it.

!!! warning
    The private key should be kept secret and should not be shared with anyone. Never ever ever. Don't do it.
    Even if you are a good person and you want to share it with your friends, don't do it.

## Signing the result 

Once Bob has the private key, we can use it to sign the result. This is directly enabled by setting the `sign` flag for your `Spooler` object. The rest has been integrated directly into the code. 

