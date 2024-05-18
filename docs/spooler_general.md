---
comments: true
---

# Bobs' perspective

In this part, we will focus on a general description of the `Spooler` object as they  are the central objects for the backend provider, i.e. Bob from the [general description](description.md). Bob will be in one of two situations:

1. Bob is really deep into the construction of quantum hardware and focuses a lot on fidelity, scalability etc. In this case, Bob will have a control PC with some complex control system like [labscript](https://github.com/labscript-suite). In industry it is known as the world of operational technology.

1. Bob loves high performance numerical computing. So he will focus on every in part of the hardware and code to make it as fast as possible. But once again it is a bit unlikely that Bob is deeply focused on a connection to the outside world.

In both cases, Bob will be able to use a `Spooler` that allows him to interact with others without too much of a hazzle. The `Spooler` object is actually provides Bob with a common interface to communicate with Alice. There he can define available gates and the configuration of the system. For the specific implementation of the `Spooler` object, see the [API documentation](api/spoolers_api.md). Here, we will simply describe the general idea of the `Spooler` object.

## General idea

The `Spooler` allows Bob to define:

- The available gates in th `ins_schema_dict` that contains the input schema of the gates
- Translate the gates in executable code through the `gen_circuit` function
- Define a substantial amount of general properties like the name, maximum amount of executions, etc.
- Manage jobs through the `add_job` function.
- Directly connect to the `StorageProvider` where Alice submit her jobs.
- If Bob is a bit more advanced, he can also sign the jobs with a private key and improve the security of the system.

## The different types of `Spooler`

There are different types of `Spooler` objects that Bob can use. 

- The `BaseSpooler` provides the basic functionality of the `Spooler` object. It is the base class for all other `Spooler` objects.
- The `LabscriptSpooler` is a `Spooler` object that is used for hardware controlled by labscript.
- The `Spooler` class that is mostly adopted for numerical code.

## The operational status

One of the hardest things to get right is the operational status of your machine. 

- In the most naive approach you might say that Alice will figure it out if the device is not around and that's it. 
- In the second step, you would like to be able to set the operational status and make it transparent to Alice. This was actually possible through the `operational` property for some time.
- But bad things might happen to your system and it might take Bob quite some time to see that the machine is currently not available. And once Bob figures this out he certainly has better things to do than to set the operational status to `False`. 

So with `v0.6` of the code we have introduced the `last_queue_check` as a property of the `Sqooler` configuration. This provides Alice additional information and might allow Alice to decide on her own if she sees the machine as active. 

In `v0.7` we started to calculate the `operational` status based on the `last_queue_check`. This made the parameter `operational` of the spooler irrelevant and we could simply calculate it for the config dictionary. So based on these properties, we are currently at the following situation:

- Each `StorageProvider` has a function `get_backend_status` that gives back the current status of the device. The here is just calculated from the last time the queue was checked.

So the `operational` status does not need to be set by Bob at all. We just calculate it based on the other information provided by Bob.