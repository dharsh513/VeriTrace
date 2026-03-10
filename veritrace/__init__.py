"""VeriTrace package."""

from .core import (
    CreatorDeclaration,
    DetectionResult,
    detect_watermark,
    generate_video_from_prompt,
    watermark_video,
)

__all__ = [
    "CreatorDeclaration",
    "DetectionResult",
    "generate_video_from_prompt",
    "watermark_video",
    "detect_watermark",
]
