"""
Here we test the spooler class and its functions.
"""

from sqooler.schemes import Spooler


test_spooler = Spooler(ins_schema_dict={}, n_wires=2)


def test_spooler_config() -> None:
    """
    Test that it is possible to get the config of the spooler.
    """
    spooler_config = test_spooler.get_configuration()
    assert spooler_config["num_wires"] == 2
    assert spooler_config["operational"]
