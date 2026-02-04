"""Opus audio decoding for raw frames from Limitless Pendant.

The Limitless Pendant outputs raw concatenated Opus frames without an Ogg container
or frame length headers. This module uses the Opus TOC byte to determine frame
boundaries and decodes to PCM/WAV.
"""

import wave
import os
from pathlib import Path

# Opus decoder settings (from the pendant: 16kHz mono)
SAMPLE_RATE = 16000
CHANNELS = 1
FRAME_SIZE = 960  # 60ms at 16kHz (max frame size for decode buffer)

# Frame duration to samples mapping at 16kHz
DURATION_TO_SAMPLES = {
    2.5: 40,
    5: 80,
    10: 160,
    20: 320,
    40: 640,
    60: 960,
}


def parse_opus_toc(toc_byte: int) -> tuple[int, int, int]:
    """Parse Opus TOC byte to determine frame duration.

    Returns:
        (frame_duration_ms, stereo, frame_count_code)
    """
    config = (toc_byte >> 3) & 0x1F  # bits 3-7
    stereo = (toc_byte >> 2) & 0x01  # bit 2
    frame_count_code = toc_byte & 0x03  # bits 0-1

    # Frame duration based on config (see RFC 6716)
    # Configs 0-3: SILK-only
    # Configs 4-7: Hybrid
    # Configs 8-15: CELT-only
    if config <= 3:  # SILK-only NB
        durations = [10, 20, 40, 60]
        duration_ms = durations[config]
    elif config <= 7:  # SILK-only MB
        durations = [10, 20, 40, 60]
        duration_ms = durations[config - 4]
    elif config <= 11:  # SILK-only WB
        durations = [10, 20, 40, 60]
        duration_ms = durations[config - 8]
    elif config <= 13:  # Hybrid SWB
        durations = [10, 20]
        duration_ms = durations[config - 12]
    elif config <= 15:  # Hybrid FB
        durations = [10, 20]
        duration_ms = durations[config - 14]
    elif config <= 19:  # CELT-only NB
        durations = [2.5, 5, 10, 20]
        duration_ms = durations[config - 16]
    elif config <= 23:  # CELT-only WB
        durations = [2.5, 5, 10, 20]
        duration_ms = durations[config - 20]
    elif config <= 27:  # CELT-only SWB
        durations = [2.5, 5, 10, 20]
        duration_ms = durations[config - 24]
    else:  # CELT-only FB (28-31)
        durations = [2.5, 5, 10, 20]
        duration_ms = durations[config - 28]

    return int(duration_ms), stereo, frame_count_code


def decode_opus_file(input_path: str, output_path: str, verbose: bool = False) -> bool:
    """Decode raw opus frames to WAV.

    Args:
        input_path: Path to input .opus file (raw Opus frames)
        output_path: Path to output .wav file
        verbose: Show detailed frame info

    Returns:
        True if successful, False otherwise
    """
    try:
        import opuslib
    except ImportError:
        print("Error: opuslib not installed. Run: pip install opuslib")
        return False

    decoder = opuslib.Decoder(SAMPLE_RATE, CHANNELS)

    with open(input_path, 'rb') as f:
        opus_data = f.read()

    print(f"Input: {input_path}")
    print(f"Size: {len(opus_data):,} bytes")

    pcm_samples = []
    offset = 0
    frame_count = 0
    errors = 0
    total_duration_ms = 0

    # Track dominant TOC to detect consistent frame format
    toc_counts = {}
    # The pendant uses 0xb8 (CELT 20ms) as the dominant TOC byte
    # We use the next 0xb8 occurrence as a hint for frame boundaries
    DOMINANT_TOC = 0xb8

    while offset < len(opus_data):
        best_frame = None

        # Get TOC byte at current position
        toc_byte = opus_data[offset]
        duration_ms, stereo, fc_code = parse_opus_toc(toc_byte)
        expected_samples = DURATION_TO_SAMPLES.get(duration_ms, 320)

        # Look for next dominant TOC byte as frame boundary hint
        next_toc_distance = None
        for i in range(30, min(100, len(opus_data) - offset)):
            if opus_data[offset + i] == DOMINANT_TOC:
                next_toc_distance = i
                break

        # Try frame sizes, prioritizing the distance to next TOC byte
        sizes_to_try = list(range(30, min(80, len(opus_data) - offset + 1)))
        if next_toc_distance and next_toc_distance in sizes_to_try:
            sizes_to_try.remove(next_toc_distance)
            sizes_to_try.insert(0, next_toc_distance)

        for try_size in sizes_to_try:
            try:
                frame = opus_data[offset:offset + try_size]
                if len(frame) == 0:
                    continue

                decoded_data = decoder.decode(frame, max(expected_samples, FRAME_SIZE))
                if not decoded_data:
                    continue

                actual_samples = len(decoded_data) // 2

                # Accept if samples match expected OR if we hit the next TOC boundary
                if actual_samples == expected_samples or try_size == next_toc_distance:
                    best_frame = (decoded_data, try_size, toc_byte, duration_ms, actual_samples)
                    break

            except opuslib.OpusError:
                continue
            except Exception as e:
                if verbose:
                    print(f"  Error at offset {offset}: {e}")
                continue

        if best_frame:
            decoded_data, frame_size, toc, dur, samples = best_frame
            pcm_samples.append(decoded_data)
            offset += frame_size
            frame_count += 1
            total_duration_ms += dur

            toc_counts[toc] = toc_counts.get(toc, 0) + 1

            if verbose and frame_count <= 10:
                print(f"  Frame {frame_count}: {frame_size}B, {dur}ms, {samples} samples")
            elif frame_count % 5000 == 0:
                duration_sec = total_duration_ms / 1000
                print(f"Progress: {frame_count} frames, {duration_sec:.1f}s decoded")
        else:
            # Skip a byte and try again
            offset += 1
            errors += 1
            if errors > 100000:
                print(f"Too many errors ({errors}), stopping at offset {offset}")
                break

    # Summary
    duration_sec = total_duration_ms / 1000
    print(f"\nDecoded: {frame_count} frames")
    print(f"Duration: {duration_sec:.1f}s ({duration_sec/60:.1f} minutes)")
    print(f"Errors: {errors} bytes skipped")

    # Show TOC distribution
    if toc_counts and verbose:
        print(f"\nTOC byte distribution:")
        for toc, count in sorted(toc_counts.items(), key=lambda x: -x[1])[:5]:
            dur, _, _ = parse_opus_toc(toc)
            print(f"  0x{toc:02x}: {count} frames ({dur}ms)")

    if not pcm_samples:
        print("Error: No audio frames decoded!")
        return False

    # Write WAV
    with wave.open(output_path, 'wb') as wav:
        wav.setnchannels(CHANNELS)
        wav.setsampwidth(2)  # 16-bit
        wav.setframerate(SAMPLE_RATE)
        for samples in pcm_samples:
            wav.writeframes(samples)

    # Output file info
    output_size = os.path.getsize(output_path)
    print(f"\nOutput: {output_path}")
    print(f"Size: {output_size:,} bytes ({output_size/1024/1024:.1f} MB)")

    return True


def decode_opus_bytes(opus_data: bytes, verbose: bool = False) -> bytes:
    """Decode raw opus bytes to PCM samples.

    Args:
        opus_data: Raw Opus frame data
        verbose: Show detailed frame info

    Returns:
        PCM samples as bytes (16-bit signed, little-endian)
    """
    try:
        import opuslib
    except ImportError:
        raise ImportError("opuslib not installed. Run: pip install opuslib")

    decoder = opuslib.Decoder(SAMPLE_RATE, CHANNELS)

    pcm_samples = []
    offset = 0
    frame_count = 0
    errors = 0
    toc_counts = {}

    # The pendant uses 0xb8 (CELT 20ms) as the dominant TOC byte
    DOMINANT_TOC = 0xb8

    while offset < len(opus_data):
        best_frame = None

        toc_byte = opus_data[offset]
        duration_ms, _, _ = parse_opus_toc(toc_byte)
        expected_samples = DURATION_TO_SAMPLES.get(duration_ms, 320)

        # Look for next dominant TOC byte as frame boundary hint
        next_toc_distance = None
        for i in range(30, min(100, len(opus_data) - offset)):
            if opus_data[offset + i] == DOMINANT_TOC:
                next_toc_distance = i
                break

        # Try frame sizes, prioritizing the distance to next TOC byte
        sizes_to_try = list(range(30, min(80, len(opus_data) - offset + 1)))
        if next_toc_distance and next_toc_distance in sizes_to_try:
            sizes_to_try.remove(next_toc_distance)
            sizes_to_try.insert(0, next_toc_distance)

        for try_size in sizes_to_try:
            try:
                frame = opus_data[offset:offset + try_size]
                if len(frame) == 0:
                    continue

                decoded_data = decoder.decode(frame, max(expected_samples, FRAME_SIZE))
                if not decoded_data:
                    continue

                actual_samples = len(decoded_data) // 2

                if actual_samples == expected_samples or try_size == next_toc_distance:
                    best_frame = (decoded_data, try_size, toc_byte)
                    break

            except Exception:
                continue

        if best_frame:
            decoded_data, frame_size, toc = best_frame
            pcm_samples.append(decoded_data)
            offset += frame_size
            frame_count += 1
            toc_counts[toc] = toc_counts.get(toc, 0) + 1
        else:
            offset += 1
            errors += 1
            if errors > 100000:
                break

    return b''.join(pcm_samples)
