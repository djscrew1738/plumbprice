# PlumbPrice — Privacy & Data Retention

## What user content we store

| Type | Bucket / Table | Source |
|------|----------------|--------|
| Blueprint PDFs | MinIO `blueprints` / `blueprint_jobs` | User upload |
| Reference docs | MinIO `documents` / `uploaded_documents` | User / admin upload |
| Photos (Phase 3) | MinIO `documents` (subprefix `photos/`) | Mobile capture |
| Voice notes (Phase 4) | MinIO `documents` (subprefix `audio/`) | Mobile capture |

## Retention policy

- All uploaded user content is kept for at most **`data_retention_days`** days
  after upload (default **90 days**).
- Users can delete their own uploads at any time via:
  - `DELETE /api/v1/blueprints/{job_id}` — removes the PDF blob immediately
    and soft-deletes the DB row.
- Soft-deleted records are hard-deleted by the
  `worker.tasks.privacy.purge_expired_uploads` celery beat task after a
  **`soft_delete_grace_days`** grace window (default **7 days**) so admins
  can recover an accidental deletion.
- The same task hard-deletes records older than `data_retention_days` even
  if the user never explicitly deleted them.

## What we do NOT delete

- Estimates, projects, proposals, and pipeline records derived from a
  blueprint persist after the source PDF is purged. Those records contain
  no raw uploaded content, only the structured numbers/notes the contractor
  has committed to as part of their business records.
- AI agent memories about the contractor's preferences (rates, supplier
  defaults, etc.) are explicit business data and persist until the user
  removes them via the admin UI.

## Configuration

```bash
# .env
DATA_RETENTION_DAYS=90        # purge uploads older than this
SOFT_DELETE_GRACE_DAYS=7      # how long after soft-delete to hard-delete
```

## Audit

Every soft-delete and hard-delete pass writes a structured log line:

- `blueprint.deleted` — user-initiated
- `privacy.purge.completed` — daily beat task summary
- `privacy.purge.<phase>_failed` — per-record failure with id and error

These lines feed structlog and end up in `/var/log/plumbprice-api.log`
(API) and the celery worker stdout.
