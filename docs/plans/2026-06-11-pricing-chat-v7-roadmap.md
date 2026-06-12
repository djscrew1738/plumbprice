# Pricing Chat v7.0 Roadmap — Comprehensive Improvement Plan

**Date:** 2026-06-11  
**Status:** Phase 1.1 + 1.2 implemented; remaining phases planned  
**Target Version:** v7.0.0 (with incremental v6.6.x–v6.9.x milestones)  
**Author:** AI Agent, v6.6.0 implementation checkpoint  

---

## 1. Executive Summary

The v6.5 pricing-chat overhaul is **complete**. All 7 sprints are green:

- ✅ Architecture refactor into composable hooks/components
- ✅ Modern chat UX (actions, command palette, shortcuts, markdown)
- ✅ Mobile, performance & accessibility
- ✅ Data visualization (waterfall, margins, sparklines, diffs)
- ✅ Collaboration & sharing
- ✅ Templates, voice input, field mode, backend hardening

This plan defines the **next 12–18 months** of pricing-chat investment. It is organized into **five strategic themes**, each broken into concrete phases with backend/frontend changes, migrations, tests, and success metrics.

**Strategic themes:**

1. **Intelligent Automation** — Let the AI do more of the estimator's busywork.
2. **Field-First Experience** — Make the chat truly usable from a job site.
3. **Trust & Accuracy** — Close the loop between estimates and actuals.
4. **Business Growth** — Turn estimates into proposals, signatures, and jobs.
5. **Platform Extensibility** — APIs, integrations, and admin tooling.

---

## 2. Current State Snapshot

### What already works

| Capability | Status | Notes |
|------------|--------|-------|
| Streaming chat with SSE | ✅ | Includes `Last-Event-ID` reconnect, DB retry, narrative persistence |
| Natural-language revisions | ✅ | Delta detection + `PricingEngine` recompute |
| Session memory / context | ✅ | County, job type, supplier preferences |
| pgvector task-code retrieval | ✅ | Top-20 ANN search merged with common codes |
| Estimate variants (compare) | ✅ | Budget / standard / premium via `chatApiV3.compare()` |
| Sharing & guest view | ✅ | JWT-signed tokens, expiry, permissions |
| Comments / @mentions | ✅ | Per-estimate threaded comments |
| Blueprint upload & analysis | ✅ | Detects fixtures; auto-seeding column in place |
| Templates | ✅ | Quick codes + saved prompt templates with variables |
| Voice input | ✅ | Browser STT primary, Whisper fallback |
| Field mode | ✅ | Large touch targets, high contrast |
| Data visualization | ✅ | Waterfall, margin bars, sparklines, diff cards |

### Known debt (unchanged)

- `test_activity_empty_on_create` — 1 pre-existing test failure.
- `client.test.ts` — 30 pre-existing TypeScript errors in test mocks.
- `BulkImportPanel.tsx` — 2 pre-existing jsx-a11y lint errors.

---

## 3. Theme 1 — Intelligent Automation

### Goal
Reduce the number of messages and manual edits required to produce a quote from first contact to signed proposal.

### Phase 1.1 — Auto-Fill from Minimal Input (v6.6.0) ✅ IMPLEMENTED

**Problem:** Users still type "3 bath remodel in Plano" and then must answer clarifying questions.

**Solution:** A lightweight "intake agent" classifies intent, runs a property lookup, and pre-fills reasonable defaults.

**Backend**

- New service: `api/app/services/intake_agent.py`
  - Input: first user message
  - Output: `IntakeResult` with `intent`, `fixture_counts`, `location`, `urgency`, `preferred_tier`, `confidence`
- Integrate with `agent_v3.py` so first classification consumes `IntakeResult`.
- Add `POST /api/v3/chat/intake` endpoint for explicit intake forms.

**Frontend**

- New component: `IntakeCard.tsx` — shows inferred facts as editable chips above the first assistant message.
- `useChatOrchestrator`: if first response includes `intake_result`, render the card and pause streaming until user confirms.

**Migration**

- None (uses existing `ChatSession` columns).

**Tests**

- `test_intake_agent.py`: unit tests for fixture inference.
- Playwright: first message triggers intake card → edit chip → confirm → estimate arrives.

---

### Phase 1.2 — Proactive Revision Suggestions (v6.6.0) ✅ IMPLEMENTED

**Problem:** Users don't know what they can revise.

**Solution:** After every estimate, the agent suggests 3 context-aware revisions based on the current estimate content and common upsells.

**Backend**

- Extend `agent_v3.py` `generate_response_stream()` to emit `suggestion` events with:
  - `label`: "Upgrade to tankless?"
  - `action`: structured delta payload
  - `confidence`: 0.0–1.0
- Rules engine in `api/app/services/revision_suggestions.py`:
  - If estimate has `wh.50g_gas_unit` → suggest tankless upgrade.
  - If no permit line → suggest adding permit.
  - If `bathroom_count > 1` → suggest whole-house repipe.

**Frontend**

- Extend `SuggestionChips.tsx` to accept server-generated suggestions.
- Clicking a suggestion sends a hidden revision message and streams the new estimate.

**Tests**

- Vitest: `SuggestionChips` renders server suggestions and calls `onSelect`.
- API test: common fixture combos yield expected suggestions.

---

### Phase 1.3 — Follow-Up & Reminder Agent (v6.7.0)

**Problem:** Estimates are created and abandoned.

**Solution:** A Celery beat task identifies stale estimates and sends contextual follow-ups via email/push.

**Backend**

- New task: `worker/tasks/followups.py` `send_estimate_followups()`
- Runs daily.
- Queries estimates with status `draft` older than 24h, no activity in 12h.
- Generates 1-sentence personalized nudge via lightweight LLM.
- Sends via Resend / push notifications.

**Frontend**

- `NotificationBell` shows follow-up summaries.
- `/settings/notifications` adds toggles for estimate follow-ups.

**Migration**

- `v6p7p0_estimate_followups` — `estimates.follow_up_sent_at` timestamp.

**Tests**

- Worker test: task runs eagerly, sends expected number of emails.

---

## 4. Theme 2 — Field-First Experience

### Goal
Make the chat the fastest way to price a job while standing in a crawl space or driveway.

### Phase 2.1 — Offline-First Chat Queue (v6.7.0)

**Problem:** Job sites have spotty connectivity; field users lose work.

**Solution:** Extend the existing `useOutbox` pattern to chat messages and blueprint uploads.

**Backend**

- `POST /api/v3/chat/sync` batch endpoint: accepts an ordered array of pending messages, returns all generated estimates in one response.
- Idempotency key per message to avoid duplicates.

**Frontend**

- `useChatOutbox.ts` hook:
  - Stores pending messages in IndexedDB.
  - Auto-syncs when connection returns.
  - Shows "Queued" badge with retry count.
- `ChatContainer`: visual offline banner + manual sync button.

**Migration**

- None.

**Tests**

- Vitest: queue, persistence, sync success/failure.
- Playwright: throttle to offline, send message, reconnect, assert sync.

---

### Phase 2.2 — Photo-Driven Estimating (v6.8.0)

**Problem:** Field techs take photos but must manually describe what they see.

**Solution:** Upload a photo of the existing fixture; vision model identifies it and proposes a replacement estimate.

**Backend**

- New endpoint: `POST /api/v3/chat/photo-estimate`
- Uses GPT-4o Vision / local Llava via `llm_structured` vision client.
- Returns detected fixture canonical item, condition notes, and recommended replacement.
- Stores photo as `ChatAttachment` with `attachment_type = "photo_estimate"`.

**Frontend**

- `PhotoEstimateButton.tsx` in input bar.
- `PhotoEstimateCard.tsx` shows detected fixture + "Looks good, price it" CTA.

**Migration**

- Add `photo_estimate` to `ChatAttachment.attachment_type` enum.

**Tests**

- Mock vision response test.
- Playwright: upload fixture photo → see detection card.

---

### Phase 2.3 — Wearable / Headset Voice Mode (v6.9.0)

**Problem:** Holding a phone while working is impractical.

**Solution:** Push-to-talk with continuous listening, wake word, and earpiece audio read-back.

**Backend**

- Extend `POST /api/v3/chat/voice` to support chunked streaming upload.
- Add TTS cache for common estimate summaries.

**Frontend**

- `VoiceInputButton.tsx` enhancements:
  - Wake-word detection ("Hey PlumbPrice").
  - Lock-screen widget for PWA.
  - Bluetooth headset button support via `mediaSession`.
- `SpeechSynthesis` read-back with pause/resume.

**Migration**

- None.

**Tests**

- Vitest: wake-word detection utility.

---

## 5. Theme 3 — Trust & Accuracy

### Goal
Every number in the chat is traceable, verifiable, and continuously improving.

### Phase 3.1 — Variance & Actuals Loop (v6.8.0)

**Problem:** Estimates drift from reality; there's no systematic correction.

**Solution:** After a job is marked complete, compare actual cost to estimate and surface variance to admins. Approved variances feed pricing recommendations.

**Backend**

- Extend `EstimateOutcome` model with `actual_line_items` JSON.
- New endpoint: `POST /api/v3/estimates/{id}/outcomes`
- `pricing_corrections.py` already emits recommendations; now auto-link to chat sessions.
- Admin endpoint: `GET /admin/pricing/variances` with filters.

**Frontend**

- `OutcomeRecorderCard.tsx` already exists; wire it into chat context.
- `VarianceChip.tsx`: if a similar past estimate had >10% variance on a line item, show a warning chip.

**Migration**

- None (uses existing models).

**Tests**

- API test: submit outcome → recommendation created.

---

### Phase 3.2 — Confidence Calibration (v6.8.0)

**Problem:** Confidence scores are not well-calibrated.

**Solution:** Track confidence → outcome correlation and adjust thresholds.

**Backend**

- `ml_confidence.py` service:
  - Bins estimates by confidence score.
  - Compares to outcome variance.
  - Returns calibration curve.
- Admin endpoint: `GET /admin/ml/confidence-calibration`.

**Frontend**

- Calibration chart in admin analytics (Recharts).
- Adjust confidence thresholds from admin UI.

**Migration**

- None.

**Tests**

- Unit tests for binning and correlation logic.

---

### Phase 3.3 — Human-in-the-Loop Review Queue (v6.9.0)

**Problem:** Low-confidence estimates go straight to customers.

**Solution:** Add a review queue for estimates below a configurable confidence threshold.

**Backend**

- `Estimate.review_status` enum: `auto_approved`, `pending_review`, `approved`, `rejected`.
- Admin endpoints:
  - `GET /admin/reviews/pending`
  - `POST /admin/reviews/{id}/approve`
  - `POST /admin/reviews/{id}/reject`
- Webhook / email notification on pending review.

**Frontend**

- `ReviewBadge.tsx` on estimate cards in chat.
- New `/admin/reviews` page with inline diff and approve/reject.

**Migration**

- `v6p9p0_estimate_review` — `estimates.review_status`, `estimates.reviewed_by`, `estimates.reviewed_at`.

**Tests**

- API test: low-confidence estimate enters queue; approve updates status.

---

## 6. Theme 4 — Business Growth

### Goal
Turn a chat estimate into revenue faster: proposals, signatures, scheduling, and payments.

### Phase 4.1 — One-Click Proposal from Chat (v6.8.0)

**Problem:** Users must leave chat to create a proposal.

**Solution:** "Create proposal" suggestion chip generates a branded PDF proposal and opens it in a side panel.

**Backend**

- Reuse existing proposal generation service.
- New endpoint: `POST /api/v3/estimates/{id}/proposals/quick`.
- Returns `proposal_id` + `pdf_url`.

**Frontend**

- `ProposalPanel.tsx` slides out from right rail.
- Shows proposal preview, editable cover letter, send button.

**Migration**

- None.

**Tests**

- API test: quick proposal created from estimate.
- Vitest: panel renders and calls send endpoint.

---

### Phase 4.2 — E-Signature Integration (v6.9.0)

**Problem:** Proposals require printing, signing, scanning.

**Solution:** Integrate DocuSign / HelloSign or a lightweight self-serve e-signature flow.

**Backend**

- New service: `api/app/services/signatures.py`
- Endpoints:
  - `POST /api/v3/proposals/{id}/signature-request`
  - `GET /api/v3/proposals/{id}/signature-status`
- Webhook receiver for signature events.

**Frontend**

- `SignatureStatusBadge.tsx` in chat and proposal list.
- `SignatureRequestDialog.tsx` for recipient + message.

**Migration**

- `v6p9p0_signature_requests` — `signature_requests` table.

**Tests**

- Mock signature provider webhook test.

---

### Phase 4.3 — Schedule from Estimate (v7.0.0)

**Problem:** Approved estimates still require manual scheduling.

**Solution:** Detect job duration from estimate labor hours and offer available calendar slots.

**Backend**

- New service: `api/app/services/scheduling.py`
- Estimate → expected labor hours → duration blocks.
- Integration with Google Calendar / Outlook / native `CalendarEvent` table.
- Endpoint: `POST /api/v3/estimates/{id}/schedule-options`.

**Frontend**

- `ScheduleOptionsCard.tsx` in chat after proposal acceptance.
- Pick slot → create calendar event.

**Migration**

- `v7p0p0_schedule_events` — `calendar_events` table.

**Tests**

- Unit tests for labor-hour → duration calculation.
- API test: schedule options returned.

---

## 7. Theme 5 — Platform Extensibility

### Goal
Let admins, partners, and power users customize and extend the chat experience.

### Phase 5.1 — Custom Prompt Rules (v6.7.0)

**Problem:** Every contractor prices differently; hard-coded prompts don't scale.

**Solution:** Admin UI to add custom rules that prepend/append text to system prompts per organization.

**Backend**

- New model: `OrganizationPromptRule` (organization_id, scope, priority, content, enabled).
- `agent_v3.py` loads rules and injects them into `build_system_prompt()`.

**Frontend**

- `/admin/prompt-rules` page: CRUD rules with preview.

**Migration**

- `v6p7p0_prompt_rules` — `organization_prompt_rules` table.

**Tests**

- API test: rule injected into prompt.

---

### Phase 5.2 — Supplier Price Alerts in Chat (v6.8.0)

**Problem:** Prices change; estimates become stale.

**Solution:** If a line-item SKU price changes after estimate creation, show a "Price changed" warning in chat.

**Backend**

- Celery task: `check_estimate_price_staleness()` runs hourly.
- Compares stored `unit_cost` to current supplier price.
- Creates `EstimatePriceAlert` records.

**Frontend**

- `PriceAlertBanner.tsx` on affected estimate cards.
- "Refresh prices" button re-runs pricing engine.

**Migration**

- `v6p8p0_price_alerts` — `estimate_price_alerts` table.

**Tests**

- Worker test: price change triggers alert.

---

### Phase 5.3 — Chat API & Webhooks for Partners (v7.0.0)

**Problem:** Partners can't embed PlumbPrice chat in their own tools.

**Solution:** Public v3 chat API keys and webhook subscriptions.

**Backend**

- `api_keys` table extension: scope `chat:read`, `chat:write`.
- New endpoints under `/api/v3/partner/chat/*`:
  - `POST /sessions`
  - `POST /messages`
  - `GET /estimates/{id}`
- Webhook event types: `estimate.created`, `estimate.revised`, `proposal.signed`.

**Frontend**

- `/settings/api` page: generate chat-scoped keys.
- `/settings/webhooks` page: subscribe to events.

**Migration**

- `v7p0p0_partner_api` — `api_keys.scopes`, `webhook_subscriptions` table.

**Tests**

- API test: partner key creates session and message.
- Webhook test: event delivered to mock endpoint.

---

## 8. Cross-Cutting Initiatives

### 8.1 — Observability & Cost Tracking

- Add OpenTelemetry spans to `agent_v3.py`, `pricing_engine.py`, and streaming endpoint.
- Track per-request LLM token cost and cache hit rate.
- Dashboard: `/admin/costs` showing daily chat cost by provider.

### 8.2 — A/B Testing Framework for Prompts

- Reuse existing `model_ab.py` shadow-deployment pattern.
- Add prompt variant experiments: `prompt_experiments` table, bucket assignment, metric tracking.
- Target: measure conversion from first message → saved estimate by prompt variant.

### 8.3 — Accessibility Certification

- Audit chat components against WCAG 2.1 AA.
- Add axe-core to Playwright E2E suite.
- Fix remaining `BulkImportPanel.tsx` a11y errors.

### 8.4 — Localization Preparation

- Extract all chat strings to a translation dictionary.
- Spanish (es-MX) as first target market for DFW contractors.
- RTL layout audit for future Arabic/Hebrew support.

---

## 9. Implementation Timeline

| Version | ETA | Phases | Headline Feature |
|---------|-----|--------|------------------|
| v6.6.0 | +2 weeks | 1.1, 1.2 | Intake agent + proactive revision suggestions |
| v6.7.0 | +5 weeks | 1.3, 2.1, 5.1 | Offline chat queue + follow-up agent + prompt rules |
| v6.8.0 | +9 weeks | 2.2, 3.1, 3.2, 4.1, 5.2 | Photo estimating + variance loop + quick proposals + price alerts |
| v6.9.0 | +13 weeks | 2.3, 3.3, 4.2 | Voice wearable mode + review queue + e-signatures |
| v7.0.0 | +18 weeks | 4.3, 5.3 | Schedule from estimate + partner API/webhooks |

---

## 10. Architecture Decisions

### Decision 1 — Keep agent_v3 as the single orchestrator
All new intelligent features (intake, suggestions, photo estimate) route through `agent_v3.py`. Avoid spawning separate agents; instead add modular sub-services called by the orchestrator.

### Decision 2 — Feature flags per theme
Each theme gets a top-level feature flag:
- `INTAKE_AGENT_ENABLED`
- `OFFLINE_CHAT_ENABLED`
- `PHOTO_ESTIMATE_ENABLED`
- `REVIEW_QUEUE_ENABLED`
- `E_SIGNATURE_ENABLED`

This lets us ship dark or run gradual rollouts.

### Decision 3 — Reuse existing MinIO + Celery infrastructure
All async work (follow-ups, price alerts, signature webhooks) uses existing Celery queues. No new infrastructure until v7.0 partner API load requires it.

### Decision 4 — Admin-first for trust features
Variance, review queue, and prompt-rule features are built for admins/owners first, then exposed to field users once stable.

---

## 11. Testing Strategy

### Unit tests
- `test_intake_agent.py`
- `test_revision_suggestions.py`
- `test_photo_estimate.py`
- `test_pricing_confidence.py`
- `test_prompt_rules.py`

### Integration tests
- `test_chat_offline_sync.py`
- `test_estimate_review_queue.py`
- `test_proposal_quick_create.py`
- `test_partner_chat_api.py`

### E2E Playwright tests
- `estimator-v3-intake.spec.ts`
- `estimator-v3-offline.spec.ts`
- `estimator-v3-photo-estimate.spec.ts`
- `estimator-v3-review-queue.spec.ts`
- `estimator-v3-proposal.spec.ts`

### Performance tests
- Target: p95 chat first response < 800ms.
- Target: streaming time-to-first-token < 300ms.
- Benchmark intake agent latency weekly.

---

## 12. Risks & Mitigation

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Photo estimate accuracy too low | Medium | High | Keep behind feature flag; fallback to manual description; human review queue |
| Offline sync conflicts | Medium | High | Idempotency keys; last-write-wins with conflict banner |
| E-signature integration complexity | Medium | Medium | Start with one provider (HelloSign); abstract interface for swaps |
| Review queue overwhelms admins | Medium | Medium | Configurable threshold; auto-approve after timeout; batch approve UI |
| Partner API abuse | Low | High | Rate limits, scoped keys, webhook signatures |
| LLM cost spikes from photo vision | Medium | Medium | Cache vision results by image hash; use local Llava when available |

---

## 13. Success Metrics

| Metric | Baseline (v6.5) | v7.0 Target | Measurement |
|--------|-----------------|-------------|-------------|
| Messages to first estimate | 3.2 | <2.0 | Chat analytics |
| Estimate abandonment rate | unknown | <30% | `estimates.status = draft` after 7 days |
| Manual edits per estimate | unknown | <3 | Line-item edit count |
| Field user satisfaction (NPS) | unknown | >50 | In-app survey after 10th estimate |
| Proposal conversion rate | unknown | >40% | Proposals signed / estimates sent |
| Estimate variance (actual vs estimate) | unknown | <10% | Outcome records |
| Chat API partner adoption | 0 | 5 integrations | Partner API key usage |

---

## 14. Open Questions

1. Should we build our own lightweight e-signature UI to avoid third-party fees, or integrate DocuSign/HelloSign first?
2. Which calendar provider should we prioritize for scheduling? Google Calendar has highest contractor adoption in DFW.
3. Do we need a native mobile app for wearable voice mode, or is PWA sufficient?
4. Should photo estimating use cloud vision (higher accuracy, cost) or local Llava (lower cost, on-prem GPU required)?
5. How do we price the partner API? Per-message, per-estimate, or seat-based?

---

*Plan saved to `docs/plans/2026-06-11-pricing-chat-v7-roadmap.md`.*
