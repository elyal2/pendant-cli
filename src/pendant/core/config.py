"""Shared configuration constants for pendant."""

import os
from pathlib import Path

# Device Configuration

# BLE UUIDs
AUDIO_SERVICE_UUID = "632de001-604c-446b-a80f-7963e950f3fb"
CONTROL_UUID = "632de002-604c-446b-a80f-7963e950f3fb"
AUDIO_DATA_UUID = "632de003-604c-446b-a80f-7963e950f3fb"
CCCD_UUID = "00002902-0000-1000-8000-00805f9b34fb"

# Alternative data channel
DATA_SERVICE_UUID = "8d53dc1d-1db7-4cd3-868b-8a527460aa84"
DATA_CHAR_UUID = "da2e7828-fbce-4e01-ae9e-261174997c48"

# BLE MTU
PREFERRED_MTU = 498  # Matches Limitless app (498 + 3 = 501, fits in 512 L2CAP)

# Pendant-specific service UUIDs with descriptions
PENDANT_SERVICES = {
    "632de001-604c-446b-a80f-7963e950f3fb": "Pendant Audio Service",
    "8d53dc1d-1db7-4cd3-868b-8a527460aa84": "Pendant Data Channel",
}

# Pendant-specific characteristic UUIDs with descriptions
PENDANT_CHARACTERISTICS = {
    "632de002-604c-446b-a80f-7963e950f3fb": "Control (Write)",
    "632de003-604c-446b-a80f-7963e950f3fb": "Audio Data (Notify)",
    "da2e7828-fbce-4e01-ae9e-261174997c48": "Bidirectional Data",
}

# Standard BLE service UUIDs
KNOWN_SERVICES = {
    "00001800-0000-1000-8000-00805f9b34fb": "Generic Access",
    "00001801-0000-1000-8000-00805f9b34fb": "Generic Attribute",
    "0000180a-0000-1000-8000-00805f9b34fb": "Device Information",
    "0000180f-0000-1000-8000-00805f9b34fb": "Battery Service",
    "00001812-0000-1000-8000-00805f9b34fb": "HID Service",
}

# Paths
PACKAGE_DIR = Path(__file__).parent.parent
PROJECT_ROOT = PACKAGE_DIR.parent.parent.parent

# Keys directory - check project root first, then ~/.config/pendant
_project_keys = PROJECT_ROOT / "keys"
_config_keys = Path.home() / ".config" / "pendant" / "keys"

if _project_keys.exists():
    KEYS_DIR = _project_keys
else:
    KEYS_DIR = _config_keys

# Timestamp validation
MIN_VALID_TIMESTAMP_MS = 1577836800000  # Jan 1, 2020


def get_pendant_address() -> str:
    """Get pendant address from PENDANT_ADDRESS environment variable."""
    addr = os.environ.get("PENDANT_ADDRESS")
    if not addr:
        raise RuntimeError(
            "PENDANT_ADDRESS environment variable not set. "
            "Run 'pendant bt scan' to find your device, then export PENDANT_ADDRESS=<mac>"
        )
    return addr
