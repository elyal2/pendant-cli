"""Bleak backend for direct BLE connection to pendant."""

from typing import Optional, Callable

from .config import DEFAULT_PENDANT_ADDRESS, CONTROL_UUID, AUDIO_DATA_UUID, PREFERRED_MTU
from .protocol import PendantProtocol


class BleakClient:
    """Bleak backend for direct BLE connection."""

    def __init__(self, address: str = DEFAULT_PENDANT_ADDRESS):
        self.address = address
        self.protocol = PendantProtocol()
        self.client = None
        self.on_response: Optional[Callable] = None
        self.private_key = None

        # BLE parameters
        self.mtu = 23  # Default BLE MTU, updated after connection

        # Audio collection
        self.opus_data = bytearray()
        self.pcm_data = bytearray()
        self.encrypted_data = bytearray()
        self.page_count = 0
        self.responses = []
        self.page_timestamps = []  # List of page_info dicts with timestamps

    async def _notification_handler(self, sender, data: bytes):
        """Handle incoming BLE notifications."""
        payload = self.protocol.parse_ble_message(data)
        if payload:
            response = self.protocol.parse_response(payload)
            if response:
                self._handle_response(response)

    def _handle_response(self, response: dict):
        """Process parsed response."""
        rtype = response.get("type")
        self.responses.append(rtype)

        if rtype == "device_info":
            print(f"\n  Device: {response.get('device_name', 'Unknown')}")
            print(f"  Firmware: {response.get('firmware_version', '?')}")
            print(f"  Hardware: {response.get('hardware_version', '?')}")

        elif rtype == "device_status":
            print(f"\n  Recording: {response.get('is_recording', False)}")
            print(f"  Storage: {response.get('storage_used_percent', 0)}%")

        elif rtype == "battery_status":
            print(f"\n  Battery: {response.get('level', 0)}%")

        elif rtype == "storage_buffer":
            self.page_count += 1
            flash_page = response.get("flash_page", b"")
            if flash_page:
                opus, pcm, encrypted, _, page_info = self.protocol.extract_audio_from_flash_page(flash_page, self.private_key)
                # Track audio offset for this page
                page_info["audio_offset_bytes"] = len(self.opus_data)
                self.page_timestamps.append(page_info)
                self.opus_data.extend(opus)
                self.pcm_data.extend(pcm)
                self.encrypted_data.extend(encrypted)
            enc_str = f" enc={len(self.encrypted_data)}B" if self.encrypted_data else ""
            print(f"\r  Page {self.page_count}: opus={len(self.opus_data)}B pcm={len(self.pcm_data)}B{enc_str}", end="", flush=True)

        if self.on_response:
            self.on_response(response)

    async def connect(self) -> bool:
        """Connect to device via Bleak."""
        from bleak import BleakClient as BC, BleakScanner

        print(f"Scanning for {self.address}...")

        # Find device
        device = None
        devices = await BleakScanner.discover(timeout=10.0, return_adv=True)
        for addr, (dev, adv) in devices.items():
            if addr.upper() == self.address.upper():
                device = dev
                break

        if not device:
            print("Device not found. Make sure it's powered on and not connected elsewhere.")
            return False

        self.client = BC(device, timeout=20.0)
        await self.client.connect()

        if not self.client.is_connected:
            print("Failed to connect!")
            return False

        # Query negotiated MTU
        try:
            self.mtu = self.client.mtu_size
            print(f"Connected (MTU: {self.mtu} bytes)")
        except Exception:
            print(f"Connected (MTU: default)")

        # Enable notifications
        await self.client.start_notify(AUDIO_DATA_UUID, self._notification_handler)
        return True

    async def send_command(self, cmd_type: str, **kwargs):
        """Send a command to the pendant."""
        cmd = self.protocol.create_command(cmd_type, **kwargs)
        await self.client.write_gatt_char(CONTROL_UUID, cmd, response=False)

    async def disconnect(self):
        """Disconnect from device."""
        if self.client and self.client.is_connected:
            await self.client.stop_notify(AUDIO_DATA_UUID)
            await self.client.disconnect()
