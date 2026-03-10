from __future__ import annotations

import json
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path

import streamlit as st

from veritrace.core import CreatorDeclaration, detect_watermark, generate_video_from_prompt, watermark_video

st.set_page_config(page_title="VeriTrace", layout="wide")

DATA_DIR = Path("data")
GEN_DIR = DATA_DIR / "generated"
UPLOAD_DIR = DATA_DIR / "uploads"
PROC_DIR = DATA_DIR / "processed"
for p in [GEN_DIR, UPLOAD_DIR, PROC_DIR]:
    p.mkdir(parents=True, exist_ok=True)

st.title("VeriTrace: Responsible AI Video Generation + Detection")
st.caption("Generate, watermark, download, and verify AI-generated videos with creator accountability metadata.")

mode = st.sidebar.radio(
    "Select Mode",
    ["Generate + Watermark", "Watermark Existing Video", "Detect Watermark"],
)

if mode == "Generate + Watermark":
    st.subheader("1) Generate video from prompt")
    prompt = st.text_area("Prompt", "A calm ocean at sunrise with soft cinematic colors")
    creator_name = st.text_input("Creator Name", "anonymous")
    intent = st.text_input("Intent Declaration", "Educational content")
    allowed_use = st.text_input("Allowed Use", "Non-deceptive social sharing")

    if st.button("Generate & Watermark"):
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        generated = GEN_DIR / f"generated_{ts}.mp4"
        watermarked = PROC_DIR / f"watermarked_{ts}.mp4"

        generate_video_from_prompt(prompt, str(generated))
        declaration = CreatorDeclaration(
            creator_name=creator_name,
            intent=intent,
            allowed_use=allowed_use,
            prompt=prompt,
            created_at=datetime.now(timezone.utc).isoformat(),
        )
        watermark_video(str(generated), str(watermarked), declaration)

        st.success("Video generated and watermarked.")
        st.video(str(watermarked))

        with open(watermarked, "rb") as f:
            st.download_button(
                "Download Watermarked Video",
                f,
                file_name=watermarked.name,
                mime="video/mp4",
            )

        result = detect_watermark(str(watermarked))
        st.write("Detection check on generated output:")
        st.json(asdict(result))

elif mode == "Watermark Existing Video":
    st.subheader("2) Add watermark to an uploaded video")
    uploaded = st.file_uploader("Upload video", type=["mp4", "mov", "avi", "mkv"])
    creator_name = st.text_input("Creator Name", "anonymous")
    intent = st.text_input("Intent Declaration", "Research / educational")
    allowed_use = st.text_input("Allowed Use", "Transparent AI-assisted content")
    prompt = st.text_input("Original Prompt (optional)", "")

    if uploaded and st.button("Apply Watermark"):
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        src = UPLOAD_DIR / f"upload_{ts}_{uploaded.name}"
        src.write_bytes(uploaded.read())
        out = PROC_DIR / f"watermarked_upload_{ts}.mp4"

        declaration = CreatorDeclaration(
            creator_name=creator_name,
            intent=intent,
            allowed_use=allowed_use,
            prompt=prompt,
            created_at=datetime.now(timezone.utc).isoformat(),
        )
        watermark_video(str(src), str(out), declaration)

        st.success("Watermark applied.")
        st.video(str(out))
        with open(out, "rb") as f:
            st.download_button("Download Watermarked Video", f, file_name=out.name, mime="video/mp4")

elif mode == "Detect Watermark":
    st.subheader("3) Detect and verify watermark")
    uploaded = st.file_uploader("Upload video for detection", type=["mp4", "mov", "avi", "mkv"])

    if uploaded and st.button("Detect"):
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        src = UPLOAD_DIR / f"detect_{ts}_{uploaded.name}"
        src.write_bytes(uploaded.read())

        result = detect_watermark(str(src))
        if result.watermark_found and result.integrity_ok:
            st.success(result.message)
        elif result.watermark_found:
            st.warning(result.message)
        else:
            st.error(result.message)

        st.json(asdict(result))

        if result.payload:
            st.markdown("### Decoded creator declaration")
            st.code(json.dumps(result.payload, indent=2), language="json")
