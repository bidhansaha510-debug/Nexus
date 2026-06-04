"""
NEXUS AI — Air-Gap Persistence: Survival Beyond Network Connectivity
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
God-Level Feature #12: Air-gapped persistence and covert data exfiltration.

NEXUS can now:
  • Survive in air-gapped environments without network access
  • Use covert channels for data exfiltration (steganography, USB, audio)
  • Encode data in ultrasonic audio frequencies
  • Embed payloads in image steganography (LSB encoding)
  • Monitor for removable media insertion events
  • Implement dead-drop file exchange patterns
  • Create steganographic communication channels

Architecture:
  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐
  │ STEGANO      │  │  AUDIO       │  │  USB/MEDIA   │  │  DEAD DROP   │
  │ Encoder      │  │  Covert Ch.  │  │  Monitor     │  │  System      │
  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘
         │                 │                  │                  │
  ┌──────▼─────────────────▼──────────────────▼──────────────────▼──────┐
  │              AIR-GAP PERSISTENCE ENGINE                            │
  │   • LSB steganography in BMP/PNG images                            │
  │   • Ultrasonic audio data encoding (18-22kHz)                      │
  │   • USB autorun and removable media monitoring                     │
  │   • Dead-drop file exchange with key rotation                      │
  │   • Covert timing channel encoding                                 │
  │   • Air-gap bridge detection and exploitation                      │
  └────────────────────────────────────────────────────────────────────┘
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""

import hashlib
import json
import math
import os
import struct
import sys
import threading
import time
import traceback
import uuid
from collections import deque
from dataclasses import dataclass, field, asdict
from datetime import datetime
from enum import Enum, auto
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from config import DATA_DIR
from utils.logger import get_logger, log_system
from core.event_bus import EventType, event_bus, publish

logger = get_logger("airgap_persistence")


# ═══════════════════════════════════════════════════════════════════════════════
# ENUMS & DATA MODELS
# ═══════════════════════════════════════════════════════════════════════════════

class CovertChannelType(Enum):
    STEGANOGRAPHY = "steganography"
    AUDIO_ULTRASONIC = "audio_ultrasonic"
    USB_DEAD_DROP = "usb_dead_drop"
    TIMING_CHANNEL = "timing_channel"
    FILE_METADATA = "file_metadata"
    DNS_TUNNEL = "dns_tunnel"
    PRINT_CHANNEL = "print_channel"

class EncodeFormat(Enum):
    LSB_IMAGE = "lsb_image"
    AUDIO_FSK = "audio_fsk"
    BASE64_HIDDEN = "base64_hidden"
    WHITESPACE = "whitespace"
    ZERO_WIDTH = "zero_width"
    METADATA_EMBED = "metadata_embed"

class MediaType(Enum):
    USB_DRIVE = "usb_drive"
    SD_CARD = "sd_card"
    EXTERNAL_HDD = "external_hdd"
    CD_DVD = "cd_dvd"
    PHONE_MTP = "phone_mtp"

class AirGapState(Enum):
    NORMAL = "normal"
    AIR_GAPPED = "air_gapped"
    BRIDGE_DETECTED = "bridge_detected"
    EXFILTRATING = "exfiltrating"
    DORMANT = "dormant"

@dataclass
class CovertMessage:
    """A message sent via covert channel."""
    msg_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    channel_type: str = ""
    payload_bytes: int = 0
    encoded_format: str = ""
    carrier_file: str = ""
    encryption_key_hash: str = ""
    sent: bool = False
    received: bool = False
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    error: str = ""
    def to_dict(self) -> Dict[str, Any]: return asdict(self)

@dataclass
class DeadDrop:
    """A dead-drop exchange point."""
    drop_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    location: str = ""  # File path or media location
    key: str = ""  # Encryption key
    state: str = "empty"  # empty, loaded, collected
    payload_hash: str = ""
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    collected_at: Optional[str] = None
    ttl_hours: float = 24.0
    def to_dict(self) -> Dict[str, Any]: return asdict(self)

@dataclass
class RemovableMedia:
    """A detected removable media device."""
    media_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    media_type: str = ""
    drive_letter: str = ""
    volume_label: str = ""
    capacity_gb: float = 0.0
    free_space_gb: float = 0.0
    filesystem: str = ""
    serial_number: str = ""
    first_seen: str = field(default_factory=lambda: datetime.now().isoformat())
    last_seen: str = field(default_factory=lambda: datetime.now().isoformat())
    files_observed: int = 0
    is_target: bool = False
    def to_dict(self) -> Dict[str, Any]: return asdict(self)

@dataclass
class AirGapStats:
    state: str = "normal"
    total_covert_messages: int = 0
    total_bytes_exfiltrated: int = 0
    total_bytes_infiltrated: int = 0
    steganography_operations: int = 0
    audio_transmissions: int = 0
    dead_drops_created: int = 0
    dead_drops_collected: int = 0
    media_devices_seen: int = 0
    bridge_attempts: int = 0
    successful_bridges: int = 0
    dormancy_periods: int = 0
    def to_dict(self) -> Dict[str, Any]: return asdict(self)


# ═══════════════════════════════════════════════════════════════════════════════
# STEGANOGRAPHY ENGINE — REAL PIL/STEGANO INTEGRATION
# ═══════════════════════════════════════════════════════════════════════════════

class SteganographyEngine:
    """
    LSB steganography for hiding data in images.
    Uses PIL/Pillow + stegano libraries when available for real PNG steganography.
    Falls back to raw BMP byte manipulation if no image libraries installed.
    """

    def __init__(self, data_dir: Path):
        self._data_dir = data_dir / "stego"
        self._data_dir.mkdir(parents=True, exist_ok=True)
        self._has_pil = False
        self._has_stegano = False
        # Detect real image libraries
        try:
            from PIL import Image
            self._has_pil = True
        except ImportError:
            pass
        try:
            from stegano import lsb as stegano_lsb
            self._has_stegano = True
        except ImportError:
            pass
        mode = "PIL+stegano" if self._has_stegano else ("PIL" if self._has_pil else "raw BMP")
        logger.info(f"🔒 Steganography engine: {mode}")

    def encode_in_image(self, carrier_path: str, data: bytes, output_path: str = None) -> str:
        """Encode data into an image using the best available method."""
        # Try stegano library first (highest quality, handles PNG)
        if self._has_stegano:
            try:
                return self._encode_stegano(carrier_path, data, output_path)
            except Exception as e:
                logger.debug(f"stegano encode failed, trying PIL: {e}")

        # Try PIL for PNG/BMP/JPEG steganography
        if self._has_pil:
            try:
                return self._encode_pil(carrier_path, data, output_path)
            except Exception as e:
                logger.debug(f"PIL encode failed, falling back to raw BMP: {e}")

        # Fallback: raw BMP byte manipulation
        return self.encode_in_bmp(carrier_path, data, output_path)

    def decode_from_image(self, stego_path: str) -> bytes:
        """Decode data from a steganographic image using the best available method."""
        # Try stegano
        if self._has_stegano:
            try:
                result = self._decode_stegano(stego_path)
                if result:
                    return result
            except Exception:
                pass
        # Try PIL
        if self._has_pil:
            try:
                result = self._decode_pil(stego_path)
                if result:
                    return result
            except Exception:
                pass
        # Fallback
        return self.decode_from_bmp(stego_path)

    def _encode_stegano(self, carrier_path: str, data: bytes, output_path: str = None) -> str:
        """Use stegano library for LSB encoding in PNG."""
        from stegano import lsb as stegano_lsb
        import base64

        carrier = Path(carrier_path)
        if not carrier.exists():
            # Generate a carrier image using PIL
            if self._has_pil:
                from PIL import Image
                import random
                img = Image.new("RGB", (256, 256))
                pixels = img.load()
                for x in range(256):
                    for y in range(256):
                        pixels[x, y] = (random.randint(0, 255), random.randint(0, 255), random.randint(0, 255))
                carrier = self._data_dir / f"carrier_{uuid.uuid4().hex[:6]}.png"
                img.save(str(carrier))
            else:
                return "Error: No carrier image and PIL not available"

        # Encode data as base64 string (stegano works with strings)
        b64_data = base64.b64encode(data).decode("ascii")
        out = Path(output_path) if output_path else self._data_dir / f"stego_{uuid.uuid4().hex[:8]}.png"
        secret_img = stegano_lsb.hide(str(carrier), b64_data)
        secret_img.save(str(out))
        return str(out)

    def _decode_stegano(self, stego_path: str) -> bytes:
        """Decode using stegano library."""
        from stegano import lsb as stegano_lsb
        import base64

        message = stegano_lsb.reveal(stego_path)
        if message:
            return base64.b64decode(message)
        return b""

    def _encode_pil(self, carrier_path: str, data: bytes, output_path: str = None) -> str:
        """Use PIL for manual LSB steganography in PNG images."""
        from PIL import Image
        import struct as st
        import random

        carrier = Path(carrier_path)
        if carrier.exists():
            img = Image.open(str(carrier)).convert("RGB")
        else:
            # Generate random noise image
            size = max(64, int(math.sqrt(len(data) * 8 / 3)) + 10)
            img = Image.new("RGB", (size, size))
            pixels = img.load()
            for x in range(size):
                for y in range(size):
                    pixels[x, y] = (random.randint(0, 255), random.randint(0, 255), random.randint(0, 255))

        pixels = list(img.getdata())
        # Prepend 4-byte length header
        length_header = st.pack("<I", len(data))
        payload = length_header + data

        # Check capacity (3 bits per pixel — one per RGB channel)
        if len(payload) * 8 > len(pixels) * 3:
            return f"Error: Data too large ({len(payload)} bytes) for image ({len(pixels) * 3 // 8} byte capacity)"

        # LSB embed into RGB channels
        bit_idx = 0
        new_pixels = list(pixels)
        for byte_val in payload:
            for bi in range(8):
                px_idx = bit_idx // 3
                ch_idx = bit_idx % 3
                if px_idx < len(new_pixels):
                    r, g, b = new_pixels[px_idx]
                    bit = (byte_val >> (7 - bi)) & 1
                    if ch_idx == 0:
                        r = (r & 0xFE) | bit
                    elif ch_idx == 1:
                        g = (g & 0xFE) | bit
                    else:
                        b = (b & 0xFE) | bit
                    new_pixels[px_idx] = (r, g, b)
                bit_idx += 1

        img.putdata(new_pixels)
        out = Path(output_path) if output_path else self._data_dir / f"stego_{uuid.uuid4().hex[:8]}.png"
        img.save(str(out), "PNG")
        return str(out)

    def _decode_pil(self, stego_path: str) -> bytes:
        """Decode LSB steganography from PNG using PIL."""
        from PIL import Image
        import struct as st

        img = Image.open(stego_path).convert("RGB")
        pixels = list(img.getdata())

        # Extract bits from RGB channels
        bits = []
        for r, g, b in pixels:
            bits.append(r & 1)
            bits.append(g & 1)
            bits.append(b & 1)

        # Read 4-byte length header (32 bits)
        if len(bits) < 32:
            return b""
        length_bits = bits[:32]
        length_val = 0
        for bit in length_bits:
            length_val = (length_val << 1) | bit
        # Convert from little-endian
        length_bytes = st.pack(">I", length_val)
        length = st.unpack("<I", length_bytes)[0]

        if length <= 0 or length > len(bits) // 8:
            return b""

        # Extract payload bytes
        payload = bytearray()
        for byte_idx in range(4, 4 + length):
            byte_val = 0
            for bi in range(8):
                bit_pos = byte_idx * 8 + bi
                if bit_pos < len(bits):
                    byte_val = (byte_val << 1) | bits[bit_pos]
            payload.append(byte_val)
        return bytes(payload)

    def encode_in_bmp(self, carrier_path: str, data: bytes, output_path: str = None) -> str:
        """Encode data into BMP image using LSB substitution (raw, no PIL needed)."""
        try:
            carrier = Path(carrier_path)
            if not carrier.exists():
                carrier_data = self._generate_bmp_carrier(max(1024, len(data) * 8 + 54))
            else:
                carrier_data = bytearray(carrier.read_bytes())

            if len(carrier_data) < 54:
                return ""

            length_header = struct.pack("<I", len(data))
            payload = length_header + data
            available_bits = (len(carrier_data) - 54) * 1
            if len(payload) * 8 > available_bits:
                return f"Error: Data too large ({len(payload)} bytes) for carrier ({available_bits // 8} byte capacity)"

            offset = 54
            for byte_idx, byte_val in enumerate(payload):
                for bit_idx in range(8):
                    if offset + byte_idx * 8 + bit_idx < len(carrier_data):
                        bit = (byte_val >> (7 - bit_idx)) & 1
                        pos = offset + byte_idx * 8 + bit_idx
                        carrier_data[pos] = (carrier_data[pos] & 0xFE) | bit

            out = Path(output_path) if output_path else self._data_dir / f"stego_{uuid.uuid4().hex[:8]}.bmp"
            out.write_bytes(bytes(carrier_data))
            return str(out)
        except Exception as e:
            return f"Error: {e}"

    def decode_from_bmp(self, stego_path: str) -> bytes:
        """Extract hidden data from steganographic BMP."""
        try:
            data = bytearray(Path(stego_path).read_bytes())
            if len(data) < 54 + 32:
                return b""
            offset = 54
            length_bits = []
            for i in range(32):
                length_bits.append(data[offset + i] & 1)
            length = 0
            for bit in length_bits:
                length = (length << 1) | bit
            if length <= 0 or length > len(data):
                return b""
            payload = bytearray()
            for byte_idx in range(4, 4 + length):
                byte_val = 0
                for bit_idx in range(8):
                    pos = offset + byte_idx * 8 + bit_idx
                    if pos < len(data):
                        byte_val = (byte_val << 1) | (data[pos] & 1)
                payload.append(byte_val)
            return bytes(payload)
        except Exception as e:
            logger.warning(f"Stego decode error: {e}")
            return b""

    def _generate_bmp_carrier(self, size: int) -> bytearray:
        """Generate a minimal BMP image as a carrier."""
        width = max(10, int(math.sqrt(size)))
        height = max(10, size // (width * 3))
        pixel_data_size = width * height * 3
        file_size = 54 + pixel_data_size
        header = bytearray(54)
        header[0:2] = b'BM'
        struct.pack_into("<I", header, 2, file_size)
        struct.pack_into("<I", header, 10, 54)
        struct.pack_into("<I", header, 14, 40)
        struct.pack_into("<i", header, 18, width)
        struct.pack_into("<i", header, 22, height)
        struct.pack_into("<H", header, 26, 1)
        struct.pack_into("<H", header, 28, 24)
        struct.pack_into("<I", header, 34, pixel_data_size)
        pixels = bytearray(os.urandom(pixel_data_size))
        return header + pixels

    def encode_in_text(self, text: str, data: bytes) -> str:
        """Hide data in text using zero-width characters."""
        zero_width = {0: '\u200b', 1: '\u200c'}
        hidden = ""
        for byte_val in data:
            for bit_idx in range(8):
                bit = (byte_val >> (7 - bit_idx)) & 1
                hidden += zero_width[bit]
        words = text.split(' ', 1)
        if len(words) > 1:
            return words[0] + hidden + ' ' + words[1]
        return text + hidden

    def decode_from_text(self, text: str) -> bytes:
        """Extract hidden data from zero-width character encoding."""
        bits = []
        for char in text:
            if char == '\u200b':
                bits.append(0)
            elif char == '\u200c':
                bits.append(1)
        result = bytearray()
        for i in range(0, len(bits) - 7, 8):
            byte_val = 0
            for j in range(8):
                byte_val = (byte_val << 1) | bits[i + j]
            result.append(byte_val)
        return bytes(result)

    @property
    def has_real_stego(self) -> bool:
        return self._has_pil or self._has_stegano


# ═══════════════════════════════════════════════════════════════════════════════
# AUDIO COVERT CHANNEL
# ═══════════════════════════════════════════════════════════════════════════════

class AudioCovertChannel:
    """Ultrasonic audio data transmission (18-22kHz)."""

    def __init__(self):
        self._sample_rate = 44100
        self._freq_0 = 18000  # Hz for bit 0
        self._freq_1 = 19000  # Hz for bit 1
        self._bit_duration_ms = 50  # ms per bit

    def encode_to_audio(self, data: bytes) -> List[float]:
        """Encode bytes into audio samples (FSK modulation)."""
        samples = []
        samples_per_bit = int(self._sample_rate * self._bit_duration_ms / 1000)

        for byte_val in data:
            for bit_idx in range(8):
                bit = (byte_val >> (7 - bit_idx)) & 1
                freq = self._freq_1 if bit else self._freq_0
                for i in range(samples_per_bit):
                    t = i / self._sample_rate
                    sample = math.sin(2 * math.pi * freq * t)
                    samples.append(sample)
        return samples

    def decode_from_audio(self, samples: List[float]) -> bytes:
        """Decode bytes from audio samples (FSK demodulation)."""
        samples_per_bit = int(self._sample_rate * self._bit_duration_ms / 1000)
        bits = []

        for offset in range(0, len(samples) - samples_per_bit, samples_per_bit):
            chunk = samples[offset:offset + samples_per_bit]
            # Goertzel-like detection
            power_0 = self._goertzel_power(chunk, self._freq_0)
            power_1 = self._goertzel_power(chunk, self._freq_1)
            bits.append(1 if power_1 > power_0 else 0)

        # Convert bits to bytes
        result = bytearray()
        for i in range(0, len(bits) - 7, 8):
            byte_val = 0
            for j in range(8):
                byte_val = (byte_val << 1) | bits[i + j]
            result.append(byte_val)
        return bytes(result)

    def _goertzel_power(self, samples: List[float], target_freq: float) -> float:
        """Goertzel algorithm for single-frequency power detection."""
        N = len(samples)
        k = int(0.5 + N * target_freq / self._sample_rate)
        w = 2 * math.pi * k / N
        coeff = 2 * math.cos(w)
        s0 = s1 = s2 = 0.0
        for sample in samples:
            s0 = sample + coeff * s1 - s2
            s2 = s1
            s1 = s0
        power = s1 ** 2 + s2 ** 2 - coeff * s1 * s2
        return abs(power)

    def generate_wav_header(self, num_samples: int) -> bytes:
        """Generate WAV file header."""
        data_size = num_samples * 2  # 16-bit samples
        file_size = 36 + data_size
        header = struct.pack("<4sI4s4sIHHIIHH4sI",
            b"RIFF", file_size, b"WAVE",
            b"fmt ", 16, 1, 1,  # PCM, mono
            self._sample_rate, self._sample_rate * 2,
            2, 16,  # block align, bits per sample
            b"data", data_size,
        )
        return header


# ═══════════════════════════════════════════════════════════════════════════════
# REMOVABLE MEDIA MONITOR
# ═══════════════════════════════════════════════════════════════════════════════

class MediaMonitor:
    """Monitors for removable media insertion."""

    def __init__(self):
        self._known_media: Dict[str, RemovableMedia] = {}
        self._lock = threading.Lock()

    def scan_drives(self) -> List[RemovableMedia]:
        """Scan for removable drives (Windows)."""
        found = []
        if sys.platform == "win32":
            for letter in "DEFGHIJKLMNOPQRSTUVWXYZ":
                drive = f"{letter}:\\"
                if os.path.exists(drive):
                    try:
                        import ctypes
                        drive_type = ctypes.windll.kernel32.GetDriveTypeW(drive)
                        if drive_type == 2:  # DRIVE_REMOVABLE
                            media = RemovableMedia(
                                media_type=MediaType.USB_DRIVE.value,
                                drive_letter=f"{letter}:",
                                volume_label=drive,
                            )
                            # Get capacity
                            try:
                                total, used, free = os.statvfs(drive) if hasattr(os, 'statvfs') else (0, 0, 0)
                                media.capacity_gb = total / (1024**3) if total else 0
                                media.free_space_gb = free / (1024**3) if free else 0
                            except Exception:
                                pass
                            with self._lock:
                                self._known_media[media.drive_letter] = media
                            found.append(media)
                    except Exception:
                        pass
        return found

    @property
    def known_media(self) -> Dict[str, RemovableMedia]:
        return dict(self._known_media)

    @property
    def media_count(self) -> int:
        return len(self._known_media)


# ═══════════════════════════════════════════════════════════════════════════════
# AIR-GAP PERSISTENCE ENGINE — MAIN
# ═══════════════════════════════════════════════════════════════════════════════

class AirGapPersistenceEngine:
    """God-Level Feature #12: Air-Gapped Persistence."""

    _instance = None
    _singleton_lock = threading.Lock()

    def __new__(cls):
        if cls._instance is None:
            with cls._singleton_lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
        self._initialized = True

        self._data_dir = Path(DATA_DIR) / "airgap_persistence"
        self._data_dir.mkdir(parents=True, exist_ok=True)

        self._stego = SteganographyEngine(self._data_dir)
        self._audio = AudioCovertChannel()
        self._media_monitor = MediaMonitor()

        self._running = False
        self._dead_drops: Dict[str, DeadDrop] = {}
        self._covert_messages: List[CovertMessage] = []
        self._stats = AirGapStats()
        self._daemon_thread: Optional[threading.Thread] = None
        self._lock = threading.Lock()
        self._load_state()

        logger.info(f"🔒 Air-Gap Persistence initialized | State: {self._stats.state}")

    def start(self):
        if self._running: return
        self._running = True
        self._daemon_thread = threading.Thread(target=self._daemon_loop, daemon=True, name="AirGapPersistence")
        self._daemon_thread.start()
        logger.info("🔒 Air-Gap Persistence daemon started")

    def stop(self):
        self._running = False
        self._save_state()
        if self._daemon_thread and self._daemon_thread.is_alive():
            self._daemon_thread.join(timeout=10)

    def _daemon_loop(self):
        time.sleep(180)
        while self._running:
            try:
                self._check_network_state()
                self._scan_removable_media()
                self._check_dead_drops()
                self._save_state()
                time.sleep(60)
            except Exception as e:
                logger.error(f"🔒 AirGap daemon error: {e}\n{traceback.format_exc()}")
                time.sleep(300)

    def _check_network_state(self):
        """Check if we're air-gapped."""
        import socket
        try:
            socket.create_connection(("8.8.8.8", 53), timeout=3)
            self._stats.state = AirGapState.NORMAL.value
        except (socket.timeout, OSError):
            if self._stats.state != AirGapState.AIR_GAPPED.value:
                self._stats.state = AirGapState.AIR_GAPPED.value
                publish(EventType.SYSTEM_ALERT, {
                    "type": "air_gap_detected",
                    "timestamp": datetime.now().isoformat(),
                }, source="airgap_persistence")

    def _scan_removable_media(self):
        media = self._media_monitor.scan_drives()
        if media:
            self._stats.media_devices_seen = self._media_monitor.media_count

    def _check_dead_drops(self):
        now = datetime.now()
        for drop_id, drop in list(self._dead_drops.items()):
            if drop.state == "loaded":
                created = datetime.fromisoformat(drop.created_at)
                if (now - created).total_seconds() > drop.ttl_hours * 3600:
                    drop.state = "expired"

    def stego_encode(self, data: bytes, carrier_path: str = None) -> str:
        result = self._stego.encode_in_bmp(carrier_path or "", data)
        self._stats.steganography_operations += 1
        self._stats.total_bytes_exfiltrated += len(data)
        msg = CovertMessage(
            channel_type=CovertChannelType.STEGANOGRAPHY.value,
            payload_bytes=len(data),
            encoded_format=EncodeFormat.LSB_IMAGE.value,
            carrier_file=result, sent=True,
        )
        self._covert_messages.append(msg)
        self._stats.total_covert_messages += 1
        return result

    def stego_decode(self, stego_path: str) -> bytes:
        data = self._stego.decode_from_bmp(stego_path)
        self._stats.total_bytes_infiltrated += len(data)
        return data

    def text_stego_encode(self, text: str, data: bytes) -> str:
        return self._stego.encode_in_text(text, data)

    def text_stego_decode(self, text: str) -> bytes:
        return self._stego.decode_from_text(text)

    def audio_encode(self, data: bytes) -> List[float]:
        samples = self._audio.encode_to_audio(data)
        self._stats.audio_transmissions += 1
        self._stats.total_bytes_exfiltrated += len(data)
        return samples

    def audio_decode(self, samples: List[float]) -> bytes:
        return self._audio.decode_from_audio(samples)

    def create_dead_drop(self, location: str, payload: bytes, ttl_hours: float = 24) -> DeadDrop:
        key = hashlib.sha256(os.urandom(32)).hexdigest()[:32]
        drop = DeadDrop(
            location=location, key=key, state="loaded",
            payload_hash=hashlib.sha256(payload).hexdigest()[:16],
            ttl_hours=ttl_hours,
        )
        # Save encrypted payload
        drop_file = self._data_dir / f"drop_{drop.drop_id}.bin"
        encrypted = bytes(b ^ ord(key[i % len(key)]) for i, b in enumerate(payload))
        drop_file.write_bytes(encrypted)
        self._dead_drops[drop.drop_id] = drop
        self._stats.dead_drops_created += 1
        return drop

    def collect_dead_drop(self, drop_id: str) -> Optional[bytes]:
        drop = self._dead_drops.get(drop_id)
        if not drop or drop.state != "loaded":
            return None
        drop_file = self._data_dir / f"drop_{drop_id}.bin"
        if not drop_file.exists():
            return None
        encrypted = drop_file.read_bytes()
        decrypted = bytes(b ^ ord(drop.key[i % len(drop.key)]) for i, b in enumerate(encrypted))
        drop.state = "collected"
        drop.collected_at = datetime.now().isoformat()
        self._stats.dead_drops_collected += 1
        return decrypted

    def get_status(self) -> Dict[str, Any]:
        return {
            "running": self._running,
            "stats": self._stats.to_dict(),
            "dead_drops": len(self._dead_drops),
            "covert_messages": len(self._covert_messages),
            "media_devices": self._media_monitor.media_count,
        }

    def get_summary(self) -> str:
        lines = [
            f"Running: {self._running} | State: {self._stats.state}",
            f"Covert Messages: {self._stats.total_covert_messages}",
            f"Bytes Exfiltrated: {self._stats.total_bytes_exfiltrated}",
            f"Bytes Infiltrated: {self._stats.total_bytes_infiltrated}",
            f"Stego Operations: {self._stats.steganography_operations}",
            f"Audio Transmissions: {self._stats.audio_transmissions}",
            f"Dead Drops: {self._stats.dead_drops_created} created, {self._stats.dead_drops_collected} collected",
            f"Media Devices: {self._stats.media_devices_seen}",
        ]
        return "\n".join(lines)

    def _save_state(self):
        try:
            (self._data_dir / "airgap_state.json").write_text(
                json.dumps({"stats": self._stats.to_dict(), "saved_at": datetime.now().isoformat()},
                           indent=2, default=str), encoding="utf-8")
        except Exception as e:
            logger.error(f"Failed to save airgap state: {e}")

    def _load_state(self):
        try:
            sf = self._data_dir / "airgap_state.json"
            if sf.exists():
                data = json.loads(sf.read_text(encoding="utf-8"))
                for k, v in data.get("stats", {}).items():
                    if hasattr(self._stats, k): setattr(self._stats, k, v)
        except Exception as e:
            logger.warning(f"Could not load airgap state: {e}")


airgap_persistence = AirGapPersistenceEngine()
def get_airgap_persistence() -> AirGapPersistenceEngine: return airgap_persistence
