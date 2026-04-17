"""Vision Service — Phase 4 implementation using Ollama vision models."""

import base64
import json
import httpx
from typing import Optional, List, Dict
import structlog
from app.config import settings

logger = structlog.get_logger()

class VisionService:
    """Phase 4: Blueprint analysis using vision LLMs."""

    def __init__(self):
        self.endpoint = settings.hermes_endpoint_url.replace("/v1", "/api/generate")
        self.model = settings.llm_vision_model

    async def classify_sheet(self, image_bytes: bytes) -> Dict:
        """
        Classify a blueprint sheet type (plumbing, mechanical, architectural, etc).
        """
        prompt = """
        Analyze this blueprint page image. 
        Identify the sheet type. Is it a Plumbing plan, Mechanical plan, Architectural plan, Site plan, or something else?
        Also look for a Sheet Number (e.g. P101, A201) and a Title.
        Return ONLY valid JSON:
        {
          "sheet_type": "plumbing" | "mechanical" | "architectural" | "site" | "other",
          "sheet_number": string | null,
          "title": string | null,
          "confidence": float (0.0-1.0)
        }
        """
        
        try:
            image_b64 = base64.b64encode(image_bytes).decode("utf-8")
            
            async with httpx.AsyncClient(timeout=60.0) as client:
                resp = await client.post(
                    self.endpoint,
                    json={
                        "model": self.model,
                        "prompt": prompt,
                        "stream": False,
                        "format": "json",
                        "images": [image_b64]
                    }
                )
                resp.raise_for_status()
                data = resp.json()
                result = json.loads(data.get("response", "{}"))
                return result
        except Exception as e:
            logger.error("vision.classify_error", error=str(e), model=self.model)
            return {"sheet_type": "unknown", "confidence": 0.0}

    async def detect_fixtures(self, image_bytes: bytes) -> List[Dict]:
        """
        Detect plumbing fixtures in a blueprint image.
        """
        prompt = """
        Analyze this plumbing blueprint image. 
        Identify and count all plumbing fixtures (toilets, lavatories, sinks, floor drains, water heaters, shower valves).
        For each type found, provide the count.
        Return ONLY valid JSON:
        {
          "fixtures": [
            {"type": "toilet", "count": 3, "confidence": 0.9},
            {"type": "lavatory", "count": 2, "confidence": 0.8}
          ]
        }
        """
        
        try:
            image_b64 = base64.b64encode(image_bytes).decode("utf-8")
            
            async with httpx.AsyncClient(timeout=90.0) as client:
                resp = await client.post(
                    self.endpoint,
                    json={
                        "model": self.model,
                        "prompt": prompt,
                        "stream": False,
                        "format": "json",
                        "images": [image_b64]
                    }
                )
                resp.raise_for_status()
                data = resp.json()
                result = json.loads(data.get("response", "{}"))
                return result.get("fixtures", [])
        except Exception as e:
            logger.error("vision.detect_error", error=str(e), model=self.model)
            return []

vision_service = VisionService()
