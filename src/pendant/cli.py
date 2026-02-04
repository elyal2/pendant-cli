"""Main CLI entry point for pendant."""

import click

from pendant import __version__
from pendant.core.config import DEFAULT_PENDANT_ADDRESS


@click.group()
@click.version_option(version=__version__)
@click.option('--address', '-a',
              envvar='PENDANT_ADDRESS',
              default=DEFAULT_PENDANT_ADDRESS,
              help='Pendant Bluetooth address')
@click.option('--verbose', '-v', is_flag=True, help='Verbose output')
@click.pass_context
def cli(ctx, address, verbose):
    """Pendant BLE Client - Communicate with Limitless Pendant."""
    ctx.ensure_object(dict)
    ctx.obj['address'] = address
    ctx.obj['verbose'] = verbose


# Import and register command groups
from pendant.commands import device, audio, bluetooth, crypto, explore, debug, settings

# Register individual commands
cli.add_command(device.status)
cli.add_command(device.info)
cli.add_command(device.listen)
cli.add_command(audio.download)
cli.add_command(audio.decode)
cli.add_command(audio.record)
cli.add_command(audio.stop)
cli.add_command(audio.clear)

# Register command groups
cli.add_command(bluetooth.bt)
cli.add_command(crypto.crypto)
cli.add_command(settings.settings)

# Register standalone commands
cli.add_command(explore.explore)
cli.add_command(debug.debug)


def main():
    """Main entry point."""
    cli()


if __name__ == "__main__":
    main()
