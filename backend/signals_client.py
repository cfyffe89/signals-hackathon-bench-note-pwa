import os
import logging
import requests
from typing import List, Dict, Any, Optional

logger = logging.getLogger("signals_client")

class SignalsClient:
    def __init__(self, base_url: Optional[str] = None, api_key: Optional[str] = None):
        self.base_url = (base_url or os.getenv("SIGNALS_BASE_URL", "https://hackathon.signalsnotebook.revvitycloud.com/api/rest/v1.0")).rstrip("/")
        self.api_key = api_key or os.getenv("SIGNALS_API_KEY", "")
        self.mock_mode = os.getenv("MOCK_MODE", "false").lower() == "true" or not self.api_key or "your-" in self.api_key

    def _headers(self, content_type: str = "application/vnd.api+json") -> Dict[str, str]:
        return {
            "x-api-key": self.api_key,
            "Content-Type": content_type
        }

    def list_experiments(self) -> List[Dict[str, Any]]:
        """Fetch list of accessible experiments to populate the mobile selector."""
        if self.mock_mode:
            logger.info("Using mock experiments list (MOCK_MODE=True)")
            return [
                {
                    "eid": "experiment:e323ff17-15c4-4706-9bf3-7f2e12a40001",
                    "name": "EXP-2026-081: Suzuki-Miyaura Pyridine Optimization",
                    "modifiedAt": "2026-09-14T18:30:00Z"
                },
                {
                    "eid": "experiment:e323ff17-15c4-4706-9bf3-7f2e12a40002",
                    "name": "EXP-2026-094: Formulation Batch 4B Viscosity Stability",
                    "modifiedAt": "2026-09-15T09:15:00Z"
                },
                {
                    "eid": "experiment:e323ff17-15c4-4706-9bf3-7f2e12a40003",
                    "name": "EXP-2026-102: HTRF Kinase Dose-Response Assay Plate 3",
                    "modifiedAt": "2026-09-15T10:45:00Z"
                }
            ]

        url = f"{self.base_url}/entities"
        params = {
            "filter[type]": "experiment",
            "page[limit]": 20
        }
        try:
            res = requests.get(url, headers=self._headers(), params=params, timeout=10)
            res.raise_for_status()
            data = res.json().get("data", [])
            experiments = []
            for item in data:
                attributes = item.get("attributes", {})
                experiments.append({
                    "eid": item.get("id"),
                    "name": attributes.get("name", "Untitled Experiment"),
                    "modifiedAt": attributes.get("modifiedAt")
                })
            return experiments
        except Exception as e:
            logger.error(f"Error fetching experiments from Signals: {e}")
            if self.mock_mode or True:
                # Fallback to demo items if sandbox network is unreachable
                return [
                    {
                        "eid": os.getenv("DEFAULT_EXPERIMENT_EID", "experiment:demo-default-101"),
                        "name": "DEMO: Active Formulation Bench Experiment",
                        "modifiedAt": "2026-09-15T11:00:00Z"
                    }
                ]

    def upload_child_attachment(
        self,
        parent_eid: str,
        filename: str,
        content_bytes: bytes,
        content_type: str = "application/octet-stream"
    ) -> Dict[str, Any]:
        """
        Uploads a file directly as a child entity of an experiment.
        Uses POST /entities/{parent_eid}/children/{filename}?force=true.
        - If filename is .html, Signals Notebook displays it as an interactive Text Element.
        - If filename is .jpg/.png, Signals displays it as an Image Element.
        - The force=true query parameter avoids 401/409 digest mismatch errors.
        """
        if self.mock_mode:
            logger.info(f"[MOCK] Uploading {filename} ({len(content_bytes)} bytes, {content_type}) to {parent_eid}")
            return {
                "status": "mock_success",
                "id": f"attachment:{filename}-mock-eid",
                "filename": filename,
                "parentEid": parent_eid,
                "sizeBytes": len(content_bytes),
                "contentType": content_type
            }

        url = f"{self.base_url}/entities/{parent_eid}/children/{filename}?force=true"
        headers = self._headers(content_type=content_type)

        try:
            res = requests.post(url, headers=headers, data=content_bytes, timeout=30)
            res.raise_for_status()
            return res.json()
        except requests.HTTPError as e:
            logger.error(f"Failed to upload {filename} to Signals: {e.response.status_code} - {e.response.text}")
            raise
        except Exception as e:
            logger.error(f"Network error during upload to Signals: {e}")
            raise
