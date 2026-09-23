# Signals AI Mobile Voice & Photo Bench Note PWA

A mobile-first Progressive Web App (PWA) designed for wet-lab scientists working at fume hoods or biosafety cabinets. It captures spoken voice observations and bench photos, uses **Gemini 2.0 Flash** to synthesize structured laboratory observation notes, and attaches them directly to active experiments in **Signals Notebook**.

---

## Architecture & Features

* **Hands-Free Dictation:** Native browser Web Speech API (`webkitSpeechRecognition`) for real-time speech-to-text without transcode latency.
* **Camera Integration:** One-tap camera capture using HTML5 `<input type="file" capture="environment">` optimized for smartphones and tablets.
* **Multimodal Intelligence:** Gemini 2.0 Flash combines spoken notes with visual evidence (turbidity, color transitions, TLC plate spots, precipitate) into an audit-compliant HTML observation entry.
* **Signals Direct Ingress:** Uses `POST /api/rest/v1.0/entities/{eid}/children/{filename}?force=true` to upload:
  * `bench_photo_*.jpg` (Image Entity)
  * `bench_note_*.html` (Rich Text Element rendered directly in the notebook)
* **Zero-Install PWA:** Fully installable to iOS and Android home screens via `manifest.json` and `sw.js`.
* **Offline / Demo Simulation Mode:** Includes a **"Load Demo Sample"** button to test the full multimodal and upload flow on a desktop browser without camera or microphone hardware.

---

## Directory Structure

```text
bench-note-pwa/
├── .devcontainer/
│   └── devcontainer.json      # GitHub Codespaces config with public port 8000
├── backend/
│   ├── app.py                 # FastAPI backend & static file server
│   ├── ai_service.py          # Gemini 2.0 Flash multimodal prompt & parser
│   ├── signals_client.py      # Signals Notebook REST client (child attachments)
│   └── requirements.txt       # Dependencies
├── frontend/
│   ├── index.html             # Mobile-first interface (Tailwind CSS CDN)
│   ├── app.js                 # Camera, speech, and API orchestration
│   ├── manifest.json          # PWA installation manifest
│   ├── sw.js                  # Service worker for offline app shell
│   └── icon.svg               # Application icon
├── .env.example               # Environment variable template
└── test_mock_upload.py        # Automated test verification script
```

---

## Quickstart (60-Second Setup)

### 1. Configure Credentials
Copy `.env.example` to `.env`:
```bash
cp .env.example .env
```
Fill in your Signals Notebook API Key, Base URL, and AI Gateway Key:
```ini
SIGNALS_BASE_URL=https://hackathon.signalsnotebook.revvitycloud.com/api/rest/v1.0
SIGNALS_API_KEY=your-signals-api-key
AI_GATEWAY_URL=https://signals-ai.revvity-hackathon.com/v1
AI_GATEWAY_KEY=sk-team-1-alpha
AI_MODEL=gemini-2.0-flash
```

*(Note: If left unconfigured, the app automatically runs in **Mock Simulation Mode** for local testing.)*

### 2. Install Dependencies & Run
```bash
pip install -r backend/requirements.txt
uvicorn backend.app:app --host 0.0.0.0 --port 8000 --reload
```

### 3. Open in Browser / Mobile
* Open **`http://localhost:8000`** in Chrome, Edge, or Safari.
* For mobile testing on your smartphone:
  * In **GitHub Codespaces**: Go to the **Ports** tab, set port `8000` visibility to **Public**, and open the generated HTTPS URL on your phone!
  * On iOS Safari: Tap **Share → Add to Home Screen**.
  * On Android Chrome: Tap **Install App**.

---

## Testing Without a Phone / Microphone
1. Open the web interface at `http://localhost:8000`.
2. Click **"🧪 Load Demo Sample"** at the top right of the Bench Capture card.
3. Click **"✨ Synthesize with Gemini Flash"** to inspect the structured observation.
4. Click **"🚀 Commit to Signals Notebook"** to upload the note and image to your experiment.
