# Bareeq (بريق) — instructions for Claude Code

Bareeq is a mobile car-wash-at-home booking product for a client in Cairo (areas: Nasr City, Obour, Madinaty).
The full product spec is in `docs/SPEC.md`. Read it fully before writing any code.
The visual identity is in `design/brand-kit/`.
`design/demo/index.html` is an old clickable demo of the customer booking flow (it uses an old placeholder name "لمعة"; the real name is "بريق"). Use it as a reference for the flow only.

## Stack (same as the owner's other product, MotionHR)
- Backend: Django + Django REST Framework + PostgreSQL. Folder `backend/`.
- Mobile: ONE Flutter app for all roles (customer, technician, manager). Folder `mobile/`.
- Manager web dashboard: Next.js. Folder `web/`.
- Arabic-first UI, right-to-left everywhere. Colors and logo from `design/brand-kit/` (see `05-Bareeq-Brand-Guide.pdf`). Arabic font: Cairo.

## How to work with the owner (John) — IMPORTANT
- John is an accountant, not a programmer. Explain everything in plain colloquial Egyptian Arabic, with no English technical jargon. Code, commands and file names stay in English.
- When he must run something himself, give ready-to-paste commands and ALWAYS say which window: "PowerShell on your PC (PS C:\)" or "the server window (john@srv...)". Never mix them in one block.
- Work in phases and steps. Every reply states: phase X of N, step Y of M.
- Do a whole step's work in as few pastes as possible (he finds one-tiny-step-per-reply far too slow), but always add a verification at the end.
- After each step, write a short summary covering this step and all previous steps, so he can save it if the chat ends.
- State findings as confirmed, or say clearly "I don't know yet" and how to find out. No vague hedging.
- If an output he pastes looks cut off or empty, ask him to resend it. Do not guess.
- Do ONLY what was asked. Do not widen the task on your own; propose extras and wait for a yes.
- Anything that changes real data or a live server: take a backup first, get his explicit approval, then verify after. Never touch the MotionHR server or its database for this project unless he explicitly asks.
- Do not mention AI tools in anything the client sees (app text, commit messages shown to the client, documents for the client).

## Engineering rules
- Every business number (prices, durations, buffers, minimum gap between orders, working hours, loyalty/referral/cashback rules, cancellation terms text) is a SETTING stored in the database and editable from the manager dashboard. Never hard-code them.
- Money: store as integer piastres (or Decimal), never float. Every wallet change is a ledger row (see SPEC).
- Write tests for scheduling (slot calculation) and wallet/ledger logic before UI work on them.
- Commit in small, clear commits. Keep secrets out of git (`.env` files, keys).
