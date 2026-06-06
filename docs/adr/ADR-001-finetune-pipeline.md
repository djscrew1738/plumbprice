# ADR-001: LLM Fine-Tuning Pipeline Architecture

**Status:** Accepted  
**Date:** 2026-06-05  
**Version:** 4.1.0

---

## Context

PlumbPrice AI v3.0 uses OpenAI GPT-4o-mini for intent classification and canonical item mapping. The classification accuracy directly determines estimate quality. As the system accumulates historical data (job wins, closed estimates, high-confidence agent traces), we have an opportunity to fine-tune a custom model that better understands DFW plumbing vocabulary and pricing context.

Key constraints:
- The LLM must never touch dollar math — only classification
- A fine-tuned model that performs worse than the baseline must be reverted automatically
- The organization's production estimates must not be disrupted during model evaluation
- OpenAI fine-tuning costs real money; we must not start jobs without sufficient quality data

---

## Decision

### Architecture

We use a **shadow deployment** pattern:

```
Incoming classify request
        │
        ▼
  ┌───────────┐
  │  Router   │◄── model_ab.py checks shadow traffic % (default 10%)
  └───────────┘
       │  90%            10%
       ▼                 ▼
 Production model   Shadow model (fine-tuned)
 (current OpenAI)       │
       │            Log result + compare
       └────────────┘
            │
       Return production result
       (shadow is silent — never shown to user)
```

The shadow model never influences the output seen by estimators. It runs silently in parallel, logging its classification alongside the production model's classification. Once 100 shadow calls accumulate, an admin can review the match rate and promote the model if it outperforms baseline by ≥5%.

### Training Data Quality Gate

Only training pairs meeting **all** of the following criteria are included:
1. Estimate confidence score ≥ 0.85
2. Estimate outcome = won (job was awarded)
3. User message length > 15 characters
4. At least 1 non-empty line item on the estimate
5. No unresolved canonical items (all items mapped)

### Data Format

OpenAI JSONL format with system + user + assistant messages:
```json
{
  "messages": [
    {"role": "system", "content": "<classification system prompt>"},
    {"role": "user", "content": "<estimator message>"},
    {"role": "assistant", "content": "<structured ClassifyResult JSON>"}
  ]
}
```

### Minimum Samples Gate

Fine-tuning only proceeds when `ML_FINETUNE_MIN_SAMPLES` (default: 50) qualifying pairs exist. This prevents wasting API spend on insufficient training data.

### Promotion Criteria

An admin can promote a shadow model to production when:
- ≥ 100 shadow inference calls have been logged
- `shadow_match_rate > baseline_score + 0.05` (5 percentage points improvement)

### Model Registry

All model versions (shadow, production, retired) are stored in the `ml_models` table with full audit trail including who promoted, when, and what the eval score was.

---

## Consequences

**Positive:**
- Production never disrupted by unvalidated model changes
- Full audit trail of all model versions and promotions
- Automatic data quality filtering prevents garbage-in-garbage-out
- Admin has full control over promotion timing

**Negative:**
- Each fine-tuning job costs ~$3-15 depending on sample count (OpenAI pricing)
- Shadow evaluation requires 100+ real requests, which takes calendar time
- If Ollama local model replaces OpenAI in the future, this pipeline needs adaptation

**Neutral:**
- Fine-tuning is opt-in (`ML_FINETUNE_ENABLED=false` by default) — must be explicitly enabled when data volume is ready
