"""Pytest fixtures for pendant tests."""

import pytest
import sys
import os

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'proto'))


@pytest.fixture
def mock_protobuf_available(monkeypatch):
    """Mock protobuf as available."""
    from pendant.core import proto
    monkeypatch.setattr(proto, 'PROTOBUF_AVAILABLE', True)


@pytest.fixture
def protocol():
    """Create a PendantProtocol instance."""
    from pendant.core.protocol import PendantProtocol
    return PendantProtocol()


@pytest.fixture
def sample_flash_page_data():
    """Sample FlashPage protobuf data for testing."""
    # This is a minimal valid FlashPage with one audio chunk
    # Created by serializing a FlashPage proto with sample data
    from pendant.core.proto import pb, PROTOBUF_AVAILABLE
    
    if not PROTOBUF_AVAILABLE:
        pytest.skip("Protobuf not available")
    
    page = pb.FlashPage()
    page.absolute_timestamp_ms = 1704067200000  # Jan 1, 2024
    page.boot_uptime_ms = 60000  # 1 minute uptime
    
    chunk = page.chunks.add()
    chunk.time_offset_ms = 0
    chunk.audio_data.codec_beamforming_data = b'\x00' * 100  # Fake opus data
    chunk.audio_data.codec_type = 1  # OPUS
    chunk.audio_data.num_frames = 1
    
    return page.SerializeToString()


@pytest.fixture
def sample_button_status_response():
    """Sample ButtonStatus response for testing."""
    from pendant.core.proto import pb, PROTOBUF_AVAILABLE
    
    if not PROTOBUF_AVAILABLE:
        pytest.skip("Protobuf not available")
    
    msg = pb.PendantAllMsg()
    msg.button_status.pressed = True
    return msg.SerializeToString()


@pytest.fixture
def sample_device_status_response():
    """Sample DeviceStatus response for testing."""
    from pendant.core.proto import pb, PROTOBUF_AVAILABLE
    
    if not PROTOBUF_AVAILABLE:
        pytest.skip("Protobuf not available")
    
    # Build nested messages separately and copy them
    storage = pb.StorageState()
    storage.total_capture_pages = 100
    storage.free_capture_pages = 75
    
    recording = pb.DeviceRecordingStatus()
    recording.recording_state = 1  # RECORDING
    
    wifi = pb.WifiStatus()
    wifi.connected = True
    
    status = pb.DeviceStatus()
    status.storage_state.CopyFrom(storage)
    status.recording_status.CopyFrom(recording)
    status.wifi_status.CopyFrom(wifi)
    
    msg = pb.PendantAllMsg()
    msg.device_status.CopyFrom(status)
    return msg.SerializeToString()
