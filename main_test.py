"""
The module that contains all the necessary logic for processing jobs in the database queue.
"""
import importlib
import json
import time
import os
import shutil
import traceback
import regex as re

from spooler_files import drpbx

def main():
    """
    Function for processing jobs continuously.
    """
    # TODO: This should be pull in automatically from the back-end config at some point.
    backends_list = ["fermions", "singlequdit", "multiqudit"]

    # loop which is looking for the jobs
    requested_backend = "singlequdit"
    requested_spooler = importlib.import_module("spooler_files.spooler_" + requested_backend)
    add_job = getattr(requested_spooler, "add_job")


if __name__ == "__main__":
    main()
