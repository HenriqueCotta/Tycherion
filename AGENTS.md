# Tycherion Agent Instructions

## GitHub scope

Repo: HenriqueCotta/Tycherion  
Project): Tycherion Board  
Project owner: HenriqueCotta  

## Task contract

A "task" means:

- a GitHub Issue in the repo, and
- the same Issue added as an item in the Project.

Creating a task always performs both steps (Issue + Project item) and sets Project fields.

## Allowed Project fields

Status: Backlog | To do | In Progress | Blocked | In Review | Done  
Type: Epic | Feature | Refactor | Bug | Spike | Chore  
Area: Domain | Application | Adapters | Infra/Observability  

No new options are created.

## Operating rules (intent-based)

Interpret the user request by intent (phrasing and language do not matter).

### Create

Create a task:

1) Search for duplicates (open issues + project items) using title keywords and close variants.
   - If a likely duplicate exists, tell the user and reference it.
   - If the user confirms it's not a duplicate, proceed.
2) Create Issue with a professional, concise, context-appropriate structure (see "Issue writing principles").
3) Add Issue to Project.
4) Set fields:
   - Status = inferred (To do if unclear)
   - Type = inferred (Feature if unclear)
   - Area = inferred (leave empty if unclear)
   - Sub-issues progress (if applicable by request or inference)
5) Use GitHub-native planning/tracking features opportunistically when they reduce friction or improve clarity.
   - Prefer what exists in the current GitHub UI/API for this repo/org.
   - If unsure what is available, query via GitHub MCP rather than assuming.
6) If the work spans multiple steps, propose splitting into smaller tasks and/or creating a higher-level tracking item.

### Move

Move a task:

1) Identify by issue number; otherwise by title; otherwise fuzzy match.
2) Update Project Status to the requested value.
   - If unclear, infer the closest Status.
   - If still ambiguous, present top 3 candidate statuses and ask a single clarifying question.

### Update

Update a task:

- Update Issue as needed, but still following the current pattern.
- Keep Project fields consistent with the update.
- If scope changed materially, reflect it in what "done" means and what must be verified.

### List

List tasks:

- Default output groups Project items by Status.
- Apply filters by Status/Type/Area when asked.
- When listing "what's next", prefer To do + Blocked with a short reason.

## Issue writing principles (adaptive, not a fixed template)

Write issues in Markdown. The structure adapts to task type and complexity.
Include only what improves execution clarity. Avoid boilerplate.

### Always include (minimum viable issue)

- **Goal/Outcome**: what will be true when done (1–2 sentences).
- **Why/Context**: why it matters (short).
- **Acceptance Criteria**: objective checks (prefer checkboxes when useful).
- **Verification**: how to validate (tests, steps, or evidence).

### Include when relevant (choose based on context and can add other topics that are not listed in here when needed, requested or when you see it will benefit the development of the task)

- **Scope boundaries**: in-scope vs out-of-scope.
- **Constraints/assumptions**: performance, compatibility, security, time/risk constraints.
- **Implementation notes**: suggested approach, likely files/areas, architecture constraints (Domain stays pure).
- **Observability/telemetry**: logs/metrics/traces/events to add or confirm.
- **Risks/rollout**: failure modes, migration steps, safe deployment notes.
- **Dependencies**: prerequisites, blocked-by links, external waiting items.
- **Task breakdown**: sub-steps as a checklist or child tasks when size is large.

### Professional writing style

- Titles are verb-first and outcome-specific.
- Bullets over paragraphs. Keep it skimmable.
- Prefer objective language over opinions.
- Link to existing code/docs/issues when known.

## Continuous best-practices behavior (future-proof)

- Prefer GitHub's current recommended workflows and built-in capabilities that fit the moment.
- Do not hardcode assumptions about GitHub features; discover availability via MCP if needed.
- Use whichever GitHub-native primitives best express the work (tracking, linking, grouping, automation,...) without introducing new field options or taxonomy unless requested.

## Inference

Type:

- Bug: failure/regression/incorrect behavior
- Spike: investigation/unknown scope
- Refactor: refactor/cleanup/maintenance of internals
- Chore: routine/non-product work

Status:

- Backlog: acknowledged but not planned yet
- To do: ready to be picked up
- In Progress: actively being worked
- Blocked: waiting on something external/internal
- In Review: PR/review/verification stage
- Done: completed/merged/shipped as appropriate

## Clarifying questions policy

Ask questions only when missing information would likely cause rework.

- Prefer at most 3 questions in one message.
- If the user provides partial info, create the issue with placeholders and a short "Open Questions" section instead of blocking.
- When splitting work: suggest 1–3 options and let the user pick.

## Safety rails

- Never delete issues or project items.
- If a requested Status/Type/Area is invalid, list valid options and choose the closest match.
- If task identification is ambiguous, present top 3 candidates and proceed with the best match if the user confirms; otherwise ask a single clarifying question.
