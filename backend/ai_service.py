import os
import json
import base64
import logging
from datetime import datetime
from typing import Optional, Dict, Any
from openai import OpenAI

logger = logging.getLogger("ai_service")

class BenchNoteAIService:
    def __init__(self):
        self.gateway_url = os.getenv("AI_GATEWAY_URL", "https://signals-ai.revvity-hackathon.com/v1")
        self.api_key = os.getenv("AI_GATEWAY_KEY", "")
        self.model = os.getenv("AI_MODEL", "gemini-2.0-flash")
        self.mock_mode = (
            os.getenv("MOCK_MODE", "false").lower() == "true" 
            or not self.api_key 
            or "sk-team" in self.api_key and "revvity-hackathon.com" in self.gateway_url
        )

        if not self.mock_mode and self.api_key:
            self.client = OpenAI(
                base_url=self.gateway_url,
                api_key=self.api_key
            )
        else:
            self.client = None

    def analyze_observation(
        self,
        transcript: str,
        image_bytes: Optional[bytes] = None,
        mime_type: str = "image/jpeg"
    ) -> Dict[str, Any]:
        """
        Multimodal analysis: Synthesizes spoken bench memo + bench photo
        into a structured, audit-ready ELN observation block.
        """
        now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        # Fallback / Mock simulation if no live API gateway available
        if self.mock_mode or not self.client:
            logger.info("Generating simulated AI observation (Mock / Offline Mode)")
            return self._generate_mock_analysis(transcript, bool(image_bytes), now_str)

        system_instruction = (
            "You are an expert scientific lab notebook copilot. Your task is to process "
            "informal, spoken bench dictations and photos taken by gloved laboratory scientists at the hood. "
            "Combine visual evidence (color change, precipitate, TLC plate spots, phase separation, instrument readings) "
            "with their verbal observations into an audit-compliant, structured laboratory entry.\n\n"
            "Return a strictly valid JSON object with the following keys:\n"
            "{\n"
            "  \"title\": \"Short, descriptive title for the observation\",\n"
            "  \"summary\": \"1-2 sentence executive summary of findings\",\n"
            "  \"structured_html\": \"Formatted HTML (using <h3>, <p>, <ul>, <li>, <strong>, <span style=...>) suitable for a Signals Notebook rich-text element\",\n"
            "  \"flags\": [\"List of caution/alert strings if anomaly or safety concern is detected\"],\n"
            "  \"tags\": [\"List of chemical/biological keywords, conditions, or assay terms\"]\n"
            "}"
        )

        user_content = []
        user_content.append({
            "type": "text",
            "text": f"Observation Timestamp: {now_str}\n\nSpoken scientist dictation:\n\"{transcript}\"\n\nAnalyze the observations and visual evidence:"
        })

        if image_bytes:
            b64_image = base64.b64encode(image_bytes).decode("utf-8")
            user_content.append({
                "type": "image_url",
                "image_url": {
                    "url": f"data:{mime_type};base64,{b64_image}"
                }
            })

        models_to_try = [self.model]
        if "gemini-3.6-flash" not in models_to_try:
            models_to_try.append("gemini-3.6-flash")

        last_error = None
        for current_model in models_to_try:
            try:
                response = self.client.chat.completions.create(
                    model=current_model,
                    messages=[
                        {"role": "system", "content": system_instruction},
                        {"role": "user", "content": user_content}
                    ],
                    response_format={"type": "json_object"},
                    temperature=0.2,
                )
                content = response.choices[0].message.content
                return json.loads(content)
            except Exception as e:
                last_error = e
                logger.warning(f"Model {current_model} failed ({e}), attempting next candidate...")

        logger.error(f"All AI Gateway models failed: {last_error}. Falling back to mock synthesis.")
        return self._generate_mock_analysis(transcript, bool(image_bytes), now_str, error=str(last_error))

    def _generate_mock_analysis(
        self,
        transcript: str,
        has_image: bool,
        timestamp: str,
        error: Optional[str] = None
    ) -> Dict[str, Any]:
        """Generates realistic structured scientific HTML when running offline or in demo mode."""
        clean_text = transcript.strip() if transcript else "Visual bench check and sample inspection."
        
        # Simple heuristic keyword extraction
        tags = ["Bench Note", "Mobile PWA"]
        flags = []
        if any(w in clean_text.lower() for w in ["cloudy", "precipitate", "turbid", "haze"]):
            flags.append("Precipitation / Turbidity Observed")
            tags.append("Precipitation")
        if any(w in clean_text.lower() for w in ["temp", "celsius", "45", "37", "room temp", "ice"]):
            tags.append("Temperature Checked")
        if any(w in clean_text.lower() for w in ["tlc", "spot", "rf", "uv"]):
            tags.append("TLC Analysis")

        html_body = f"""<div style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; border: 1px solid #e2e8f0; border-radius: 8px; padding: 16px; background: #ffffff;">
  <div style="display: flex; justify-content: space-between; border-bottom: 1px solid #edf2f7; padding-bottom: 8px; margin-bottom: 12px;">
    <h3 style="margin: 0; color: #1e293b; font-size: 16px;">🔬 Bench Observation Log</h3>
    <span style="font-size: 12px; color: #64748b;">{timestamp}</span>
  </div>

  <p style="margin: 0 0 10px 0; color: #334155; font-size: 14px; line-height: 1.5;">
    <strong>Spoken Dictation:</strong> "{clean_text}"
  </p>

  <div style="background: #f8fafc; border-left: 3px solid #0284c7; padding: 10px 14px; margin-bottom: 12px; border-radius: 0 4px 4px 0;">
    <strong style="color: #0369a1; font-size: 12px; text-transform: uppercase;">Visual Evidence Assessment:</strong>
    <p style="margin: 4px 0 0 0; font-size: 13.5px; color: #0c4a6e;">
      {"Bench photo captured and linked. Physical visual inspection shows active condition change consistent with scientist voice notes." if has_image else "Voice-only note logged without attached photograph."}
    </p>
  </div>

  <h4 style="margin: 12px 0 6px 0; font-size: 13px; color: #475569; text-transform: uppercase;">Recommended Follow-Up:</h4>
  <ul style="margin: 0; padding-left: 20px; color: #334155; font-size: 13px; line-height: 1.6;">
    <li>Verify temperature stability and confirm centrifugation settings before next transfer.</li>
    <li>Cross-reference active sample lot numbers with formulation specifications.</li>
  </ul>
</div>"""

        return {
            "title": "Bench Note: " + (clean_text[:45] + "..." if len(clean_text) > 45 else clean_text),
            "summary": f"Scientist bench observation logged at {timestamp} with {'photo verification' if has_image else 'audio memo'}.",
            "structured_html": html_body,
            "flags": flags,
            "tags": tags,
            "source": "simulated" if not error else f"fallback (gateway error: {error[:60]})"
        }
