from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

import cv2
import numpy as np


@dataclass
class CreatorDeclaration:
    creator_name: str
    intent: str
    allowed_use: str
    prompt: str
    created_at: str


@dataclass
class DetectionResult:
    watermark_found: bool
    payload: Optional[dict]
    integrity_ok: bool
    message: str


def _canonical_json(data: dict) -> str:
    return json.dumps(data, sort_keys=True, separators=(",", ":"))


def _payload_signature(payload: dict) -> str:
    canonical = _canonical_json(payload).encode("utf-8")
    return hashlib.sha256(canonical).hexdigest()


def _build_payload(declaration: CreatorDeclaration) -> dict:
    body = asdict(declaration)
    body["system"] = "VeriTrace"
    body["version"] = "1.0"
    body["watermark_type"] = "visible+invisible"
    body["signature"] = _payload_signature(body)
    return body


def _serialize_payload(payload: dict) -> bytes:
    text = _canonical_json(payload)
    return text.encode("utf-8")


def _to_bits(data: bytes) -> list[int]:
    bits = []
    for byte in data:
        for i in range(8):
            bits.append((byte >> (7 - i)) & 1)
    return bits


def _from_bits(bits: list[int]) -> bytes:
    out = bytearray()
    for i in range(0, len(bits), 8):
        b = 0
        for j in range(8):
            b = (b << 1) | bits[i + j]
        out.append(b)
    return bytes(out)


def _embed_bits_in_frame(frame: np.ndarray, bits: list[int]) -> np.ndarray:
    """Embed bits using block-based blue-channel intensity for compression robustness."""
    out = frame.copy()
    block = 4
    cols = frame.shape[1] // block
    rows = frame.shape[0] // block
    capacity = cols * rows
    if len(bits) > capacity:
        raise ValueError("Payload too large for invisible watermark capacity")

    for idx, bit in enumerate(bits):
        r = idx // cols
        c = idx % cols
        y0, y1 = r * block, (r + 1) * block
        x0, x1 = c * block, (c + 1) * block
        level = 240 if bit else 16
        out[y0:y1, x0:x1, 0] = level
    return out


def _extract_bits_from_frame(frame: np.ndarray, bit_count: int) -> list[int]:
    block = 4
    cols = frame.shape[1] // block
    rows = frame.shape[0] // block
    capacity = cols * rows
    if bit_count > capacity:
        raise ValueError("Bit count exceeds frame capacity")

    bits: list[int] = []
    for idx in range(bit_count):
        r = idx // cols
        c = idx % cols
        y0, y1 = r * block, (r + 1) * block
        x0, x1 = c * block, (c + 1) * block
        avg_blue = float(frame[y0:y1, x0:x1, 0].mean())
        bits.append(1 if avg_blue > 128 else 0)
    return bits


def _build_header(payload_len: int) -> bytes:
    # 4-byte magic + 4-byte payload length
    magic = b"VTRC"
    return magic + payload_len.to_bytes(4, "big")


def _parse_header(blob: bytes) -> tuple[bool, int]:
    if len(blob) < 8:
        return False, 0
    magic = blob[:4]
    if magic != b"VTRC":
        return False, 0
    payload_len = int.from_bytes(blob[4:8], "big")
    return True, payload_len


def generate_video_from_prompt(prompt: str, output_path: str, seconds: int = 4, fps: int = 24) -> str:
    width, height = 640, 360
    total_frames = seconds * fps
    out = cv2.VideoWriter(output_path, cv2.VideoWriter_fourcc(*"mp4v"), fps, (width, height))

    if not out.isOpened():
        raise RuntimeError("Unable to initialize video writer")

    for i in range(total_frames):
        frame = np.zeros((height, width, 3), dtype=np.uint8)
        t = i / max(1, total_frames - 1)

        r = int(20 + 200 * t)
        g = int(120 + 100 * (1 - t))
        b = int(180 + 50 * np.sin(i / 8.0))
        frame[:] = (b, g, r)

        cv2.putText(
            frame,
            "AI GENERATED VIDEO",
            (40, 80),
            cv2.FONT_HERSHEY_SIMPLEX,
            1.0,
            (255, 255, 255),
            2,
            cv2.LINE_AA,
        )

        wrapped_prompt = (prompt[:60] + "...") if len(prompt) > 60 else prompt
        cv2.putText(
            frame,
            f"Prompt: {wrapped_prompt}",
            (30, 170),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.65,
            (10, 10, 10),
            2,
            cv2.LINE_AA,
        )

        x = 20 + int((width - 120) * t)
        cv2.rectangle(frame, (x, 260), (x + 100, 320), (255, 255, 255), -1)
        cv2.putText(frame, "VT", (x + 30, 300), cv2.FONT_HERSHEY_DUPLEX, 1.0, (30, 30, 30), 2, cv2.LINE_AA)

        out.write(frame)

    out.release()
    return output_path


def watermark_video(input_path: str, output_path: str, declaration: CreatorDeclaration) -> str:
    cap = cv2.VideoCapture(input_path)
    if not cap.isOpened():
        raise RuntimeError(f"Cannot open input video: {input_path}")

    fps = cap.get(cv2.CAP_PROP_FPS) or 24.0
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

    writer = cv2.VideoWriter(output_path, cv2.VideoWriter_fourcc(*"mp4v"), fps, (width, height))
    if not writer.isOpened():
        cap.release()
        raise RuntimeError("Cannot open video writer")

    payload = _build_payload(declaration)
    payload_bytes = _serialize_payload(payload)
    header = _build_header(len(payload_bytes))
    blob = header + payload_bytes
    bits = _to_bits(blob)

    frame_idx = 0
    while True:
        ok, frame = cap.read()
        if not ok:
            break

        overlay_text = f"AI Generated | VeriTrace | Creator: {declaration.creator_name}"
        cv2.putText(frame, overlay_text, (10, height - 18), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2, cv2.LINE_AA)
        cv2.putText(frame, overlay_text, (10, height - 18), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 0), 1, cv2.LINE_AA)

        if frame_idx == 0:
            frame = _embed_bits_in_frame(frame, bits)

        writer.write(frame)
        frame_idx += 1

    cap.release()
    writer.release()
    return output_path


def detect_watermark(video_path: str) -> DetectionResult:
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        return DetectionResult(False, None, False, "Cannot open video file")

    ok, frame = cap.read()
    cap.release()
    if not ok:
        return DetectionResult(False, None, False, "Video contains no readable frames")

    try:
        header_bits = _extract_bits_from_frame(frame, 8 * 8)
        header = _from_bits(header_bits)
        valid_magic, payload_len = _parse_header(header)
        if not valid_magic or payload_len <= 0:
            return DetectionResult(False, None, False, "No VeriTrace watermark signature detected")

        payload_bits = _extract_bits_from_frame(frame, (8 + payload_len) * 8)[64:]
        payload_bytes = _from_bits(payload_bits)
        payload = json.loads(payload_bytes.decode("utf-8"))

        signature = payload.get("signature")
        payload_copy = dict(payload)
        payload_copy.pop("signature", None)
        recomputed = _payload_signature(payload_copy)
        integrity_ok = signature == recomputed

        if integrity_ok:
            return DetectionResult(True, payload, True, "VeriTrace watermark found and verified")
        return DetectionResult(True, payload, False, "VeriTrace watermark found but integrity check failed")
    except Exception as exc:
        return DetectionResult(False, None, False, f"Watermark decode error: {exc}")


def _demo() -> None:
    Path("data/generated").mkdir(parents=True, exist_ok=True)
    src = "data/generated/demo_generated.mp4"
    out = "data/generated/demo_watermarked.mp4"

    generate_video_from_prompt("A futuristic city skyline at sunset", src)
    declaration = CreatorDeclaration(
        creator_name="demo-user",
        intent="Educational demonstration",
        allowed_use="Public awareness",
        prompt="A futuristic city skyline at sunset",
        created_at=datetime.now(timezone.utc).isoformat(),
    )
    watermark_video(src, out, declaration)
    result = detect_watermark(out)
    print(json.dumps(asdict(result), indent=2))


if __name__ == "__main__":
    _demo()
