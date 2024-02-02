---
comments: true
---

# Release information


In this guide we will cover the key information about the different releases.

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