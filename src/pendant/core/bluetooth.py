"""Bluetooth utility functions using bluetoothctl."""

import subprocess
import time
import re
from typing import Optional

from .config import DEFAULT_PENDANT_ADDRESS


def run_bluetoothctl(*commands, timeout=30) -> tuple[bool, str]:
    """Run bluetoothctl commands and return result.

    Args:
        *commands: Commands to run in sequence
        timeout: Total timeout in seconds

    Returns:
        Tuple of (success, output)
    """
    proc = subprocess.Popen(
        ['bluetoothctl'],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=0
    )

    for cmd in commands:
        proc.stdin.write(cmd + "\n")
        proc.stdin.flush()
        time.sleep(0.5)

    proc.stdin.write("quit\n")
    proc.stdin.flush()

    try:
        output, _ = proc.communicate(timeout=timeout)
        return True, output
    except subprocess.TimeoutExpired:
        proc.kill()
        output, _ = proc.communicate()
        return False, output


def get_device_status(address: str = DEFAULT_PENDANT_ADDRESS) -> dict:
    """Get current device status from bluetoothctl."""
    result = subprocess.run(
        ['bluetoothctl', 'info', address],
        capture_output=True, text=True, timeout=5
    )

    status = {
        "found": False,
        "paired": False,
        "bonded": False,
        "trusted": False,
        "connected": False,
        "name": None,
    }

    if result.returncode != 0 or "not available" in result.stdout.lower():
        return status

    status["found"] = True
    output = result.stdout

    if "Paired: yes" in output:
        status["paired"] = True
    if "Bonded: yes" in output:
        status["bonded"] = True
    if "Trusted: yes" in output:
        status["trusted"] = True
    if "Connected: yes" in output:
        status["connected"] = True

    # Extract name
    match = re.search(r"Name: (.+)", output)
    if match:
        status["name"] = match.group(1).strip()

    return status


def pair_device(address: str = DEFAULT_PENDANT_ADDRESS) -> bool:
    """Pair and bond with the Pendant device.

    The Pendant uses "Just Works" pairing (NoInputNoOutput).
    """
    print(f"Pairing with {address}...")
    print("Make sure the device is:")
    print("  - Powered on and awake (tap to wake)")
    print("  - Not connected to your phone")
    print()

    # Check current status
    status = get_device_status(address)

    if status["bonded"] and status["connected"]:
        print("Device is already paired and connected!")
        return True

    print("Step 1/5: Powering on Bluetooth...")
    run_bluetoothctl("power on")

    print("Step 2/5: Setting up pairing agent...")
    run_bluetoothctl("agent NoInputNoOutput", "default-agent")

    if status["found"]:
        print("Step 3/5: Removing old pairing...")
        run_bluetoothctl(f"remove {address}")
        time.sleep(1)

    print("Step 4/5: Scanning for device...")
    run_bluetoothctl("scan on", timeout=10)
    time.sleep(8)
    run_bluetoothctl("scan off")

    print("Step 5/5: Pairing, trusting, and connecting...")

    # Run the pairing sequence
    proc = subprocess.Popen(
        ['bluetoothctl'],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=0
    )

    def send(cmd, delay=2):
        print(f"  > {cmd}")
        proc.stdin.write(cmd + "\n")
        proc.stdin.flush()
        time.sleep(delay)

    send("power on", 1)
    send("agent NoInputNoOutput", 1)
    send("default-agent", 1)
    send(f"pair {address}", 5)
    send(f"trust {address}", 2)
    send(f"connect {address}", 5)
    proc.stdin.write("quit\n")
    proc.stdin.flush()

    try:
        proc.communicate(timeout=30)
    except subprocess.TimeoutExpired:
        proc.kill()
        proc.communicate()

    # Check result
    final_status = get_device_status(address)

    print()
    if final_status["bonded"]:
        print("Pairing successful!")
        print(f"  Paired:    {final_status['paired']}")
        print(f"  Bonded:    {final_status['bonded']}")
        print(f"  Connected: {final_status['connected']}")

        if not final_status["connected"]:
            print("\nConnecting...")
            connect_device(address)

        return True
    else:
        print("Pairing may have failed.")
        print("Troubleshooting:")
        print("  1. Factory reset the Pendant (hold button 10+ seconds)")
        print("  2. Make sure phone app is not connected to it")
        print("  3. Tap the Pendant to wake it up")
        print("  4. Try running the pair command again")
        return False


def connect_device(address: str = DEFAULT_PENDANT_ADDRESS) -> bool:
    """Connect to an already-paired device."""
    status = get_device_status(address)

    if not status["bonded"]:
        print("Device is not bonded. Run 'pendant bt pair' first.")
        return False

    if status["connected"]:
        print("Device is already connected!")
        return True

    print(f"Connecting to {address}...")
    run_bluetoothctl(f"connect {address}", timeout=10)

    # Check result
    time.sleep(2)
    final_status = get_device_status(address)

    if final_status["connected"]:
        print("Connected successfully!")
        return True
    else:
        print("Connection failed. The device may be asleep or out of range.")
        print("Tap the device to wake it, then try again.")
        return False


def ensure_connected(address: str = DEFAULT_PENDANT_ADDRESS, verbose: bool = True) -> bool:
    """Ensure device is connected, auto-connecting if needed.

    Returns True if device is connected (or was successfully connected).
    Returns False if connection failed.
    """
    status = get_device_status(address)

    if status["connected"]:
        return True

    if not status["bonded"]:
        if verbose:
            print(f"Device {address} is not paired.")
            print("Run 'pendant bt pair' first.")
        return False

    # Device is bonded but not connected - try to connect
    if verbose:
        print(f"Auto-connecting to {address}...")

    run_bluetoothctl(f"connect {address}", timeout=10)
    time.sleep(2)

    final_status = get_device_status(address)
    if final_status["connected"]:
        if verbose:
            print("Connected!")
        return True
    else:
        if verbose:
            print("Auto-connect failed. Device may be asleep or out of range.")
            print("Tap the device to wake it, then try again.")
        return False


def disconnect_device(address: str = DEFAULT_PENDANT_ADDRESS) -> bool:
    """Disconnect from device (but keep pairing)."""
    print(f"Disconnecting from {address}...")
    run_bluetoothctl(f"disconnect {address}")
    print("Disconnected.")
    return True


def forget_device(address: str = DEFAULT_PENDANT_ADDRESS) -> bool:
    """Remove device pairing completely."""
    print(f"Removing pairing for {address}...")
    run_bluetoothctl(f"remove {address}")
    print("Device pairing removed.")
    print("You'll need to pair again to use the device.")
    return True


def print_bt_status(address: str = DEFAULT_PENDANT_ADDRESS) -> bool:
    """Print device connection status."""
    print(f"Checking status for {address}...")
    status = get_device_status(address)

    if not status["found"]:
        print(f"\n  Device not found in Bluetooth cache.")
        print(f"  Run 'pendant bt pair' to pair.")
        return False

    print(f"\n  Device: {status['name'] or 'Unknown'}")
    print(f"  Paired:    {'yes' if status['paired'] else 'no'}")
    print(f"  Bonded:    {'yes' if status['bonded'] else 'no'}")
    print(f"  Trusted:   {'yes' if status['trusted'] else 'no'}")
    print(f"  Connected: {'yes' if status['connected'] else 'no'}")

    if status["bonded"] and status["connected"]:
        print(f"\n  Ready to use! Run: pendant status")
        return True
    elif status["bonded"]:
        print(f"\n  Bonded but not connected. Run: pendant bt connect")
        return True
    else:
        print(f"\n  Not bonded. Run: pendant bt pair")
        return False
