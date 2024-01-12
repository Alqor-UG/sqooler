"""
Here we test the spooler class and its functions.
"""

from sqooler.schemes import Spooler, StatusMsgDict


class TestSpooler(Spooler):
    """
    A dummy spooler for testing.
    """

    def check_experiment(self, exper_dict: dict) -> tuple[str, bool]:
        """
        Check the validity of the experiment.
        This has to be implement in each subclass extra.

        Args:
            exper_dict: The dictionary that contains the logic and should
                be verified.
        """
        return "No error", True


def test_spooler_config() -> None:
    """
    Test that it is possible to get the config of the spooler.
    """
    test_spooler = Spooler(ins_schema_dict={}, n_wires=2)

    spooler_config = test_spooler.get_configuration()
    assert spooler_config.num_wires == 2
    assert spooler_config.operational


def test_spooler_operational() -> None:
    """
    Test that it is possible to set the operational status of the spooler.
    """
    test_spooler = Spooler(ins_schema_dict={}, n_wires=2, operational=False)

    spooler_config = test_spooler.get_configuration()
    assert spooler_config.num_wires == 2
    assert not spooler_config.operational


def test_spooler_add_job() -> None:
    """
    Test that it is possible to add a job to the spooler.
    """

    test_spooler = TestSpooler(ins_schema_dict={}, n_wires=2, operational=False)
    status_msg_draft = {
        "job_id": "Test_ID",
        "status": "None",
        "detail": "None",
        "error_message": "None",
    }

    job_payload = {
        "experiment_0": {
            "instructions": [],
            "num_wires": 2,
            "shots": 4,
            "wire_order": "interleaved",
        },
    }
    status_msg_dict = StatusMsgDict(**status_msg_draft)
    result_dict, status_msg_dict = test_spooler.add_job(job_payload, status_msg_dict)
    assert result_dict is not None
