# Welcome to Sqooler

This is a collection of cold atom simulators that you can access through the `qiskit-cold-atom` and the `qlued` interface:

- `qiskit-cold-atom` allows the enduser to write the circuit definitions on its laptop and send them to the server in form of a nice *json* file.
- `qlued` handles the user management and stores the received *json* file in an appropiate queue.
- `sqooler` acts as the backend that performs the calculations from the queue and sends back the result into the storage.

To enable this work-flow, the simulator has to follow a few rules on how to parse the json files etc. This is what we have started to standardize and simplify as much as possible. In the following we documented each module its purpose and look forward to your contributions.