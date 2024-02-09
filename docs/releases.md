---
comments: true
---

# Release information


In this guide we will cover the key information about the different releases.

## v0.5

This release further increased the typing and testing of the package. It also fixed some long standing usability bugs for the user. 

What Changed:

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

What Changed:

* Introduce the `StatusMsgDict` for proper typing of status messages 
* Enforce cleaner typing of `ExperimentDict` 
* Improved testing of the `Spooler` 
* Introduce the `GateDict` to properly type the `gate_list_from_dict`
* Improved testing, typing and error handling of the `gen_circuit` 
* Added `LabscriptSpooler` class 
* Add the `gen_script` from the labscriptspooler nd created the `spoolers` module