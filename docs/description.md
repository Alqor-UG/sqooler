---
comments: true
---

# General description

In this document, we will outline the general ideas behind `sqooler`. `sqooler` was built by cold atom hardware providers who wanted something like `qiskit` or `pennylane` for their systems. It is meant to allow access to quantum hardware to non-experts in the construction and maintenance of quantum hardware to provide access to their hardware. It also stems from the observation the different people have very different interests.

 - As a *user*, often a theoretical physicist,  we have very little interest in the supplier of the calculation. We just want the calculation properly done. In the following we will call this person *Alice*.
 - As a supplier *backend provider*, often experimental physicists or engineers, we have little interest in the person demanding the calculation. If you are european you might even be happy to not know too much about them. In the following we will call this person *Bob*.
 
 Until now we might sketch the whole process up like this:

``` mermaid
sequenceDiagram
  autonumber
  actor Alice
  actor Bob
  Alice->>Bob: I want to have a calculation done.
  Bob->>Alice: Send me your instructions that go with the hardware constraints.
  Alice->>Bob: Here are my instructions.
  loop shots
        Bob->>Bob: Verify the instruction!
        Bob->>Bob: Execute the job!
        Bob->>Bob: Save the results in a nice fashion!
  end
  Bob->>Alice: Here are the results.
```

In the typical collaboration between experimental and theoretical physicists the whole process would be done in long and detailled discussions. However, with `sqooler` we standardize the process and make it more efficient. This standardization comes with the following choices:

- All operations on the hardware are formulated as *discrete* gates. This abstracts away the hardware and makes it possible to use the same code for different hardware.
- The instructions are sent in a *json* format. This makes it easy to verify the instructions and to execute the job.
- The results are sent back in a *json* format. This makes it easy to verify the results and to save them in a nice fashion.
- We align with the *qiskit* ecosystem where possible. However, we are much closer to the "metal" than most qiskit modules.

As you can see the above diagram contains all the necessary steps to get the job done. 

## The basic architecture

It was around this idea that `sqooler` was built. Technically it was implemented in the following rough architecture:

- *Alice* communicates only with a `qlued` server. This server is responsible to enforce all the above standards.
- If the received instructions are valid, the `qlued` server sends the instructions to a *storage*.
- *Bob* looks regularly into the *storage*, executes the jobs and safe the results there. He never interacts with the *qlued* instance or *Alice*.

Hence, we can sketch the information exchange as follows:

``` mermaid
flowchart LR
    id1(Alice) -- json API --- id2[qlued]
    id2[qlued] -- sqooler --- id3[(storage)]
    id3[(storage)] -- sqooler --- id4(Bob)
```

This means that *Alice* only needs to have an efficient way to communicate with the *qlued* instance. This problem is solved by `qlued` and `qiskit-cold-atoms`:

- `qlued` provides a *json* API with all the necessary endpoints to send in the instructions.
- `qiskit-cold-atoms` provides a circuit based *qiskit* module to directly access the *qlued* instance as any other provider.

Any interaction with the storage happens through `sqooler`.  Especially the interaction between *Bob* and the database happens through `sqooler`:

- Bob is regularly looking for new jobs in the storage, executes them and saves the results there.
- This makes sure that Bob never has to grant access privileges to any outside contributor.
- This also decouples the execution of the jobs from the communication with *Alice*.

For more details on the implementation feel free to look into the detailled documents. 

## A few words on decentralization

The whole scheme is set up to be as modular as possible. This makes the maintenance of the system easier and allows for a lot of flexibility. Some key considerations are:

- Anyone can set up a `qlued` instance and provide access to their hardware.
- Any `qlued` instance can be connected to several storages. Ownership of the `qlued` instance and the storage can be decoupled.
- Bob can choose to work with any storage he likes. For the moment the queue is not set up to work with several storages at the same time. However, this is a feature that could be easily added in the future if there is a demand for it.

This means that the whole scheme can be fairly decentral and does not necessarily involve any trust. The only needed trust is at the following points:

- *Alice* has to trust that she receives good results. How this can be tested for a quantum computer is to our understanding a hard and fairly open problem.
- The storage provider has to put the access keys into the `qlued` instance. Right now we have not yet cryptographically encrypted the access keys. Adding this feature would actually also allow us to remove any trust from the storage provider.

Finally, you might have recognized that the whole scheme does not involve any financial incentives for anyone. Considerations there are on 
