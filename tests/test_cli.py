"""
Test module for the cli module.
"""

from click.testing import CliRunner
from icecream import ic

from sqooler.cli import cli_private_key_str
from sqooler.security import jwk_from_config_str


def test_generate_key() -> None:
    runner = CliRunner()
    result = runner.invoke(cli_private_key_str, input="testkey")
    assert result.exit_code == 0
    assert "testkey" in result.output

    # now isolate the key
    key = result.output.split("\n")[3]

    # and check if it is a valid key
    private_jwk = jwk_from_config_str(key)
    assert private_jwk.kid == "testkey"
    assert private_jwk.key_ops == "sign"
