"""Vision Service — Phase 4 implementation using Ollama vision models."""

import base64
import json
import httpx
from typing import Optional, List, Dict
import structlog
from app.config import settings

logger = structlog.get_logger()

# Module-level singletons — reuse connection pools across requests
_classify_client: httpx.AsyncClient | None = None
_extract_client: httpx.AsyncClient | None = None


def _get_classify_client() -> httpx.AsyncClient:
    global _classify_client
    if _classify_client is None or _classify_client.is_closed:
        _classify_client = httpx.AsyncClient(timeout=60.0)
    return _classify_client


def _get_extract_client() -> httpx.AsyncClient:
    global _extract_client
    if _extract_client is None or _extract_client.is_closed:
        _extract_client = httpx.AsyncClient(timeout=90.0)
    return _extract_client


class VisionService:
    """Phase 4: Blueprint analysis using vision LLMs."""

    def __init__(self):
        self.endpoint = settings.hermes_endpoint_url.replace("/v1", "/api/generate")
        self.model = settings.llm_vision_model

    async def classify_sheet(self, image_bytes: bytes, ocr_hint: Optional[str] = None) -> Dict:
        """
        Classify a blueprint sheet type (plumbing, mechanical, architectural, etc).

        ``ocr_hint`` — optional snippet of native PDF text from the page header /
        title block, used to ground the classifier without forcing it to read
        every glyph from a low-res rendering.
        """
        prompt_parts = [
            "Analyze this blueprint page image.",
            "Identify the sheet type. Is it a Plumbing plan, Mechanical plan, "
            "Architectural plan, Site plan, or something else?",
            "Also look for a Sheet Number (e.g. P101, A201) and a Title.",
        ]
        if ocr_hint:
            prompt_parts.append(f"Native text on the page (use as a hint): {ocr_hint[:1500]}")
        prompt_parts.append(
            'Return ONLY valid JSON: {"sheet_type": "plumbing"|"mechanical"|'
            '"architectural"|"site"|"other","sheet_number": string|null,'
            '"title": string|null,"confidence": float}'
        )
        prompt = "\n".join(prompt_parts)
        
        try:
            image_b64 = base64.b64encode(image_bytes).decode("utf-8")
            client = _get_classify_client()
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

    async def detect_fixtures(self, image_bytes: bytes, ocr_hint: Optional[str] = None) -> Dict:
        """
        Detect plumbing fixtures in a blueprint image.

        Returns a dict: {"status": "ok"|"error", "fixtures": [...], "error": str|None}
        Callers can distinguish "vision succeeded with zero fixtures" from
        "vision call failed".
        """
        prompt_parts = [
            "You are a plumbing estimator analyzing a plumbing blueprint sheet.",
            "Identify and count every plumbing fixture or rough-in shown.",
            "Use these canonical types (lowercase, snake_case):",
            "  toilet, water_closet, urinal, lavatory, kitchen_sink, mop_sink, "
            "  laundry_sink, bar_sink, prep_sink, shower, tub, tub_shower, "
            "  water_heater, tankless_water_heater, floor_drain, hose_bib, "
            "  washing_machine, dishwasher, disposal, ice_maker, "
            "  gas_appliance, prv, water_softener, backflow_preventer, "
            "  drinking_fountain, eye_wash, sink",
            "For each distinct type found, return one entry with the total count.",
            "Be conservative: if you are unsure a symbol is plumbing, do NOT include it.",
        ]
        if ocr_hint:
            prompt_parts.append(f"Native PDF text from this page (legend, schedule, notes): {ocr_hint[:2000]}")
        prompt_parts.append(
            'Return ONLY valid JSON: {"fixtures":[{"type": string,"count": int,"confidence": float}]}'
        )
        prompt = "\n".join(prompt_parts)
        
        try:
            image_b64 = base64.b64encode(image_bytes).decode("utf-8")
            client = _get_extract_client()
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
            return {"status": "ok", "fixtures": result.get("fixtures", []), "error": None}
        except Exception as e:
            logger.error("vision.detect_error", error=str(e), model=self.model)
            return {"status": "error", "fixtures": [], "error": str(e)}

    async def describe_photo(self, image_bytes: bytes, hint: Optional[str] = None) -> Dict:
        """
        Phase 3 — analyze a field photo (single image) for plumbing items.

        Returns a structured dict the quick-quote service can map to labor
        templates:

            {
              "status": "ok"|"error",
              "items": [{"type": str, "count": int, "confidence": float,
                         "condition": "ok"|"leaking"|"broken"|"corroded"|"missing"|null,
                         "brand": str|null, "model": str|null, "size": str|null,
                         "notes": str|null}],
              "scene": "kitchen"|"bathroom"|"laundry"|"mechanical"|"exterior"|"unknown",
              "summary": str,
              "error": str|None
            }
        """
        prompt_parts = [
            "You are a senior plumber inspecting a field photo from a job site.",
            "Identify every plumbing item visible (fixtures, valves, water heaters, "
            "pipes, traps, supply lines, gas appliances, etc.) and any visible problems.",
            "Use these canonical item types (lowercase snake_case):",
            "  toilet, lavatory, kitchen_sink, faucet_kitchen, faucet_lavatory, "
            "  shower_valve, tub_spout, tub_shower, shower_head, water_heater, "
            "  tankless_water_heater, garbage_disposal, dishwasher, washing_machine, "
            "  ice_maker_line, hose_bib, angle_stop, supply_line, p_trap, "
            "  s_trap, vent, cleanout, prv, water_softener, backflow_preventer, "
            "  gas_valve, gas_appliance, floor_drain, sump_pump, ejector_pump, "
            "  pipe_pvc, pipe_copper, pipe_pex, pipe_galvanized, pipe_cast_iron, "
            "  leak, corrosion, water_damage, mold, other",
            "For condition use one of: ok, leaking, broken, corroded, missing, null.",
            "If a brand or model is legible (Rheem, Moen, Delta, Kohler, AO Smith, "
            "Bradford White, Navien, Rinnai, etc.), include it.",
            "Sizes (e.g. 40 gal, 50 gal, 1/2\", 3/4\") should be in `size`.",
            "Be conservative: if you are unsure, lower the confidence; do not invent items.",
        ]
        if hint:
            prompt_parts.append(f"User's note about this photo: {hint[:500]}")
        prompt_parts.append(
            'Return ONLY valid JSON of the form: '
            '{"items":[{"type":string,"count":int,"confidence":float,'
            '"condition":string|null,"brand":string|null,"model":string|null,'
            '"size":string|null,"notes":string|null}],'
            '"scene":"kitchen"|"bathroom"|"laundry"|"mechanical"|"exterior"|"unknown",'
            '"summary":string}'
        )
        prompt = "\n".join(prompt_parts)

        try:
            image_b64 = base64.b64encode(image_bytes).decode("utf-8")
            client = _get_extract_client()
            resp = await client.post(
                self.endpoint,
                json={
                    "model": self.model,
                    "prompt": prompt,
                    "stream": False,
                    "format": "json",
                    "images": [image_b64],
                },
            )
            resp.raise_for_status()
            data = resp.json()
            result = json.loads(data.get("response", "{}"))
            return {
                "status": "ok",
                "items": result.get("items", []) or [],
                "scene": result.get("scene", "unknown"),
                "summary": result.get("summary", "") or "",
                "error": None,
            }
        except Exception as e:
            logger.error("vision.describe_photo_error", error=str(e), model=self.model)
            return {"status": "error", "items": [], "scene": "unknown",
                    "summary": "", "error": str(e)}


vision_service = VisionService()
