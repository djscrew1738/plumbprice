# PlumbPrice AI App Shell Refresh

Date: 2026-03-29
Status: Proposed

## Goal

Redesign the app shell around a mobile-first field workflow that lets plumbers start pricing work immediately, then expand that same workflow into a clearer desktop estimating environment.

The shell should:

- Prioritize fast quote creation and job file intake on mobile
- Keep recent work easy to resume from the home screen
- Preserve one unified pricing workspace instead of splitting the product into disconnected tools
- Extend cleanly to desktop without turning into a different product

This redesign must fit inside the existing Next.js frontend, current routes, and current backend contracts.

## Product Direction

The shell should stop behaving like a tool-heavy dashboard and instead behave like a field launcher into one pricing workspace.

The main promise of the shell is simple:

- Start a quick quote
- Upload photos, PDFs, or other job files
- Resume recent pricing work

Everything else should become secondary support navigation.

## Recommended Approach

Use a field-first launcher shell.

Why this approach:

- It matches the user's stated mobile priorities: `Quick Quote` and `Upload Job Files`
- It removes the current friction of dropping users into a dense chat dashboard
- It gives mobile users a faster first decision on jobsites
- It still scales into a wider desktop workspace without rethinking the product model

Alternative directions such as a full command-center shell or jobs-inbox-first shell are less aligned with the immediate mobile-first behavior the user wants.

## Information Architecture

### Mobile-First Structure

Mobile becomes the primary design constraint.

The home screen should contain:

- Slim top bar with current market or county, active job context when present, and a lightweight account or menu trigger
- Main launcher region with two large primary action cards:
  - `Quick Quote`
  - `Upload Job Files`
- `Recent Jobs` section below the launcher for resumable work
- Reduced bottom navigation:
  - `Home`
  - `Jobs`
  - `Pipeline`
  - `More`

`Suppliers` and `Admin` should move out of the primary mobile tab bar and live under `More`.

### Desktop Expansion

Desktop should preserve the same core workflow rather than becoming a different product.

The desktop shell should expand into three regions:

- Left rail for navigation and recent jobs
- Center workspace for quote creation, uploads, and assistant interaction
- Right rail for pricing summary, assumptions, confidence, and next actions

The two primary launcher actions should remain visible near the top of the desktop workspace, but they can sit side by side instead of stacking vertically.

## Core User Flow Model

Every entry point in the shell should lead into the same pricing workspace.

### Quick Quote

`Quick Quote` should open a focused pricing route instead of the current chat-first shell.

The workspace should include:

- County or market controls near the top
- Prompt composer positioned for fast use on mobile
- Estimate artifact displayed as the main output once pricing returns
- Transcript preserved as supporting context rather than the dominant visual structure

### Upload Job Files

`Upload Job Files` should open a dedicated intake flow that prioritizes:

- Camera
- Photo library
- File picker

After files are attached, the user should land in the same pricing workspace used by `Quick Quote`, so the app retains one mental model.

### Recent Jobs

`Recent Jobs` should behave as resumable active work, not passive history.

Each item should surface operational state directly, such as:

- `Awaiting details`
- `Files processing`
- `Estimate ready`

When available, each row should also expose recent activity timing and a visible draft or estimate-total signal.

## App Shell Design

### Mobile Shell

The mobile home screen should be a launcher, not a dashboard and not a direct drop into the old estimator page.

Key design behaviors:

- One-handed-friendly spacing and tap targets
- Large, sturdy action cards with concise helper text
- Recent jobs visually subordinate to the two primary actions
- Clear state visibility without hunting through headers or hidden menus

The top bar should stay slim and operational rather than decorative.

### Desktop Shell

Desktop should feel like the same product after mobile, only with more simultaneous visibility.

Key behaviors:

- Narrow left rail instead of a dominant dashboard sidebar
- Center workspace remains the main decision surface
- Persistent right rail only for useful summary information
- Slim status bar header with county or market, active job, and session context

Pages such as `Saved Estimates`, `Pipeline`, `Suppliers`, and `Admin` should inherit the new shell language, but only the workspace should use the full three-region layout.

## Visual Direction

The current dark glass styling should be replaced with a warmer industrial system.

Visual rules:

- Light canvas by default
- Warm off-white, sand, slate, and steel as the base palette
- One assertive accent color for AI and action states
- Larger, more editorial typography
- Stronger hierarchy with fewer micro-labels
- Rounded rectangles instead of soft pills for primary controls
- Reduced use of dark overlays, glass effects, and decorative glow

Target impression:

- Jobsite-ready quoting tool
- Estimating desk
- Professional bid software

Avoid:

- Crypto dashboard styling
- Neon-heavy gradients
- Low-contrast glass cards
- Bottom nav patterns that feel generic or consumer-app-like

## Component Model

The refreshed shell should consolidate around a smaller set of reusable layout components.

Primary shell components:

- `AppShell`
- `LauncherHome`
- `PrimaryActionCard`
- `RecentJobsList`
- `WorkspaceHeader`
- `WorkspaceEntryBar`
- `SummaryRail`
- `MoreSheet`

The current estimator transcript and estimate breakdown concepts can remain, but they should be reframed as workspace artifacts inside the new shell instead of living inside the current dark chat layout.

## Data And State Strategy

The redesign should avoid requiring backend contract changes as a first step.

Frontend expectations:

- Reuse existing estimator and chat pricing flows for `Quick Quote`
- Route upload-led flows into the same workspace state after intake
- Derive recent-job states from existing saved estimate or job metadata where possible
- Preserve the existing secondary pages while applying the new shell and visual system

If some upload-led workflows are only partially wired, the UI may ship with transparent progressive disclosure as long as the shell does not imply unsupported behavior.

## Error Handling And System States

Shell-level state must be visible inline, not hidden behind toasts.

Requirements:

- Jobs with file uploads in progress must show processing state directly in `Recent Jobs`
- Quote failures must render inline recovery UI with clear retry paths
- Missing information should appear as concrete follow-up requests in the workspace
- Empty states must explain the two primary starting paths: quick pricing or file upload
- Unsupported or incomplete flows must be framed honestly with guided messaging

Desktop can express these same states more persistently in the job list and summary rail, but the state model should remain consistent across breakpoints.

## Testing

The implementation should verify both shell structure and critical workflow entry points.

At minimum, testing should cover:

- Mobile launcher rendering with the two primary actions visible
- Navigation behavior for `Home`, `Jobs`, `Pipeline`, and `More`
- Recent job state rendering for resumable statuses
- Quick quote entry into the unified workspace
- Upload entry into the unified workspace
- Desktop layout expansion into left rail, center workspace, and right summary rail

## Out Of Scope

This shell refresh does not require:

- Backend pricing contract changes
- A full blueprint workflow redesign beyond shell-level entry and state framing
- Functional redesign of admin or supplier capabilities beyond adopting the new shell system
