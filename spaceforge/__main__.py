"""
Main entry point for spaceforge module.
"""

import click

from spaceforge._version import get_version
from spaceforge.generator import generate_command
from spaceforge.runner import run_command


@click.group()
@click.version_option(version=get_version(), prog_name="spaceforge")
def cli() -> None:
    """Spaceforge - Spacelift Plugin Framework

    A Python framework for building Spacelift plugins with hook-based functionality.
    """
    pass


# Add subcommands
cli.add_command(generate_command)
cli.add_command(run_command)

# KLUDGE: Add a hidden "runner" alias to the "run" command for backward compatibility.
# It could be removed in the next major version.
runner_alias = click.Command(
    callback=run_command.callback,
    help=run_command.help,
    hidden=True,
    name="runner",
    params=run_command.params,
)
cli.add_command(runner_alias)


def main() -> None:
    """Main entry point."""
    cli()


if __name__ == "__main__":
    main()
