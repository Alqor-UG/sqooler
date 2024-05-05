"""
This module contains some cli commands that simplify the work with the sqooler package.
"""

import click

from .security import create_jwk_pair


@click.command()
@click.option(
    "--kid", prompt="Key ID", help="The key identifier. Should be short and unique."
)
def cli_private_key_str(kid: str) -> None:
    """
    This command line allows you to generate a private key string that is necessary to enable
    signing within sqooler.
    """
    private_jwk, _ = create_jwk_pair(kid=kid)
    private_key_str = private_jwk.to_config_str()
    click.echo("Your private key is:\n")
    click.secho(private_key_str, fg="green")
    click.echo("\n")
    click.echo("Save it now in the environment variables or the appropiate .env file")


if __name__ == "__main__":
    cli_private_key_str(kid="test_key")
