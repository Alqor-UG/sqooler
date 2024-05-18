---
comments: true
---

# Introduction to storage providers

In this part, we will focus on a general description of the `StorageProvider` object as they are essential links between the backend provider, i.e. Bob from the [general description](description.md), and the frontend provider, i.e. Alice. For the specific implementation of the `StorageProvider` object, see the [API documentation](storage_providers/storage_providers.md). The `StorageProvider` fulfills two major objectives:

1. It gives a common set of functions to the backend provider to store and retrieve information that is necessary for the operation.
2. It provides a basic interface that is implemented by different storages like a local file system, an unstructured database, or a cloud storage.

In the following, we will therefore explain the basic ideas behind the objects and how they are used within the `sqooler` package.


## Core functions

In any situation Bob and Alice have to manipulate information on the storage. And the basic functions are very much the same. Therefore we have defined the `StorageCore`, which defines the basic set of functions that are necessary for the operation. These functions are:

- `upload`: Uploads a file to the storage to the given path.
- `update`: Updates a file in the storage at the given path.
- `get`: Gets a file from the storage at the given path.
- `move`: Moves a file from one path to another.
- `delete`: Deletes a file from the storage at the given path.

So it is basically a standardized CRUD interface, which allows you to build upon on fairly easily the more complicated functions.


## Storage provider

The `StorageProvider` wraps around the `StorageCore` and provides a more high-level interface that really makes it possible to send quantum circuits around and check their status. It provides functionality to manipulate the following main points:

- *Configuration:* Somehow Alice and Bob need to exchange information about the configuration of the backend on which the calculation should be performed. This can be done with the appropiate `upload_config`, `update_config` and `get_config`. The `get_backend_dict` and `get_backend_status` wrapped around the `get_config` to provide information that is compatible with `QISKIT`. 
- *Job:* Alice main interest in the system is to submit jobs. So the `StorageProvider` has functions to `upload_job`, `get_job`. Bob is further able to handle the jobs in th queue through `get_next_job_in_queue`.
- *Result:* After the job is done, Bob needs to store the results. This is done with the `upload_result` and `get_result` functions. It is also possible to verify the origin with `verify_result`.
- *Status:* The `StorageProvider` also provides functions to update the status of the job with `upload_status` and `get_status`. 
- *Keys:* The `StorageProvider` also provides functionality to sign and verify files through the functionality of the [security module](security_general.md).

All of this is set up to be as flexible as possible and we have now implemented the `StorageProvider` for three different storage systems:

- *Local files*: This is most helpful for testing and small users. For more information see [local](storage_providers/local.md).
- *MongoDB*: This is a more scalable solution that can be used for larger projects. For more information see [mongodb](storage_providers/mongodb.md).
- *Dropbox*: One of the classic cloud storage providers. For more information see [dropbox](storage_providers/dropbox.md).
