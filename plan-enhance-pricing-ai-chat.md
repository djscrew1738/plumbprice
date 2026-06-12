# Plan: Enhance Pricing AI Chat (v6.0.0)

**Scope:** Substantial (3–4 weeks) · Contractor power-user focus · ChatGPT-style conversational UX

---

## 1. Goal & Scope

**Objective:** Make the v3 pricing chat feel like a true plumbing estimator partner — it remembers context, handles natural revisions, classifies rare tasks accurately, and learns from its mistakes.

**IN scope:**
- Semantic task-code retrieval for better classification coverage
- Natural-language estimate revision (add / remove / modify / upgrade)
- Session-scoped property context memory (county, stories, access, urgency)
- Classification feedback loop (thumbs up/down → admin analytics)
- Streaming persistence fix + inline estimate editing + context-aware suggestion chips

**OUT of scope:**
- True cross-session long-term memory (RAG over all past estimates) — deferred to v6.1
- Full blueprint structural analysis integration — deferred until blueprint takeoff accuracy > 85%
- Voice chat overhaul — separate initiative
- Public widget overhaul — separate initiative

---

## 2. Files to Create / Modify

### Phase 1 — Intelligent Task Code Discovery
| File | Action | Purpose |
|------|--------|---------|
| `api/app/services/task_code_embeddings.py` | **NEW** | Build & query pgvector embeddings for all 314+ canonical items |
| `api/alembic/versions/v6p0p0_chat_embeddings.py` | **NEW** | Migration: `chat_embeddings` table (id, canonical_item, embedding, model_name) |
| `api/app/services/llm_structured.py` | **MODIFY** | `classify()` prompt now receives dynamically retrieved top-20 task codes + the 69 common ones |
| `api/app/scripts/seed_embeddings.py` | **NEW** | One-shot script to generate embeddings for all canonical items |
| `api/app/services/agent_v3.py` | **MODIFY** | Wire embedding retrieval before classification |

### Phase 2 — Estimate Revision & Follow-up
| File | Action | Purpose |
|------|--------|---------|
| `api/app/services/agent_v3.py` | **MODIFY** | Add `detect_revision_intent()` + `apply_estimate_delta()` methods |
| `api/app/services/pricing_engine.py` | **MODIFY** | Add `calculate_delta_estimate()` — takes previous estimate + delta spec, returns new estimate |
| `api/app/schemas/chat.py` | **MODIFY** | Add `revision_type` enum (`add`, `remove`, `modify`, `upgrade`, `downgrade`) to request/response |
| `web/src/components/estimator-v3/ChatMessageListV3.tsx` | **MODIFY** | Render estimate diffs (green +added, red -removed) inline |
| `web/src/components/estimator-v3/EstimateDiffCard.tsx` | **NEW** | Visual diff showing old vs new line items |

### Phase 3 — Session Memory & Property Context
| File | Action | Purpose |
|------|--------|---------|
| `api/alembic/versions/v6p0p0_chat_session_context.py` | **NEW** | Migration: `context_json` column on `chat_sessions` |
| `api/app/models/chat.py` | **MODIFY** | Add `context_json` to `ChatSession` model |
| `api/app/services/agent_v3.py` | **MODIFY** | `extract_property_context()` — LLM extracts structured context from first 1-3 messages |
| `api/app/services/agent_v3.py` | **MODIFY** | `build_system_prompt()` — prepend extracted context to every classification |
| `web/src/components/estimator-v3/PropertyContextBar.tsx` | **NEW** | Subtle chip bar above input showing "Dallas County · 2-story · Standard access" |
| `api/app/routers/v3/chat.py` | **MODIFY** | Return `context` in `ChatPriceResponseV3` |

### Phase 4 — Misclassification Feedback Loop
| File | Action | Purpose |
|------|--------|---------|
| `api/alembic/versions/v6p0p0_classification_feedback.py` | **NEW** | Migration: `classification_feedback` table |
| `api/app/models/chat.py` | **MODIFY** | Add `ClassificationFeedback` ORM model |
| `api/app/routers/v3/chat.py` | **MODIFY** | `POST /api/v3/chat/feedback` endpoint |
| `web/src/components/estimator-v3/EstimateFeedbackBar.tsx` | **NEW** | Thumbs up/down + "What were you looking for?" free text |
| `web/src/lib/api-v3.ts` | **MODIFY** | `chatApiV3.submitFeedback()` method |
| `web/src/components/admin/AnalyticsTab.tsx` | **MODIFY** | Add "Classification Quality" heatmap (task code × accuracy) |
| `api/app/services/task_code_embeddings.py` | **MODIFY** | `reweight_from_feedback()` — bump/down-rank task codes based on feedback |

### Phase 5 — Streaming & Frontend Polish
| File | Action | Purpose |
|------|--------|---------|
| `api/app/routers/v3/chat.py` | **MODIFY** | Fix streaming endpoint: write final narrative back to `ChatMessage` after stream completes |
| `web/src/components/estimator-v3/EstimatorPageV3.tsx` | **MODIFY** | Inline estimate editing within chat messages; context-aware suggestion chips |
| `web/src/components/estimator-v3/SuggestionChips.tsx` | **MODIFY** | Chips now adapt to estimate state: "Add permit?", "Break out labor?", "Upgrade water heater?", "Save estimate?" |
| `web/src/components/estimator-v3/ToolCallIndicator.tsx` | **NEW** | Visual spinner showing "Searching materials…", "Looking up labor…" during tool calls |
| `api/app/routers/v3/chat.py` | **MODIFY** | Emit `tool_call` events with human-readable labels for frontend display |

---

## 3. Architecture / Key Decisions

### Decision 1: pgvector for Task Code Retrieval
**Trade-off:** Pre-computed embeddings (fast, requires migration) vs. on-the-fly keyword search (no migration, less accurate).
**Winner:** Pre-computed embeddings using existing pgvector infrastructure. We already have HNSW indexes and embedding infrastructure from v4.1. One-time seed script, then sub-10ms ANN queries.

### Decision 2: Delta Pricing, Not Full Re-pricing
**Trade-off:** Re-run the full pricing engine on every revision (simple, but loses manual edits) vs. apply deltas to the previous estimate (complex, preserves user intent).
**Winner:** Delta pricing. The engine computes a new estimate from scratch, but the *frontend* renders a diff. If the user previously edited line items, we warn that revisions will overwrite manual changes.

### Decision 3: Session-Scoped Context, Not Cross-Session Memory
**Trade-off:** True long-term RAG (powerful, complex, privacy concerns) vs. session context (good enough for 90% of estimates, simpler).
**Winner:** Session context for v6.0. Most plumbing estimates are scoped to a single conversation. Cross-session memory requires careful PII handling and is deferred.

### Decision 4: Feedback Loop Writes to DB, Not Immediate Retraining
**Trade-off:** Real-time embedding updates (complex, risk of poisoning) vs. batch reweighting from feedback (simple, admin-reviewed).
**Winner:** Batch reweighting. Feedback is stored immediately, but embeddings are only updated via a weekly admin-triggered job or explicit "Apply Feedback" button.

---

## 4. Step-by-Step Implementation

### Phase 1 — Intelligent Task Code Discovery (Days 1–4)
1. **Migration**: Create `chat_embeddings` table with pgvector `vector(1024)` column.
2. **Seed script**: `scripts/seed_embeddings.py` generates embeddings for all 314 canonical items using the existing `llm_embedding_model` (mxbai-embed-large). Insert into `chat_embeddings`.
3. **Service**: `task_code_embeddings.py` with `search_similar_task_codes(query: str, top_k: int = 20) -> list[str]`.
4. **Agent wiring**: In `agent_v3.py`, before calling `llm_structured.classify()`, retrieve top-20 similar codes from embeddings. Merge with the 69 common codes (deduplicated).
5. **LLM prompt update**: `llm_structured.py` classify prompt now receives the merged ~80-89 codes instead of a static list.
6. **Test**: Add test in `tests/routers/v3/test_chat.py` — send a rare task code message, assert it classifies correctly.

### Phase 2 — Estimate Revision & Follow-up (Days 5–9)
1. **Revision detection**: In `agent_v3.py`, after classification, check if the message contains revision keywords ("upgrade", "downgrade", "add", "remove", "instead of", "swap", "change to") AND a `session_id` with a previous estimate exists.
2. **Delta extraction**: Use a lightweight LLM prompt to parse the user's intent into a structured delta: `{ "action": "upgrade", "target_canonical_item": "wh.50g_gas_unit", "new_canonical_item": "wh.75g_gas_unit" }`.
3. **Pricing engine**: Add `calculate_delta_estimate()` that takes the previous estimate breakdown + delta spec, re-prices, and returns a new breakdown.
4. **Diff rendering**: Frontend `EstimateDiffCard` compares old and new `line_items` arrays, showing +added / -removed / ~modified rows.
5. **Test**: Test revision flow end-to-end: create estimate → send "upgrade to 75g" → verify new estimate has 75g water heater and updated totals.

### Phase 3 — Session Memory & Property Context (Days 10–13)
1. **Migration**: Add `context_json` JSONB column to `chat_sessions`.
2. **Extraction prompt**: After the first successful classification in a new session, fire a lightweight LLM call: "Extract property context from this conversation: county, property_type, stories, age, access_type, urgency." Return JSON.
3. **Persistence**: Save extracted context to `ChatSession.context_json`.
4. **Prompt injection**: In `build_system_prompt()`, prepend: "Property context: Dallas County, 2-story house, standard access."
5. **Frontend**: `PropertyContextBar` displays chips; users can click to edit/clear context.
6. **Test**: Test that context is extracted and reused across messages in the same session.

### Phase 4 — Misclassification Feedback Loop (Days 14–17)
1. **Migration**: `classification_feedback` table (id, session_id, message_id, task_code_detected, task_code_intended, feedback_type, comment, created_at).
2. **API**: `POST /api/v3/chat/feedback` — stores feedback record.
3. **Frontend**: `EstimateFeedbackBar` appears below each estimate card. Thumbs up = quick submit. Thumbs down = opens a small dropdown with common corrections + free text.
4. **Admin analytics**: Add a "Classification Quality" section to `AnalyticsTab` showing:
   - Top 10 misclassified task codes
   - Accuracy heatmap by task code category
   - Recent feedback comments table
5. **Reweighting job**: Weekly Celery task that reads feedback and adjusts task code embedding weights (simple: if code X was misclassified as Y 3+ times, reduce Y's similarity score for queries matching X's embedding region).
6. **Test**: Test feedback submission + admin analytics rendering.

### Phase 5 — Streaming & Frontend Polish (Days 18–21)
1. **Streaming persistence fix**: In the SSE endpoint, after `generate_response_stream()` completes, update the `ChatMessage` row with the full narrative text. Currently it's written as empty string.
2. **Inline editing**: In `ChatMessageListV3`, add an "Edit" button to estimate cards. Opens a mini `EstimateEditor` inline. On save, re-submits as a revision.
3. **Suggestion chips**: Rewrite chip generation logic. Chips are now context-aware:
   - After first estimate: "Add permit cost?", "Break out labor vs materials?", "Upgrade fixtures?"
   - After revision: "Save this estimate?", "Create proposal?"
   - After save: "Start new estimate?", "View all estimates?"
4. **Tool call visualization**: `ToolCallIndicator` shows animated dots + label when tools are running. SSE emits `tool_call` events with `{"tool": "search_materials", "label": "Searching material costs…"}`.
5. **Test**: E2E Playwright test for the full flow: send message → see tool indicators → see estimate → click suggestion chip → see revision.

---

## 5. Testing Strategy

### Unit Tests
- `test_task_code_embeddings.py`: Embedding generation, ANN search accuracy, deduplication with common codes.
- `test_pricing_engine_delta.py`: Delta calculation for add/remove/modify/upgrade actions.
- `test_agent_v3_context_extraction.py`: Mock LLM responses, assert context JSON structure.

### Integration Tests
- `test_chat_revision.py`: Full API flow — create estimate → revision message → assert diff response structure.
- `test_chat_feedback.py`: Submit feedback → assert DB record → assert admin analytics endpoint.
- `test_chat_streaming_persistence.py`: Stream endpoint → assert final narrative is persisted.

### E2E Tests (Playwright)
- `estimator-v3-revision.spec.ts`: User sends message, gets estimate, clicks "Upgrade water heater", sees diff.
- `estimator-v3-context.spec.ts`: Property context chips appear and are editable.
- `estimator-v3-feedback.spec.ts`: Thumbs down → select correction → submit → toast confirmation.

### Edge Cases
- **Rare task code (bottom 20% frequency)**: Ensure embedding retrieval surfaces it.
- **Conflicting revision**: "Add disposal" then "Remove disposal" in same session → should net to no change.
- **Empty context extraction**: User sends only "hi" → no context extracted, no error.
- **Feedback spam**: Rate-limit feedback submission to 1 per estimate per user.
- **Streaming timeout**: Narrative stream times out → static fallback still persisted.

---

## 6. Risks & Rollback

| Risk | Likelihood | Mitigation | Rollback |
|------|------------|------------|----------|
| Embedding retrieval adds >200ms latency to classify | Medium | Pre-warm embeddings in Redis cache; fallback to static 69-code list if retrieval fails | Toggle `USE_TASK_EMBEDDINGS=false` in config |
| Revision detection false-positives | Medium | Require high confidence (>0.85) from revision parser; show "Did you mean to revise?" confirmation | Revert `agent_v3.py` to skip revision branch |
| Context extraction pollutes classification with wrong county | Low | Validate extracted county against known DFW counties; discard if invalid | Clear `context_json` column manually |
| Feedback table grows unbounded | Medium | Add 90-day TTL on feedback rows; Celery beat task purges old records | N/A — data retention fix |
| Streaming persistence fix causes DB write amplification | Low | Only update the single `ChatMessage` row; no additional writes | Revert streaming endpoint to not persist narrative |

---

## 7. Success Metrics

| Metric | Baseline (v5.9) | Target (v6.0) | Measurement |
|--------|----------------|---------------|-------------|
| Task code accuracy (rare items) | ~60% | >85% | Manual spot-check of 50 rare tasks |
| Revision request handling rate | 0% | >70% | Log revision detection vs. successful delta |
| Average messages to first estimate | 3.2 | <2.5 | Chat session analytics |
| User feedback submission rate | 0% | >5% of estimates | `classification_feedback` row count |
| Streaming narrative persistence | 0% | 100% | DB query for `assistant_answer IS NOT NULL` |

---

*Plan saved to `plan-enhance-pricing-ai-chat.md`.*
