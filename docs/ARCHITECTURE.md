# PlumbPrice AI — System Architecture

## 1. System Overview

PlumbPrice AI is a purpose-built estimating platform for DFW-area plumbing contractors. It replaces
spreadsheet-based estimating with a chat-driven interface that produces itemized, line-level quotes
backed by real supplier pricing. The system is designed around one core guarantee: every price shown
to the user can be traced directly to a supplier SKU and a labor template — no opaque AI black boxes
in the calculation path.

The platform is scoped to residential service and remodel work in the Dallas–Fort Worth metroplex,
with a supplier network of Ferguson Enterprises, Moore Supply Co., and Apex Supply. Tax rates are
county-aware (Tarrant, Dallas, Collin, Denton, etc.). Labor rates reflect licensed master plumber
plus journeyman helper staffing norms for the region.

### Design Principles

1. **Deterministic pricing.** The LLM extracts intent and maps it to canonical line items. All
   dollar math happens in pure Python with no LLM involvement. The same inputs must always produce
   the same dollar output.

2. **Full traceability.** Every line item on an estimate carries a `trace_json` blob identifying
   the supplier, SKU, cost at time of quote, labor template code, multipliers applied, and any
   assumptions made.

3. **Confidence transparency.** The system surfaces a 0.0–1.0 confidence score and a human-readable
   label (High / Medium / Low / Estimate-Only) on every estimate. Scores degrade automatically when
   supplier prices go stale.

4. **Phase-gated complexity.** The platform ships useful functionality in Phase 1 before adding
   document RAG (Phase 3) or computer vision blueprint analysis (Phase 4). Worker stubs for future
   phases are present but return no-ops today.

---

## 2. Service Architecture

```
                          ┌─────────────────────────────────────────┐
                          │             Browser / Mobile            │
                          │         React + Vite (port 5173)        │
                          └──────────────────┬──────────────────────┘
                                             │ HTTPS / REST
                          ┌──────────────────▼──────────────────────┐
                          │          FastAPI API (port 8000)        │
                          │   /api/v1/chat  /api/v1/estimates       │
                          │   /api/v1/suppliers  /api/v1/admin      │
                          └──────┬───────────────────────┬──────────┘
                                 │                       │
               ┌─────────────────▼──────┐   ┌───────────▼───────────┐
               │  PostgreSQL 16 + pgvec │   │    Redis 7 (cache +   │
               │  (primary data store)  │   │    Celery broker)     │
               └────────────────────────┘   └───────────┬───────────┘
                                                        │
                          ┌─────────────────────────────▼──────────┐
                          │        Celery Worker (Python)          │
                          │  tasks.supplier_refresh  (daily beat)  │
                          │  tasks.document_processing (Phase 3)   │
                          │  tasks.blueprint_analysis  (Phase 4)   │
                          └──────────────────┬─────────────────────┘
                                             │
                          ┌──────────────────▼──────────────────────┐
                          │        MinIO (object storage)           │
                          │  supplier PDFs / blueprints / exports   │
                          └─────────────────────────────────────────┘
```

All services run in Docker containers orchestrated by `docker-compose.yml`. In production the API
and worker images are built from the same `api/Dockerfile`; the worker simply overrides the
entrypoint command. The web container serves the Vite build via Nginx.

### Service Responsibilities

| Service   | Image              | Responsibility                                         |
|-----------|--------------------|--------------------------------------------------------|
| api       | plumbprice/api     | REST endpoints, LLM routing, pricing engine            |
| worker    | plumbprice/api     | Async tasks: price refresh, doc processing, blueprints |
| beat      | plumbprice/api     | Celery Beat scheduler (daily supplier refresh)         |
| db        | pgvector/pgvector  | Primary relational + vector store                      |
| redis     | redis:7-alpine     | Celery broker, result backend, API cache               |
| minio     | minio/minio        | S3-compatible object store for uploaded files          |
| web       | nginx:alpine       | Static file serving + /api proxy pass                  |

---

## 3. Database Design

The schema lives in `api/alembic/versions/001_initial_schema.py`. All tables use integer surrogate
primary keys. `created_at` / `updated_at` are timezone-aware timestamps.

### Core Entity Groups

**Tenant / Auth**
- `organizations` — the plumbing company. Single-tenant in Phase 1; schema supports multi-tenant.
- `users` — employees with `role` (admin, estimator, field_tech).

**Pricing Reference Data** (read-heavy, seeded, refreshed by worker)
- `suppliers` — Ferguson, Moore Supply, Apex. `slug` is used as a stable identifier in code.
- `supplier_products` — one row per (supplier, canonical_item) pair. `canonical_item` is the
  product-agnostic key (e.g., `"toilet_elongated_standard"`) used to join across suppliers.
  `confidence_score` is a float 0.0–1.0; the daily worker decrements scores on stale rows.
- `supplier_price_history` — append-only price audit trail. Written whenever `cost` changes.
- `labor_templates` — installation time standards keyed by `code` (e.g., `"toilet_replace"`).
  Stores base hours, lead/helper rates, access multipliers, urgency multipliers as JSONB.
- `material_assemblies` — bill-of-materials templates. Each assembly maps to a list of
  canonical_items with quantities. Used to explode a single "replace toilet" line into all parts.
- `markup_rules` — per-job-type markup percentages (residential, commercial, warranty).

**Estimates**
- `estimates` — the root estimate record with totals, confidence score, county, tax rate.
- `estimate_line_items` — individual labor, material, and misc lines. Each carries `trace_json`
  with full cost provenance.
- `estimate_versions` — immutable snapshots taken before any edit. Enables full revision history.
- `assumptions_log` — every assumption the system made (e.g., "assumed standard access") is
  recorded here for audit and AI fine-tuning.

**Document RAG (Phase 3)**
- `uploaded_documents` — uploaded supplier catalogs, spec sheets, manufacturer docs.
- `document_chunks` — text chunks with embedding vectors (pgvector column added in Phase 3).

**Blueprint Analysis (Phase 4)**
- `blueprint_jobs` — uploaded PDF blueprint sets.
- `blueprint_pages` — individual pages rendered to images.
- `blueprint_detections` — fixture detections with bounding boxes and confidence scores.

**Audit**
- `audit_logs` — table-level change log for compliance. Written by application layer, not triggers.

### Key Design Decisions

- **`canonical_item` as the join key** rather than supplier SKU. This decouples the pricing
  engine from supplier catalog churn. When Ferguson changes a SKU, only `supplier_products` needs
  updating; the assembly and labor template references remain stable.

- **JSONB for flexible data, not for queryable fields.** `config_json` on labor templates and
  `trace_json` on line items store structured blobs that the application reads. Anything that needs
  to be filtered or indexed gets a dedicated column.

- **pgvector extension** enabled in migration 001 even though vectors are not used until Phase 3.
  This avoids a disruptive schema migration later and has zero overhead until the column is added.

- **Float for money.** In Phase 1, float precision is acceptable because all prices are displayed
  to two decimal places and rounding errors at the cent level do not affect business decisions.
  A future migration to `NUMERIC(10,2)` is straightforward.

---

## 4. Pricing Engine Design

The pricing engine is the most critical component of the system. It must be deterministic,
auditable, and never rely on an LLM for arithmetic.

### Data Flow: Chat to Estimate

```
User message
    │
    ▼
┌─────────────────────────────────────────────┐
│  LLM Intent Extraction (OpenAI GPT-4o)      │
│  Input:  user message + chat history        │
│  Output: structured JSON                    │
│    { job_type, county, fixtures: [          │
│        { canonical_item, quantity,          │
│          access_level, urgency }            │
│    ], assumptions: [...] }                  │
└──────────────────┬──────────────────────────┘
                   │  structured intent only — no math
                   ▼
┌─────────────────────────────────────────────┐
│  Assembly Resolver                          │
│  canonical_item -> material_assembly        │
│  Explodes each fixture into canonical parts │
│  with quantities                            │
└──────────────────┬──────────────────────────┘
                   │
                   ▼
┌─────────────────────────────────────────────┐
│  Supplier Pricer                            │
│  For each canonical_item:                   │
│  1. Query supplier_products WHERE           │
│     canonical_item = X AND supplier = pref  │
│  2. If not found, fallback to best price    │
│     across all active suppliers             │
│  3. Record source, SKU, confidence_score    │
└──────────────────┬──────────────────────────┘
                   │
                   ▼
┌─────────────────────────────────────────────┐
│  Labor Calculator                           │
│  For each fixture:                          │
│  hours = base_hours                         │
│        * access_multipliers[access_level]   │
│        * urgency_multipliers[urgency]       │
│  lead_cost   = hours * lead_rate            │
│  helper_cost = helper_hours * helper_rate   │
│  disposal    = disposal_hours * lead_rate   │
└──────────────────┬──────────────────────────┘
                   │
                   ▼
┌─────────────────────────────────────────────┐
│  Markup & Tax Engine                        │
│  materials_total * (1 + materials_markup)   │
│  labor_total    * (1 + labor_markup)        │
│  misc_flat (truck charge, consumables)      │
│  tax = materials_total * county_tax_rate    │
│  grand_total = sum of all                   │
└──────────────────┬──────────────────────────┘
                   │
                   ▼
┌─────────────────────────────────────────────┐
│  Confidence Scorer                          │
│  min(supplier_confidence_scores)            │
│  penalized for: unresolved canonicals,      │
│  stale prices (>7 days), missing items,     │
│  LLM assumption count                       │
│  -> 0.0-1.0 score + High/Med/Low label      │
└──────────────────┬──────────────────────────┘
                   │
                   ▼
              Estimate saved to DB
              with full trace_json per line
```

### Canonical Item System

Every product in the system is identified by a string key like `toilet_elongated_standard`,
`prv_3_4_inch`, or `wax_ring_standard`. These keys are:

- Defined once in `supplier_service.py` as `CANONICAL_MAP`
- Referenced by `material_assemblies` (which parts go in which assembly)
- Referenced by `labor_templates` (which assemblies does this labor code apply to)
- Stored on `estimate_line_items.canonical_item` for traceability
- Used as the foreign-key equivalent between suppliers (without actual FK constraints, since
  suppliers can temporarily be out of stock on an item)

When a new product category is added, the workflow is:
1. Add the canonical key to `CANONICAL_MAP` with pricing for each supplier
2. Add or update the material assembly referencing it
3. Run the seed script or a targeted migration to populate `supplier_products`

---

## 5. Phase Roadmap

### Phase 1 — Core Estimating (Current)

Deliverables:
- Chat-driven estimate generation for service / remodel jobs
- 80+ canonical plumbing items with DFW supplier pricing
- Labor templates for 30+ installation types with access and urgency multipliers
- County-aware tax rates (Tarrant, Dallas, Collin, Denton, Rockwall)
- Estimate CRUD, versioning, PDF export
- JWT authentication with organization scoping
- Daily Celery Beat worker (price refresh stub)
- Admin UI for supplier product management

### Phase 2 — Live Supplier Pricing

Deliverables:
- Supplier-specific HTTP scrapers or API integrations (Ferguson has a trade API)
- Automated confidence score updates on successful price fetch
- Price change alerts when cost deviates more than 10% from previous
- `decrement_confidence_scores` task fully implemented: stale prices lose 0.05/day after 7 days

### Phase 3 — Document RAG

Deliverables:
- `process_document` task fully implemented: PDF -> text -> 512-token chunks -> embeddings
- pgvector similarity search integrated into the pricing chat context
- Supplier catalog PDFs processed on upload, queryable via semantic search
- Manufacturer spec sheets surfaced as supporting evidence in estimate assumptions

### Phase 4 — Blueprint Takeoff

Deliverables:
- `analyze_blueprint` task fully implemented: PDF -> page images -> sheet classification
- Computer vision fixture detection on plumbing plan sheets (PyMuPDF + YOLO or GPT-4V)
- Detected fixture counts auto-populate estimate line items
- Blueprint viewer UI with detection overlays
- Confidence scores reflect detection confidence from CV model

---

## 6. Security Model

- All API routes require a valid JWT (HS256, 30-minute expiry, 7-day refresh).
- Organization scoping: every DB query filters by `organization_id` derived from the JWT claim.
  Users cannot read or write data belonging to another organization.
- Admin routes (`/api/v1/admin/*`) additionally require `is_admin=True` on the user record.
- Passwords are hashed with bcrypt (passlib, 12 rounds).
- File uploads are validated for MIME type and size before being written to MinIO.
- The LLM receives only the user's text message and a sanitized system prompt. No PII or raw DB
  data is sent to OpenAI.
- All API responses are logged to `audit_logs` for compliance review.
