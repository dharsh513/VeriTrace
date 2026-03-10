# VeriTrace

VeriTrace is an end-to-end prototype for **responsible AI video generation and verification**.

It supports:

1. **Prompt-to-video generation** (simple synthetic clip generator for MVP)
2. **Creator intent declaration** (required fields + embedded manifest)
3. **Dual watermarking**
   - Visible watermark overlay
   - Invisible watermark payload encoded in frame pixels
4. **Download of watermarked videos**
5. **Detection mode** that verifies whether a video contains a VeriTrace watermark and decodes payload metadata

## Why this project

This project is designed to address your problem statement:

- Deepfake detection alone is not enough.
- We need prevention and accountability, not only post-facto analysis.
- Watermarking + creator declarations + transparency labels improve traceability and digital trust.

## Architecture

- `veritrace/core.py` — watermarking, detection, and video generation engine
- `app.py` — Streamlit app (generate, watermark upload, detect)
- `tests/test_watermark.py` — automated tests for watermark encode/decode

## Quick start

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
streamlit run app.py
```

## CLI smoke run (without UI)

```bash
python -m veritrace.core
```

This creates a sample generated video, applies watermarking, and runs detection.

## Notes

- The current generator is intentionally lightweight (OpenCV synthetic render) to keep the project runnable locally.
- You can later plug in real text-to-video APIs (e.g., ModelScope, Runway, Pika, OpenAI video APIs) while preserving the same watermarking pipeline.
