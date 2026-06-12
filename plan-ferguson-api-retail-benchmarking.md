# Plan — Verify Ferguson Live API + Retail Benchmarking

> **Scope**: Backend (`api/`) + Admin UI (`web/`)  
> **Goal**: Replace simulation pricing with verified Ferguson Trade Partner API integration, add a web-scraper fallback, and pivot manufacturer feeds to reliable Apify-based retail benchmarking from Home Depot / Lowe's.  
> **Version target**: 5.9.0

---

## 1. Goal & Scope

### In Scope
- Verify and activate Ferguson Trade Partner API (OAuth2 client credentials)
- Build Ferguson web-scraper fallback for when API is unavailable
- Add robust retry, circuit breaker, and health-check logic specifically for Ferguson
- Pivot Kohler/Moen/AO Smith feeds to Apify-based Home Depot / Lowe's retail benchmarking
- Expand Apify coverage from 12 items to 100+ common plumbing SKUs
- Add retail-to-wholesale price inference (60–70% of MSRP depending on category)
- Add admin UI for feed configuration and manual price override
- Add price alert notification endpoints + admin inbox UI
- Document API credentials and rate limits

### Out of Scope
- Geographic expansion beyond DFW
- ERP/accounting system integrations
- Subscription cost databases (RSMeans, Xactimate, Bluebook)
- Real-time inventory level APIs (Ferguson does not expose this publicly)
- Mobile app changes

---

## 2. Files to Create / Modify

### Ferguson API & Scraper
| File | Action | Purpose |
|------|--------|---------|
| `api/app/services/data_sources/suppliers/ferguson.py` | MODIFY | Verify live endpoint, fix response parsing, remove hardcoded simulation |
| `api/app/services/price_feeds/ferguson_adapter.py` | MODIFY | Stop hardcoding `simulation_mode=True`; honor env config |
| `api/app/services/price_feeds/ferguson_scraper.py` | NEW | Web-scraper fallback that parses ferguson.com search pages |
| `api/app/services/price_feeds/__init__.py` | NEW | Auto-register all adapters on import |
| `api/app/config.py` | MODIFY | Add `FERGUSON_API_VERIFY_MODE`, `FERGUSON_RATE_LIMIT_RPS`, `APIFY_TOKEN` validation |

### Retail Benchmarking (Apify)
| File | Action | Purpose |
|------|--------|---------|
| `api/app/services/data_sources/apify_source.py` | MODIFY | Expand from 12 → 100+ SKUs; add Lowe's; improve parsing |
| `api/app/services/price_feeds/retail_benchmark_adapter.py` | NEW | Wraps Apify source with retail→wholesale inference |
| `api/app/services/price_feeds/retail_inference.py` | NEW | Category-based MSRP→wholesale multiplier rules |
| `api/app/services/data_sources/expanded_apify_urls.json` | NEW | 100+ Home Depot / Lowe's search URLs mapped to canonical items |

### Admin & Alerts
| File | Action | Purpose |
|------|--------|---------|
| `api/app/routers/admin_pricing.py` | MODIFY | Add price alert CRUD endpoints, feed config endpoints |
| `api/app/routers/admin_feeds.py` | NEW | Dedicated router for feed config, manual sync trigger |
| `api/app/services/price_alert_service.py` | NEW | Generate and acknowledge price alerts |
| `web/src/components/admin/PriceAlertsTab.tsx` | NEW | Admin inbox for price change alerts |
| `web/src/components/admin/FeedConfigPanel.tsx` | NEW | Toggle feeds, set simulation mode, trigger manual sync |
| `web/src/components/admin/AdminPage.tsx` | MODIFY | Add Alerts and Feed Config tabs |
| `web/src/lib/hooks/useAdmin.ts` | MODIFY | Add `usePriceAlerts`, `useFeedConfig`, `useTriggerSync` |

### Worker & Monitoring
| File | Action | Purpose |
|------|--------|---------|
| `worker/tasks/price_feed_sync.py` | MODIFY | Run Apify benchmark + Ferguson API + Ferguson scraper fallback |
| `worker/tasks/supplier_refresh.py` | MODIFY | Remove incorrect `APIFY_TOKEN` gating; use feed health |
| `api/app/services/price_feed_adapter.py` | MODIFY | Add `last_error` tracking, response time metrics |

### Tests
| File | Action | Purpose |
|------|--------|---------|
| `api/tests/services/test_ferguson_adapter.py` | NEW | Mock OAuth2, mock product response, fallback behavior |
| `api/tests/services/test_retail_benchmark.py` | NEW | Apify response parsing, wholesale inference |
| `api/tests/services/test_price_alert_service.py` | NEW | Alert generation thresholds, ack flow |
| `api/tests/routers/test_admin_feeds.py` | NEW | Feed config, manual sync, health endpoint |

### Documentation
| File | Action | Purpose |
|------|--------|---------|
| `docs/FERGUSON_API.md` | NEW | Setup guide: how to get credentials, sandbox testing, rate limits |
| `docs/APIFY_RETAIL_BENCHMARK.md` | NEW | URL catalog, refresh cadence, wholesale inference rules |
| `AGENTS.md` | MODIFY | Add Ferguson + Apify sections |
| `CHANGELOG.md` | MODIFY | v5.9.0 entry |

---

## 3. Architecture & Key Decisions

### 3.1 Ferguson: API First, Scraper Fallback
**Decision**: Try Ferguson OAuth2 API first. If it fails (auth, rate limit, 5xx), fall back to the web scraper. If both fail, degrade to simulation.

**Why**: The official API is the only way to get real wholesale net prices. But Ferguson rate-limits and occasionally has outages. The scraper fallback keeps prices fresh when the API is down.

**Trade-off**: Maintaining both paths is more code. We mitigate by putting the fallback behind a small abstraction so the worker task doesn't need to know which source succeeded.

### 3.2 Retail Benchmarking Instead of Manufacturer Scrapers
**Decision**: Replace Kohler/Moen/AO Smith category-page scrapers with Apify-based Home Depot / Lowe's searches, then infer wholesale price.

**Why**: Manufacturer sites are designed for consumers, not wholesale buyers. Retail sites have stable search URLs, consistent HTML, and broad SKU coverage. A 60–70% retail-to-wholesale inference is more accurate than the current generic selectors on manufacturer listing pages.

**Trade-off**: We're estimating wholesale, not reading it. Confidence scores will reflect this (0.65 vs 0.95 for Ferguson API).

### 3.3 Confidence-Weighted Price Selection
**Decision**: When multiple feeds return a price for the same canonical item, store all results but prefer the highest-confidence feed.

**Why**: Ferguson API (0.95) > Ferguson scraper (0.75) > retail benchmark (0.65) > simulation (0.60). This gives transparent provenance for every price.

**Rule**:
```python
PREFERENCE = {
    "ferguson_api": 0.95,
    "ferguson_scraper": 0.75,
    "retail_benchmark": 0.65,
    "simulation": 0.60,
}
```

### 3.4 Config-Driven Feed Behavior
**Decision**: Add environment flags to control Ferguson behavior: `FERGUSON_API_VERIFY_MODE` (`strict`, `lenient`, `off`) and `FERGUSON_RATE_LIMIT_RPS`.

**Why**: Makes it safe to test the Ferguson API in development without risking production. `strict` fails hard on API errors; `lenient` falls through to scraper/simulation; `off` always uses simulation.

---

## 4. Step-by-Step Implementation

### Phase 1 — Ferguson API Verification (6–8 hours)
1. **Apply for / retrieve Ferguson sandbox credentials** and add to `.env.example`
2. **Update `ferguson.py`**: Replace `TODO(ferguson-api)` with verified endpoint path and response parser
3. **Add sandbox test**: Hit Ferguson sandbox with 5 SKUs, inspect response shape, adjust parsing
4. **Add rate limiting**: Token bucket in `FergusonScraper` using `FERGUSON_RATE_LIMIT_RPS`
5. **Update `ferguson_adapter.py`**: Read `FERGUSON_API_VERIFY_MODE`; do not hardcode `simulation_mode=True`
6. **Create `ferguson_scraper.py`**: Parse ferguson.com search results for SKU + price
7. **Create `__init__.py`**: Auto-register all feed adapters
8. **Update `config.py`**: Add new env vars with validation

### Phase 2 — Retail Benchmarking (6–8 hours)
9. **Curate `expanded_apify_urls.json`**: 100+ Home Depot / Lowe's URLs mapped to canonical items
10. **Refactor `apify_source.py`**: Support batching, Lowe's, better price extraction
11. **Create `retail_inference.py`**: Category multipliers (fixtures 0.60, water heaters 0.65, fittings 0.70)
12. **Create `retail_benchmark_adapter.py`**: Wrap Apify + apply inference
13. **Deprecate old manufacturer scrapers**: Move `kohler_scraper.py`, `moen_scraper.py`, `ao_smith_scraper.py` to `price_feeds/legacy/` or delete

### Phase 3 — Price Alerts & Feed Admin (6–7 hours)
14. **Create `price_alert_service.py`**: Detect >threshold price changes, create `SupplierPriceAlert` rows
15. **Add alert endpoints** to `admin_pricing.py`: `GET /price-alerts`, `PATCH /price-alerts/{id}/ack`
16. **Create `admin_feeds.py` router**: `GET /config`, `POST /config`, `POST /sync`, `GET /health`
17. **Add frontend hooks**: `usePriceAlerts`, `useFeedConfig`, `useTriggerSync`
18. **Build `PriceAlertsTab.tsx`**: Inbox with ack/filter
19. **Build `FeedConfigPanel.tsx`**: Toggle adapters, trigger manual sync
20. **Update `AdminPage.tsx`**: Add Alerts and Feed Config tabs

### Phase 4 — Worker Integration (3–4 hours)
21. **Update `price_feed_sync.py`**: Run Ferguson API → scraper → retail benchmark with confidence tracking
22. **Fix `supplier_refresh.py`**: Remove `APIFY_TOKEN` gating; rely on feed registry health
23. **Update `price_feed_adapter.py`**: Add response time tracking and `last_error`

### Phase 5 — Testing & Docs (4–5 hours)
24. **Write `test_ferguson_adapter.py`**: Mock OAuth2 + response, fallback chain
25. **Write `test_retail_benchmark.py`**: Apify fixture, inference math
26. **Write `test_price_alert_service.py`**: Threshold edge cases
27. **Write `test_admin_feeds.py`**: Config update, manual sync endpoint
28. **Write `docs/FERGUSON_API.md`**: Credentials, sandbox, rate limits
29. **Write `docs/APIFY_RETAIL_BENCHMARK.md`**: URL catalog, inference rules
30. **Update `AGENTS.md` and `CHANGELOG.md`**

---

## 5. Testing Strategy

### Unit Tests
- Ferguson adapter: OAuth2 token fetch, batch SKU lookup, fallback to scraper on 5xx, fallback to simulation on auth failure
- Retail inference: Each category maps to correct multiplier; unknown category defaults to 0.65
- Price alert service: 5% threshold triggers alert; 4% does not; ack sets `acknowledged=true`

### Integration Tests
- `POST /admin/feeds/sync` triggers worker and returns task ID
- `PATCH /admin/price-alerts/{id}` requires admin, updates acknowledged fields
- Ferguson sandbox test hits real endpoint in CI only when `FERGUSON_API_VERIFY_MODE=strict`

### Edge Cases
- **Ferguson returns partial batch**: Update available SKUs, leave others stale
- **Apify free tier exhausted**: Mark retail_benchmark feed as degraded, do not fail sync
- **No price change**: No alert created, no price_history row written
- **Multiple feeds for same item**: Highest confidence wins, but all are stored for audit

---

## 6. Risks & Rollback

| Risk | Likelihood | Mitigation |
|------|------------|------------|
| Ferguson API response shape differs from docs | Medium | `lenient` mode falls through; extensive sandbox testing in Phase 1 |
| Ferguson blocks scraper with CAPTCHA | Medium | Respect robots.txt, use browser-like headers, rate limit; simulation remains final fallback |
| Apify free tier runs out mid-sync | High | Track credits in health; skip retail benchmark when depleted |
| Retail inference is off by category | Medium | Make multipliers admin-configurable per category |
| Alert spam on first sync | Medium | Only alert on delta > threshold; suppress alerts for brand-new items |

**Rollback**: All changes are additive. Disable Ferguson API by setting `FERGUSON_API_VERIFY_MODE=off`. Disable retail benchmark by removing it from the registry. Revert is a config change, not a code deploy.

---

## 7. Effort Estimate

| Phase | Hours | Files |
|-------|-------|-------|
| Phase 1 — Ferguson API Verification | 6–8 | 5 |
| Phase 2 — Retail Benchmarking | 6–8 | 4 |
| Phase 3 — Price Alerts & Feed Admin | 6–7 | 7 |
| Phase 4 — Worker Integration | 3–4 | 3 |
| Phase 5 — Testing & Docs | 4–5 | 6 |
| **Total** | **25–32 hours** | **~25 files** |

---

## 8. Success Criteria

- [ ] Ferguson API returns real prices in development when credentials are configured
- [ ] Ferguson scraper fallback returns prices when API is disabled
- [ ] Retail benchmark adapter covers 100+ canonical items with stable Apify URLs
- [ ] Wholesale inference is within ±10% of known DFW wholesale prices for test sample
- [ ] Price alerts create DB rows when cost changes > threshold
- [ ] Admin can view and acknowledge price alerts in the UI
- [ ] Admin can trigger manual feed sync and see task status
- [ ] All new tests pass; total API test suite ≥ 1,520 passing
- [ ] Documentation exists for Ferguson credentials and Apify URL catalog
