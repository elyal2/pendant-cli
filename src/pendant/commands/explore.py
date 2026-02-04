"""Explore command: GATT service exploration."""

import asyncio

import click

from pendant.core.config import (
    DEFAULT_PENDANT_ADDRESS,
    PENDANT_SERVICES,
    PENDANT_CHARACTERISTICS,
    KNOWN_SERVICES,
)


# Standard characteristic UUIDs
KNOWN_CHARACTERISTICS = {
    "00002a00-0000-1000-8000-00805f9b34fb": "Device Name",
    "00002a01-0000-1000-8000-00805f9b34fb": "Appearance",
    "00002a19-0000-1000-8000-00805f9b34fb": "Battery Level",
    "00002a29-0000-1000-8000-00805f9b34fb": "Manufacturer Name",
    "00002a24-0000-1000-8000-00805f9b34fb": "Model Number",
    "00002a25-0000-1000-8000-00805f9b34fb": "Serial Number",
    "00002a26-0000-1000-8000-00805f9b34fb": "Firmware Revision",
    "00002a27-0000-1000-8000-00805f9b34fb": "Hardware Revision",
    "00002a28-0000-1000-8000-00805f9b34fb": "Software Revision",
}


def get_service_name(uuid: str) -> str:
    """Get human-readable name for a service UUID."""
    uuid_lower = uuid.lower()
    if uuid_lower in PENDANT_SERVICES:
        return PENDANT_SERVICES[uuid_lower]
    if uuid_lower in KNOWN_SERVICES:
        return KNOWN_SERVICES[uuid_lower]
    return "Unknown"


def get_char_name(uuid: str) -> str:
    """Get human-readable name for a characteristic UUID."""
    uuid_lower = uuid.lower()
    if uuid_lower in PENDANT_CHARACTERISTICS:
        return PENDANT_CHARACTERISTICS[uuid_lower]
    if uuid_lower in KNOWN_CHARACTERISTICS:
        return KNOWN_CHARACTERISTICS[uuid_lower]
    return "Unknown"


@click.command()
@click.argument('address', required=False)
@click.pass_context
def explore(ctx, address):
    """Explore GATT services and characteristics.

    If no address is given, uses the configured pendant address or scans.
    """
    if address is None:
        address = ctx.obj.get('address', DEFAULT_PENDANT_ADDRESS)

    asyncio.run(_explore_device(address))


async def _explore_device(address: str):
    """Connect to device and explore GATT services."""
    from bleak import BleakClient, BleakScanner

    click.echo(f"Connecting to {address}...")

    # Try to find device first
    device = None
    devices = await BleakScanner.discover(timeout=5.0, return_adv=True)
    for addr, (dev, adv) in devices.items():
        if addr.upper() == address.upper():
            device = dev
            break

    if not device:
        # Try direct connection anyway
        click.echo("Device not found in scan, attempting direct connection...")

    async with BleakClient(address, timeout=20.0) as client:
        if not client.is_connected:
            raise click.ClickException("Failed to connect!")

        click.echo(f"Connected: {client.is_connected}")
        click.echo(f"MTU: {client.mtu_size}")
        click.echo()

        # Enumerate services
        for service in client.services:
            service_name = get_service_name(service.uuid)
            click.echo(f"Service: {service.uuid}")
            click.echo(f"  Name: {service_name}")

            for char in service.characteristics:
                char_name = get_char_name(char.uuid)
                props = ", ".join(char.properties)

                click.echo(f"  Characteristic: {char.uuid}")
                click.echo(f"    Name: {char_name}")
                click.echo(f"    Properties: {props}")

                # Try to read value if readable
                if "read" in char.properties:
                    try:
                        value = await client.read_gatt_char(char.uuid)
                        # Try to decode as string
                        try:
                            value_str = value.decode('utf-8')
                            click.echo(f"    Value: {value_str}")
                        except UnicodeDecodeError:
                            click.echo(f"    Value (hex): {value.hex()}")
                    except Exception as e:
                        click.echo(f"    Read error: {e}")

                # List descriptors
                for desc in char.descriptors:
                    click.echo(f"    Descriptor: {desc.uuid}")

            click.echo()
