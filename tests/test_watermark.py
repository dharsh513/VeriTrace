from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

from veritrace.core import CreatorDeclaration, detect_watermark, generate_video_from_prompt, watermark_video


def test_generate_watermark_and_detect(tmp_path: Path) -> None:
    generated = tmp_path / "generated.mp4"
    watermarked = tmp_path / "watermarked.mp4"

    generate_video_from_prompt("test prompt", str(generated), seconds=1, fps=12)
    declaration = CreatorDeclaration(
        creator_name="tester",
        intent="unit test",
        allowed_use="testing",
        prompt="test prompt",
        created_at=datetime.now(timezone.utc).isoformat(),
    )

    watermark_video(str(generated), str(watermarked), declaration)
    result = detect_watermark(str(watermarked))

    assert result.watermark_found
    assert result.integrity_ok
    assert result.payload is not None
    assert result.payload["creator_name"] == "tester"
    assert result.payload["prompt"] == "test prompt"


def test_detection_fails_on_unwatermarked_video(tmp_path: Path) -> None:
    generated = tmp_path / "plain.mp4"
    generate_video_from_prompt("plain", str(generated), seconds=1, fps=12)

    result = detect_watermark(str(generated))
    assert not result.watermark_found
