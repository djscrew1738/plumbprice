# PlumbPrice AI 3.1 Foundation Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Build the first real 3.1 foundation slice by adding opportunity pipeline visibility and immutable estimate version workflow to the existing product.

**Architecture:** Reuse the current `projects` and `estimates` models instead of inventing parallel entities. Extend the API so every persisted estimate creates a version snapshot, expose version and pipeline endpoints, and add a new pipeline-first UI surface in the Next.js app so users can manage jobs and estimates instead of only generating quotes.

**Tech Stack:** FastAPI, SQLAlchemy async ORM, pytest, Next.js App Router, React, TypeScript, axios.

---

### Task 1: Add failing API tests for estimate versioning and project pipeline

**Files:**
- Modify: `api/tests/conftest.py`
- Create: `api/tests/routers/test_estimates.py`
- Create: `api/tests/routers/test_projects.py`

**Step 1: Write the failing test**

Add tests that prove:
- creating a chat-backed estimate also creates version `1`
- listing estimate versions returns immutable snapshot data
- creating a project returns a lead-stage pipeline item
- listing projects can be filtered by pipeline status

Example test targets:

```python
async def test_chat_estimate_creates_initial_version(...):
    ...

async def test_list_estimate_versions_returns_snapshot_history(...):
    ...

async def test_create_project_defaults_to_lead_pipeline_status(...):
    ...

async def test_list_projects_filters_by_status(...):
    ...
```

**Step 2: Run test to verify it fails**

Run:

```bash
. .venv-prodcheck/bin/activate && pytest -q api/tests/routers/test_estimates.py api/tests/routers/test_projects.py
```

Expected:
- FAIL because routes or behavior do not exist yet

**Step 3: Write minimal implementation**

Implement only the fields and routes required to satisfy the tests:
- project create/list routes
- estimate version creation on persistence
- estimate version list endpoint

**Step 4: Run test to verify it passes**

Run:

```bash
. .venv-prodcheck/bin/activate && pytest -q api/tests/routers/test_estimates.py api/tests/routers/test_projects.py
```

Expected:
- PASS

**Step 5: Commit**

```bash
git add api/tests/conftest.py api/tests/routers/test_estimates.py api/tests/routers/test_projects.py api/app/routers/estimates.py api/app/routers/projects.py api/app/services/estimate_service.py api/app/schemas/estimates.py api/app/schemas/projects.py api/app/models/projects.py api/app/main.py
git commit -m "feat: add estimate versioning and project pipeline api"
```

### Task 2: Persist immutable estimate versions

**Files:**
- Modify: `api/app/services/estimate_service.py`
- Modify: `api/app/models/estimates.py`
- Modify: `api/app/schemas/estimates.py`
- Modify: `api/app/routers/estimates.py`

**Step 1: Write the failing test**

Add a test that verifies:
- the first saved estimate gets version `1`
- each later published revision creates a new immutable snapshot
- the snapshot includes totals, assumptions, sources, county, preferred supplier, and line items

**Step 2: Run test to verify it fails**

Run:

```bash
. .venv-prodcheck/bin/activate && pytest -q api/tests/routers/test_estimates.py::test_list_estimate_versions_returns_snapshot_history
```

Expected:
- FAIL because snapshot creation or listing is incomplete

**Step 3: Write minimal implementation**

Implement:
- helper to build snapshot JSON from an `Estimate` and its line items
- automatic version `1` creation during `persist_estimate`
- endpoint `GET /api/v1/estimates/{estimate_id}/versions`

**Step 4: Run test to verify it passes**

Run:

```bash
. .venv-prodcheck/bin/activate && pytest -q api/tests/routers/test_estimates.py::test_list_estimate_versions_returns_snapshot_history
```

Expected:
- PASS

**Step 5: Commit**

```bash
git add api/app/services/estimate_service.py api/app/models/estimates.py api/app/schemas/estimates.py api/app/routers/estimates.py api/tests/routers/test_estimates.py
git commit -m "feat: persist immutable estimate versions"
```

### Task 3: Add project pipeline API

**Files:**
- Create: `api/app/routers/projects.py`
- Create: `api/app/schemas/projects.py`
- Modify: `api/app/main.py`
- Modify: `api/app/models/projects.py`
- Test: `api/tests/routers/test_projects.py`

**Step 1: Write the failing test**

Add tests for:
- `POST /api/v1/projects`
- `GET /api/v1/projects`
- filtering by `status`
- lightweight pipeline summary counts

**Step 2: Run test to verify it fails**

Run:

```bash
. .venv-prodcheck/bin/activate && pytest -q api/tests/routers/test_projects.py
```

Expected:
- FAIL because router and schema do not exist yet

**Step 3: Write minimal implementation**

Implement:
- project create request schema
- project list response schema
- project summary response with counts by stage
- router registration in `app.main`

**Step 4: Run test to verify it passes**

Run:

```bash
. .venv-prodcheck/bin/activate && pytest -q api/tests/routers/test_projects.py
```

Expected:
- PASS

**Step 5: Commit**

```bash
git add api/app/routers/projects.py api/app/schemas/projects.py api/app/main.py api/app/models/projects.py api/tests/routers/test_projects.py
git commit -m "feat: add project pipeline endpoints"
```

### Task 4: Add frontend pipeline dashboard page

**Files:**
- Create: `web/src/app/pipeline/page.tsx`
- Create: `web/src/components/pipeline/PipelinePage.tsx`
- Modify: `web/src/components/layout/Sidebar.tsx`
- Modify: `web/src/components/layout/Header.tsx`
- Modify: `web/src/lib/api.ts`
- Modify: `web/src/types/index.ts`

**Step 1: Write the failing test**

If test harness is unavailable, use build verification as the executable contract:
- page compiles
- API types line up
- pipeline columns render from fetched project data

**Step 2: Run test to verify it fails**

Run:

```bash
cd web && npm run build
```

Expected:
- FAIL while the new page/API types are incomplete

**Step 3: Write minimal implementation**

Implement:
- new `Pipeline` nav entry
- pipeline page with columns for `lead`, `estimate_sent`, `won`, `lost`
- project cards showing customer, county, job type, estimate count, and latest value
- summary strip using pipeline counts from API

**Step 4: Run test to verify it passes**

Run:

```bash
cd web && npm run lint && npm run build
```

Expected:
- PASS

**Step 5: Commit**

```bash
git add web/src/app/pipeline/page.tsx web/src/components/pipeline/PipelinePage.tsx web/src/components/layout/Sidebar.tsx web/src/components/layout/Header.tsx web/src/lib/api.ts web/src/types/index.ts
git commit -m "feat: add pipeline dashboard"
```

### Task 5: Connect pipeline to estimate detail surfaces

**Files:**
- Modify: `web/src/components/estimates/EstimatesListPage.tsx`
- Modify: `web/src/components/estimator/EstimatorPage.tsx`
- Modify: `web/src/lib/api.ts`

**Step 1: Write the failing test**

Use build verification to prove:
- estimate rows can link to version history
- estimator responses can carry created project/estimate metadata if present

**Step 2: Run test to verify it fails**

Run:

```bash
cd web && npm run build
```

Expected:
- FAIL if types or links are incomplete

**Step 3: Write minimal implementation**

Implement:
- “View versions” entry from estimates list
- project/estimate metadata cards in estimator side panel when available

**Step 4: Run test to verify it passes**

Run:

```bash
cd web && npm run lint && npm run build
```

Expected:
- PASS

**Step 5: Commit**

```bash
git add web/src/components/estimates/EstimatesListPage.tsx web/src/components/estimator/EstimatorPage.tsx web/src/lib/api.ts
git commit -m "feat: connect estimates to pipeline workflow"
```

### Task 6: Run full verification for the foundation slice

**Files:**
- Modify: none

**Step 1: Run backend verification**

```bash
. .venv-prodcheck/bin/activate && pytest -q api/tests
```

Expected:
- PASS

**Step 2: Run frontend verification**

```bash
cd web && npm run lint && npm run build
```

Expected:
- PASS

**Step 3: Run compose validation**

```bash
docker compose config -q
```

Expected:
- PASS

**Step 4: Commit verification-only state if needed**

```bash
git status --short
```

Expected:
- only intentional files changed

**Step 5: Commit**

```bash
git add -A
git commit -m "feat: ship 3.1 foundation slice"
```
