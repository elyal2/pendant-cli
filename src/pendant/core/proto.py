"""Protobuf import wrapper with nice error handling."""

import sys
from pathlib import Path

# Add proto directory to path for imports
_proto_dir = Path(__file__).parent.parent.parent.parent / "proto"
if _proto_dir.exists() and str(_proto_dir) not in sys.path:
    sys.path.insert(0, str(_proto_dir))

try:
    import pendant_pb2 as pb
    PROTOBUF_AVAILABLE = True
except ImportError:
    pb = None  # type: ignore
    PROTOBUF_AVAILABLE = False

__all__ = ['pb', 'PROTOBUF_AVAILABLE']
