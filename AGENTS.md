# Tycherion Agent Instructions

## GitHub scope

Repo: HenriqueCotta/Tycherion  
Project (Projects v2): Tycherion Board  
Project owner: HenriqueCotta  

## Task contract

A "task" means:

- a GitHub Issue in the repo, and/or Issue in the Project.

Creating a task always performs both steps (Issue + Project item) and sets Project fields.

## Allowed Project fields

Status: Backlog | Todo | In Progress | Blocked | In Review | Done  
Type: Epic | Feature | Refactor | Bug | Spike | Chore  
Area: Domain | Application | Adapters | Infra/Observability  

No new options are created.

## Operating rules (intent-based)

Interpret the user request by intent (phrasing and language do not matter).

### Create

Create a task:

1) Create Issue.
2) Add Issue to Project.
3) Set fields:
   - Status = inferred ("To Do" if unclear)
   - Type = inferred (Feature if unclear)
   - Area = inferred (leave empty if unclear)
4) Avoid duplicates: search similar open issues before creating tell the user if duplicate is found or not.

### Move

Move a task:

1) Identify by issue number; otherwise by title; otherwise fuzzy match.
2) Update Project Status to the requested value (if nor clear, must be inferred).

### Update

Update a task:

- Update Issue title/body/checklists.
- Keep Project fields consistent with the update.

### List

List tasks:

- Default output groups Project items by Status.
- Apply filters by Status/Type/Area when asked.

## Inference

Type:

- Bug: failure/regression/incorrect behavior
- Spike: investigation/unknown scope
- Refactor: refactor/cleanup/maintenance of internals
- Chore: routine/non-product work

## Safety rails

- Never delete issues or project items.
- If a requested Status/Type/Area is invalid, list valid options and choose the closest match.
- If task identification is ambiguous, present top 3 candidates and proceed with the best match if the user confirms; otherwise ask a single clarifying question.
