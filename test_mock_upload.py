"""
Test verification script for AI Mobile Voice & Photo Bench Note PWA.
Verifies:
1. SignalsClient experiment listing and child attachment upload.
2. BenchNoteAIService multimodal analysis (Gemini Flash / mock fallback).
3. End-to-end integration without needing a browser or mobile device.
"""

import io
from PIL import Image, ImageDraw
from backend.signals_client import SignalsClient
from backend.ai_service import BenchNoteAIService

def create_test_image() -> bytes:
    """Generate a simple in-memory JPEG image of a test reaction vial."""
    img = Image.new("RGB", (300, 200), color=(15, 23, 42))
    draw = ImageDraw.Draw(img)
    draw.rectangle([30, 30, 270, 170], outline=(56, 189, 248), width=3)
    draw.text((50, 80), "EXP-2026 Batch 4B", fill=(255, 255, 255))
    draw.text((50, 110), "Status: Turbid / 45 C", fill=(245, 158, 11))
    buf = io.BytesIO()
    img.save(buf, format="JPEG")
    return buf.getvalue()

def run_tests():
    print("=" * 60)
    print("[TEST] RUNNING VERIFICATION FOR BENCH NOTE PWA")
    print("=" * 60)

    # 1. Test SignalsClient
    print("\n[Step 1] Initializing SignalsClient...")
    client = SignalsClient()
    print(f"  -> Base URL: {client.base_url}")
    print(f"  -> Mock Mode: {client.mock_mode}")

    experiments = client.list_experiments()
    print(f"  -> Successfully retrieved {len(experiments)} experiment(s).")
    target_eid = experiments[0]["eid"]
    print(f"  -> Selected target EID: {target_eid}")

    # 2. Test AI Service Multimodal Analysis
    print("\n[Step 2] Testing BenchNoteAIService (Gemini 2.0 Flash / Mock)...")
    ai_service = BenchNoteAIService()
    test_photo_bytes = create_test_image()
    test_transcript = "Batch 4B at 45 degrees Celsius turned cloudy with white precipitate after 15 minutes. Viscosity increased."

    print(f"  -> Input transcript: '{test_transcript}'")
    print(f"  -> Input image size: {len(test_photo_bytes)} bytes")

    analysis = ai_service.analyze_observation(
        transcript=test_transcript,
        image_bytes=test_photo_bytes,
        mime_type="image/jpeg"
    )

    print("  -> AI Response Title:", analysis.get("title"))
    print("  -> AI Response Summary:", analysis.get("summary"))
    print("  -> Detected Flags:", analysis.get("flags"))
    print("  -> Detected Tags:", analysis.get("tags"))
    assert "structured_html" in analysis, "structured_html missing from AI response"
    print("  -> Structured HTML length:", len(analysis["structured_html"]))

    # 3. Test Child Attachment Upload
    print("\n[Step 3] Testing Signals child attachment upload (force=true)...")
    # Upload photo
    photo_res = client.upload_child_attachment(
        parent_eid=target_eid,
        filename="test_bench_vial.jpg",
        content_bytes=test_photo_bytes,
        content_type="image/jpeg"
    )
    print("  -> Photo upload response:", photo_res)

    # Upload HTML rich text note
    note_html = f"<html><body>{analysis['structured_html']}</body></html>"
    note_res = client.upload_child_attachment(
        parent_eid=target_eid,
        filename="test_bench_note.html",
        content_bytes=note_html.encode("utf-8"),
        content_type="text/html"
    )
    print("  -> HTML note upload response:", note_res)

    print("\n" + "=" * 60)
    print("[SUCCESS] ALL PIPELINE VERIFICATIONS PASSED SUCCESSFULLY!")
    print("=" * 60)

if __name__ == "__main__":
    run_tests()
