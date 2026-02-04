"""Tests for pendant.core.protocol module."""

import pytest


class TestPendantProtocol:
    """Tests for the PendantProtocol class."""

    def test_create_command_set_led(self, protocol):
        """Test creating a set_led command."""
        cmd = protocol.create_command("set_led", state=1)
        assert isinstance(cmd, bytes)
        assert len(cmd) > 0

    def test_create_command_set_led_brightness(self, protocol):
        """Test creating a set_led_brightness command."""
        cmd = protocol.create_command("set_led_brightness", brightness=50)
        assert isinstance(cmd, bytes)
        assert len(cmd) > 0

    def test_create_command_set_vad_threshold(self, protocol):
        """Test creating a set_vad_threshold command."""
        cmd = protocol.create_command("set_vad_threshold", threshold=0.5)
        assert isinstance(cmd, bytes)
        assert len(cmd) > 0

    def test_create_command_set_device_name(self, protocol):
        """Test creating a set_device_name command."""
        cmd = protocol.create_command("set_device_name", name="MyPendant")
        assert isinstance(cmd, bytes)
        assert len(cmd) > 0

    def test_create_command_add_wifi_credentials(self, protocol):
        """Test creating an add_wifi_credentials command."""
        cmd = protocol.create_command("add_wifi_credentials", ssid="TestNetwork", password="password123")
        assert isinstance(cmd, bytes)
        assert len(cmd) > 0

    def test_create_command_connect_to_wifi(self, protocol):
        """Test creating a connect_to_wifi command."""
        cmd = protocol.create_command("connect_to_wifi", ssid="TestNetwork")
        assert isinstance(cmd, bytes)
        assert len(cmd) > 0

    def test_create_command_disconnect_wifi(self, protocol):
        """Test creating a disconnect_wifi command."""
        cmd = protocol.create_command("disconnect_wifi")
        assert isinstance(cmd, bytes)
        assert len(cmd) > 0

    def test_create_command_unpair_bluetooth(self, protocol):
        """Test creating an unpair_bluetooth command."""
        cmd = protocol.create_command("unpair_bluetooth")
        assert isinstance(cmd, bytes)
        assert len(cmd) > 0

    def test_create_command_unknown_raises(self, protocol):
        """Test that unknown command types raise ValueError."""
        with pytest.raises(ValueError, match="Unknown command type"):
            protocol.create_command("unknown_command")

    def test_message_index_increments(self, protocol):
        """Test that message index increments with each command."""
        initial_index = protocol.message_index
        protocol.create_command("get_device_info")
        assert protocol.message_index == initial_index + 1
        protocol.create_command("get_device_status")
        assert protocol.message_index == initial_index + 2

    def test_parse_button_status_response(self, protocol, sample_button_status_response):
        """Test parsing a button_status response."""
        result = protocol.parse_response(sample_button_status_response)
        assert result is not None
        assert result["type"] == "button_status"
        assert result["pressed"] is True

    def test_parse_device_status_response(self, protocol, sample_device_status_response):
        """Test parsing a device_status response."""
        result = protocol.parse_response(sample_device_status_response)
        assert result is not None
        assert result["type"] == "device_status"
        assert result["is_recording"] is True
        assert result["storage_used_percent"] == 25  # (100-75)/100 * 100
        assert result["wifi_connected"] is True

    def test_extract_audio_from_flash_page(self, protocol, sample_flash_page_data):
        """Test extracting audio data from a flash page."""
        opus, pcm, encrypted, codec_type, page_info = protocol.extract_audio_from_flash_page(
            sample_flash_page_data
        )
        assert isinstance(opus, bytes)
        assert len(opus) == 100  # Our sample data
        assert codec_type == 1  # OPUS
        assert page_info["absolute_timestamp_ms"] == 1704067200000

    def test_ble_message_fragmentation_single(self, protocol):
        """Test BLE message parsing with single fragment."""
        from pendant.core.proto import pb, PROTOBUF_AVAILABLE
        
        if not PROTOBUF_AVAILABLE:
            pytest.skip("Protobuf not available")
        
        # Create a BLE message with single fragment
        msg = pb.BLEMessageFromPendantToNative()
        msg.index = 1
        msg.ble_fragment_seq = 0
        msg.num_fragments = 1
        msg.payload = b"test_payload"
        
        data = msg.SerializeToString()
        result = protocol.parse_ble_message(data)
        
        assert result == b"test_payload"


class TestExistingCommands:
    """Tests for existing commands to ensure no regressions."""

    def test_create_command_get_device_info(self, protocol):
        """Test creating a get_device_info command."""
        cmd = protocol.create_command("get_device_info")
        assert isinstance(cmd, bytes)
        assert len(cmd) > 0

    def test_create_command_get_device_status(self, protocol):
        """Test creating a get_device_status command."""
        cmd = protocol.create_command("get_device_status")
        assert isinstance(cmd, bytes)
        assert len(cmd) > 0

    def test_create_command_download_flash_pages(self, protocol):
        """Test creating a download_flash_pages command."""
        cmd = protocol.create_command("download_flash_pages", batch=True, realtime=False)
        assert isinstance(cmd, bytes)
        assert len(cmd) > 0

    def test_create_command_set_current_time(self, protocol):
        """Test creating a set_current_time command."""
        cmd = protocol.create_command("set_current_time", timestamp_ms=1704067200000)
        assert isinstance(cmd, bytes)
        assert len(cmd) > 0

    def test_create_command_start_recording(self, protocol):
        """Test creating a start_recording command."""
        cmd = protocol.create_command("start_recording")
        assert isinstance(cmd, bytes)
        assert len(cmd) > 0

    def test_create_command_stop_recording(self, protocol):
        """Test creating a stop_recording command."""
        cmd = protocol.create_command("stop_recording")
        assert isinstance(cmd, bytes)
        assert len(cmd) > 0

    def test_create_command_clear_storage(self, protocol):
        """Test creating a clear_storage command."""
        cmd = protocol.create_command("clear_storage")
        assert isinstance(cmd, bytes)
        assert len(cmd) > 0

    def test_create_command_factory_reset(self, protocol):
        """Test creating a factory_reset command."""
        cmd = protocol.create_command("factory_reset")
        assert isinstance(cmd, bytes)
        assert len(cmd) > 0

    def test_create_command_set_ble_pair(self, protocol):
        """Test creating a set_ble_pair command."""
        cmd = protocol.create_command("set_ble_pair", enable=True)
        assert isinstance(cmd, bytes)
        assert len(cmd) > 0

    def test_create_command_set_server_public_key(self, protocol):
        """Test creating a set_server_public_key command."""
        fake_key = b'\x00' * 32
        cmd = protocol.create_command("set_server_public_key", public_key=fake_key)
        assert isinstance(cmd, bytes)
        assert len(cmd) > 0
