# PlumbPrice API Error Reference

All error responses share the FastAPI default shape:

```json
{ "detail": "Human-readable error message" }
```

Validation errors (422) follow Pydantic's structured shape:

```json
{ "detail": [{ "loc": ["body", "email"], "msg": "field required", "type": "value_error.missing" }] }
```

Every response includes an `X-Request-ID` header (echoed from input or generated). Quote it when filing tickets.

---

## Status code catalog

### 200 / 201 — Success
Normal operation. 201 only on resource creation (rare; most POSTs return 200 with the new object).

### 204 — No Content
Used for delete operations. Body is empty.

### 400 — Bad Request
**Causes:** Malformed payload, business-rule violation (e.g., email already registered, invalid reset token, missing required form field).

**Recovery:** Inspect `detail`. Show user a friendly message; do NOT retry as-is.

**Examples:**
- `auth/register` with existing email → "Email already registered"
- `auth/reset-password` with invalid/expired token → "Invalid or expired reset token"
- `photos/quick-quote` with non-image MIME → "Unsupported file type"

### 401 — Unauthorized
**Causes:** Missing, expired, or invalid JWT.

**Recovery:** Web client redirects to `/login`. Native/PWA clients should attempt a silent refresh once; if that fails, prompt re-login.

**Examples:**
- `auth/login` with wrong password (slowapi may also return 429 here under burst)
- Any protected endpoint when cookie/Bearer expired

### 403 — Forbidden
**Causes:** Authenticated user lacks role/permission for resource.

**Recovery:** Surface "You don't have access to this resource". Do NOT retry. Admin routes require `is_admin=True`.

### 404 — Not Found
**Causes:** Resource does not exist OR (deliberately) caller lacks access. Public proposal tokens always return 404 on expired/invalid to avoid enumeration.

**Recovery:** Show "Not found" UI. Do not retry.

### 409 — Conflict
**Causes:** Optimistic-concurrency conflict, idempotency-key collision.

**Recovery:** Re-fetch the canonical state and ask the user how to proceed.

### 413 — Payload Too Large
**Causes:** File upload exceeds size limit (e.g., photo >10MB raw, blueprint >50MB).

**Recovery:** Pre-resize on client. The capture page already pre-resizes via `lib/imageProcessing.ts` — re-check the encoder if this fires.

### 415 — Unsupported Media Type
**Causes:** Wrong Content-Type header or non-allow-listed file MIME on multipart upload.

**Recovery:** Show "Unsupported file type." Allow-list:
- Photos: `image/jpeg`, `image/png`, `image/heic`, `image/webp`
- Blueprints: `application/pdf`, `image/png`, `image/jpeg`, `image/tiff`

### 422 — Unprocessable Entity
**Causes:** Pydantic schema validation failure. `detail` is an array of field-level errors.

**Recovery:** Map `loc` to form fields and surface inline error text. Do not retry without user input.

### 429 — Too Many Requests
**Causes:** slowapi (per-IP) or app-level rate counter (per-account) exceeded.

**Recovery:**
- Honor `Retry-After` header when present.
- Show toast: "You're going a bit fast — try again in N seconds."
- Background-sync queue (PWA) should re-queue with exponential backoff (start 30s, cap 5min).

**Limits in effect (as of 2.1.1):**
| Endpoint | Limit | Scope |
|---|---|---|
| `/auth/login` | 20/min | per IP (slowapi) + 5/15min per account (lockout) |
| `/auth/register` | 5/min | per IP |
| `/auth/forgot-password` | 5/min | per IP + per account window |
| `/auth/reset-password` | 10/min | per IP |
| `/voice/transcribe` | 30/min | per IP |
| `/voice/parse` | 15/min | per IP |
| `/voice/converse` | 30/min | per IP |
| `/photos/quick-quote` | 20/min | per IP |
| `/blueprints/quick-quote` | 10/min | per IP |
| `/documents/parse` | 10/min | per IP |
| `/chat/*` POST | 30/min, 20/min for new sessions | per IP |
| `/proposals/{id}/send` | 20/hour | per IP |
| `/public-agent/converse` | configurable (default 30/min) | per IP |
| `/public/proposals/{token}` GET | 60/min | per IP |
| `/public/proposals/{token}/accept|decline` | 10/min | per IP |

### 500 — Internal Server Error
**Causes:** Unhandled exception in handler, database error, OS error.

**Recovery:** Web shows generic "Something went wrong, our team has been notified." Worker tasks retry per Celery `autoretry_for`. Sentry/OTel will capture (when wired in `b1-sentry-otel`).

### 502 — Bad Gateway
**Causes:** Upstream LLM (OpenAI/Anthropic/Ollama) returned an error or invalid payload that the resilience layer could not normalize.

**Recovery:** Most callers retry once with provider fallback (cloud → local or vice versa). If 502 persists, surface "AI service temporarily unavailable, try again."

### 503 — Service Unavailable
**Causes:** Database or critical dependency unreachable; rolling-deploy startup window; resilience-layer circuit-breaker open.

**Recovery:** Honor `Retry-After`. Background queues should pause and retry. `/health/*` probes will reflect the same state.

### 504 — Gateway Timeout
**Causes:** LLM provider timed out beyond the resilience layer's max-wait.

**Recovery:** Same as 502.

---

## Error envelope quick reference

```ts
type ApiError = {
  detail: string | { loc: (string|number)[]; msg: string; type: string }[];
};
```

Frontend hook `useSafeQuery` already discriminates on `isError`; status-specific handling lives in `web/src/lib/api.ts` interceptors.

---

## Background-sync retry policy (PWA)

When network is offline or the API returns 429/5xx, the offline queue should:
1. Persist the request in IndexedDB (Dexie store `outbox`, see `a2-offline-estimator`).
2. Retry on `online` event AND on a 30s/2m/5m schedule (capped).
3. Drop and notify on 4xx other than 408/425/429 (those are retriable).
4. Surface queued count in the UI badge (mounted in `ClientLayout`).

---

## Observability

- All requests log: method, path, status, latency_ms, user_id, request_id (see `main.py:318+`).
- Slow queries (>500ms) log a SQL-tagged event (`database.py:34+`).
- Sentry + OpenTelemetry wiring is tracked under `b1-sentry-otel`.
