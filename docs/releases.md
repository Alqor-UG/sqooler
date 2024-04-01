---
comments: true
---

# Release information

In this guide we will cover the key information about the different releases.

## v0.6

In this release, we continued the work on clean typing and we introduced first concepts for better security and logging, so extending the list of features.

### What's Changed

* Improved documentation 
* Fix the cold atom type by 
* Clean distinction between backend name and display name 
* timestamp the loops of the queue
* Much cleaner add job 
* Cleaner tests 
* Make it possible to sign the results for the backend supplier 
* Delete file should fail if file does not exist
* Do not allow to add a config with a name that already exists
* Make it possible to log basic activities

### Migration Guide

- We have changed the syntax for the `gen_circuit` function to make it simpler to understand the code. It now takes the `exp_name` as the first argument and the `exp_dict` of the new type `ExperimentalInputDict` as the second argument. 
- We are now distinguishing pretty strictly between the `backend_name` and the `display_name`. The `display_name` is the short alphanumeric string that acts as identifier. The `backend_name` also contains the name of the `StorageProvider` and if the system is a simulator or not.
- To sign the results and the config you need to store a private `jwk` as described in the documentation for [security](security.md).
- The `add_job` function now takes the `job_id` as the second parameter instead of the the `StatusMsgDict`. This removed some error sources.


## v0.5

This release further increased the typing and testing of the package. It also fixed some long standing usability bugs for the user. 

### What's Changed

* Cleaner error handling of missing status
* Unify the error handling for the `get_file_content` function amongst `StorageProvider`s.
* Put the different `StorageProvider`s into the `storage_provider` module to make it easier to add new ones.
* Type and verify the status string to be "INITIALIZING", "QUEUED", "DONE", "ERROR" and introduce the functions `get_init_status` as well as `get_init_results` that help with the initialization.
* Clean out the names given to the backends and storage providers such that they conform with the intended logic of being alphanumeric names only.
* Enforce the coupling map of the `GateInstruction`.
* Give back the measured wires and the instructions for each *experiment* to make it easier to reconstruct. 
* Introduced the new `DataDict` for better typing for the results.

## v0.4

This release focused on better typing with `pydantic` and a simpler deployment on the back-end side.

### What's Changed

* Introduce the `StatusMsgDict` for proper typing of status messages 
* Enforce cleaner typing of `ExperimentDict` 
* Improved testing of the `Spooler` 
* Introduce the `GateDict` to properly type the `gate_list_from_dict`
* Improved testing, typing and error handling of the `gen_circuit` 
* Added `LabscriptSpooler` class 
* Add the `gen_script` from the labscriptspooler nd created the `spoolers` module