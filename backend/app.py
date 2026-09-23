import os
import logging
from datetime import datetime
from typing import Optional
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
dotenv_path = Path(__file__).parent.parent / ".env"
if dotenv_path.exists():
    load_dotenv(dotenv_path)
else:
    load_dotenv()

from fastapi import FastAPI, UploadFile, File, Form, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel

from .signals_client import SignalsClient
from .ai_service import BenchNoteAIService

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("bench_pwa")

app = FastAPI(title="AI Mobile Voice & Photo Bench Note PWA")

# Enable CORS for local testing and mobile cross-origin access
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

signals_client = SignalsClient()
ai_service = BenchNoteAIService()

# Determine frontend directory
FRONTEND_DIR = Path(__file__).parent.parent / "frontend"

@app.get("/api/health")
def health_check():
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "mock_mode": signals_client.mock_mode,
        "ai_model": ai_service.model
    }

@app.get("/api/experiments")
def get_experiments():
    """Returns available active experiments for the mobile dropdown."""
    try:
        experiments = signals_client.list_experiments()
        return {"experiments": experiments}
    except Exception as e:
        logger.error(f"Failed to fetch experiments: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/analyze-note")
async def analyze_bench_note(
    transcript: str = Form(""),
    photo: Optional[UploadFile] = File(None)
):
    """
    Step 1 of 2: Uses Gemini 3.5 Flash to synthesize voice transcript + photo
    into a structured scientific observation for the scientist to review.
    """
    image_bytes = None
    mime_type = "image/jpeg"

    if photo:
        raw_bytes = await photo.read()
        logger.info(f"Received photo upload: {photo.filename} ({len(raw_bytes)} bytes, content_type={photo.content_type})")
        try:
            import io
            from PIL import Image, ImageOps
            with Image.open(io.BytesIO(raw_bytes)) as pil_img:
                # Correct iOS camera orientation
                pil_img = ImageOps.exif_transpose(pil_img)
                pil_img = pil_img.convert("RGB")
                max_dim = 800
                if max(pil_img.size) > max_dim:
                    pil_img.thumbnail((max_dim, max_dim))
                buf = io.BytesIO()
                pil_img.save(buf, format="JPEG", quality=80)
                image_bytes = buf.getvalue()
                mime_type = "image/jpeg"
                logger.info(f"Normalized mobile image to JPEG: {len(image_bytes)} bytes ({pil_img.size})")
        except Exception as img_err:
            logger.warning(f"Image normalization warning: {img_err}, using raw bytes")
            image_bytes = raw_bytes
            mime_type = photo.content_type or "image/jpeg"

    logger.info(f"Synthesizing note: transcript='{transcript[:80]}...', has_image={bool(image_bytes)}")

    try:
        analysis = ai_service.analyze_observation(
            transcript=transcript,
            image_bytes=image_bytes,
            mime_type=mime_type
        )
        logger.info(f"Synthesis complete! Source: {analysis.get('source')}, Title: {analysis.get('title')}")
        return {"status": "success", "analysis": analysis}
    except Exception as e:
        logger.error(f"Analysis error: {e}")
        raise HTTPException(status_code=500, detail=f"AI analysis failed: {str(e)}")

class CommitRequest(BaseModel):
    experiment_eid: str
    title: str
    structured_html: str

@app.post("/api/commit-to-signals")
async def commit_to_signals(
    experiment_eid: str = Form(...),
    title: str = Form(...),
    structured_html: str = Form(...),
    photo: Optional[UploadFile] = File(None)
):
    """
    Uploads the verified bench observation note (HTML text element)
    and optional bench photo (image element) directly into the Signals experiment.
    """
    timestamp_slug = datetime.now().strftime("%Y%m%d_%H%M%S")
    results = {}

    try:
        # 1. Upload Photo if present
        if photo:
            photo_bytes = await photo.read()
            photo_name = f"bench_photo_{timestamp_slug}.jpg"
            photo_res = signals_client.upload_child_attachment(
                parent_eid=experiment_eid,
                filename=photo_name,
                content_bytes=photo_bytes,
                content_type=photo.content_type or "image/jpeg"
            )
            results["photo_attachment"] = photo_res

        # 2. Upload formatted HTML note
        # Signals Notebook automatically interprets .html as an editable Text Element!
        note_name = f"bench_note_{timestamp_slug}.html"
        full_html = f"""<!DOCTYPE html>
<html>
<head><meta charset="utf-8"><title>{title}</title></head>
<body>
{structured_html}
</body>
</html>"""

        note_res = signals_client.upload_child_attachment(
            parent_eid=experiment_eid,
            filename=note_name,
            content_bytes=full_html.encode("utf-8"),
            content_type="text/html"
        )
        results["note_attachment"] = note_res
        results["status"] = "success"
        results["message"] = f"Observation and assets attached to {experiment_eid}"
        return results

    except Exception as e:
        logger.error(f"Failed to commit to Signals: {e}")
        raise HTTPException(status_code=500, detail=f"Signals upload failed: {str(e)}")

# Mount frontend files at root
if FRONTEND_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(FRONTEND_DIR)), name="static")

    @app.get("/")
    def serve_index():
        return FileResponse(FRONTEND_DIR / "index.html")

    @app.get("/manifest.json")
    def serve_manifest():
        return FileResponse(FRONTEND_DIR / "manifest.json", media_type="application/json")

    @app.get("/sw.js")
    def serve_sw():
        return FileResponse(FRONTEND_DIR / "sw.js", media_type="application/javascript")
