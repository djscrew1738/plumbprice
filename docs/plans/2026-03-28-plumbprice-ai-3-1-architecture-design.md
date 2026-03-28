# PlumbPrice AI 3.1 Architecture Design

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:writing-plans before implementing this design.

**Goal:** Define a production-grade system architecture for PlumbPrice AI 3.1 that supports estimating, approvals, proposals, document intelligence, and commercial learning loops.

**Architecture:** PlumbPrice AI 3.1 should use a hybrid platform architecture. A single transactional core API owns all business state and commercial workflows, while specialized workers handle slow, retryable, and compute-heavy jobs such as document processing, blueprint analysis, proposal rendering, notifications, and learning pipelines.

**Tech Stack:** Next.js web app, FastAPI core API, Celery-style workers, PostgreSQL, Redis, S3-compatible object storage, vector retrieval, structured observability.

---

## 1. Architectural Principles

1. Commercial state must be correct before it is fast.
2. Business truth lives in PostgreSQL, not caches or queues.
3. Versioned estimates are immutable snapshots.
4. AI interprets and retrieves context; deterministic pricing computes totals.
5. Expensive or slow work must stay off the request path.
6. Side effects should be driven by an outbox/event model, not direct in-request worker calls.
7. Tenant isolation, auditability, and replayability are mandatory.

## 2. Top-Level System Shape

### 2.1 Runtime Components

- `web-app`
  Next.js application for estimating, pipeline views, approvals, proposals, admin, and customer operations.
- `core-api`
  Transactional backend and system of record for all business workflows.
- `worker-high-priority`
  Handles approval notifications, proposal delivery, and other latency-sensitive background jobs.
- `worker-documents`
  Handles OCR, parsing, chunking, embedding, and file-derived knowledge workflows.
- `worker-blueprints`
  Handles blueprint page rendering, fixture detection, and takeoff generation.
- `worker-proposals`
  Handles PDF rendering, regeneration, and branded document assembly.
- `worker-learning`
  Handles actual-vs-estimated variance analysis, feedback aggregation, and recommendation generation.
- `postgres`
  Primary relational store and commercial source of truth.
- `redis`
  Queue broker, rate-limit store, short-lived cache, and distributed lock backend.
- `object-storage`
  Stores blueprints, images, proposal PDFs, exports, and attachments.
- `search-index`
  Retrieval layer for semantic and metadata search. Start with PostgreSQL plus vector support unless scale proves otherwise.
- `analytics-sink`
  Product and commercial event stream for dashboards, cohort analysis, and pricing intelligence.

### 2.2 Recommended Deployment Boundary

Use a hybrid platform:

- keep `core-api` as one transactional application boundary
- isolate workers by workload type and priority
- avoid early transactional microservice splits

This gives fast product iteration while preventing compute-heavy AI and document work from destabilizing core business workflows.

## 3. Internal Core API Boundaries

Organize the API by business domains, not router files.

### 3.1 Identity and Tenancy

Responsibilities:

- organizations
- users
- role assignments
- branch/location scoping
- permission checks
- request actor context

### 3.2 CRM and Opportunity Management

Responsibilities:

- customers
- contacts
- jobs
- opportunities
- stage changes
- follow-ups
- pipeline state

### 3.3 Estimating

Responsibilities:

- estimate records
- estimate versions
- estimate line items
- assumptions
- comments
- confidence
- pricing traces

### 3.4 Pricing

Responsibilities:

- labor templates
- material assemblies
- supplier pricing
- tax rules
- margin policy
- organization-specific overrides
- regional adjustments

### 3.5 Workflow

Responsibilities:

- approval requests
- approval decisions
- review queues
- SLA timers
- escalations
- task generation

### 3.6 Proposals

Responsibilities:

- proposal records
- proposal versions
- delivery attempts
- acceptance state
- signature readiness

### 3.7 Documents and Knowledge

Responsibilities:

- uploaded files
- document chunks
- embeddings
- blueprint jobs
- blueprint detections
- retrieval references

### 3.8 Learning and Outcomes

Responsibilities:

- won/lost outcomes
- actual job costs
- variance analysis
- pricing feedback
- template recommendations

## 4. Core Domain Model

The product should revolve around this chain:

`Opportunity -> Estimate -> Estimate Version -> Proposal -> Outcome`

### 4.1 Primary Tables

- `organizations`
- `organization_settings`
- `users`
- `user_role_assignments`
- `customers`
- `customer_contacts`
- `jobs`
- `opportunities`
- `opportunity_stage_history`
- `estimates`
- `estimate_versions`
- `estimate_line_items`
- `estimate_assumptions`
- `estimate_pricing_traces`
- `estimate_comments`
- `approval_requests`
- `approval_decisions`
- `proposals`
- `proposal_versions`
- `proposal_deliveries`
- `proposal_acceptances`
- `documents`
- `document_chunks`
- `blueprint_jobs`
- `blueprint_pages`
- `blueprint_detections`
- `supplier_catalog_items`
- `supplier_price_snapshots`
- `labor_templates`
- `material_assemblies`
- `margin_policies`
- `actual_job_costs`
- `estimate_outcomes`
- `audit_logs`
- `domain_events_outbox`

### 4.2 Relationship Model

- one `customer` can have many `jobs`
- one `job` can have many `opportunities`
- one `opportunity` can have many `estimates`
- one `estimate` can have many immutable `estimate_versions`
- one `estimate_version` can have many `estimate_line_items`
- one `estimate_version` can have many assumptions and one primary pricing trace
- one `proposal` is generated from one exact `estimate_version`
- one `proposal` can have many deliveries and one acceptance result
- one `estimate` can eventually link to one `estimate_outcome`

### 4.3 Estimate Versioning Rules

Estimate versions must be immutable.

Required fields on `estimate_versions`:

- `estimate_id`
- `version_number`
- `status`
- `job_type`
- `county`
- `preferred_supplier`
- `labor_total`
- `materials_total`
- `tax_total`
- `markup_total`
- `misc_total`
- `subtotal`
- `grand_total`
- `confidence_score`
- `confidence_label`
- `margin_estimate`
- `risk_flags`
- `source_prompt`
- `created_by`
- `created_at`
- `supersedes_version_id`

Why this matters:

- approvals target stable snapshots
- proposals can be reproduced exactly
- revisions can be diffed
- finance and operations get reliable auditability
- learning pipelines compare outcomes to the exact quoted version

## 5. Pricing Trace and Explainability

Every estimate version should store a machine-readable pricing trace.

Required trace components:

- selected labor template
- selected material assembly
- supplier prices used
- tax rule used
- margin rule used
- fallback/default values used
- retrieval references used
- AI interpretation summary
- confidence factors
- manual override reasons

The system should always be able to answer:

- why the number is what it is
- which supplier data was used
- what assumptions were made
- what defaults were applied
- which version of the estimate was sent to the customer

## 6. Request Path vs Async Path

### 6.1 Synchronous Request Path

These workflows must stay in the core API request path:

- create opportunity
- open estimator
- submit pricing request
- save draft estimate
- publish estimate version
- request approval
- approve or reject
- create proposal record
- issue proposal send command

These need low latency and strong transactional guarantees.

### 6.2 Asynchronous Path

These workflows should run through workers:

- blueprint OCR
- blueprint page rendering
- fixture detection
- document chunking
- embedding generation
- supplier sync jobs
- PDF proposal rendering
- email delivery retries
- reminder automation
- learning jobs
- analytics aggregation

These need retries, observability, and idempotency more than low latency.

## 7. Event and Outbox Architecture

Use a transactional outbox pattern.

### 7.1 Write Flow

1. API writes domain state to PostgreSQL.
2. In the same transaction, API writes event rows to `domain_events_outbox`.
3. Relay process publishes queued outbox records to Redis or another broker.
4. Workers consume the events and execute side effects.
5. Workers update job state or emit follow-on events.

### 7.2 Event Catalog

Estimate events:

- `estimate.created`
- `estimate.version_created`
- `estimate.version_published`
- `estimate.repriced`

Approval events:

- `approval.requested`
- `approval.approved`
- `approval.rejected`
- `approval.escalated`

Proposal events:

- `proposal.created`
- `proposal.render_requested`
- `proposal.rendered`
- `proposal.sent`
- `proposal.delivery_failed`
- `proposal.viewed`
- `proposal.accepted`

Document events:

- `document.uploaded`
- `document.chunked`
- `document.embedded`
- `blueprint.analysis_requested`
- `blueprint.analysis_completed`
- `blueprint.analysis_failed`

Learning events:

- `job.closed_won`
- `job.closed_lost`
- `job.actuals_recorded`
- `pricing.feedback_generated`

### 7.3 Queue Contract Rules

Queue payloads must:

- include `organization_id`
- include stable object IDs
- include a message schema version
- include an idempotency key
- avoid embedding large mutable documents unless necessary

Example payload:

```json
{
  "schema_version": 1,
  "event_id": "uuid",
  "event_type": "proposal.render_requested",
  "organization_id": 42,
  "proposal_id": 187,
  "proposal_version_id": 3,
  "estimate_version_id": 91,
  "idempotency_key": "proposal-render-187-v3"
}
```

## 8. Queue Topology

Separate queues by urgency and workload profile.

- `high-priority`
  approvals, notifications, customer-visible updates
- `documents`
  chunking, OCR, embeddings
- `blueprints`
  page analysis and takeoffs
- `proposals`
  render and regenerate
- `integrations`
  supplier syncs, webhook handlers, external system jobs
- `learning`
  feedback and variance analysis
- `analytics`
  derived metrics and aggregation

This prevents low-value or heavy jobs from starving customer-visible workflows.

## 9. AI, Retrieval, and Deterministic Pricing

3.1 should explicitly separate interpretation from pricing.

### 9.1 Required Pipeline

1. `User input`
   Natural language, blueprint, images, attachments, or prior job context.
2. `Intent interpretation layer`
   AI extracts likely job type, scope, ambiguity, and candidate pricing structures.
3. `Retrieval layer`
   Fetches organization pricing rules, templates, supplier items, and prior relevant work.
4. `Normalization layer`
   Produces a structured pricing request.
5. `Deterministic pricing engine`
   Calculates the commercial totals.
6. `Response composer`
   Returns answer text, estimate breakdown, assumptions, and trace.

### 9.2 Non-Negotiable Boundary

AI may:

- classify intent
- extract structure
- summarize assumptions
- rank likely templates or materials

AI may not:

- directly author final commercial totals without deterministic pricing rules
- silently mutate account pricing policy
- bypass margin rules or approval policies

### 9.3 Confidence Model

Confidence should be built from components:

- classification confidence
- retrieval quality
- supplier price freshness
- amount of default/fallback usage
- blueprint completeness
- missing scope details
- manual override frequency

Confidence must be actionable, not cosmetic.

## 10. Approval Architecture

Approvals should be rule-driven and snapshot-bound.

### 10.1 Approval Triggers

- low margin
- low confidence
- large estimate value
- manual commercial override
- stale supplier pricing
- nonstandard scope

### 10.2 Approval Tables

`approval_requests`:

- `organization_id`
- `estimate_version_id`
- `requested_by`
- `required_role`
- `priority`
- `reason_codes`
- `status`
- `sla_due_at`

`approval_decisions`:

- `approval_request_id`
- `decided_by`
- `decision`
- `comment`
- `created_at`

Reason codes should be normalized values, not free text, so they can drive automation and reporting.

## 11. Proposal Architecture

Proposal state must be modeled separately from estimate state.

### 11.1 Required Proposal Objects

`proposals`:

- `organization_id`
- `estimate_version_id`
- `customer_id`
- `status`
- `template_id`
- `branding_profile_id`

`proposal_versions`:

- `proposal_id`
- `version_number`
- `content_snapshot_json`
- `pdf_storage_key`
- `hash`

`proposal_deliveries`:

- `proposal_id`
- `channel`
- `destination`
- `provider`
- `provider_message_id`
- `status`
- `sent_at`
- `opened_at`
- `failed_at`

### 11.2 Proposal Status Model

- `draft`
- `render_pending`
- `rendered`
- `delivery_pending`
- `sent`
- `delivery_failed`
- `accepted`
- `expired`

This gives operational visibility and retry control.

## 12. Storage Architecture

### 12.1 PostgreSQL

Use PostgreSQL as the commercial source of truth.

Recommended schema areas:

- `identity`
- `crm`
- `estimating`
- `pricing`
- `workflow`
- `proposals`
- `documents`
- `analytics`

### 12.2 Redis

Redis should be used only for:

- queue broker
- TTL cache
- rate limiting
- dedupe keys
- distributed locks

Do not store commercial truth in Redis.

### 12.3 Object Storage

Store:

- blueprint PDFs
- blueprint page images
- proposal PDFs
- customer attachments
- exported reports
- branding assets

Recommended object key pattern:

- `org/{org_id}/blueprints/{job_id}/source.pdf`
- `org/{org_id}/blueprints/{job_id}/pages/{page_no}.png`
- `org/{org_id}/proposals/{proposal_id}/versions/{version_no}.pdf`

## 13. Multi-Tenancy and Security

Tenant isolation must be enforced in design, not only at the controller layer.

Rules:

- every business object must have `organization_id`
- repositories must enforce tenant filtering
- queue payloads must carry tenant context
- object storage keys must be tenant-scoped
- search queries must include tenant boundaries
- audit logs must record tenant, actor, and request metadata

Recommended role model:

- `owner`
- `admin`
- `estimator`
- `reviewer`
- `sales`
- `ops`
- `viewer`

Permissions should be capability-based on top of role assignment.

## 14. Observability

### 14.1 Required Context

Every request and worker job should carry:

- `trace_id`
- `request_id`
- `organization_id`
- `user_id`
- `estimate_id`
- `estimate_version_id`
- `proposal_id`
- `job_id`

### 14.2 Required Metrics

- request latency by route
- queue depth by queue
- worker retry rate
- blueprint processing duration
- proposal render duration
- proposal send failure rate
- stale supplier price usage rate
- low-confidence estimate rate
- approval turnaround time
- estimate acceptance rate
- margin leakage by template and county

### 14.3 Logging Standards

- structured JSON logs only
- explicit redaction policy for PII and secrets
- operational logs separate from audit logs
- correlated request and worker traces

## 15. Reliability and Failure Handling

Design for partial failure explicitly.

### 15.1 Expected Failure Modes

- AI classifier fails
- supplier pricing is stale or unavailable
- blueprint analysis fails
- proposal rendering fails
- delivery provider fails
- search/index is stale
- duplicate worker delivery happens

### 15.2 Required Responses

- classifier failure falls back to manual clarification
- stale supplier data returns a visible warning and confidence penalty
- blueprint failure does not block manual estimating
- proposal rendering retries without duplicating the proposal record
- notification retries use idempotency keys
- duplicate worker deliveries do not duplicate side effects

### 15.3 Idempotency Requirements

Must exist for:

- proposal sends
- document ingestion
- blueprint job starts
- external webhooks
- supplier sync writes
- acceptance callbacks

## 16. Deployment Topology

### 16.1 Production Shape

- `web`
  multiple stateless instances behind a load balancer
- `core-api`
  multiple stateless instances behind a load balancer
- `worker-high-priority`
  isolated autoscaling pool
- `worker-documents`
  isolated autoscaling pool
- `worker-blueprints`
  isolated autoscaling pool
- `worker-proposals`
  isolated autoscaling pool
- `postgres`
  managed service with backups and point-in-time recovery
- `redis`
  managed or HA deployment
- `object-storage`
  managed S3-compatible backend
- `observability stack`
  logs, metrics, tracing, and alerting

### 16.2 Environments

- `dev`
- `staging`
- `prod`

### 16.3 Release Gates

- migration validation
- lint and build
- API test suite
- smoke test after deploy
- queue health verification
- rollback plan for app and schema changes

## 17. What 3.1 Should Not Do

Do not introduce these in 3.1:

- fully split transactional microservices
- event sourcing for all state
- autonomous pricing self-modification
- AI-generated pricing without deterministic verification
- giant orchestration layers in the critical path

These would add failure surface faster than they add value.

## 18. Recommended Repository Layout Evolution

Target application structure:

- `app/domains/identity`
- `app/domains/crm`
- `app/domains/estimating`
- `app/domains/pricing`
- `app/domains/workflow`
- `app/domains/proposals`
- `app/domains/documents`
- `app/domains/learning`
- `app/platform/db`
- `app/platform/queue`
- `app/platform/storage`
- `app/platform/search`
- `app/platform/telemetry`
- `app/platform/auth`

This keeps business logic separated from infrastructure and gives a clean path to later extraction if it ever becomes necessary.

## 19. Recommended Next Artifact

Before implementation, create a detailed execution plan that includes:

- concrete schema changes
- migration sequencing
- queue definitions
- event payload contracts
- service module boundaries
- testing strategy
- deployment rollout plan

The next step after this design should be a task-by-task implementation plan, not direct coding against an informal architecture idea.
