"""
Load external pricing templates from web/templates/pricing and expose simple accessors.
This keeps the JSON files as the source of truth and serves them via the API.
"""
from pathlib import Path
import json
from typing import Dict, Any, List, Optional

_project_root = Path(__file__).resolve().parents[3]
_templates_dir = _project_root / "web" / "templates" / "pricing"

_TEMPLATES: Dict[str, Dict[str, Any]] = {}


def _load_templates() -> None:
    global _TEMPLATES
    _TEMPLATES = {}
    if not _templates_dir.exists():
        return

    for p in sorted(_templates_dir.glob("*.json")):
        try:
            data = json.loads(p.read_text(encoding="utf-8"))
        except Exception:
            continue

        # Ensure there is an id field; fall back to filename without extension
        tpl_id = data.get("id") or p.stem
        data["_source_file"] = str(p.relative_to(_project_root))
        _TEMPLATES[str(tpl_id)] = data


# Load on import
_load_templates()


def list_pricing_templates() -> List[Dict[str, Any]]:
    """Return a shallow list of templates (id, name, description, tags)."""
    out = []
    for tpl in _TEMPLATES.values():
        out.append({
            "id": tpl.get("id"),
            "name": tpl.get("name"),
            "description": tpl.get("description"),
            "sku": tpl.get("sku"),
            "base_price": tpl.get("base_price"),
            "region": tpl.get("region"),
            "tags": tpl.get("tags", []),
        })
    return out


def get_pricing_template(template_id: str) -> Optional[Dict[str, Any]]:
    return _TEMPLATES.get(template_id)


def refresh_templates() -> None:
    """Re-scan the templates directory and refresh cached templates."""
    _load_templates()
