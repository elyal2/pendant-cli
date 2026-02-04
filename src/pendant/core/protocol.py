"""Pendant BLE protocol implementation (protobuf encoding/decoding)."""

from datetime import datetime
from typing import Optional

from .proto import pb, PROTOBUF_AVAILABLE
from .config import KEYS_DIR

# Module-level debug flag
DEBUG_MODE = False


class PendantProtocol:
    """Implements the Pendant BLE protocol (protobuf encoding/decoding)."""

    def __init__(self):
        self.message_index = 0
        self.pending_fragments: dict[int, list[bytes]] = {}

    def create_ble_message(self, payload: bytes) -> bytes:
        """Wrap a payload in BLE message envelope."""
        if not PROTOBUF_AVAILABLE:
            return payload

        msg = pb.BLEMessageFromNativeToPendant()
        msg.index = self.message_index
        msg.ble_fragment_seq = 0
        msg.num_fragments = 1
        msg.payload = payload
        self.message_index += 1
        return msg.SerializeToString()

    def parse_ble_message(self, data: bytes) -> Optional[bytes]:
        """Parse BLE message and handle fragmentation."""
        if not PROTOBUF_AVAILABLE:
            return data

        try:
            msg = pb.BLEMessageFromPendantToNative()
            msg.ParseFromString(bytes(data))

            if msg.num_fragments == 1:
                return msg.payload

            # Handle fragmentation
            if msg.index not in self.pending_fragments:
                self.pending_fragments[msg.index] = [None] * msg.num_fragments

            self.pending_fragments[msg.index][msg.ble_fragment_seq] = msg.payload

            if all(f is not None for f in self.pending_fragments[msg.index]):
                complete = b''.join(self.pending_fragments[msg.index])
                del self.pending_fragments[msg.index]
                return complete

            return None

        except Exception:
            return None

    def create_command(self, cmd_type: str, **kwargs) -> bytes:
        """Create a ServerCommandMsg protobuf."""
        if not PROTOBUF_AVAILABLE:
            raise RuntimeError("Protobuf not available")

        cmd = pb.ServerCommandMsg()

        # Set request_id
        request_data = pb.RequestData()
        request_data.request_id = self.message_index + 1
        cmd.request_data.CopyFrom(request_data)

        if cmd_type == "get_device_info":
            cmd.get_device_info.CopyFrom(pb.GetDeviceInfo())

        elif cmd_type == "get_device_status":
            cmd.get_device_status.CopyFrom(pb.GetDeviceStatus())

        elif cmd_type == "download_flash_pages":
            dl = pb.DownloadFlashPages()
            dl.batch_mode_enabled = kwargs.get("batch", True)
            dl.real_time_mode_enabled = kwargs.get("realtime", False)
            cmd.download_flash_pages.CopyFrom(dl)

        elif cmd_type == "set_current_time":
            sct = pb.SetCurrentTime()
            sct.timestamp_ms = kwargs.get("timestamp_ms", int(datetime.now().timestamp() * 1000))
            cmd.set_current_time.CopyFrom(sct)

        elif cmd_type == "start_recording":
            cmd.start_recording.CopyFrom(pb.StartRecording())

        elif cmd_type == "stop_recording":
            cmd.stop_recording.CopyFrom(pb.StopRecording())

        elif cmd_type == "set_ble_pair":
            pair = pb.SetBLEPair()
            pair.enable = kwargs.get("enable", True)
            cmd.set_ble_pair.CopyFrom(pair)

        elif cmd_type == "clear_storage":
            cmd.clear_pendant_storage.CopyFrom(pb.ClearPendantStorage())

        elif cmd_type == "factory_reset":
            cmd.factory_reset_pendant.CopyFrom(pb.FactoryResetPendant())

        elif cmd_type == "set_server_public_key":
            key_msg = pb.SetServerPublicKey()
            key_msg.public_key = kwargs.get("public_key", b"")
            cmd.set_audio_encryption_server_public_key.CopyFrom(key_msg)

        elif cmd_type == "set_led":
            led_msg = pb.SetLed()
            led_msg.state = kwargs.get("state", 0)
            cmd.set_led.CopyFrom(led_msg)

        elif cmd_type == "set_led_brightness":
            brightness_msg = pb.SetLEDBrightness()
            brightness_msg.brightness = kwargs.get("brightness", 100)
            cmd.set_led_brightness.CopyFrom(brightness_msg)

        elif cmd_type == "set_vad_threshold":
            vad_msg = pb.SetVADThreshold()
            vad_msg.threshold = kwargs.get("threshold", 0.5)
            cmd.set_vad_threshold.CopyFrom(vad_msg)

        elif cmd_type == "set_device_name":
            name_msg = pb.SetDeviceName()
            name_msg.name = kwargs.get("name", "Pendant")
            cmd.set_device_name.CopyFrom(name_msg)

        elif cmd_type == "unpair_bluetooth":
            cmd.unpair_bluetooth.CopyFrom(pb.UnpairBluetooth())

        elif cmd_type == "disconnect_wifi":
            cmd.disconnect_wifi.CopyFrom(pb.DisconnectWifi())

        elif cmd_type == "connect_to_wifi":
            wifi_msg = pb.ConnectToWifi()
            wifi_msg.ssid = kwargs.get("ssid", "")
            cmd.connect_to_wifi.CopyFrom(wifi_msg)

        elif cmd_type == "add_wifi_credentials":
            wifi_msg = pb.AddWifiCredentials()
            wifi_msg.ssid = kwargs.get("ssid", "")
            wifi_msg.password = kwargs.get("password", "")
            cmd.add_wifi_credentials.CopyFrom(wifi_msg)

        else:
            raise ValueError(f"Unknown command type: {cmd_type}")

        return self.create_ble_message(cmd.SerializeToString())

    def parse_response(self, payload: bytes) -> Optional[dict]:
        """Parse a PendantAllMsg response."""
        if not PROTOBUF_AVAILABLE:
            return {"raw": payload.hex()}

        try:
            msg = pb.PendantAllMsg()
            msg.ParseFromString(payload)

            content_type = msg.WhichOneof("content")
            result = {"type": content_type}

            if content_type == "device_info":
                info = msg.device_info
                result.update({
                    "firmware_version": info.firmware_version,
                    "hardware_version": info.hardware_version,
                    "serial_number": info.serial_number,
                    "device_name": info.device_name,
                })

            elif content_type == "device_status":
                status = msg.device_status

                # Extract recording status from field 7 (DeviceRecordingStatus)
                # recording_state: 0=NOT_RECORDING, 1=RECORDING, 2=LISTENING
                is_recording = False
                if status.HasField('recording_status'):
                    is_recording = status.recording_status.recording_state == 1

                # Calculate storage percentage from field 5 (StorageState)
                storage_percent = 0
                if status.HasField('storage_state'):
                    total = status.storage_state.total_capture_pages
                    free = status.storage_state.free_capture_pages
                    if total > 0:
                        storage_percent = int((total - free) / total * 100)

                # Extract wifi status from field 1 (WifiStatus)
                wifi_connected = False
                if status.HasField('wifi_status'):
                    wifi_connected = status.wifi_status.connected

                result.update({
                    "is_recording": is_recording,
                    "storage_used_percent": storage_percent,
                    "wifi_connected": wifi_connected,
                })

            elif content_type == "storage_buffer":
                buf = msg.storage_buffer
                result.update({
                    "session": buf.session,
                    "run": buf.run,
                    "seq": buf.seq,
                    "index": buf.index,
                    "flash_page": buf.flash_page,
                    "error": buf.flash_page_error,
                })

            elif content_type == "battery_status":
                bat = msg.battery_status
                # state: 1=CHARGING, 2=DISCHARGING, 3=NOT_CHARGING, 4=FULL
                is_charging = bat.state in (1, 4)  # CHARGING or FULL
                result.update({
                    "level": bat.soc,  # State of Charge is the battery %
                    "charging": is_charging,
                    "voltage": bat.voltage,
                    "state": bat.state,
                })

            elif content_type == "set_current_time_response":
                result["success"] = msg.set_current_time_response.success

            elif content_type == "real_time_audio_data":
                result.update({
                    "data": msg.real_time_audio_data.data,
                    "seq": msg.real_time_audio_data.seq,
                })

            elif content_type == "button_status":
                result.update({
                    "pressed": msg.button_status.pressed,
                })

            # Extract response_data if present
            if msg.HasField("response_data"):
                result["request_id"] = msg.response_data.request_id
                result["response_success"] = msg.response_data.success

            return result

        except Exception as e:
            return {"type": "parse_error", "error": str(e), "raw": payload.hex()}

    def extract_audio_from_flash_page(self, data: bytes, private_key=None) -> tuple[bytes, bytes, bytes, int, dict]:
        """Extract audio data from FlashPage protobuf.

        Returns:
            tuple of (opus_data, pcm_data, encrypted_data, codec_type, page_info)
            codec_type: 0=unspecified, 1=opus, 2=pcm
            page_info: dict with timestamp metadata
        """
        opus_data = bytearray()
        pcm_data = bytearray()
        encrypted_data = bytearray()
        codec_type = 0
        page_info = {
            "absolute_timestamp_ms": 0,
            "boot_uptime_ms": 0,
            "chunks": []
        }

        if not PROTOBUF_AVAILABLE:
            return bytes(opus_data), bytes(pcm_data), bytes(encrypted_data), codec_type, page_info

        try:
            page = pb.FlashPage()
            page.ParseFromString(data)

            # Capture page-level timestamps
            page_info["absolute_timestamp_ms"] = page.absolute_timestamp_ms
            page_info["boot_uptime_ms"] = page.boot_uptime_ms

            if DEBUG_MODE:
                print(f"\n    FlashPage: ts={page.absolute_timestamp_ms}, uptime={page.boot_uptime_ms}, chunks={len(page.chunks)}")

            for i, chunk in enumerate(page.chunks):
                # Chunk is not a oneof - check if audio_data field is populated
                has_audio = chunk.HasField('audio_data') if hasattr(chunk, 'HasField') else bool(chunk.audio_data.ByteSize())

                if DEBUG_MODE:
                    fields = []
                    if chunk.time_offset_ms:
                        fields.append(f"t={chunk.time_offset_ms}ms")
                    if has_audio:
                        fields.append("audio")
                    if chunk.HasField('battery_status'):
                        fields.append(f"bat={chunk.battery_status.level}%")
                    if chunk.HasField('recording_status'):
                        fields.append(f"rec={chunk.recording_status.is_recording}")
                    print(f"      Chunk {i}: {', '.join(fields) if fields else 'empty'}")

                if has_audio:
                    audio = chunk.audio_data
                    codec_type = audio.codec_type

                    # Record chunk timing info
                    chunk_info = {
                        "time_offset_ms": chunk.time_offset_ms,
                        "audio_offset_bytes": len(opus_data),  # Offset into opus stream
                    }
                    page_info["chunks"].append(chunk_info)

                    # Extract ALL PCM fields
                    if audio.pcm_omni_mic_data:
                        if DEBUG_MODE:
                            print(f"        pcm_omni_mic: {len(audio.pcm_omni_mic_data)}B")
                        pcm_data.extend(audio.pcm_omni_mic_data)
                    if audio.pcm_directional_mic_data:
                        if DEBUG_MODE:
                            print(f"        pcm_directional_mic: {len(audio.pcm_directional_mic_data)}B")
                        pcm_data.extend(audio.pcm_directional_mic_data)
                    if audio.pcm_beamforming_data:
                        if DEBUG_MODE:
                            print(f"        pcm_beamforming: {len(audio.pcm_beamforming_data)}B")
                        pcm_data.extend(audio.pcm_beamforming_data)
                    if audio.pcm_manual_beamforming_data:
                        if DEBUG_MODE:
                            print(f"        pcm_manual_beamforming: {len(audio.pcm_manual_beamforming_data)}B")
                        pcm_data.extend(audio.pcm_manual_beamforming_data)

                    # Extract ALL codec/opus fields
                    if audio.codec_beamforming_data:
                        if DEBUG_MODE:
                            print(f"        codec_beamforming: {len(audio.codec_beamforming_data)}B")
                        opus_data.extend(audio.codec_beamforming_data)
                    if audio.codec_manual_beamforming_data:
                        if DEBUG_MODE:
                            print(f"        codec_manual_beamforming: {len(audio.codec_manual_beamforming_data)}B")
                        opus_data.extend(audio.codec_manual_beamforming_data)

                    # Handle encrypted data
                    if audio.HasField('encrypted_codec_beamforming_data'):
                        enc = audio.encrypted_codec_beamforming_data
                        if DEBUG_MODE:
                            print(f"        encrypted: ciphertext={len(enc.ciphertext)}B, nonce={len(enc.nonce)}B, tag={len(enc.tag)}B")

                        if private_key and enc.ciphertext:
                            # Try to decrypt
                            decrypted = self._decrypt_audio(enc, private_key)
                            if decrypted:
                                opus_data.extend(decrypted)
                            else:
                                encrypted_data.extend(enc.ciphertext)
                        else:
                            encrypted_data.extend(enc.ciphertext)

                    if DEBUG_MODE and audio.codec_type:
                        print(f"        codec_type: {audio.codec_type}, num_frames: {audio.num_frames}")

        except Exception as e:
            print(f"Failed to extract audio: {e}")
            import traceback
            traceback.print_exc()

        return bytes(opus_data), bytes(pcm_data), bytes(encrypted_data), codec_type, page_info

    def _decrypt_audio(self, encrypted, private_key) -> Optional[bytes]:
        """Decrypt encrypted audio data using our private key."""
        try:
            from nacl.public import SealedBox

            # The encryption likely uses crypto_box_seal (anonymous sender)
            # or crypto_box (authenticated sender)
            box = SealedBox(private_key)
            # Combine nonce + ciphertext + tag for NaCl format
            # Different crypto libs have different formats
            combined = encrypted.nonce + encrypted.ciphertext + encrypted.tag
            try:
                return box.decrypt(combined)
            except Exception:
                # Try without combining
                return box.decrypt(encrypted.ciphertext)
        except Exception as e:
            if DEBUG_MODE:
                print(f"        Decryption failed: {e}")
            return None


def load_private_key():
    """Load private key from keys directory if it exists."""
    key_file = KEYS_DIR / "private.key"
    if key_file.exists():
        try:
            from nacl.public import PrivateKey
            key_bytes = key_file.read_bytes()
            return PrivateKey(key_bytes)
        except Exception as e:
            print(f"Warning: Failed to load private key: {e}")
    return None


def generate_keypair():
    """Generate a new X25519 keypair for encryption."""
    try:
        from nacl.public import PrivateKey
    except ImportError:
        print("Error: pynacl not installed. Run: pip install pynacl")
        return None, None

    KEYS_DIR.mkdir(parents=True, exist_ok=True)

    private_key = PrivateKey.generate()
    public_key = private_key.public_key

    # Save keys
    private_file = KEYS_DIR / "private.key"
    public_file = KEYS_DIR / "public.key"

    private_file.write_bytes(bytes(private_key))
    public_file.write_bytes(bytes(public_key))

    # Make private key readable only by owner
    private_file.chmod(0o600)

    return private_file, public_file
