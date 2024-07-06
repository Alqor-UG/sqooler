---
comments: true
---

# Security and signing

In this section we will discuss some of the cryptographic work that we started. All of the code in this regard can be found in the [security](api/security_api.md) module.  Before we go into more detail on the discussion, let us remind ourselves of the general architecture of the workflow:

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

This is done by running the following command in the terminal:

```zsh
sqoolerkey --kid <YOUR-PREFERRED-KEY-ID> 
```

The `kid` is the key id and should be unique for each key. As Bob you can then copy this string into your preferred storage from which we load it.

!!! warning
    The private key should be kept secret and should not be shared with anyone. Never ever ever. Don't do it.
    Even if you are a good person and you want to share it with your friends, don't do it.


## The public key

Once the private is set up, Bob can upload the public key to the `StorageProvider`. This is done by the `upload_public_key` method, which stores the public key at the appropiate point in the storage. The public key can then be be accessed by anyone through the `get_public_key` method. A few important points are here to note about the public key:

- We store the public key as [Json Web Key (JWK)](https://datatracker.ietf.org/doc/html/rfc7517) in the storage. This allows us to store some context around the key.
- Importantly this also allows us to add the algorithm and a key id.
- However, for the moment anyone with access to the storage can access and change the public key. This is a security risk that we have not yet addressed. The key challenge will be that the public key is stored and immutable once it is published.
- It is possible that several `Sqooler` objects use the same private/public key pair if they run on the same control machine. While this is unlikely for real hardware it is actually exactly the configuration of the [sqooler-example](https://github.com/Alqor-UG/sqooler-example). For this reason, we have attached the kid of the pair to each configuration.


## Verifying the results

Alice is now also able to verify the results through the `verify_result`, which is available for each `StorageProvider`. It uses the `display_name` to get the appropiate public key, the `job_id` to pull the result and then verifies the payload. 

## Signing the configuration

It is now also possible to sign the backend configuration. This happens automatically if the `Spooler` object is configured to be signed. The `upload_config` and `update_config` will then sign the document before uploading it to the storage. This enables us now to have several backend providers in parallel without a central authority. Importantly, we can now hinder the collusion of two backends with the same name because you can only update the files if you are the owner of the private key.