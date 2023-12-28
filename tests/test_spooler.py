"""
Here we test the spooler class and its functions.
"""

from sqooler.schemes import Spooler


def test_spooler_config() -> None:
    """
    Test that it is possible to get the config of the spooler.
    """
    test_spooler = Spooler(ins_schema_dict={}, n_wires=2)

    spooler_config = test_spooler.get_configuration()
    assert spooler_config["num_wires"] == 2
    assert spooler_config["operational"]


def test_spooler_operational() -> None:
    """
    Test that it is possible to set the operational status of the spooler.
    """
    test_spooler = Spooler(ins_schema_dict={}, n_wires=2, operational=False)

    spooler_config = test_spooler.get_configuration()
    assert spooler_config["num_wires"] == 2
    assert not spooler_config["operational"]
