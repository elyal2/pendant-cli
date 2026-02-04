# AGENTS.md

Guidelines for AI coding agents working in this repository.

## Project Overview

Python CLI for communicating with the Limitless Pendant BLE device. Uses Protocol Buffers over BLE GATT, reverse-engineered from the Android app.

## Development Environment

```bash
# Enter dev environment (required - installs deps via uv)
nix develop

# Regenerate protobuf (if proto/pendant.proto changes)
protoc --python_out=proto proto/pendant.proto
```

## Build & Run Commands

```bash
pendant status              # Device status
pendant download -d         # Download and decode to WAV
pendant bt pair             # Pair device (required first time)
pendant bt connect          # Connect to paired device
```

## Testing

**No test suite exists yet.** If adding tests:
- Use `pytest`, place in `tests/`, name files `test_*.py`
- Run: `pytest tests/` or `pytest tests/test_file.py::test_function -v`

## Linting & Formatting

**No linters configured.** If adding, prefer `ruff` in `pyproject.toml`.

## Code Style Guidelines

### Python Version & Imports

Requires Python 3.11-3.12. Import order: stdlib, third-party, local.

```python
from datetime import datetime             # stdlib
import click                              # third-party
from pendant.core.config import KEYS_DIR  # local absolute
from .protocol import PendantProtocol     # local relative (within package)
```

- **Relative imports** within `core/` for sibling modules
- **Absolute imports** in `commands/` when importing from `core/`
- Defer heavy imports inside functions (e.g., `import dbus`)

### Type Annotations

```python
def parse_message(self, data: bytes) -> Optional[bytes]:
    self.fragments: dict[int, list[bytes]] = {}  # Modern 3.9+ syntax
```

- Annotate function signatures; use `Optional[T]` not `T | None`

### Naming Conventions

| Type | Convention | Example |
|------|------------|---------|
| Functions/variables | `snake_case` | `parse_ble_message`, `opus_data` |
| Classes | `PascalCase` | `PendantProtocol`, `DBusClient` |
| Constants | `UPPER_SNAKE_CASE` | `DEFAULT_PENDANT_ADDRESS` |
| Private methods | `_leading_underscore` | `_init_dbus` |

### Docstrings

Minimal Google-style. Module docstrings are single-line. Complex functions document Args/Returns.

```python
def extract_audio(self, data: bytes) -> tuple[bytes, int]:
    """Extract audio data from FlashPage protobuf.
    
    Args:
        data: Raw protobuf bytes
    Returns:
        tuple of (opus_data, codec_type)
    """
```

### Error Handling

```python
# CLI: use click.ClickException
raise click.ClickException("Failed to connect")

# Library: use built-in exceptions with context
raise ValueError(f"Unknown command: {cmd_type}")
```

No custom exceptions. Broad `except Exception` acceptable for protocol parsing.

### Output & Logging

No logging module - use `print()` for debug, `click.echo()` for CLI output.

```python
DEBUG_MODE = False
if DEBUG_MODE:
    print(f"FlashPage: ts={page.absolute_timestamp_ms}")
```

### Class Structure

```python
class DBusClient:
    """Brief description."""
    def __init__(self, address: str):
        self.address = address
        self.protocol = PendantProtocol()
    
    def _init_dbus(self): ...      # Private helpers first
    def connect(self) -> bool: ... # Public API after
```

### CLI Commands

```python
@click.command()
@click.option('--decode', '-d', is_flag=True, help='Auto-decode to WAV')
@click.pass_context
def download(ctx, decode):
    """Download stored recordings from the pendant."""
```

## Architecture

```
src/pendant/
├── cli.py              # Main Click entry point
├── commands/           # CLI commands (audio.py, bluetooth.py, device.py)
└── core/               # Library (protocol.py, dbus_client.py, bleak_client.py, opus.py)
```

### Key Patterns

- **Dual BLE backends**: `DBusClient` (sync/GLib) and `BleakClient` (async)
- **Protocol separation**: `PendantProtocol` handles protobuf, clients handle transport
- **Composition**: Protocol composed into client classes

### BLE UUIDs

- Control (write): `632de002-604c-446b-a80f-7963e950f3fb`
- Data (notify): `632de003-604c-446b-a80f-7963e950f3fb`

### Protocol Notes

- Device requires Bluetooth bonding before commands work
- Audio: Opus @ 16kHz mono, raw frames (no Ogg) - use `pendant decode`
- Encryption: X25519 + ChaCha20-Poly1305
- Device MAC set via `PENDANT_ADDRESS` env var (required, use `pendant bt scan` to find it)
