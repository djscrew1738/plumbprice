# ADR-002: PWA Offline Architecture for Field Techs

**Status:** Accepted  
**Date:** 2026-06-05  
**Version:** 4.1.0

---

## Context

Field plumbing technicians visit job sites where mobile connectivity is unreliable (older homes with thick walls, basements, rural DFW fringe areas). They need to:
1. Capture photos of plumbing issues
2. Create a draft estimate
3. Reference the customer's address and job notes

All of this must work with zero internet connectivity. Results must sync automatically when connectivity is restored, without data loss.

The existing Next.js app has:
- `outbox.ts` — Dexie/IndexedDB outbox queue (already written, gated behind `flag:outbox_offline` localStorage flag)
- `withRetry.ts` — exponential backoff for mutations
- `useOnlineStatus.ts` — `navigator.onLine` hook
- No PWA manifest or service worker yet

---

## Decision

### PWA Setup

We use **next-pwa** (or a hand-rolled service worker if `next-pwa` conflicts with Turbopack) to register a service worker.

Cache strategy:
```
/field/*            → NetworkFirst (try network, fall back to cache)
/field/photo        → CacheFirst (shell only — photos are IndexedDB)
/offline            → CacheOnly (pre-cached fallback page)
fonts, icons, JS    → StaleWhileRevalidate
API calls           → NetworkOnly (never cache API responses in SW)
```

### Offline Estimate Storage

Photos captured offline are stored in **IndexedDB** (via Dexie) as base64 blobs under a `offline_photos` table with a `session_id` key.

Draft estimates created offline are stored in the existing `outbox` Dexie table with `type: "estimate_create"` and full payload.

### Sync Strategy

We use the **Background Sync API** (`ServiceWorkerRegistration.sync.register("outbox-sync")`) where available. For browsers that don't support Background Sync, the app falls back to syncing on `navigator.onLine` = true (via `useOnlineStatus` hook triggering a flush).

**Conflict resolution:** The server always wins on conflict. If the same estimate ID was modified both offline and online, the server version is kept and the user is shown a conflict banner.

### Field Tech Role Boundary

The `/field` route section is only accessible to users with `role = "field_tech"` or `role = "admin"`. Other roles are redirected to the main app.

On login, `field_tech` users are redirected to `/field` automatically by the auth middleware.

### Push Notifications

Push notifications use the **Web Push** standard (VAPID). The push subscription endpoint is stored in `push_subscriptions` table and sent from `push_service.py` using `pywebpush`.

Push events trigger on:
- New job assignment (from dispatcher/admin)
- Price alert (supplier price changed >10%)
- Estimate approved by customer (via customer portal)

Push is degraded gracefully on iOS < 16.4 (no Web Push support) — users see in-app notifications only.

---

## Consequences

**Positive:**
- Field techs can work in zero-connectivity environments
- Photos and draft estimates are never lost
- Push notifications remove the need to manually check for new job assignments

**Negative:**
- Service worker caching adds build complexity and potential cache staleness bugs
- Offline estimate sync requires careful conflict resolution UI
- iOS Push support is still maturing (16.4+ required) — some field techs may need to update iOS

**Neutral:**
- `flag:outbox_offline` is enabled by default on `/field` routes, but disabled elsewhere to prevent accidental offline queuing on the estimator
- The `/field` PWA section is intentionally separate from the main estimator UI — mobile-optimized with 44px tap targets and no sidebar

### Offline Data Boundaries

We do NOT cache:
- Estimate pricing data (could become stale)
- Supplier product catalog (too large)
- Admin data

We DO cache:
- App shell (layout, navigation, fonts)
- Today's job list (synced on last online visit)
- Labor template codes (small, rarely changes)
- DFW county list (static)
