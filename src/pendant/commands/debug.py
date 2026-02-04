"""Debug command: download with detailed flash page inspection."""

import click

from pendant.core import protocol as protocol_module
from pendant.commands.audio import download


@click.command()
@click.pass_context
def debug(ctx):
    """Download with detailed flash page inspection."""
    # Enable debug mode
    protocol_module.DEBUG_MODE = True
    click.echo("Debug mode enabled - showing flash page details")

    # Invoke the download command
    ctx.invoke(download, decode=False, output='.')
