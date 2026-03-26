# PlumbPrice AI — API Reference

Base URL (development): `http://localhost:8000`
Base URL (production): `https://api.plumbprice.com`

All endpoints are prefixed with `/api/v1`. All request and response bodies are JSON unless noted.
All timestamps are ISO 8601 with UTC timezone (`2025-06-15T14:30:00Z`).

---

## Authentication

PlumbPrice uses JWT Bearer tokens. Obtain a token pair via `POST /api/v1/auth/login`. Include the
access token in the `Authorization` header for all subsequent requests:

```
Authorization: Bearer <access_token>
```

### POST /api/v1/auth/login

Authenticate and receive a token pair.

**Request**

```json
{
  "email": "estimator@acmeplumbing.com",
  "password": "s3cur3pass!"
}
```

**Response 200**

```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer",
  "expires_in": 1800
}
```

**Response 401**

```json
{ "detail": "Incorrect email or password" }
```

---

### POST /api/v1/auth/refresh

Exchange a refresh token for a new access token.

**Request**

```json
{ "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..." }
```

**Response 200**

```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer",
  "expires_in": 1800
}
```

---

### GET /api/v1/auth/me

Return the authenticated user profile.

**Response 200**

```json
{
  "id": 12,
  "email": "estimator@acmeplumbing.com",
  "full_name": "Jake Martinez",
  "role": "estimator",
  "is_active": true,
  "is_admin": false,
  "organization_id": 3,
  "created_at": "2025-01-15T09:00:00Z"
}
```

---

## Chat / Pricing

### POST /api/v1/chat/price

The primary endpoint. Accepts a natural-language description of plumbing work and returns a full
itemized estimate. The LLM extracts intent; the pricing engine performs all calculations
deterministically.

**Request**

```json
{
  "message": "Replace the master bath toilet with a Kohler Cimarron elongated, standard access, normal urgency",
  "county": "tarrant",
  "preferred_supplier": "ferguson",
  "chat_history": [
    {
      "role": "user",
      "content": "I need a quote for master bath work"
    },
    {
      "role": "assistant",
      "content": "Happy to help. What fixtures need replacing?"
    }
  ],
  "project_id": 47,
  "save_estimate": true
}
```

**Fields**

| Field               | Type             | Required | Description                                              |
|---------------------|------------------|----------|----------------------------------------------------------|
| `message`           | string           | Yes      | User's description of the work                           |
| `county`            | string           | No       | DFW county for tax rate (default: `tarrant`)             |
| `preferred_supplier`| string           | No       | Supplier slug to prefer (default: org default)           |
| `chat_history`      | array of objects | No       | Prior turns for context continuity                       |
| `project_id`        | integer          | No       | Associate estimate with an existing project              |
| `save_estimate`     | boolean          | No       | Persist estimate to DB (default: `true`)                 |

**Response 200**

```json
{
  "estimate_id": 138,
  "title": "Master Bath — Toilet Replacement",
  "job_type": "service",
  "status": "draft",
  "confidence_score": 0.92,
  "confidence_label": "High",
  "county": "tarrant",
  "tax_rate": 0.0825,
  "preferred_supplier": "ferguson",
  "line_items": [
    {
      "id": 501,
      "line_type": "material",
      "description": "Kohler Cimarron Elongated Toilet — Ferguson",
      "quantity": 1.0,
      "unit": "ea",
      "unit_cost": 187.40,
      "total_cost": 187.40,
      "supplier": "ferguson",
      "sku": "K-3609-0",
      "canonical_item": "toilet_elongated_standard",
      "sort_order": 1,
      "trace_json": {
        "supplier_product_id": 204,
        "cost_at_quote": 187.40,
        "confidence_score": 0.97,
        "last_verified": "2025-06-10T08:00:00Z"
      }
    },
    {
      "id": 502,
      "line_type": "material",
      "description": "Wax Ring — Ferguson",
      "quantity": 1.0,
      "unit": "ea",
      "unit_cost": 6.85,
      "total_cost": 6.85,
      "supplier": "ferguson",
      "sku": "7200-WX",
      "canonical_item": "wax_ring_standard",
      "sort_order": 2,
      "trace_json": { "supplier_product_id": 205, "cost_at_quote": 6.85, "confidence_score": 0.97 }
    },
    {
      "id": 503,
      "line_type": "material",
      "description": "Closet Bolts — Ferguson",
      "quantity": 1.0,
      "unit": "ea",
      "unit_cost": 3.20,
      "total_cost": 3.20,
      "supplier": "ferguson",
      "sku": "CB-5500",
      "canonical_item": "closet_bolts",
      "sort_order": 3,
      "trace_json": { "supplier_product_id": 206, "cost_at_quote": 3.20, "confidence_score": 0.97 }
    },
    {
      "id": 504,
      "line_type": "labor",
      "description": "Toilet Replacement — Lead Plumber (1.5 hrs)",
      "quantity": 1.5,
      "unit": "hr",
      "unit_cost": 95.00,
      "total_cost": 142.50,
      "canonical_item": null,
      "sort_order": 10,
      "trace_json": {
        "labor_template_code": "toilet_replace",
        "base_hours": 1.5,
        "access_multiplier": 1.0,
        "urgency_multiplier": 1.0,
        "lead_rate": 95.00
      }
    },
    {
      "id": 505,
      "line_type": "misc",
      "description": "Truck charge / consumables",
      "quantity": 1.0,
      "unit": "ea",
      "unit_cost": 45.00,
      "total_cost": 45.00,
      "sort_order": 20,
      "trace_json": { "source": "markup_rule", "job_type": "service" }
    }
  ],
  "labor_total": 142.50,
  "materials_total": 197.45,
  "tax_total": 16.29,
  "markup_total": 59.24,
  "misc_total": 45.00,
  "subtotal": 444.19,
  "grand_total": 460.48,
  "assumptions": [
    "Standard toilet rough-in distance (12 inch) assumed",
    "Existing shut-off valve functional — not replaced",
    "Standard floor mount, no in-wall carrier"
  ],
  "sources": [
    { "type": "supplier", "name": "Ferguson Enterprises", "slug": "ferguson" }
  ],
  "assistant_message": "Here is your estimate for replacing the master bath toilet with a Kohler Cimarron elongated. The total is $460.48, which includes materials at Ferguson pricing, 1.5 hours of labor, and applicable Tarrant County tax. Note: I assumed a standard 12-inch rough-in and that the existing shut-off valve is in good condition.",
  "valid_until": "2025-07-15T14:30:00Z"
}
```

**Response 422 — Unprocessable (intent extraction failure)**

```json
{
  "detail": "Could not determine job scope from message. Please describe which fixtures need service or replacement."
}
```

---

## Estimates

### GET /api/v1/estimates

List all estimates for the authenticated user's organization.

**Query Parameters**

| Param      | Type    | Description                                              |
|------------|---------|----------------------------------------------------------|
| `status`   | string  | Filter: `draft`, `sent`, `approved`, `archived`          |
| `job_type` | string  | Filter: `service`, `remodel`, `new_construction`         |
| `project_id`| int    | Filter by project                                        |
| `limit`    | int     | Page size (default: 20, max: 100)                        |
| `offset`   | int     | Pagination offset (default: 0)                           |

**Response 200**

```json
{
  "total": 142,
  "items": [
    {
      "id": 138,
      "title": "Master Bath — Toilet Replacement",
      "job_type": "service",
      "status": "draft",
      "grand_total": 460.48,
      "confidence_label": "High",
      "county": "tarrant",
      "created_at": "2025-06-15T14:30:00Z",
      "valid_until": "2025-07-15T14:30:00Z",
      "project_id": 47
    }
  ]
}
```

---

### POST /api/v1/estimates

Create a blank estimate (manual entry, no chat).

**Request**

```json
{
  "title": "Kitchen Remodel — Rough-In",
  "job_type": "remodel",
  "county": "dallas",
  "preferred_supplier": "moore_supply",
  "project_id": 51
}
```

**Response 201**

```json
{
  "id": 139,
  "title": "Kitchen Remodel — Rough-In",
  "job_type": "remodel",
  "status": "draft",
  "grand_total": 0.0,
  "county": "dallas",
  "created_at": "2025-06-15T15:00:00Z"
}
```

---

### GET /api/v1/estimates/{estimate_id}

Retrieve a single estimate with all line items.

**Response 200** — Same structure as the `POST /api/v1/chat/price` response body, minus
`assistant_message`.

**Response 404**

```json
{ "detail": "Estimate not found" }
```

---

### PATCH /api/v1/estimates/{estimate_id}

Update estimate metadata or line items. A version snapshot is created automatically before
any modification.

**Request**

```json
{
  "status": "sent",
  "title": "Master Bath — Toilet Replacement (Revised)"
}
```

**Response 200** — Updated estimate object.

---

### DELETE /api/v1/estimates/{estimate_id}

Soft-delete an estimate (sets `status = "archived"`).

**Response 204** — No content.

---

### GET /api/v1/estimates/{estimate_id}/versions

List all saved versions of an estimate.

**Response 200**

```json
[
  {
    "id": 22,
    "version_number": 1,
    "change_summary": "Initial creation via chat",
    "created_at": "2025-06-15T14:30:00Z",
    "created_by": 12
  },
  {
    "id": 23,
    "version_number": 2,
    "change_summary": "Status changed to sent",
    "created_at": "2025-06-15T16:00:00Z",
    "created_by": 12
  }
]
```

---

### GET /api/v1/estimates/{estimate_id}/versions/{version_id}

Retrieve the full snapshot JSON for a specific version.

**Response 200** — Full estimate snapshot as stored in `snapshot_json`.

---

### GET /api/v1/estimates/{estimate_id}/export/pdf

Generate and stream a PDF copy of the estimate.

**Response 200** — `Content-Type: application/pdf`

---

## Suppliers

### GET /api/v1/suppliers

List all active suppliers.

**Response 200**

```json
[
  {
    "id": 1,
    "name": "Ferguson Enterprises",
    "slug": "ferguson",
    "type": "wholesale",
    "website": "https://www.ferguson.com",
    "phone": "972-555-0101",
    "city": "Dallas",
    "is_active": true
  },
  {
    "id": 2,
    "name": "Moore Supply Co.",
    "slug": "moore_supply",
    "type": "wholesale",
    "website": "https://www.mooresupply.com",
    "phone": "214-555-0102",
    "city": "Dallas",
    "is_active": true
  },
  {
    "id": 3,
    "name": "Apex Supply",
    "slug": "apex",
    "type": "wholesale",
    "website": "https://www.apexsupply.com",
    "phone": "817-555-0103",
    "city": "Fort Worth",
    "is_active": true
  }
]
```

---

### GET /api/v1/suppliers/{supplier_id}/products

List products for a supplier, optionally filtered by canonical item.

**Query Parameters**

| Param            | Type   | Description                            |
|------------------|--------|----------------------------------------|
| `canonical_item` | string | Filter by canonical item key           |
| `limit`          | int    | Page size (default: 50, max: 500)      |
| `offset`         | int    | Pagination offset                      |

**Response 200**

```json
{
  "total": 87,
  "items": [
    {
      "id": 204,
      "canonical_item": "toilet_elongated_standard",
      "sku": "K-3609-0",
      "name": "Kohler Cimarron Elongated ADA Toilet",
      "brand": "Kohler",
      "unit": "ea",
      "cost": 187.40,
      "confidence_score": 0.97,
      "last_verified": "2025-06-10T08:00:00Z",
      "is_active": true,
      "is_preferred": true
    }
  ]
}
```

---

### GET /api/v1/suppliers/compare

Compare prices across all active suppliers for a given canonical item.

**Query Parameters**

| Param            | Type   | Required | Description              |
|------------------|--------|----------|--------------------------|
| `canonical_item` | string | Yes      | Canonical item key       |

**Response 200**

```json
{
  "canonical_item": "toilet_elongated_standard",
  "results": [
    {
      "supplier": "ferguson",
      "sku": "K-3609-0",
      "name": "Kohler Cimarron Elongated",
      "cost": 187.40,
      "confidence_score": 0.97
    },
    {
      "supplier": "moore_supply",
      "sku": "K3609-0-MC",
      "name": "Kohler Cimarron Elongated White",
      "cost": 191.00,
      "confidence_score": 0.95
    },
    {
      "supplier": "apex",
      "sku": "APX-KCIMARRON-EL",
      "name": "Kohler Cimarron Elongated — Apex",
      "cost": 185.75,
      "confidence_score": 0.88
    }
  ]
}
```

---

## Projects

### GET /api/v1/projects

List projects for the authenticated user's organization.

**Query Parameters**

| Param    | Type   | Description                              |
|----------|--------|------------------------------------------|
| `status` | string | Filter: `active`, `complete`, `archived` |
| `limit`  | int    | Page size (default: 20)                  |
| `offset` | int    | Pagination offset                        |

**Response 200**

```json
{
  "total": 18,
  "items": [
    {
      "id": 47,
      "name": "Johnson Residence — Master Bath",
      "job_type": "service",
      "status": "active",
      "customer_name": "Robert Johnson",
      "address": "4421 Oak Meadow Dr",
      "city": "Fort Worth",
      "county": "tarrant",
      "state": "TX",
      "created_at": "2025-06-01T09:00:00Z"
    }
  ]
}
```

---

### POST /api/v1/projects

Create a new project.

**Request**

```json
{
  "name": "Johnson Residence — Master Bath",
  "job_type": "service",
  "customer_name": "Robert Johnson",
  "customer_phone": "817-555-9900",
  "customer_email": "rjohnson@email.com",
  "address": "4421 Oak Meadow Dr",
  "city": "Fort Worth",
  "county": "tarrant",
  "state": "TX",
  "zip_code": "76109"
}
```

**Response 201** — Created project object.

---

### GET /api/v1/projects/{project_id}

Retrieve a project with its associated estimates.

**Response 200**

```json
{
  "id": 47,
  "name": "Johnson Residence — Master Bath",
  "job_type": "service",
  "status": "active",
  "customer_name": "Robert Johnson",
  "customer_phone": "817-555-9900",
  "customer_email": "rjohnson@email.com",
  "address": "4421 Oak Meadow Dr",
  "city": "Fort Worth",
  "county": "tarrant",
  "state": "TX",
  "zip_code": "76109",
  "estimates": [
    {
      "id": 138,
      "title": "Master Bath — Toilet Replacement",
      "status": "sent",
      "grand_total": 460.48,
      "created_at": "2025-06-15T14:30:00Z"
    }
  ]
}
```

---

## Documents (Phase 3)

### POST /api/v1/documents/upload

Upload a supplier catalog, spec sheet, or other document for RAG processing.

**Request** — `multipart/form-data`

| Field       | Type   | Required | Description                                              |
|-------------|--------|----------|----------------------------------------------------------|
| `file`      | file   | Yes      | PDF, max 50 MB                                           |
| `doc_type`  | string | Yes      | `supplier_catalog`, `spec_sheet`, `warranty`, `other`    |
| `supplier_id`| int   | No       | Associate with a supplier                                |

**Response 202** — Accepted for async processing.

```json
{
  "id": 77,
  "original_filename": "ferguson-plumbing-2025.pdf",
  "doc_type": "supplier_catalog",
  "status": "queued",
  "file_size": 14728192,
  "created_at": "2025-06-15T15:30:00Z"
}
```

---

### GET /api/v1/documents

List uploaded documents.

**Response 200**

```json
{
  "total": 5,
  "items": [
    {
      "id": 77,
      "original_filename": "ferguson-plumbing-2025.pdf",
      "doc_type": "supplier_catalog",
      "status": "complete",
      "file_size": 14728192,
      "created_at": "2025-06-15T15:30:00Z"
    }
  ]
}
```

---

## Admin Endpoints

All admin endpoints require `is_admin=True` on the authenticated user.

### GET /api/v1/admin/users

List all users in the system.

**Response 200**

```json
{
  "total": 8,
  "items": [
    {
      "id": 12,
      "email": "estimator@acmeplumbing.com",
      "full_name": "Jake Martinez",
      "role": "estimator",
      "is_active": true,
      "is_admin": false,
      "organization_id": 3,
      "last_login": "2025-06-14T08:15:00Z"
    }
  ]
}
```

---

### POST /api/v1/admin/users

Create a new user.

**Request**

```json
{
  "email": "newtech@acmeplumbing.com",
  "password": "Temp1234!",
  "full_name": "Maria Torres",
  "role": "field_tech",
  "organization_id": 3
}
```

**Response 201** — Created user object (password not returned).

---

### PATCH /api/v1/admin/users/{user_id}

Update user fields.

**Request**

```json
{
  "is_active": false
}
```

**Response 200** — Updated user object.

---

### GET /api/v1/admin/suppliers/{supplier_id}/products

Admin view of all supplier products including inactive ones.

**Response 200** — Same schema as `GET /api/v1/suppliers/{supplier_id}/products` but includes
`is_active: false` rows.

---

### POST /api/v1/admin/suppliers/{supplier_id}/products

Add a new product to a supplier.

**Request**

```json
{
  "canonical_item": "prv_3_4_inch",
  "sku": "PRV-34-WC",
  "name": "Watts 3/4\" Pressure Reducing Valve",
  "brand": "Watts",
  "unit": "ea",
  "cost": 42.50,
  "confidence_score": 1.0
}
```

**Response 201** — Created product object.

---

### PATCH /api/v1/admin/suppliers/{supplier_id}/products/{product_id}

Update supplier product pricing or metadata. Automatically appends a row to
`supplier_price_history` if `cost` changes.

**Request**

```json
{
  "cost": 44.75,
  "confidence_score": 1.0
}
```

**Response 200** — Updated product object.

---

### GET /api/v1/admin/audit-logs

Retrieve audit log entries.

**Query Parameters**

| Param       | Type   | Description                                    |
|-------------|--------|------------------------------------------------|
| `table_name`| string | Filter by table (e.g., `estimates`)            |
| `user_id`   | int    | Filter by user                                 |
| `action`    | string | Filter: `create`, `update`, `delete`           |
| `from`      | string | ISO 8601 start datetime                        |
| `to`        | string | ISO 8601 end datetime                          |
| `limit`     | int    | Page size (default: 50)                        |
| `offset`    | int    | Pagination offset                              |

**Response 200**

```json
{
  "total": 320,
  "items": [
    {
      "id": 1440,
      "table_name": "estimates",
      "record_id": 138,
      "action": "create",
      "new_values": { "title": "Master Bath — Toilet Replacement", "grand_total": 460.48 },
      "user_id": 12,
      "ip_address": "192.168.1.55",
      "created_at": "2025-06-15T14:30:00Z"
    }
  ]
}
```

---

### POST /api/v1/admin/worker/trigger-refresh

Manually trigger the supplier price refresh Celery task.

**Response 202**

```json
{
  "task_id": "f47ac10b-58cc-4372-a567-0e02b2c3d479",
  "status": "queued"
}
```

---

### GET /api/v1/admin/worker/task/{task_id}

Check the status of a Celery task.

**Response 200**

```json
{
  "task_id": "f47ac10b-58cc-4372-a567-0e02b2c3d479",
  "status": "SUCCESS",
  "result": {
    "status": "complete",
    "suppliers": {
      "ferguson": { "status": "pending", "items_updated": 0 },
      "moore_supply": { "status": "pending", "items_updated": 0 },
      "apex": { "status": "pending", "items_updated": 0 }
    }
  }
}
```

---

## Health

### GET /health

Liveness probe — no authentication required.

**Response 200**

```json
{ "status": "ok" }
```

---

### GET /health/ready

Readiness probe — checks DB and Redis connectivity.

**Response 200**

```json
{
  "status": "ready",
  "db": "ok",
  "redis": "ok"
}
```

**Response 503**

```json
{
  "status": "not_ready",
  "db": "ok",
  "redis": "error: Connection refused"
}
```

---

## Error Responses

All errors follow a consistent envelope:

```json
{
  "detail": "Human-readable error message"
}
```

| HTTP Status | Meaning                                              |
|-------------|------------------------------------------------------|
| 400         | Bad request — malformed JSON or invalid field value  |
| 401         | Missing or invalid Bearer token                      |
| 403         | Authenticated but insufficient permissions           |
| 404         | Resource not found or belongs to another org         |
| 422         | Validation error — field-level details in `detail`   |
| 429         | Rate limit exceeded (LLM endpoint: 30 req/min/user)  |
| 500         | Internal server error — check logs                   |
| 503         | Dependency unavailable (DB, Redis, OpenAI)           |

### 422 Validation Error Detail

```json
{
  "detail": [
    {
      "loc": ["body", "county"],
      "msg": "value is not a valid county. Must be one of: tarrant, dallas, collin, denton, rockwall",
      "type": "value_error"
    }
  ]
}
```
