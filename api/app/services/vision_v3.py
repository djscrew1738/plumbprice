"""
Vision Service v3 — Enhanced blueprint analysis with rooms, pipe runs, and bounding boxes.

Extends the v1 vision pipeline with:
- Fixture detection v2: bounding boxes for review UI highlighting
- Room detection: spatial layout extraction
- Pipe run estimation: linear takeoff for piping

All prompts are conservative — low-confidence detections are flagged for review.
"""

import base64
import json
import httpx
from typing import Optional, Dict, Any
import structlog
from app.config import settings

logger = structlog.get_logger()

_vision_client: httpx.AsyncClient | None = None


def _get_vision_client() -> httpx.AsyncClient:
    global _vision_client
    if _vision_client is None or _vision_client.is_closed:
        _vision_client = httpx.AsyncClient(timeout=120.0)
    return _vision_client


class VisionServiceV3:
    """v3 vision pipeline with spatial intelligence.

    v4.1 upgrade: supports GPT-4V (VISION_PROVIDER=openai) with Ollama as fallback.
    Detection confidence < VISION_DETECTION_REVIEW_THRESHOLD is flagged for review.
    """

    def __init__(self):
        self.endpoint = settings.hermes_endpoint_url.replace("/v1", "/api/generate")
        self.model = settings.llm_vision_model

    # ── Internal helpers ──────────────────────────────────────────────────────

    async def _call_vision(
        self,
        image_bytes: bytes,
        prompt: str,
        timeout: float = 120.0,
    ) -> Optional[Dict[str, Any]]:
        """Call the configured vision provider with a prompt and image.

        Routes to GPT-4V when VISION_PROVIDER=openai; falls back to Ollama.
        """
        if settings.vision_provider == "openai" and settings.openai_api_key:
            return await self._call_gpt4v(image_bytes, prompt, timeout=timeout)
        return await self._call_ollama(image_bytes, prompt, timeout=timeout)

    async def _call_gpt4v(
        self,
        image_bytes: bytes,
        prompt: str,
        timeout: float = 120.0,
    ) -> Optional[Dict[str, Any]]:
        """Call GPT-4V via the OpenAI Chat Completions API with image_url format."""
        try:
            import openai

            image_b64 = base64.b64encode(image_bytes).decode("utf-8")
            client = openai.AsyncOpenAI(
                api_key=settings.openai_api_key,
                timeout=timeout,
            )
            response = await client.chat.completions.create(
                model="gpt-4o",
                response_format={"type": "json_object"},
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:image/jpeg;base64,{image_b64}",
                                    "detail": "high",
                                },
                            },
                            {"type": "text", "text": prompt},
                        ],
                    }
                ],
                max_tokens=2048,
            )
            raw = response.choices[0].message.content or "{}"
            return json.loads(raw)
        except Exception as exc:
            logger.warning("vision_v3.gpt4v_failed", error=str(exc))
            # Fall back to Ollama
            return await self._call_ollama(image_bytes, prompt, timeout=timeout)

    async def _call_ollama(
        self,
        image_bytes: bytes,
        prompt: str,
        timeout: float = 120.0,
    ) -> Optional[Dict[str, Any]]:
        """Call Ollama vision model with a prompt and image."""
        try:
            image_b64 = base64.b64encode(image_bytes).decode("utf-8")
            client = _get_vision_client()
            resp = await client.post(
                self.endpoint,
                json={
                    "model": self.model,
                    "prompt": prompt,
                    "stream": False,
                    "format": "json",
                    "images": [image_b64],
                },
                timeout=timeout,
            )
            resp.raise_for_status()
            data = resp.json()
            raw = data.get("response", "{}")
            return json.loads(raw)
        except Exception as exc:
            logger.warning("vision_v3.ollama_failed", error=str(exc), model=self.model)
            return None

    # ── Sheet classification (unchanged from v1) ──────────────────────────────

    async def classify_sheet(self, image_bytes: bytes, ocr_hint: Optional[str] = None) -> Dict[str, Any]:
        """Classify a blueprint sheet type."""
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
        result = await self._call_vision(image_bytes, "\n".join(prompt_parts), timeout=60.0)
        if result is None:
            return {"sheet_type": "unknown", "confidence": 0.0}
        return result

    # ── Fixture detection v2 (with bounding boxes) ────────────────────────────

    async def detect_fixtures_v2(
        self,
        image_bytes: bytes,
        ocr_hint: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Detect plumbing fixtures with bounding boxes for review UI highlighting.

        Returns: {"fixtures": [{"type", "count", "confidence", "bounding_box": {x,y,w,h}}]}
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
            "Also provide a bounding_box for the most representative instance of each type.",
            "The bounding_box should be in pixel coordinates relative to the image: {x, y, w, h}.",
        ]
        if ocr_hint:
            prompt_parts.append(f"Native PDF text from this page (legend, schedule, notes): {ocr_hint[:2000]}")
        prompt_parts.append(
            'Return ONLY valid JSON: {"fixtures":[{"type": string,"count": int,'
            '"confidence": float,"bounding_box": {"x": int,"y": int,"w": int,"h": int}}]}'
        )

        result = await self._call_vision(image_bytes, "\n".join(prompt_parts), timeout=120.0)
        if result is None:
            return {"fixtures": [], "error": "vision call failed"}

        # Validate, sanitize, and flag low-confidence detections for review
        review_threshold = settings.vision_detection_review_threshold
        fixtures = []
        for f in result.get("fixtures", []):
            fixture_type = str(f.get("type", "")).lower().strip()
            count = max(1, min(100, int(f.get("count", 1))))
            confidence = max(0.0, min(1.0, float(f.get("confidence", 0.0))))
            bbox = f.get("bounding_box")
            if bbox and isinstance(bbox, dict):
                bbox = {
                    "x": int(bbox.get("x", 0)),
                    "y": int(bbox.get("y", 0)),
                    "w": int(bbox.get("w", 0)),
                    "h": int(bbox.get("h", 0)),
                }
            else:
                bbox = None

            fixtures.append({
                "type": fixture_type,
                "count": count,
                "confidence": confidence,
                "bounding_box": bbox,
                "needs_review": confidence < review_threshold,
            })

        return {"fixtures": fixtures}

    # ── Room detection (NEW) ──────────────────────────────────────────────────

    async def detect_rooms(
        self,
        image_bytes: bytes,
        ocr_hint: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Detect rooms and their spatial layout from a blueprint.

        Returns: {"rooms": [{"type", "name", "bounding_box": {x,y,w,h}, "area_sqft", "confidence"}]}
        """
        prompt_parts = [
            "You are analyzing an architectural or plumbing floor plan.",
            "Identify every distinct room or space shown on the plan.",
            "For each room, determine:",
            "  - room_type: bathroom | kitchen | utility | bedroom | living_room | "
            "garage | closet | hallway | other",
            "  - room_name: a descriptive name like 'Master Bath' or 'Kitchen'",
            "  - bounding_box: pixel coordinates {x, y, w, h} of the room outline",
            "  - area_sqft: approximate area in square feet (if scale is visible)",
            "  - fixture_count: number of plumbing fixtures visible in this room",
            "Be conservative. If a room boundary is unclear, skip it.",
        ]
        if ocr_hint:
            prompt_parts.append(f"Native PDF text (room labels, schedules): {ocr_hint[:1500]}")
        prompt_parts.append(
            'Return ONLY valid JSON: {"rooms":[{"type": string,"name": string,'
            '"bounding_box": {"x": int,"y": int,"w": int,"h": int},'
            '"area_sqft": float|null,"fixture_count": int|null,"confidence": float}]}'
        )

        result = await self._call_vision(image_bytes, "\n".join(prompt_parts), timeout=120.0)
        if result is None:
            return {"rooms": [], "error": "vision call failed"}

        rooms = []
        for r in result.get("rooms", []):
            room_type = str(r.get("type", "other")).lower().strip()
            room_name = str(r.get("name", "")).strip() or None
            confidence = max(0.0, min(1.0, float(r.get("confidence", 0.0))))
            area_sqft = r.get("area_sqft")
            if area_sqft is not None:
                try:
                    area_sqft = float(area_sqft)
                except (TypeError, ValueError):
                    area_sqft = None
            fixture_count = r.get("fixture_count")
            if fixture_count is not None:
                try:
                    fixture_count = int(fixture_count)
                except (TypeError, ValueError):
                    fixture_count = None

            bbox = r.get("bounding_box")
            if bbox and isinstance(bbox, dict):
                bbox = {
                    "x": int(bbox.get("x", 0)),
                    "y": int(bbox.get("y", 0)),
                    "w": int(bbox.get("w", 0)),
                    "h": int(bbox.get("h", 0)),
                }
            else:
                bbox = None

            rooms.append({
                "type": room_type,
                "name": room_name,
                "bounding_box": bbox,
                "area_sqft": area_sqft,
                "fixture_count": fixture_count,
                "confidence": confidence,
            })

        return {"rooms": rooms}

    # ── Pipe run detection (NEW) ──────────────────────────────────────────────

    async def detect_pipe_runs(
        self,
        image_bytes: bytes,
        px_per_ft: Optional[float] = None,
        ocr_hint: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Detect pipe runs and estimate linear footage from a blueprint.

        Returns: {"pipe_runs": [{"pipe_type", "length_ft", "start_point", "end_point", "confidence"}]}
        """
        scale_hint = ""
        if px_per_ft:
            scale_hint = f"The scale for this sheet is {px_per_ft:.1f} pixels per foot. "

        prompt_parts = [
            "You are analyzing a plumbing plan (P-plan or plumbing plan sheet).",
            "Identify every visible pipe run (solid or dashed lines connecting fixtures).",
            "For each pipe run, determine:",
            "  - pipe_type: copper_3_4 | copper_1 | pvc_4 | pvc_6 | pex_1 | pex_3_4 | gas_1 | drain_4 | abs_3 | abs_4 | other",
            "  - from_fixture: the plumbing fixture or element where this run originates (e.g. 'toilet', 'lavatory', 'water_heater', 'drain_stack')",
            "  - to_fixture: the plumbing fixture or element where this run terminates",
            "  - material_type: copper | pvc | pex | abs | galvanized | cast_iron | other",
            "  - start_point: {x, y} pixel coordinates of the pipe start",
            "  - end_point: {x, y} pixel coordinates of the pipe end",
            "  - length_ft: approximate length in feet (use the scale if visible, or your best estimate from the image)",
            "  - bounding_box: {x, y, w, h} enclosing the pipe run",
            "Be very conservative. Only include clearly visible, continuous pipe runs.",
            "Do NOT guess pipe sizes — use 'other' if unsure.",
        ]
        if scale_hint:
            prompt_parts.insert(1, scale_hint)
        if ocr_hint:
            prompt_parts.append(f"Native PDF text (pipe schedule, notes): {ocr_hint[:1500]}")
        prompt_parts.append(
            'Return ONLY valid JSON: {"pipe_runs":[{"pipe_type": string,'
            '"from_fixture": string,"to_fixture": string,"material_type": string,'
            '"start_point": {"x": int,"y": int},"end_point": {"x": int,"y": int},'
            '"length_ft": float|null,"bounding_box": {"x": int,"y": int,"w": int,"h": int},'
            '"confidence": float}]}'
        )

        result = await self._call_vision(image_bytes, "\n".join(prompt_parts), timeout=120.0)
        if result is None:
            return {"pipe_runs": [], "error": "vision call failed"}

        review_threshold = settings.vision_detection_review_threshold
        pipe_runs = []
        for pr in result.get("pipe_runs", []):
            pipe_type = str(pr.get("pipe_type", "other")).lower().strip()
            confidence = max(0.0, min(1.0, float(pr.get("confidence", 0.0))))
            length_ft = pr.get("length_ft")
            if length_ft is not None:
                try:
                    length_ft = float(length_ft)
                except (TypeError, ValueError):
                    length_ft = None

            start_point = pr.get("start_point")
            end_point = pr.get("end_point")
            bbox = pr.get("bounding_box")

            def _parse_point(p):
                if p and isinstance(p, dict):
                    return {"x": int(p.get("x", 0)), "y": int(p.get("y", 0))}
                return None

            pipe_runs.append({
                "pipe_type": pipe_type,
                "from_fixture": pr.get("from_fixture"),
                "to_fixture": pr.get("to_fixture"),
                "material_type": pr.get("material_type", "other"),
                "start_point": _parse_point(start_point),
                "end_point": _parse_point(end_point),
                "length_ft": length_ft,
                "bounding_box": bbox if isinstance(bbox, dict) else None,
                "confidence": confidence,
                "needs_review": confidence < review_threshold,
                # routing_json: structured for blueprint_pipe_runs.routing_json column
                "routing_json": {
                    "from_fixture": pr.get("from_fixture"),
                    "to_fixture": pr.get("to_fixture"),
                    "material_type": pr.get("material_type", "other"),
                    "pipe_type": pipe_type,
                },
            })

        return {"pipe_runs": pipe_runs}

    # ── Photo analysis (unchanged from v1) ────────────────────────────────────

    async def describe_photo(self, image_bytes: bytes) -> Dict[str, Any]:
        """Analyze a field photo for the quick-quote flow."""
        prompt = (
            "Describe what you see in this plumbing-related photo. "
            "Identify the fixture, problem, or context. "
            "Return JSON: {\"description\": string, \"fixture_type\": string|null, "
            "\"issue\": string|null, \"confidence\": float}"
        )
        result = await self._call_vision(image_bytes, prompt, timeout=60.0)
        if result is None:
            return {"description": "", "confidence": 0.0}
        return result


# ── Singleton ─────────────────────────────────────────────────────────────────

vision_service_v3 = VisionServiceV3()
