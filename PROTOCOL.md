# Limitless Pendant BLE Protocol Documentation

This document describes the Bluetooth Low Energy (BLE) protocol used by the Limitless Pendant
device, reverse-engineered from the Limitless Android app (v2.1.6) and verified through testing.

## Overview

The Pendant uses **Google Protocol Buffers** for all communication over BLE. Messages are
fragmented to fit within BLE packet size limits and wrapped in a BLE message envelope.

**IMPORTANT: Bluetooth Bonding Required**

The Pendant will NOT respond to any commands until it is properly bonded. The Android app
uses `createBond()` during connection, and the device checks bonding state before processing
commands. You must:

1. Pair the device: `bluetoothctl pair $PENDANT_ADDRESS`
2. Trust the device: `bluetoothctl trust $PENDANT_ADDRESS`
3. Connect: `bluetoothctl connect $PENDANT_ADDRESS`

The device uses "Just Works" pairing (NoInputNoOutput capability).

---

## BLE Characteristics

| UUID | Name | Direction | Properties |
|------|------|-----------|------------|
| `632de001-604c-446b-a80f-7963e950f3fb` | Audio Service | - | Service UUID |
| `632de002-604c-446b-a80f-7963e950f3fb` | Control | Phone → Pendant | Write, Write-No-Response |
| `632de003-604c-446b-a80f-7963e950f3fb` | Data | Pendant → Phone | Notify |
| `8d53dc1d-1db7-4cd3-868b-8a527460aa84` | Data Channel Service | - | Service UUID |
| `da2e7828-fbce-4e01-ae9e-261174997c48` | Bidirectional | Both | Write-No-Response, Notify |

---

## Message Framing

All messages are wrapped in a BLE envelope that handles fragmentation:

```protobuf
// Phone → Pendant
message BLEMessageFromNativeToPendant {
  int32 index = 1;           // Message index (incrementing)
  int32 ble_fragment_seq = 2; // Fragment sequence number (0-based)
  int32 num_fragments = 3;    // Total number of fragments
  bytes payload = 4;          // Protobuf payload (fragment)
}

// Pendant → Phone
message BLEMessageFromPendantToNative {
  int32 index = 1;           // Message index
  int32 ble_fragment_seq = 2; // Fragment sequence number
  int32 num_fragments = 3;    // Total number of fragments
  bytes payload = 4;          // Protobuf payload (fragment)
}
```

### Fragmentation Logic
1. Serialize the inner protobuf message
2. If message fits in one BLE packet: `num_fragments=1`, `ble_fragment_seq=0`
3. If larger: split payload across fragments, increment `ble_fragment_seq` for each
4. Receiver reassembles fragments by concatenating payloads in order

---

## Flash Page Structure (IMPORTANT)

**The Chunk message is NOT a oneof** - this was a critical discovery during reverse engineering.
The Android app's protobuf defines Chunk with 13 independent optional fields:

```protobuf
message FlashPage {
  int64 absolute_timestamp_ms = 1;  // Recording timestamp (ms since epoch)
  int64 boot_uptime_ms = 2;         // Device uptime when recorded
  repeated Chunk chunks = 3;         // Multiple chunks per page
}

// IMPORTANT: NOT a oneof - all fields are optional and can coexist
message Chunk {
  int32 time_offset_ms = 1;           // Offset from page timestamp
  PendantAudioData audio_data = 2;    // Audio data (field 2, NOT 1!)
  ButtonStatus button_status = 3;
  WifiStatus wifi_status = 4;
  BleStatus ble_status = 5;
  BatteryStatus battery_status = 6;
  UsbStatus usb_status = 7;
  ImuData imu_data = 8;
  RecordingStatus recording_status = 9;
  LogOutput log_output = 10;
  RuntimeStatus runtime_status = 11;
  StorageStatus storage_status = 12;
  CpuStatus cpu_status = 13;
}
```

Each chunk contains a `time_offset_ms` indicating when it was recorded relative to the
page's `absolute_timestamp_ms`. Multiple status types can be present in the same chunk.

---

## Audio Data Format

```protobuf
message PendantAudioData {
  bytes pcm_omni_mic_data = 1;           // Raw PCM from omni mic
  bytes pcm_directional_mic_data = 2;    // Raw PCM from directional mic
  bytes pcm_beamforming_data = 3;        // Beamformed PCM
  bytes codec_beamforming_data = 4;      // Opus-encoded beamformed audio (MOST COMMON)
  bytes codec_manual_beamforming_data = 5;
  bytes reserved_1 = 6;
  bytes pcm_manual_beamforming_data = 7;
  bool did_start_recording = 8;
  bool did_stop_recording = 9;
  CodecType codec_type = 10;             // 1=OPUS, 2=PCM
  int32 num_frames = 11;                 // Number of audio frames
  int32 degree_of_arrival = 12;          // Sound direction (degrees)
  EncryptedBytes encrypted_codec_beamforming_data = 13;  // Encrypted audio
}
```

### Audio Encoding Details (Verified)

| Property | Value |
|----------|-------|
| Codec | Opus |
| Sample Rate | 16000 Hz |
| Channels | Mono |
| Bit Depth | 16-bit |
| Frame Size | ~960 samples (60ms) |
| Format | Raw concatenated Opus frames (no Ogg container) |

**Important**: The `codec_beamforming_data` field contains raw Opus frames concatenated
together WITHOUT an Ogg container or frame length headers. Each frame is typically 20-120
bytes. You must use an Opus decoder that can handle raw frames.

---

## Audio Encryption

The device supports optional audio encryption using **X25519 key exchange** with
**ChaCha20-Poly1305** (or similar AEAD cipher).

### Encryption Structure
```protobuf
message EncryptedBytes {
  bytes ciphertext = 1;    // Encrypted audio data
  bytes nonce = 2;         // Initialization vector (12 or 24 bytes)
  bytes tag = 3;           // Authentication tag (16 bytes)
}
```

### Key Injection

You can inject your own public key to decrypt future recordings:

1. Generate X25519 keypair: `python pendant_client.py keygen`
2. Send public key to device: `python pendant_client.py setkey`
3. New recordings will be encrypted with your key
4. Download will auto-decrypt: `python pendant_client.py download`

**Note**: Existing recordings encrypted with Limitless's server key cannot be decrypted
without their private key.

### SetServerPublicKey Command
```protobuf
message SetServerPublicKey {
  bytes public_key = 1;   // 32-byte X25519 public key
}
```

---

## Commands (Phone → Pendant)

Commands are sent as `ServerCommandMsg` protobuf:

### Verified Working Commands

| Field | Command | Description |
|-------|---------|-------------|
| 6 | SetCurrentTime | Sync device clock (timestamp_ms) |
| 8 | DownloadFlashPages | Download stored recordings |
| 14 | GetDeviceInfo | Get firmware/hardware info |
| 21 | GetDeviceStatus | Get recording state, storage % |
| 28 | SetServerPublicKey | Set encryption public key |

### DownloadFlashPages
```protobuf
message DownloadFlashPages {
  bool batch_mode_enabled = 1;      // Download stored recordings
  bool real_time_mode_enabled = 2;  // Stream real-time audio
}
```

---

## Responses (Pendant → Phone)

### PendantAllMsg Fields
| Field | Type | Description |
|-------|------|-------------|
| 1 | DeviceInfoMsg | Firmware, hardware, serial |
| 2 | StorageBufferMsg | Audio data pages |
| 3 | SetCurrentTimeResponse | Time sync confirmation |
| 5 | DeviceStatus | Recording state, storage % |
| 7 | BatteryStatus | Battery level, charging state |
| 8 | ButtonStatus | Button press events |

### StorageBufferMsg
```protobuf
message StorageBufferMsg {
  IngestType ingest_type = 1;   // 1=AUDIO, 2=LOG, 3=IMU
  int32 session = 2;            // Recording session ID
  int32 run = 3;                // Run number within session
  int64 seq = 4;                // Sequence number
  int32 index = 5;              // Page index
  bytes flash_page = 6;         // Serialized FlashPage protobuf
  FlashPageError flash_page_error = 7;
}
```

---

## Typical Download Flow

```
Phone                               Pendant
  |                                    |
  |-- SetCurrentTime ----------------->|
  |<- SetCurrentTimeResponse ----------|
  |                                    |
  |-- DownloadFlashPages ------------->|
  |   (batch_mode_enabled=true)        |
  |<- StorageBufferMsg (page 0) -------|
  |<- StorageBufferMsg (page 1) -------|
  |<- DeviceStatus --------------------|  (periodic)
  |<- BatteryStatus -------------------|  (periodic)
  |<- StorageBufferMsg (page 2) -------|
  |   ... (continues until done)       |
  |                                    |
```

Pages are sent continuously. The device also sends periodic `DeviceStatus` and
`BatteryStatus` messages during download.

---

## Implementation Notes

### Linux/BlueZ

1. **Use bluetoothctl for pairing** - bleak's pairing doesn't work well with this device
2. **Use D-Bus for communication** if device is already connected via system Bluetooth
3. **D-Bus path format**: `/org/bluez/hci0/dev_CB_DF_0B_0A_E2_13`
4. **Enable notifications** via `StartNotify()` D-Bus method

### Audio Decoding

The opus data requires special handling:
1. Data is raw Opus frames without Ogg container
2. Use `opuslib` Python library for decoding
3. Try frame sizes from 20-500 bytes to find boundaries
4. Sample rate: 16000 Hz, Mono, 16-bit

Example decode command:
```bash
python decode_opus.py pendant_audio.opus output.wav
```

### Known Issues

1. **StartRecording/StopRecording** - May not work via BLE (button-only)
2. **Some chunks have no audio** - Contain only status/timing data

**Fixed:** Battery level now reads from standard BLE Battery Service (reliable)

---

## Files Reference

### Python Scripts
- `pendant_client.py` - Main client (status, download, encryption)
- `pendant_connect.py` - Bluetooth pairing utility
- `pendant_scan.py` - BLE device scanner
- `pendant_explore.py` - GATT service explorer
- `decode_opus.py` - Raw Opus to WAV converter

### Protocol Definitions
- `proto/pendant.proto` - Protobuf definitions
- `proto/pendant_pb2.py` - Generated Python code

### Decompiled Source
- `limitless_source/sources/ai/limitless/pendant/flash_page/FlashPageProto$*.java`
- `limitless_source/sources/ai/limitless/pendant/server/ServerProto$*.java`
- `limitless_source/sources/ai/limitless/mobile/bluetooth/C5905h.java`

---

## Device Info

- **Device Name**: Pendant
- **MAC Address**: Set via `PENDANT_ADDRESS` env var
- **App Version**: Limitless v2.1.6
- **Audio Codec**: Opus @ 16kHz mono
- **Encryption**: X25519 + ChaCha20-Poly1305 (optional)
