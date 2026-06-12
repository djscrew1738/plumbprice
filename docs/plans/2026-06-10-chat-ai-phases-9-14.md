# Chat AI Enhancement — Phases 9–14 Implementation Plan

**Date:** 2026-06-10  
**Status:** Phases 9–10 complete, Phase 11 in progress, Phases 12–14 planned  
**Target Version:** v6.3.0

---

## Phase 9 — Proactive Memory Suggestions ✅ COMPLETE

### What it does
Before LLM classification, the agent retrieves the user's top-3 most relevant `agent_memories` (preference, profile, fact). It formats them as context and generates `suggested_context` — structured suggestions with field, value, reason, and confidence.

### Backend changes
- `agent_v3.py`: `_build_suggested_context()` generates structured suggestions from memories
- `llm_structured.py`: `classify()` accepts `memory_context` and injects it into system prompt
- `chat.py` router: forwards `suggested_context` in both streaming and non-streaming responses

### Frontend changes
- `api-v3.ts`: `SuggestedContextV3` type, added to `ChatPriceResponseV3` and stream events
- `EstimatorPageV3.tsx`: 
  - Captures `suggested_context` from pricing stream events
  - Renders dismissible chip row above input with 💡 icon and confidence stars
  - Clicking a chip appends `field: value` to the input
  - Clears on send

### Test coverage
- `test_chat_session.py`: 8 passed

---

## Phase 10 — Enhanced Revision Diff ✅ COMPLETE

### What it does
`_compute_estimate_diff` now matches line items by `canonical_item` (falling back to `description`) instead of fragile index-based matching. This makes material swaps, quantity changes, and line-item additions/removals render correctly in frontend diff badges.

### Backend changes
- `agent_v3.py`: `_compute_estimate_diff()` uses dict keyed by `canonical_item or description`
- Detects added, removed, and modified (quantity or unit_price changed) line items

### Frontend changes
- `ChatMessageListV3.tsx`: already renders added (+N blue), removed (−N red), modified (~N violet), and total delta badges

---

## Phase 11 — Blueprint-to-Estimate Auto-Seeding 🚧 IN PROGRESS

### Goal
When a user uploads a blueprint, the AI analysis detects fixture counts (sinks, toilets, water heaters, etc.). Instead of just showing a summary, these counts should automatically seed the estimate quantities when the user next asks for an estimate.

### Backend plan
1. **Extend `BlueprintAnalysisResult`** to return structured `detected_fixtures: list[FixtureCount]`
2. **Store fixtures on `ChatSession`** — new JSONB column `blueprint_fixtures` or reuse `metadata`
3. **Inject fixtures into classify prompt** — when a blueprint was uploaded, add: "Blueprint detected: 3 sinks, 2 toilets..."
4. **Seed quantities in `PricingEngine`** — if task_code matches a detected fixture, use the detected count as default quantity

### Frontend plan
1. After blueprint upload, show detected fixtures in a small summary chip
2. When estimate is generated, show "🔧 Quantities seeded from blueprint" tooltip

### Open questions
- Should fixture detection happen in the worker (Celery) or inline during chat?
- How to map detected fixture names to canonical task codes?

---

## Phase 12 — Multi-Estimate Comparison

### Goal
Allow users to generate 2–3 variant estimates (e.g., budget / standard / premium) and compare them side-by-side in the chat.

### Backend plan
1. **New endpoint** `POST /api/v3/chat/compare` — accepts a message and generates N variants
2. **Variant generation strategies**:
   - `budget`: use lower-grade materials, minimal labor multipliers
   - `standard`: default pricing
   - `premium`: upgrade materials, add warranty line items
3. **Store variants** as linked `Estimate` rows with `variant_group_id`
4. **New response type** `ChatCompareResponseV3` with array of estimates + diff summary

### Frontend plan
1. **Compare mode toggle** in input area (💰 Budget | ⚖️ Standard | ⭐ Premium)
2. **Side-by-side cards** in chat when compare response arrives
3. **Highlight differences** — which line items change, total delta between variants

### Complexity: Medium

---

## Phase 13 — Voice Input & Hands-Free Mode

### Goal
Enable field technicians to dictate estimates hands-free using speech-to-text, with the AI reading back the estimate via TTS.

### Backend plan
1. **New endpoint** `POST /api/v3/chat/voice` — accepts audio blob, returns transcribed text + estimate
2. **Integration options**:
   - Whisper API (OpenAI) for transcription
   - Browser-native `SpeechRecognition` for frontend transcription (faster, no upload)
3. **TTS response** — optional `audio_url` in response using OpenAI TTS or browser `SpeechSynthesis`

### Frontend plan
1. **Mic button** in input bar with recording animation
2. **Voice activity detection** — auto-stop after silence
3. **Read-back toggle** — "Read estimate aloud" switch in settings
4. **Accessibility** — full keyboard + screen reader support for voice flow

### Complexity: Medium-High

---

## Phase 14 — Estimate Versioning & Branching

### Goal
Treat estimates like git commits — every revision creates a new version, users can browse history, diff between versions, and "branch" to explore alternatives without losing the original.

### Backend plan
1. **`EstimateVersion` table** (already exists) — store immutable snapshots
2. **New endpoints**:
   - `GET /estimates/{id}/versions` — list all versions
   - `GET /estimates/{id}/versions/{version_id}/diff` — diff against previous
   - `POST /estimates/{id}/branch` — fork current estimate into a new estimate tree
3. **Version numbering** — semantic-style: `1.0`, `1.1`, `2.0` based on revision depth
4. **Chat integration** — `revert to version N` natural language command

### Frontend plan
1. **Timeline UI** — vertical timeline of estimate versions in the breakdown sheet
2. **Diff view** — inline added/removed/changed highlighting between selected versions
3. **Branch button** — "Explore alternative" creates a branch from any version
4. **Restore button** — revert chat to a previous version's state

### Complexity: High

---

## Migration Strategy

| Phase | Migration | Tables/Columns |
|-------|-----------|---------------|
| 9 | None | Uses existing `agent_memories` |
| 10 | None | Pure code change |
| 11 | `v6p3p0_blueprint_fixtures` | `chat_sessions.blueprint_fixtures` JSONB |
| 12 | `v6p4p0_estimate_variants` | `estimates.variant_group_id`, `estimates.variant_label` |
| 13 | None | External API integration |
| 14 | `v6p5p0_estimate_branches` | `estimates.branch_id`, `estimates.version_number` |

---

## Appendix: Pre-existing Issues

- `test_activity_empty_on_create` — 1 pre-existing failure unrelated to chat AI
- `client.test.ts` TypeScript errors — 30 pre-existing type issues in test mocks
- `BulkImportPanel.tsx` a11y lint errors — 2 pre-existing jsx-a11y issues
