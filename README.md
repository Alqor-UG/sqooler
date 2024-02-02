# Welcome to Sqooler

We are proud to be currently sponsored by the *Unitary Fund*. It enables us to set up a good test environment and make it as straight-forward as possible to integrate cold atoms with circuits. This documentation will improve as the good goes beyond the initial piloting status. 

[![Unitary Fund](https://img.shields.io/badge/Supported%20By-UNITARY%20FUND-brightgreen.svg?style=for-the-badge)](https://unitary.fund) 

`Sqooler` is an SDK that allows developers to provide cloud access to their code in a secure fashion. A few important features:

- The PC never has to grant access privileges to any outside contributor.
- The remote jobs are heavily controlled through [pydantic](https://docs.pydantic.dev/latest/).
- Simple setup through templates.
- Direct integration with web services like [qlued](https://github.com/Alqor-UG/qlued).
- Fully open source.

It allows cold atom hardware and simulators to be accessed through the `qiskit-cold-atom` and the `qlued` API:

- `qiskit-cold-atom` allows the enduser to write the circuit definitions on its laptop and send them to the server in form of a nice *json* file.
- `qlued` handles the user management and stores the received *json* file in an appropiate queue.
- `sqooler` acts as the SDK that pulls the the calculations from the queue and sends back the result into the storage.
- end devices like the [sqooler-example](https://github.com/Alqor-UG/sqooler-example) or the [labscript-qc-example](https://github.com/Alqor-UG/labscript-qc-example) can perform the calculation and display it to the user.

To enable this work-flow, the simulator has to follow a few rules on how to parse the json files etc. This is what we have started to standardize and simplify as much as possible. In the following we documented each module its purpose and look forward to your contributions.

## Getting started

We provide templates for a simple startup:

- If you are using cold atoms with labscript, we recommend [this template](https://github.com/Alqor-UG/labscript-qc-example).
- If you are developping high performance simulators and look for a flexible way to make the cloud-ready, we recommend [this template](https://github.com/Alqor-UG/sqooler-example).

If you would like to just play with the package, you can simply install it with a simple:

```
pip install sqooler
```


## Contributing

See [the contributing guide](docs/contributing.md) for detailed instructions on how to get started with a contribution to our project. We accept different **types of contributions**, most of them don't require you to write a single line of code.

On the [sqooler](https://alqor-ug.github.io/sqooler/) site, you can click the make a contribution button at the top of the page to open a pull request for quick fixes like typos, updates, or link fixes.

For more complex contributions, you can [open an issue](https://github.com/alqor-ug/sqooler/issues) to describe the changes you'd like to see.

If you're looking for a way to contribute, you can scan through our [existing issues](https://github.com/alqor-ug/sqooler/issues) for something to work on. 

### Join us in discussions

We use GitHub Discussions to talk about all sorts of topics related to documentation and this site. For example: if you'd like help troubleshooting a PR, have a great new idea, or want to share something amazing you've learned in our docs, join us in the [discussions](https://github.com/alqor-ug/sqooler/discussions).

## License

Any code within this repo is licenced under the [Unlicense](LICENSE) license.

The sqooler documentation in the docs folders are licensed under a [Creative Commons Attribution-ShareAlike 4.0 International License (CC BY-SA 4.0)](https://creativecommons.org/licenses/by-sa/4.0/).


## Thanks :purple_heart:

Thanks for all your contributions and efforts towards improving sqooler. We thank you for being part of our :sparkles: community :sparkles:!
