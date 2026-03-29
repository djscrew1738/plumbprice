# PlumbPrice AI Pricing Assistant Redesign

Date: 2026-03-29
Status: Proposed

## Goal

Reposition the web app from a dark multi-tool dashboard into a unified pricing assistant that feels credible for field service pricing and capable for blueprint-driven estimating.

The redesigned product should be:

- Beautiful: high-contrast, intentional, premium, and distinctive without feeling decorative
- Simple: one primary workflow instead of multiple competing entry points
- Effective: the interface should help the user understand what the AI priced, what evidence it used, and where uncertainty remains

This redesign must work within the existing Next.js app, current API contracts, and current Docker-based deployment model for `https://app.ctlplumbingllc.com`.

## Product Positioning

The app becomes a single pricing workspace for three estimating motions:

- Repair pricing
- Blueprint pricing
- Floorplan pricing

These are not separate products. They are modes of the same assistant.

The assistant is responsible for:

- Accepting natural-language requests and uploaded job artifacts
- Extracting scope from files and descriptions
- Producing estimate outputs with clear assumptions and confidence
- Letting the user inspect price construction before saving or sharing the result

## UX Direction

### Recommended Approach

Use a command-center layout with one unified workspace.

Why this approach:

- It matches the actual product story better than the current tool-first navigation
- It reduces cognitive load by giving the user one clear starting point
- It supports both quick repair quotes and document-heavy blueprint jobs
- It can be implemented as a frontend-heavy redesign without requiring backend re-architecture first

### Visual Character

The current UI uses dark glass patterns, small controls, and repeated pill/card styling. The redesign should move to a warmer, more editorial industrial aesthetic.

Design principles:

- Light workspace with dark ink text as the default
- Warm off-white, stone, slate, and steel as the main palette
- One assertive accent color for AI and action states
- Larger type and stronger spacing rhythm
- Fewer borders, more panel definition through tone and shadow
- Results rendered as structured artifacts, not only chat bubbles

Target impression:

- Estimating desk
- Construction spec sheet
- Professional bid software

Avoid:

- Crypto dashboard styling
- Neon gradients as the main identity
- Overuse of translucent glass effects
- Tiny chips and low-contrast labels

## Information Architecture

### Primary Navigation

Reduce the app to one dominant destination and a small set of support destinations.

Primary destinations:

- Workspace
- Saved Estimates
- Pipeline

Secondary destinations:

- Suppliers
- Admin

Blueprints and proposals should no longer read as separate top-level product silos in the main navigation. Those capabilities should surface inside the workspace and estimate detail flows.

### Workspace Model

The `Workspace` page is the main landing experience and replaces the current feel of a chat-only estimator page.

Workspace regions:

- Left rail: navigation, recent jobs, quick project switching
- Center canvas: assistant interaction, upload targets, estimate generation flow
- Right rail: live pricing summary, extracted scope, assumptions, confidence, and next actions

Mobile behavior:

- Left rail collapses into sheet navigation
- Center canvas remains primary
- Right rail becomes a docked bottom summary panel or stacked section

## Core User Flows

### 1. Repair Pricing

The user asks a service-style question in natural language.

The interface should:

- Default to a concise prompt composer with example service jobs
- Show location/context controls near the prompt, not buried in a header
- Return a structured estimate card with total, range, confidence, assumptions, and breakdown
- Keep the conversational transcript visible but secondary to the estimate artifact

### 2. Blueprint Pricing

The user uploads PDFs or plan images and asks for pricing.

The interface should:

- Present upload affordances prominently when `Blueprint` mode is selected
- Show uploaded files and processing states inline in the conversation area
- Render extracted scope in readable sections such as fixtures, piping, labor, and open questions
- Keep the right rail synced with totals and confidence as blueprint analysis progresses

### 3. Floorplan Pricing

The user uploads or describes a floorplan and wants rough-in/finish pricing.

The interface should:

- Guide the user to describe job type, building size, fixture count, and finish level if those details are missing
- Show the AI’s interpreted room/fixture model before final pricing
- Emphasize editable assumptions because floorplan-only pricing is often approximate

## Page-Level Design

### App Shell

Change the shell from dark fixed panels to a high-clarity workspace shell.

Changes:

- Replace the current black background with a warm neutral canvas
- Narrow and simplify the sidebar
- Turn the header into a slim project/status bar instead of a dense top nav
- Use a persistent desktop summary rail only where it adds value

### Workspace Page

This page is the flagship redesign.

Sections:

- Hero-level workspace intro when empty
- Mode switcher for `Repair`, `Blueprint`, `Floorplan`
- Prompt composer with upload support and smart example prompts
- Transcript with assistant artifacts
- Sticky summary rail with price, range, confidence, assumptions, and extracted quantities

Artifacts in the transcript should include:

- Estimate cards
- Assumption cards
- File-processing states
- Extraction summaries
- Follow-up questions

### Saved Estimates

The estimates page should feel like a work queue, not a generic list.

Changes:

- Introduce a clearer title and summary stats
- Use denser but more legible rows/cards
- Surface estimate type, county, confidence, created date, and total more clearly
- Improve scanability for recent operational use

### Pipeline

Keep the page, but visually subordinate it to the main pricing workflow.

Changes:

- Match the new neutral palette and typography
- Preserve functional data
- Remove visually loud card treatments that compete with the workspace

### Suppliers and Admin

These should inherit the new visual system but remain utility pages.

Changes:

- Keep existing capabilities
- Reduce decorative styling
- Align controls, spacing, and form patterns with the workspace system

## Component Design

### New or Heavily Revised Components

- `WorkspaceShell`
- `ModeSwitcher`
- `PromptComposer`
- `UploadDropzone`
- `AssistantArtifactCard`
- `EstimateSummaryRail`
- `RecentJobsRail`
- `ConfidencePanel`
- `AssumptionsPanel`

### Design System Rules

- Favor rounded rectangles over pills for primary controls
- Reserve accent color for action, active mode, and AI emphasis
- Use strong typography hierarchy instead of many micro-labels
- Inputs should feel like workspace tools, not chat bubbles
- Motion should emphasize state change and reveal, not constant decoration

## Data and State Flow

The redesign should avoid requiring backend contract changes as a first step.

Frontend strategy:

- Reuse the existing chat pricing endpoint for `Repair` mode
- Add UI states for file upload and extracted artifacts using the existing and near-future blueprint routes
- Keep the estimate summary rail derived from the latest assistant estimate response
- Store current mode and active job context in page state

If some blueprint/floorplan workflows are not fully wired yet, the interface may ship with progressive disclosure:

- Fully functional repair pricing
- Blueprint upload flow visible and partially connected if backend support is incomplete
- Floorplan mode framed as guided estimating with transparent “AI needs more detail” prompts where necessary

This is acceptable as long as the UI makes capability boundaries explicit and does not fake unsupported behavior.

## Error Handling

The interface must handle uncertainty and failures clearly.

Requirements:

- Upload states must show processing, success, and failure explicitly
- Pricing failures must appear inline in the workspace, not only as toasts
- Confidence must always be visible when an estimate is shown
- Missing information should trigger follow-up prompts with concrete requested inputs
- Empty states should explain what the assistant can price and what file formats it accepts

## Testing

Frontend verification should cover:

- Workspace render and mode switching
- Prompt composer interaction
- Estimate artifact rendering
- Responsive behavior of the shell and summary rail
- Estimates list regressions

Recommended testing scope for implementation:

- Add React component tests where test infrastructure exists
- At minimum, run lint and production build for the web app
- Manually verify desktop and mobile layouts in a browser before any production deployment

## Production Readiness Constraints

The redesign is only production ready if:

- The web app builds cleanly in production mode
- Existing routes continue to function
- The new workspace remains usable without blueprint uploads
- Contrast, touch targets, and keyboard focus states remain acceptable
- Layout regressions are checked on desktop and mobile widths
- Deployment configuration for `app.ctlplumbingllc.com` does not require undocumented infrastructure changes

Deployment to production should happen only after:

- Frontend implementation is complete
- Verification passes locally
- The deployment target and release steps are confirmed from the current environment

## Rollout Strategy

Implement as a frontend-first redesign in the existing app router structure.

Suggested sequence:

1. Replace the global visual system and app shell
2. Rebuild the estimator as the new workspace
3. Refresh saved estimates to match the new system
4. Restyle pipeline, suppliers, and admin for consistency
5. Verify responsive behavior and production build
6. Deploy using the existing production path

## Scope Boundaries

Included:

- Drastic UI/UX redesign of the Next.js frontend
- Unified workspace information architecture
- Revised estimator/workspace experience for repair, blueprint, and floorplan pricing
- Visual system update across major pages

Not included in this redesign spec:

- Backend pricing engine changes
- New blueprint extraction models
- Proposal generation redesign
- Authentication redesign
- Database schema changes unless required by separate implementation work

## Open Assumptions

- The current backend can continue serving repair pricing without contract changes
- Blueprint and floorplan workflows can be represented in the UI even if some backend capabilities are still partial
- Production deployment for `app.ctlplumbingllc.com` is based on the documented Docker path or an equivalent existing release workflow

These assumptions are acceptable for implementation planning, but deployment should verify the real release path before pushing production.
