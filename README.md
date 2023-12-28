# Welcome to Sqooler

We are proud to be currently sponsored by the *Unitary Fund*. It enables us to set up a good test environment and make it as straight-forward as possible to integrate cold atoms with circuits. This documentation will improve as the good goes beyond the initial piloting status. 

[![Unitary Fund](https://img.shields.io/badge/Supported%20By-UNITARY%20FUND-brightgreen.svg?style=for-the-badge)](https://unitary.fund) 

`Sqooler` is an SDK that allows developers to provide cloud access to their code in a secure fashion. A few important features:

- The PC never has to grant access privileges to any outside contributor.
- The remote jobs are heavily controlled through [pydantic](https://docs.pydantic.dev/latest/).
- Simple setup through templates.

This is a collection of cold atom simulators that you can access through the `qiskit-cold-atom` and the `qlued` interface:

- `qiskit-cold-atom` allows the enduser to write the circuit definitions on its laptop and send them to the server in form of a nice *json* file.
- `qlued` handles the user management and stores the received *json* file in an appropiate queue.
- `sqooler` acts as the backend that performs the calculations from the queue and sends back the result into the storage.

To enable this work-flow, the simulator has to follow a few rules on how to parse the json files etc. This is what we have started to standardize and simplify as much as possible. In the following we documented each module its purpose and look forward to your contributions.

## Getting started

We provide templates for a simple startup:

- If you are using cold atoms with labscript, we recommend [this template](https://github.com/Alqor-UG/labscript-qc-example).
- If you are developping high performance simulators and look for a flexible way to make the cloud-ready, we recommend [this template](https://github.com/Alqor-UG/sqooler-example).

If you would like to just play with the package, you can simply install it with a simple:

```
pip install -e git+https://github.com/Alqor-UG/sqooler.git
```


# Old documentation
The simplest way to use the package is to deploy it to `heroku`. This directly starts the `maintainer.py` in a loop, because it is defined like that in the `Procfile`.  However, you will also need to have the following credentials of the Dropbox:

- `APP_KEY`, `APP_SECRET` and `REFRESH_TOKEN`. Please head over to the documentation of `qlued` to see how they might be set up.
- They should be all defined `Settings` > `Config Vars`. 
- Now your system  should automatically look for jobs that are under `Backend_files/Queued_Jobs`, process them and safe the result under `Backend_files/Finished_Jobs`.


## Getting started locally
    
> :warning: This part of the documentiation needs a lot of love. Feel free to help us making it more understandable.

If you would like to write some new simulator, extend it etc, you will need to deploy the code locally. Then you will need to:

- clone or fork the repo.
- pip install the `requirements.txt`.
- define `APP_KEY`, `APP_SECRET` and `REFRESH_TOKEN` in the `.env` file that is you should create in the root directory.
- run the maintainer with `python maintainer.py`.
