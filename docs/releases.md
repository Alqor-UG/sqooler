---
comments: true
---

# Release information

In this guide we will cover the key information about the different releases.

## v0.9

In this release we made the `StorageProvider` more flexible and especially the paths.

### What's Changed

- The `StorageProvider` now has a `get_attribute_path` and `get_attribute_id`.
- This should massively simplify path directions and make the specific paths fairly obsolete in the future.
- We also updated the migration to get rid of old depreceated code.

### Migration Guide

For the `StorageProvider`the different paths like `pks_path` are not call explicitly anymore but only through the `get_attribute_path`. For future versions it is possible that we remove them completely and we advise you to migrate towards the `get_attribute_path`.

## v0.8

In this release we focused on a substantially more flexible `StorageProvider` and added the new `StorageCore`.

### What's Changed

- We introduced the `StorageCore` that only contains the essential file manipulations.
- Simpler testing as `get_dummy config` is now part of the `utils` module.
- Made the function in the `StorageCore` and `StorageProvider` more consistent.
- Verify that the display name in the uploaded config dict is the same as the argument that was used
- Made the path used in the `MongodbProvider` more transparent.
- Add some documentation on the `StorageProvider`.

### Migration Guide

We have simplified the naming of a number of functions and depreceated them:

- `update_file` is now `update`
- `get_file_content` is now `get`
- `upload_file` is now `upload`
- `delete_file` is now `delete`
- `move_file` is now `move`
- `get_job_content` is now `get_job`

This also likely the last release which allows the `operational` attribute in the `BackendConfigSchemaIn`.

## v0.7

We focused on a simpler usage of the sqooler in this release and the stabilization of the code.

### What's Changed

* Make the operational status depend on last checked
* Fix the default if the `private_jwk` is missing 
* Make the delay between runs in the main loop adjustable
* Remove the operational status from the backend config. Now calculated directly from the last time the queued was checked
* Sign also upload status
* Identify the kid with the display name of the spooler
* Add a simple option to verify results
* Have a command line option to create the private jwk string
* Fail get next safely if no config is presen
* Cleaner tests for improved coverage and more precise testing
* Migration fixes for upgrades from v0.6

### Migration Guide

* The operational status is now dependent on the last checked in time. This means that the operational status is now only `True` if the last checked in time is less than the `T_TIMEOUT`. It can be set as a config variable.
* `T_WAIT_MAIN` set the relay between loops in the `main` function. It can be set as a config variable.

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
- To sign the results and the config you need to store a private `jwk` as described in the documentation for [security](security_general.md#setting-up-the-private-key).
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