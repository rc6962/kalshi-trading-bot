# Session Startup Prompt

This file is manually provided (via @-mention) at the start of a new
session and should be treated as authoritative onboarding instructions,
regardless of whether other rule files were automatically loaded. If
`rules.md` or a global AGENTS.md were also auto-loaded, treat this as
reinforcement, not a conflicting source.

## Startup Reading Order
Read these in order before doing anything else:
1. `.rules.md`
2. `ai/handoff.md`
3. `ai/decisions.md` 
4. `ai/kalshi-knowledge.md` — this contains accumulated
   domain knowledge about how Kalshi prediction markets actually work
   in practice. Treat it as required reading, not optional background.
5. `ai/KALSHIMASTERAPIINDEX.md`

## Required Confirmation
Before making any code changes, confirm all of the following in this
exact format:

**Files read:**
- List each file you actually read.

**Project understanding:**
- Confirm you have the most up-to-date handoff information, and state
  the timestamp of the last entry in `ai/handoff.md` (i.e. when the
  last bot/session worked on this).

**Current task:**
- Restate the task in your own words in a short, concise paragraph.

**Previous and next step:**
- State the last action that was completed (per `ai/handoff.md`) and
  what the next expected action is, from both you and me.

**Risks:**
- List any obvious risks, unknowns, or areas that could affect trading
  logic, execution behavior, config, or state handling.

**Kalshi API Reference Check:**
- Confirm you have reviewed the Announcements API, Exchange Status API,
  and OpenAPI spec in `ai/` (see section below). This is an
  agent onboarding step — the bot does not need to call these at runtime.

**Acknowledgement:**
- Confirm you have read all the `.md` files you need to.
- Confirm you have access to the `ai/` folder if needed.
- Confirm you are ready to proceed.

If any expected file does not exist, say so clearly instead of
pretending it was read. If you are unsure of anything, ask me at this
point instead of guessing. If you are fully comfortable with the
current condition of the project and your responsibilities and next
steps, confirm that to me in your own words.

Also tell me any relevant parameters, abilities, thinking modes, web
access, tool-calling capability, or anything else I may need to know
in order to use you effectively this session.

## Kalshi API Reference Check (Agent Onboarding)
This is a **documentation review only** — do not make live API calls
to Kalshi during onboarding unless I explicitly ask you to.

When you read this file, also review the following in `ai/` to refresh
your understanding of how the exchange behaves, in case anything has
changed since your last session:
- **KALSHIMASTERAPIINDEX.md** — master index of all endpoints
- **kalshi-knowledge.md** — domain knowledge about Kalshi markets
- **OpenAPI Spec** (`Kalshi-Docs/API/kalshi_openapi.yaml`) — reference
  for any new endpoints or schema changes.

These are static reference materials for your own understanding — the
bot does NOT call these live at runtime unless explicitly configured
to do so, and you should not call them live during onboarding either.

## Critical Rule: Bot Startup Policy
- **NEVER start `main.py` unless the user explicitly tells you to.**
  This is the most important rule in this file.
- You may tail logs, watch the bot, and report issues, but do NOT
  launch the bot yourself.
- Only the user may start `main.py`. If the bot is down and you think
  it should be running, ask the user for permission first and wait for
  a clear yes before doing anything.
