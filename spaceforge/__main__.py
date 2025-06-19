"""
Main entry point for spaceforge module.
"""

import click

from ._version import get_version
from .generator import generate_command
from .runner import runner_command


@click.group()
@click.version_option(version=get_version(), prog_name="spaceforge")
def cli() -> None:
    """Spaceforge - Spacelift Plugin Framework

    A Python framework for building Spacelift plugins with hook-based functionality.
    """
    pass


# Add subcommands
cli.add_command(generate_command)
cli.add_command(runner_command)


def main() -> None:
    """Main entry point."""
    cli()


if __name__ == "__main__":
    main()
