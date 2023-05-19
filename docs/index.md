---
comments: true
---

# Welcome to Sqooler

This is a collection of cold atom simulators that you can access through the `qiskit-cold-atom` and the `qlued` interface:

- `qiskit-cold-atom` allows the enduser to write the circuit definitions on its laptop and send them to the server in form of a nice *json* file.
- `qlued` handles the user management and stores the received *json* file in an appropiate queue.
- `sqooler` acts as the backend that performs the calculations from the queue and sends back the result into the storage.

To enable this work-flow, the simulator has to follow a few rules on how to parse the json files etc. This is what we have started to standardize and simplify as much as possible. In the following we documented each module its purpose and look forward to your contributions.

## Getting started on heroku

The simplest way to use the package is to deploy it to `heroku`. This directly starts the `maintainer.py` in a loop, because it is defined like that in the `Procfile`.  However, you will also need to have the following credentials of the Dropbox:

- `APP_KEY`, `APP_SECRET` and `REFRESH_TOKEN`. Please head over to the documentation of `qlued` to see how they might be set up.
- They should be all defined `Settings` > `Config Vars`. 
- Now your system  should automatically look for jobs that are under `Backend_files/Queued_Jobs`, process them and safe the result under `Backend_files/Finished_Jobs`.


## Getting started locally

!!! note
    
    This part of the documentiation needs a lot of love. Feel free to help us making it more understandable.

If you would like to write some new simulator, extend it etc, you will need to deploy the code locally. Then you will need to:

- clone or fork the repo.
- pip install the `requirements.txt`.
- define `APP_KEY`, `APP_SECRET` and `REFRESH_TOKEN` in the `.env` file that is you should create in the root directory.

## First steps

The whole system is set up on `python`. First, create a local environment. You can then install the requirements via `pip install -r requirements-dev.txt`.

Second, we need to enable the storage of the settings, which we manage with [python-decouple](https://pypi.org/project/python-decouple/). To do so, create a `.env` file in the root directory. 
```
project
│   README.md
│   maintainer.py
|   .env
|   ...    
│
└───.github
│   │   ...
|
└───utils
│   │   ...
|
│   ...
```

An example content of this file would be:

``` python
# setting for MongoDB
MONGODB_USERNAME = <YOUR-USERNAME>
MONGODB_PASSWORD = <YOUR-PASSWORD>
MONGODB_DATABASE_URL = <YOUR-URL>

# settings for the Dropbox, if you use it as a storage
APP_KEY=<YOUR-APP-KEY>
APP_SECRET=<YOUR-APP-SECRED>
REFRESH_TOKEN=<YOUR-REFRESH-TOKEN>
```

Then, to configure the storage make sure which one you use as we provide different options. For example, if you use the MongoDB storage you have to set the `MONGODB_USERNAME`, `MONGODB_PASSWORD` and `MONGODB_DATABASE_URL`.

If you use the Dropbox storage, add the `APP_KEY`, `APP_SECRET` and `REFRESH_TOKEN` to the `.env` file.

To run the system you should run the `maintainer` with `python maintainer.py`.

!!! note
    
    This step also uploads the configuration of the backends onto the storage. So it is crucial for any kind of tests that involve `qlued`.

You can now also stop the maintainer and test the system systematically. This can be performed via `python - m pytest`.


